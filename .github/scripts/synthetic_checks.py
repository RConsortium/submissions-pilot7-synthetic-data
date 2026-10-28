"""Independent structural/transport checks and measured synthetic-data findings."""

from collections import Counter
from datetime import date, timedelta
import csv
import json
import math
from pathlib import Path

import polars as pl
from lxml import etree


def raw_rows(base, group):
    with (base / 'data/odm/extracted' / f'{group.lower()}.csv').open(newline='') as handle:
        return list(csv.DictReader(handle))


def frame(base, domain, section='adam'):
    return pl.read_parquet(base / 'data' / section / f'{domain.lower()}-yamaa.parquet')


def measure(records, denominator, *, unit='records', note=None):
    subjects = sorted({r['USUBJID'] for r in records if r.get('USUBJID')})
    return {'count': len(records), 'denominator': denominator, 'unit': unit,
            'subject_count': len(subjects), 'subjects': subjects,
            'examples': records[:10], 'note': note}


def normalized(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def check_transport(parquet, xpt):
    """Read every XPT cell with pyreadstat, independently of the yamaa writer."""
    import pyreadstat

    source = pl.read_parquet(parquet)
    data, metadata = pyreadstat.read_xport(xpt, output_format='dict')
    if list(data) != source.columns or metadata.number_rows != source.height:
        raise ValueError(f'{xpt}: transport dimensions/order differ')
    checked = 0
    for name, typ in source.schema.items():
        for index, (expected, observed) in enumerate(zip(source[name].to_list(), data[name])):
            observed = normalized(observed)
            if typ == pl.String:
                equal = (expected or '') == (observed or '')
            elif expected is None:
                equal = observed is None
            elif isinstance(expected, float):
                equal = observed is not None and math.isclose(expected, observed, rel_tol=1e-12, abs_tol=1e-12)
            else:
                equal = expected == observed
            if not equal:
                raise ValueError(f'{xpt}: {name} row {index + 1} differs: {expected!r} / {observed!r}')
            checked += 1
    return checked


def check_define(root, base, section, domains):
    schema = etree.XMLSchema(etree.parse(str(root / '.github/schemas/cdisc/define/2.1/define2-1-0.xsd')))
    path = base / 'data' / section / 'define.xml'
    document = etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True))
    schema.assertValid(document)
    ns = {'o': 'http://www.cdisc.org/ns/odm/v1.3', 'd': 'http://www.cdisc.org/ns/def/v2.1',
          'x': 'http://www.w3.org/1999/xlink'}
    groups = document.findall('.//o:ItemGroupDef', ns)
    if {g.get('Name') for g in groups} != set(domains):
        raise ValueError(f'{path}: dataset inventory does not match the project')
    ids = {element.get('OID') for element in document.iter() if element.get('OID')}
    for element in document.iter():
        for name, value in element.attrib.items():
            if name in ['ItemOID', 'CodeListOID', 'MethodOID', 'ValueListOID'] and value not in ids:
                raise ValueError(f'{path}: unresolved {name}={value}')
    for leaf in document.findall('.//d:leaf', ns):
        href = leaf.get('{http://www.w3.org/1999/xlink}href')
        target = (path.parent / href).resolve()
        target.relative_to(base.resolve())
        if not target.is_file():
            raise ValueError(f'{path}: missing leaf target {href}')
    return {'status': 'passed', 'schema': 'CDISC Define-XML 2.1 XSD',
            'version': '2.1.0', 'datasets': len(groups), 'path': path.relative_to(root).as_posix()}


def check_datasets(root, study, declaration):
    base = root / study
    dm = frame(base, 'DM', 'sdtm')
    subjects = set(dm['USUBJID'].to_list())
    records = []
    for section in ['sdtm', 'adam']:
        from resolved_specs import specification_packet

        for relative in declaration[section]['specs']:
            path = base / 'spec/yamaa' / relative
            spec = specification_packet(root, path)['model']
            domain = spec['domain']
            parquet = base / 'data' / section / f'{domain.lower()}-yamaa.parquet'
            data = pl.read_parquet(parquet)
            if data.select(spec['keys']).is_duplicated().any():
                raise ValueError(f'{study}/{domain}: duplicate keys')
            if any(data[key].null_count() for key in spec['keys']):
                raise ValueError(f'{study}/{domain}: missing key values')
            if not set(data['USUBJID'].to_list()).issubset(subjects):
                raise ValueError(f'{study}/{domain}: subject not present in DM')
            if section == 'sdtm' and domain in ['DM', 'AE', 'EX', 'CM', 'DS', 'MH', 'XP']:
                source = raw_rows(base, 'TT' if domain == 'XP' else domain)
                if len(source) != data.height:
                    raise ValueError(f'{study}/{domain}: source row loss or duplication')
            if section == 'adam' and 'APPRFL' in data.columns and (data['APPRFL'] != 'N').any():
                raise ValueError(f'{study}/{domain}: unreviewed output claims approval')
            cells = check_transport(parquet, parquet.with_name(domain.lower() + '.xpt'))
            records.append({'domain': domain, 'section': section, 'rows': data.height,
                            'columns': data.width, 'keys': spec['keys'], 'build': 'succeeded',
                            'reference_comparison': 'unavailable', 'key_subject_checks': 'passed',
                            'xpt_roundtrip': 'passed', 'xpt_cells_checked': cells,
                            'spec': path.relative_to(root).as_posix(),
                            'parquet': parquet.relative_to(root).as_posix(),
                            'xpt': parquet.with_name(domain.lower()+'.xpt').relative_to(root).as_posix()})
    if set(frame(base, 'ADSL')['USUBJID'].to_list()) != subjects:
        raise ValueError(f'{study}: ADSL does not cover every source subject')
    return records


def check_source_trace(base):
    """Check collected values independently of the mapping specifications."""
    checked = 0
    for domain, fields in [('EX', ['EXTRT', 'EXDOSE', 'EXDOSU', 'EXSTDTC']),
                           ('AE', ['AETERM', 'AEDECOD', 'AESTDTC', 'AEENDTC', 'AETOXGR'])]:
        source = {(r['USUBJID'], r['SRCSEQ']): r for r in raw_rows(base, domain)}
        for row in frame(base, domain, 'sdtm').to_dicts():
            original = source[(row['USUBJID'], str(row[domain+'SEQ']))]
            for field in fields:
                source_field = 'EXDTC' if field == 'EXSTDTC' and 'EXDTC' in original else field
                expected = original.get(source_field) or None
                if field == 'EXDOSE' and expected is not None:
                    expected = float(expected)
                if row[field] != expected:
                    raise ValueError(f'{domain}: collected {field} changed for {row["USUBJID"]}')
                checked += 1
    inventory = json.loads((base / 'data/odm/extracted/inventory.json').read_text())
    source = {}
    for group in inventory['groups'].values():
        if group['name'].startswith('LB_'):
            for row in raw_rows(base, group['name']):
                for item in group['items']:
                    field = inventory['items'][item]['name']
                    source[(row['USUBJID'], row['SRCSEQ'], item)] = row.get(field) or None
    for row in frame(base, 'LB', 'sdtm').to_dicts():
        if source[(row['USUBJID'], row['LBSPID'], row['LBREFID'])] != row['LBORRES']:
            raise ValueError('LB: original result changed during structural mapping')
        checked += 1
    # A baseline candidate must be numeric, on/before first dose, and unique.
    baselines = 0
    for domain in ['ADLB', 'ADVS', 'ADQS', 'ADEG']:
        data = frame(base, domain)
        selected = data.filter(pl.col('ABLFL') == 'Y')
        if selected.select('USUBJID', 'PARAMCD').is_duplicated().any():
            raise ValueError(f'{domain}: multiple baseline candidates per subject/parameter')
        if selected.filter(pl.col('AVAL').is_null() | pl.col('ADT').is_null() |
                           (pl.col('ADT') > pl.col('TRTSDT'))).height:
            raise ValueError(f'{domain}: ineligible baseline candidate')
        if data.filter(pl.col('CHG').is_not_null() &
                       ((pl.col('CHG') - (pl.col('AVAL') - pl.col('BASE'))).abs() > 1e-10)).height:
            raise ValueError(f'{domain}: inconsistent change from baseline')
        baselines += selected.height
    tte = frame(base, 'ADTTE')
    if tte['ANL01FL'].null_count() != tte.height:
        raise ValueError('ADTTE: primary efficacy flag populated before review')
    if tte.filter((pl.col('AVAL') != (pl.col('ADT') - pl.col('STARTDT')).dt.total_days()+1) |
                  ~pl.col('CNSR').is_in([0, 1])).height:
        raise ValueError('ADTTE: inconsistent duration or censor value')
    return {'status': 'passed', 'collected_values_checked': checked,
            'baseline_candidates_checked': baselines, 'time_to_event_records_checked': tte.height,
            'scope': 'Collected EX/AE/LB preservation, baseline eligibility/uniqueness, changes and TTE arithmetic. Does not approve clinical rules.'}


def temporal_observations(base, adsl, inventory):
    rand = {r['USUBJID']: r['RANDDT'] for r in adsl.to_dicts()}
    discrepancies, fractional, total_days, total_integers = [], [], 0, 0
    for oid, group in inventory['groups'].items():
        rows = raw_rows(base, group['name'])
        fields = {i.rsplit('.', 1)[-1]: inventory['items'][i] for i in group['items']}
        day_fields = [f for f in fields if f.endswith('DY') and f not in ['RECURDY', 'OSDY', 'DFSDY']]
        for row in rows:
            for field in day_fields:
                date_fields = [field[:-2] + suffix for suffix in ['DTC', 'STDTC']]
                dtc = next((row.get(d) for d in date_fields if row.get(d)), None)
                if not dtc or not row.get(field):
                    continue
                reference = rand[row['USUBJID']]
                collected = date.fromisoformat(dtc)
                expected = (collected-reference).days + int(collected >= reference)
                total_days += 1
                if float(row[field]) != expected:
                    discrepancies.append({'USUBJID': row['USUBJID'], 'group': group['name'],
                                          'sequence': row['SRCSEQ'], 'date': dtc, 'field': field,
                                          'source_day': row[field], 'date_derived_day': expected})
            for field, item in fields.items():
                if item['data_type'] != 'integer' or not row.get(field):
                    continue
                total_integers += 1
                try:
                    number = float(row[field])
                    bad = not number.is_integer()
                except ValueError:
                    bad = True
                if bad:
                    fractional.append({'USUBJID': row['USUBJID'], 'group': group['name'],
                                       'field': field, 'source_value': row[field], 'declared_type': 'integer'})
    return {'source_day_mismatch': measure(discrepancies, total_days, unit='date/day pairs'),
            'integer_metadata_mismatch': measure(fractional, total_integers, unit='integer-declared values')}


def clinical_observations(root, study):
    base = root / study
    adsl = frame(base, 'ADSL')
    inventory = json.loads((base / 'data/odm/extracted/inventory.json').read_text())
    observations = temporal_observations(base, adsl, inventory)
    end = 'PFS' if study == 'kn189' else 'DFS'
    tte = frame(base, 'ADTTE')
    summary = {r['USUBJID']: r for r in tte.filter(pl.col('PARAMCD') == end).to_dicts()}
    candidate = tte.filter(pl.col('PARAMCD') == end+'CAND')
    differences = []
    for row in candidate.to_dicts():
        other = summary[row['USUBJID']]
        if (row['AVAL'], row['CNSR']) != (other['AVAL'], other['CNSR']):
            differences.append({'USUBJID': row['USUBJID'], 'source_days': other['AVAL'],
                                'candidate_days': row['AVAL'], 'source_censor': other['CNSR'],
                                'candidate_censor': row['CNSR']})
    observations['endpoint_disagreement'] = measure(differences, len(summary), unit='subjects',
        note='The candidate omits sensitivity censoring rules and is not an approved primary endpoint.')
    deaths = adsl.filter(pl.col('DTHFL') == 'Y')
    ds = frame(base, 'DS', 'sdtm')
    dated = set(ds.filter((pl.col('DSDECOD') == 'DEATH') & pl.col('DSSTDTC').is_not_null())['USUBJID'])
    missing = [{'USUBJID': row['USUBJID'], 'source_implied_death_date': str(row['DTHDT'])}
               for row in deaths.to_dicts() if row['USUBJID'] not in dated]
    observations['death_without_disposition'] = measure(missing, deaths.height, unit='source-summary deaths')
    for sd, key in [('LB', 'missing_lab_units'), ('VS', 'missing_vs_units')]:
        data = frame(base, sd, 'sdtm')
        numeric = data.filter(pl.col(sd+'STRESN').is_not_null())
        absent = numeric.filter(pl.col(sd+'STRESU').is_null())
        observations[key] = measure(absent.select(['USUBJID', sd+'TESTCD']).to_dicts(), numeric.height)
        observations[key]['parameters'] = absent.group_by(sd+'TESTCD').len().sort(sd+'TESTCD').to_dicts()
    baseline, total = [], 0
    for domain in ['ADLB', 'ADVS', 'ADQS', 'ADEG']:
        data = frame(base, domain).filter(pl.col('ABLFL') == 'Y')
        total += data.height
        for row in data.filter(pl.col('ADT') == pl.col('TRTSDT')).select('USUBJID','PARAMCD','ADT').to_dicts():
            baseline.append({**row, 'ADT': str(row['ADT']), 'dataset': domain})
    observations['baseline_same_day'] = measure(baseline, total, unit='selected baseline candidates',
        note='Date equality establishes neither pre-dose nor post-dose order.')
    ae = raw_rows(base, 'AE')
    observations['severity_recode'] = measure(
        [{'USUBJID':r['USUBJID'],'source_severity':r['AESEV'],'sdtm_severity':'SEVERE'}
         for r in ae if r['AESEV']=='LIFE-THREATENING'], len(ae))
    strata = adsl.filter(pl.col('STRATA').is_null())
    observations['strata_completeness'] = measure(strata.select('USUBJID').to_dicts(), adsl.height,
        note='Completeness of reconstructed values is not agreement with an IVRS file.')
    if study == 'kn189':
        ex = raw_rows(base, 'EX')
        observations['chemotherapy_units'] = measure(
            [{'USUBJID':r['USUBJID'],'treatment':r['EXTRT'],'dose':r['EXDOSE'],
              'unit':r['EXDOSU'],'adjustment':r['EXADJ']}
             for r in ex if r['EXADJ'] in ['DOSE INTERRUPTED','WITHDRAWN']],
            len(ex),note='Nominal recorded dose on interruption/withdrawal records requires an administration decision.')
    else:
        qs = frame(base, 'ADQS')
        selected = qs.filter(pl.col('ADY').is_between(352, 546))
        observations['pro_week52'] = measure(selected.select('USUBJID','PARAMCD','ADY').to_dicts(), qs.height,
            note='Observed records in SAP window only. The scheduled-eligible denominator is unavailable.')
        observations['pro_week52']['parameters'] = selected.group_by('PARAMCD').len().to_dicts()
    return observations

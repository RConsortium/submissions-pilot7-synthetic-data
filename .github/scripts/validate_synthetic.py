"""Build synthetic SDTM/ADaM, submission files, and a reviewable evidence record."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import jsonschema
import polars as pl
import yaml

from synthetic_odm import stage
from synthetic_checks import check_datasets, check_define, check_source_trace, clinical_observations, frame
from synthetic_evidence import artifact_inventory
from resolved_specs import process_study, specification_packet

ROOT = Path(__file__).resolve().parents[2]
ENGINE_PIN = '5976b74fddfbcbcad4d53ba550cb1e3773e07a5b'


def review_register(root, study, observations):
    base = root / study
    path = base / 'spec/review/findings.json'
    review = json.loads(path.read_text())
    schema = json.loads((root / '.github/schemas/synthetic-review.schema.json').read_text())
    jsonschema.validate(review, schema)
    if review['study'] != study:
        raise ValueError('Wrong study in review register')
    ids = [f['id'] for f in review['findings']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate finding identifiers')
    for coverage in review['coverage']:
        if set(coverage['findings']) - set(ids):
            raise ValueError(f"Unknown coverage findings: {coverage['id']}")
    for finding in review['findings']:
        for citation in finding['citations']:
            source = (base / citation['document']).resolve()
            source.relative_to(base.resolve())
            text = source.read_text()
            quote = citation['quote']
            if quote not in text:
                raise ValueError(f"{finding['id']}: source quotation not found")
            # Exact source line references, not merely matching text elsewhere.
            at_line = '\n'.join(text.splitlines()[citation['line']-1:])
            if not at_line.startswith(quote):
                raise ValueError(f"{finding['id']}: source line does not locate its quote")
        key = finding.get('measurement')
        if key and key not in observations:
            raise ValueError(f"{finding['id']}: missing measurement {key}")
        finding['evidence'] = observations.get(key)
        finding['observation_status'] = ('observed' if key and observations[key]['count'] else
                                         'not_observed' if key else 'not_measured')
        if finding['kind'] == 'conflict' and key and not observations[key]['count']:
            finding['kind'] = 'decision'
            finding['summary'] += ' No differences were observed in this measurement; source conventions still require confirmation.'
    return review


def summaries(base):
    adsl = frame(base, 'ADSL')
    ae = frame(base, 'ADAE')
    tte = frame(base, 'ADTTE')
    cohort = adsl.group_by('TRT01P').agg(pl.len().alias('subjects'),
        (pl.col('SAFFL')=='Y').sum().alias('safety_subjects'),
        pl.col('AGE').mean().alias('mean_age'),
        (pl.col('DTHFL')=='Y').sum().alias('source_summary_deaths')).sort('TRT01P')
    teae = ae.filter(pl.col('TRTEMFL')=='Y').group_by('TRT01A').agg(
        pl.len().alias('events'),pl.col('USUBJID').n_unique().alias('subjects'),
        (pl.col('AESER')=='Y').sum().alias('serious_events'))
    efficacy = tte.group_by('PARAMCD','TRT01P','DTYPE').agg(
        pl.len().alias('subjects'),(pl.col('CNSR')==0).sum().alias('events'),
        (pl.col('CNSR')==1).sum().alias('censored')).sort('PARAMCD','TRT01P')
    return {'cohort':cohort.to_dicts(),'treatment_emergent_events':teae.to_dicts(),
            'endpoint_counts':efficacy.to_dicts(),
            'interpretation':'Descriptive development counts. No confirmatory testing or published-trial reproduction is claimed.'}


def write_markdown(base, report):
    lines = ['# '+report['study'].upper()+' development findings','',
             'Build status: '+report['status']+'. Human analysis approval: pending.', '',
             'All source-summary endpoints and candidate derivations remain provisional.', '',
             '| ID | Type | Finding |','| --- | --- | --- |']
    for finding in report['review']['findings']:
        lines.append(f"| {finding['id']} | {finding['kind']} | {finding['title']} |")
    for finding in report['review']['findings']:
        lines += ['', '## '+finding['id']+': '+finding['title'], '', finding['summary'], '',
                  'Action: '+finding['proposed_action']]
        if finding['evidence']:
            e=finding['evidence']
            lines += ['',f"Measured: {e['count']} / {e['denominator']} {e['unit']}; {e['subject_count']} distinct subjects."]
        for cite in finding['citations']:
            lines += ['',f"Source: {cite['document']}:{cite['line']} ({cite['section']}).", '',
                      '> '+cite['quote'].replace('\n','\n> ')]
    (base / 'log/findings.md').write_text('\n'.join(lines)+'\n',encoding='ascii',errors='xmlcharrefreplace')


def validate(study, root=ROOT):
    import yamaa

    base = root / study
    target = root / '.build/synthetic' / study / 'report.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.unlink(missing_ok=True)
    report = {'schema_version':1,'study':study,'status':'failed',
              'created_utc':datetime.now(timezone.utc).isoformat(),
              'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'yamaa_revision':ENGINE_PIN,'engine':yamaa.info(),
              'validation_scope':'Development build, independent structural and transport checks; not regulatory or independent reference validation.',
              'packages':{n:importlib.metadata.version(n) for n in ['yamaa','polars','pyarrow','lxml','pyreadstat']}}
    try:
        if '1.0' not in yamaa.info()['language_versions']:
            raise ValueError('The installed yamaa does not support the required 1.0 language')
        process_study(root, study, check=True)
        inventory=stage(study,root)
        report['source_subjects']=inventory['subjects']
        for section in ['sdtm', 'adam']:
            (base / 'data' / section).mkdir(parents=True, exist_ok=True)
        project_file=base/'spec/yamaa/project.yaml'
        declaration=yaml.safe_load(project_file.read_text())
        project=yamaa.project(project_file)
        checked=project.check()
        if checked.status!='succeeded':raise ValueError(checked.issues.to_pylist())
        for section in ['sdtm','adam']:
            run=project.run(section)
            if run.status!='succeeded':raise ValueError(run.issues.to_pylist())
            run.save()
            print(study,section,'built',len(run),'datasets',flush=True)
            submission=project.submission(section,created=report['created_utc'].split('.')[0])
            if submission.status!='succeeded':raise ValueError(submission.issues.to_pylist())
            submission.save()
        report['datasets']=check_datasets(root,study,declaration)
        for dataset in report['datasets']:
            if dataset['section'] == 'adam':
                path = root / dataset['spec']
                dataset['resolved_specification'] = specification_packet(root, path)
        report['source_trace_checks']=check_source_trace(base)
        report['define_xml']={section:check_define(root,base,section,
            [d['domain'] for d in report['datasets'] if d['section']==section]) for section in ['sdtm','adam']}
        observations=clinical_observations(root,study)
        report['review']=review_register(root,study,observations)
        report['observations']=observations
        report['summaries']=summaries(base)
        report['status']='succeeded'
        report['reference_comparison']='unavailable'
        report['human_review']='pending'
        report['artifacts']=artifact_inventory(root,study)
        write_markdown(base,report)
    except Exception as error:
        report['error']=str(error)
        print('FAILED:',error,flush=True)
    target.write_text(json.dumps(report,indent=2,ensure_ascii=True)+'\n')
    print(study,report['status'],target,flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',choices=['kn189','kn564'])
    args=parser.parse_args()
    return int(validate(args.study)['status']!='succeeded')


if __name__=='__main__':raise SystemExit(main())

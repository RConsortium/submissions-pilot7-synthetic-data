#!/usr/bin/env python3
"""Build ADLBH input parquet from SDTM LB.

ADLBH: Hematology analysis dataset (49,932 x 46).
- 24,966 base rows from LB (17 HEMATOLOGY params) + EOT duplicates.
- 24,966 underscore rows ("change from previous visit, relative to normal range").

All complex derivation (EOT selection, ANL01FL, underscore) done here honestly
in Python; the YAMAA spec does ADSL lookup + column mapping.
"""
import polars as pl
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

D = Path(__file__).resolve().parents[1]
OUT = D / 'upstream' / 'adlbh_input.parquet'

def sas_round1(x):
    """Round to 1 decimal, half away from zero (SAS style), cleaning binary noise."""
    if x is None:
        return None
    # Clean binary floating-point noise (lab values have <6 meaningful decimals)
    xc = round(float(x), 9)
    return float(Decimal(str(xc)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))

# 17 hematology params: LBTESTCD -> (PARAM, PARAMN)
PARAMS = {
    'HGB':     ('Hemoglobin (mmol/L)', 1.0),
    'HCT':     ('Hematocrit', 2.0),
    'MCV':     ('Ery. Mean Corpuscular Volume (fL)', 3.0),
    'MCH':     ('Ery. Mean Corpuscular Hemoglobin (fmol(Fe))', 4.0),
    'MCHC':    ('Ery. Mean Corpuscular HGB Concentration (mmol/L)', 5.0),
    'WBC':     ('Leukocytes (GI/L)', 6.0),
    'LYM':     ('Lymphocytes (GI/L)', 7.0),
    'MONO':    ('Monocytes (GI/L)', 8.0),
    'EOS':     ('Eosinophils (GI/L)', 9.0),
    'BASO':    ('Basophils (GI/L)', 10.0),
    'PLAT':    ('Platelet (GI/L)', 11.0),
    'RBC':     ('Erythrocytes (TI/L)', 12.0),
    'ANISO':   ('Anisocytes', 13.0),
    'MACROCY': ('Macrocytes', 14.0),
    'MICROCY': ('Microcytes', 15.0),
    'POIKILO': ('Poikilocytes', 16.0),
    'POLYCHR': ('Polychromasia', 17.0),
}
# 12 params eligible for ANL01FL
ANL12 = {'BASO','EOS','HCT','HGB','LYM','MCH','MCHC','MCV','MONO','PLAT','RBC','WBC'}
# 5 categorical (no numeric range; ANRIND always H)
CAT5 = {'ANISO','MACROCY','MICROCY','POIKILO','POLYCHR'}

# VISIT -> (AVISIT, AVISITN)
def avisit(visit: str):
    v = visit.strip().upper()
    if v == 'SCREENING 1':
        return ('        Baseline', 0.0)
    if v.startswith('WEEK'):
        n = v.split()[1]
        # right-justify AVISIT to width 16 (observed in official)
        label = f'Week {n}'
        return (label.rjust(16), float(n))
    if v.startswith('UNSCHEDULED'):
        return ('               .', None)
    raise ValueError(f'Unknown VISIT: {visit!r}')

lb = pl.read_parquet(D / 'sdtm' / 'lb.parquet')
lb = lb.filter(pl.col('LBTESTCD').is_in(list(PARAMS.keys())))
# Exclude visits not in ADaM (e.g. AMBUL ECG REMOVAL, BASELINE, RETRIEVAL)
lb = lb.filter(~pl.col('VISIT').is_in(['AMBUL ECG REMOVAL', 'BASELINE', 'RETRIEVAL']))
print('LB rows (17 params, ADaM visits):', lb.shape[0])

# Base fields
rows = []
for r in lb.iter_rows(named=True):
    avis, avisn = avisit(r['VISIT'])
    param, paramn = PARAMS[r['LBTESTCD']]
    # ADT from LBDTC (date part) as datetime.date
    from datetime import date as _date
    lbdtc = r['LBDTC']
    if isinstance(lbdtc, str) and len(lbdtc) >= 10:
        adt = _date(int(lbdtc[0:4]), int(lbdtc[5:7]), int(lbdtc[8:10]))
    elif hasattr(lbdtc, 'date'):
        adt = lbdtc.date()
    else:
        adt = lbdtc
    rows.append({
        'USUBJID': r['USUBJID'],
        'AVISIT': avis,
        'AVISITN': avisn,
        'ADY': float(r['LBDY']) if r['LBDY'] is not None else None,
        'ADT': adt,
        'VISIT': r['VISIT'],
        'VISITNUM': float(r['VISITNUM']) if r['VISITNUM'] is not None else None,
        'PARAM': param,
        'PARAMCD': r['LBTESTCD'],
        'PARAMN': paramn,
        'PARCAT1': 'HEM',
        'AVAL': float(r['LBSTRESN']) if r['LBSTRESN'] is not None else None,
        # A1LO null when LBSTNRLO is null or 0 (0 = no lower limit for these params)
        'A1LO': (float(r['LBSTNRLO']) if (r['LBSTNRLO'] is not None and float(r['LBSTNRLO']) != 0.0) else None),
        'A1HI': float(r['LBSTNRHI']) if r['LBSTNRHI'] is not None else None,
        # Raw range for _AVAL half-width (preserve 0)
        '_RLO': float(r['LBSTNRLO']) if r['LBSTNRLO'] is not None else None,
        '_RHI': float(r['LBSTNRHI']) if r['LBSTNRHI'] is not None else None,
        'ABLFL': 'Y' if r['LBBLFL'] == 'Y' else '',
        'LBSEQ': float(r['LBSEQ']) if r['LBSEQ'] is not None else None,
        'LBNRIND': r['LBNRIND'] or '',
        'LBSTRESN': float(r['LBSTRESN']) if r['LBSTRESN'] is not None else None,
    })

df = pl.DataFrame(rows)
print('base rows:', df.shape[0])

# BASE per (USUBJID, PARAMCD) from ABLFL='Y' row
base = (df.filter(pl.col('ABLFL') == 'Y')
          .select(['USUBJID', 'PARAMCD', 'AVAL'])
          .rename({'AVAL': 'BASE'}))
df = df.join(base, on=['USUBJID', 'PARAMCD'], how='left')

# CHG = AVAL - BASE; null for Baseline (AVISITN=0)
df = df.with_columns(
    pl.when((pl.col('AVISITN') == 0) | pl.col('BASE').is_null() | pl.col('AVAL').is_null())
      .then(None)
      .otherwise(pl.col('AVAL') - pl.col('BASE'))
      .alias('CHG')
)

# Ratios
df = df.with_columns(
    pl.when(pl.col('A1LO').is_not_null() & pl.col('AVAL').is_not_null())
      .then(pl.col('AVAL') / pl.col('A1LO')).otherwise(None).alias('R2A1LO'),
    pl.when(pl.col('A1HI').is_not_null() & pl.col('AVAL').is_not_null())
      .then(pl.col('AVAL') / pl.col('A1HI')).otherwise(None).alias('R2A1HI'),
    pl.when(pl.col('A1LO').is_not_null() & pl.col('BASE').is_not_null())
      .then(pl.col('BASE') / pl.col('A1LO')).otherwise(None).alias('BR2A1LO'),
    pl.when(pl.col('A1HI').is_not_null() & pl.col('BASE').is_not_null())
      .then(pl.col('BASE') / pl.col('A1HI')).otherwise(None).alias('BR2A1HI'),
)

# ALBTRVAL = max(1.5*A1HI - AVAL, AVAL - 0.5*A1LO)
# Uses raw _RLO (0 preserved) for the lower term; if both ranges null, result null.
df = df.with_columns(
    pl.when(pl.col('AVAL').is_not_null() & (pl.col('_RHI').is_not_null() | pl.col('_RLO').is_not_null()))
      .then(pl.max_horizontal(
          pl.when(pl.col('_RHI').is_not_null()).then(1.5 * pl.col('_RHI') - pl.col('AVAL')).otherwise(None),
          pl.when(pl.col('_RLO').is_not_null()).then(pl.col('AVAL') - 0.5 * pl.col('_RLO')).otherwise(None),
      ))
      .otherwise(None)
      .alias('ALBTRVAL')
)

# ANRIND: L if AVAL < 0.5*A1LO, H if AVAL > 1.5*A1HI, else N; CAT5 always H
df = df.with_columns(
    pl.when(pl.col('PARAMCD').is_in(list(CAT5))).then(pl.lit('H'))
      .when(pl.col('AVAL').is_not_null() & pl.col('A1LO').is_not_null() & (pl.col('AVAL') < 0.5 * pl.col('A1LO'))).then(pl.lit('L'))
      .when(pl.col('AVAL').is_not_null() & pl.col('A1HI').is_not_null() & (pl.col('AVAL') > 1.5 * pl.col('A1HI'))).then(pl.lit('H'))
      .otherwise(pl.lit('N'))
      .alias('ANRIND')
)

# BNRIND: same on BASE; '' if BASE null
df = df.with_columns(
    pl.when(pl.col('BASE').is_null()).then(pl.lit(''))
      .when(pl.col('PARAMCD').is_in(list(CAT5))).then(pl.lit('H'))
      .when(pl.col('A1LO').is_not_null() & (pl.col('BASE') < 0.5 * pl.col('A1LO'))).then(pl.lit('L'))
      .when(pl.col('A1HI').is_not_null() & (pl.col('BASE') > 1.5 * pl.col('A1HI'))).then(pl.lit('H'))
      .otherwise(pl.lit('N'))
      .alias('BNRIND')
)

# EOT: for each (USUBJID, PARAMCD), max AVISITN among scheduled (excl 26, excl null).
# If max > 0, duplicate that row as EOT.
sched = df.filter(pl.col('AVISITN').is_not_null() & (pl.col('AVISITN') != 26))
maxn = sched.group_by(['USUBJID', 'PARAMCD']).agg(pl.col('AVISITN').max().alias('maxn'))
maxn = maxn.filter(pl.col('maxn') > 0)
# Get the source rows (one per USUBJID/PARAMCD/maxn)
src = df.join(maxn, on=['USUBJID', 'PARAMCD'], how='inner')
src = src.filter(pl.col('AVISITN') == pl.col('maxn'))
# There should be one per group; if ties (shouldn't happen), take first
src = src.unique(subset=['USUBJID', 'PARAMCD'], keep='first')
print('EOT source rows:', src.shape[0])

eot = src.with_columns(
    pl.lit('End of Treatment').alias('AVISIT'),
    pl.lit(99.0).alias('AVISITN'),
    pl.lit('Y').alias('AENTMTFL'),
).drop('maxn')

# Non-EOT get AENTMTFL='' initially; will set Y on max-visit sources below
df = df.with_columns(pl.lit('').alias('AENTMTFL'))

# Combine base + EOT
df = pl.concat([df, eot], how='diagonal')
print('base + EOT rows:', df.shape[0])

# AENTMTFL='Y' on both the EOT row and its source (max-visit) row
src_keys = src.select(['USUBJID', 'PARAMCD', 'LBSEQ'])
df = df.join(src_keys.with_columns(pl.lit('Y').alias('_ent')), on=['USUBJID', 'PARAMCD', 'LBSEQ'], how='left')
df = df.with_columns(
    pl.when((pl.col('AVISIT') == 'End of Treatment') | pl.col('_ent').is_not_null())
      .then(pl.lit('Y')).otherwise(pl.lit('')).alias('AENTMTFL')
).drop('_ent')

# ANL01FL: for 12 params, max ALBTRVAL over Weeks 2-24 (AVISITN 2..24), tie -> earliest AVISITN.
# Week 26 excluded, Baseline/'.' excluded.
df = df.with_columns(pl.lit('').alias('ANL01FL'))
elig = df.filter(
    pl.col('PARAMCD').is_in(list(ANL12)) &
    pl.col('AVISITN').is_not_null() &
    (pl.col('AVISITN') >= 2) & (pl.col('AVISITN') <= 24) &
    pl.col('ALBTRVAL').is_not_null()
)
# For each (USUBJID, PARAMCD), find max ALBTRVAL, then earliest AVISITN among ties
win = (elig.sort(['USUBJID', 'PARAMCD', 'ALBTRVAL', 'AVISITN'],
                 descending=[False, False, True, False])
           .unique(subset=['USUBJID', 'PARAMCD'], keep='first')
           .select(['USUBJID', 'PARAMCD', 'AVISITN'])
           .rename({'AVISITN': 'win_n'}))
# Mark winners (non-EOT)
df = df.join(win, on=['USUBJID', 'PARAMCD'], how='left')
df = df.with_columns(
    pl.when((pl.col('AVISIT') != 'End of Treatment') &
            pl.col('PARAMCD').is_in(list(ANL12)) &
            (pl.col('AVISITN') == pl.col('win_n')))
      .then(pl.lit('Y'))
      .otherwise(pl.col('ANL01FL'))
      .alias('ANL01FL')
)
# EOT inherits from source (same LBSEQ)
eot_flag = df.filter(pl.col('AVISIT') != 'End of Treatment').select(['USUBJID', 'PARAMCD', 'LBSEQ', 'ANL01FL'])
df = df.join(eot_flag.rename({'ANL01FL': 'src_flag'}), on=['USUBJID', 'PARAMCD', 'LBSEQ'], how='left')
df = df.with_columns(
    pl.when(pl.col('AVISIT') == 'End of Treatment')
      .then(pl.col('src_flag'))
      .otherwise(pl.col('ANL01FL'))
      .alias('ANL01FL')
).drop(['win_n', 'src_flag'])

print('ANL01FL=Y count:', df.filter(pl.col('ANL01FL') == 'Y').shape[0])

# --- Underscore rows ---
# For each base row (incl EOT), create _PARAMCD row.
# _AVAL = round((AVAL - prev_AVAL) / ((A1HI - A1LO)/2), 1)
# prev = previous scheduled visit's AVAL by AVISITN (excl '.', excl EOT, excl Baseline? Baseline has no prev).
# For EOT, _AVAL = source visit's _AVAL.

# First, compute _AVAL for non-EOT scheduled rows.
# Get scheduled non-EOT base rows ordered by AVISITN
sched_base = df.filter(
    (pl.col('AVISIT') != 'End of Treatment') &
    pl.col('AVISITN').is_not_null()
).sort(['USUBJID', 'PARAMCD', 'AVISITN'])

# For each (USUBJID, PARAMCD), shift AVAL to get prev
sched_base = sched_base.with_columns(
    pl.col('AVAL').shift(1).over(['USUBJID', 'PARAMCD']).alias('prev_AVAL'),
    pl.col('A1LO').shift(1).over(['USUBJID', 'PARAMCD']).alias('prev_A1LO'),
    pl.col('A1HI').shift(1).over(['USUBJID', 'PARAMCD']).alias('prev_A1HI'),
)
# _AVAL uses raw range (_RLO/_RHI, preserving 0) for half-width
# Use SAS-style rounding (half away from zero) via Python UDF
sched_base = sched_base.with_columns(
    pl.when(pl.col('AVISITN') == 0).then(None)  # Baseline: no prev
      .when(pl.col('prev_AVAL').is_null() | pl.col('_RLO').is_null() | pl.col('_RHI').is_null()).then(None)
      .otherwise(((pl.col('AVAL') - pl.col('prev_AVAL')) / ((pl.col('_RHI') - pl.col('_RLO')) / 2)))
      .alias('_ratio')
)
sched_base = sched_base.with_columns(
    pl.col('_ratio').map_elements(sas_round1, return_dtype=pl.Float64).alias('_AVAL_raw')
).drop('_ratio')

# Map _AVAL back to df (non-EOT)
df = df.join(
    sched_base.select(['USUBJID', 'PARAMCD', 'AVISITN', '_AVAL_raw']),
    on=['USUBJID', 'PARAMCD', 'AVISITN'],
    how='left'
)
# For EOT, _AVAL = source's _AVAL (join on LBSEQ)
src_u = df.filter(pl.col('AVISIT') != 'End of Treatment').select(['USUBJID', 'PARAMCD', 'LBSEQ', '_AVAL_raw'])
df = df.join(src_u.rename({'_AVAL_raw': '_AVAL_src'}), on=['USUBJID', 'PARAMCD', 'LBSEQ'], how='left')
df = df.with_columns(
    pl.when(pl.col('AVISIT') == 'End of Treatment').then(pl.col('_AVAL_src')).otherwise(pl.col('_AVAL_raw')).alias('_AVAL')
).drop(['_AVAL_raw', '_AVAL_src'])

# For '.' (unscheduled, AVISITN null): _AVAL is null (no previous scheduled)
# Already null because not in sched_base.

# Build underscore rows
u = df.with_columns(
    ('_' + pl.col('PARAMCD')).alias('PARAMCD'),
    (pl.col('PARAM') + ' change from previous visit, relative to normal range').str.slice(0, 100).alias('PARAM'),
    (pl.col('PARAMN') + 100).alias('PARAMN'),
    pl.col('_AVAL').alias('AVAL'),
    pl.lit(None, dtype=pl.Float64).alias('BASE'),
    pl.lit(None, dtype=pl.Float64).alias('CHG'),
    pl.lit(None, dtype=pl.Float64).alias('A1LO'),
    pl.lit(None, dtype=pl.Float64).alias('A1HI'),
    pl.lit(None, dtype=pl.Float64).alias('R2A1LO'),
    pl.lit(None, dtype=pl.Float64).alias('R2A1HI'),
    pl.lit(None, dtype=pl.Float64).alias('BR2A1LO'),
    pl.lit(None, dtype=pl.Float64).alias('BR2A1HI'),
    # ANRIND from _AVAL
    pl.when(pl.col('_AVAL').is_null()).then(pl.lit(''))
      .when(pl.col('_AVAL') > 1.0).then(pl.lit('H'))
      .when(pl.col('_AVAL') < -1.0).then(pl.lit('L'))
      .otherwise(pl.lit('N')).alias('ANRIND'),
    pl.lit('').alias('BNRIND'),
    # ABLFL: '' for underscore? Check official.
).drop('_AVAL')

# Check ABLFL for underscore: official had '' even for Baseline underscore? Let me set and verify.
# Actually from earlier, _HGB Baseline had ABLFL=''. So underscore ABLFL is always ''.
u = u.with_columns(pl.lit('').alias('ABLFL'))

# Combine
full = pl.concat([df, u], how='diagonal')
print('total rows:', full.shape[0])

# Underscore ANL01FL: separate selection. For _12 params, max |_AVAL| over Weeks 2-24,
# tie -> earliest AVISITN. EOT inherits from source.
# Reset underscore ANL01FL (was copied from base)
full = full.with_columns(
    pl.when(pl.col('PARAMCD').str.starts_with('_')).then(pl.lit('')).otherwise(pl.col('ANL01FL')).alias('ANL01FL')
)
u_elig = full.filter(
    pl.col('PARAMCD').str.starts_with('_') &
    pl.col('PARAMCD').str.slice(1).is_in(list(ANL12)) &
    (pl.col('AVISIT') != 'End of Treatment') &
    pl.col('AVISITN').is_not_null() &
    (pl.col('AVISITN') >= 2) & (pl.col('AVISITN') <= 24) &
    pl.col('AVAL').is_not_null()
).with_columns(pl.col('AVAL').abs().alias('_abs'))
u_win = (u_elig.sort(['USUBJID', 'PARAMCD', '_abs', 'AVISITN'],
                     descending=[False, False, True, False])
               .unique(subset=['USUBJID', 'PARAMCD'], keep='first')
               .select(['USUBJID', 'PARAMCD', 'AVISITN'])
               .rename({'AVISITN': 'uwin_n'}))
full = full.join(u_win, on=['USUBJID', 'PARAMCD'], how='left')
full = full.with_columns(
    pl.when(pl.col('PARAMCD').str.starts_with('_') &
            (pl.col('AVISIT') != 'End of Treatment') &
            (pl.col('AVISITN') == pl.col('uwin_n')))
      .then(pl.lit('Y')).otherwise(pl.col('ANL01FL')).alias('ANL01FL')
).drop('uwin_n')
# EOT inherits from source for underscore (redo for full incl. underscore)
eot_flag2 = full.filter(pl.col('AVISIT') != 'End of Treatment').select(['USUBJID', 'PARAMCD', 'LBSEQ', 'ANL01FL'])
full = full.join(eot_flag2.rename({'ANL01FL': 'src_flag2'}), on=['USUBJID', 'PARAMCD', 'LBSEQ'], how='left')
full = full.with_columns(
    pl.when(pl.col('AVISIT') == 'End of Treatment')
      .then(pl.col('src_flag2'))
      .otherwise(pl.col('ANL01FL'))
      .alias('ANL01FL')
).drop('src_flag2')

print('ANL01FL=Y total:', full.filter(pl.col('ANL01FL') == 'Y').shape[0])

# Order by (USUBJID, ADY, PARAMN, AVISITN)
full = full.sort(['USUBJID', 'ADY', 'PARAMN', 'AVISITN'], nulls_last=True)

# Select and order columns for input (YAMAA spec will add ADSL)
# Keep all needed for output
cols = ['USUBJID', 'AVISIT', 'AVISITN', 'ADY', 'ADT', 'VISIT', 'VISITNUM',
        'PARAM', 'PARAMCD', 'PARAMN', 'PARCAT1',
        'AVAL', 'BASE', 'CHG', 'A1LO', 'A1HI', 'R2A1LO', 'R2A1HI', 'BR2A1LO', 'BR2A1HI',
        'ANL01FL', 'ALBTRVAL', 'ANRIND', 'BNRIND', 'ABLFL', 'AENTMTFL',
        'LBSEQ', 'LBNRIND', 'LBSTRESN']
full = full.select(cols)
full = full.with_columns(pl.lit('CDISCPILOT01').alias('STUDYID'))

full.write_parquet(OUT)
# YAMAA does not support large_string; rewrite with plain string
import pyarrow as pa
import pyarrow.parquet as pq
t = pq.read_table(OUT)
fields = [pa.field(f.name, pa.string(), nullable=f.nullable, metadata=f.metadata)
          if pa.types.is_large_string(f.type) else f for f in t.schema]
pq.write_table(t.cast(pa.schema(fields)), OUT)
print('wrote', OUT, full.shape, '(string, not large_string)')

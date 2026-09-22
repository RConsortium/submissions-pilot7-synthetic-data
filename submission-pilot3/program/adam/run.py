import os, shutil
from pathlib import Path
import polars as pl, pyarrow as pa, pyarrow.parquet as pq, yamaa
HERE = Path(__file__).resolve().parent; WORK = HERE / "work"
for d in ("sdtm", "inputs", "derived"): (WORK / d).mkdir(parents=True, exist_ok=True)
for n in "dm ds ex qs sv vs sc mh ae lb supplb".split(): shutil.copy2(HERE / "../../data/sdtm" / f"{n}.parquet", WORK / "sdtm" / f"{n}.parquet")
S, I = pl.String, pl.Int64
schemas = {"plan": {"USUBJID": S, "PARAMCD": S, "AVISIT": S, "AVISITN": I}, "aw_lookup": {"AVISIT": S, "AWRANGE": S, "AWTARGET": I, "AWLO": I, "AWHI": I}}
for n, s in schemas.items(): pl.read_csv(HERE / "inputs" / f"{n}.csv", schema=s, null_values=[""]).write_parquet(WORK / "inputs" / f"{n}.parquet")
pl.read_parquet(WORK / "sdtm/qs.parquet").with_columns(pl.col("QSDTC").str.to_date("%Y-%m-%d", strict=True).alias("QSDTC_D")).write_parquet(WORK / "sdtm/qs_str.parquet")
for spec in HERE.glob("*.yaml"): shutil.copy2(spec, WORK / spec.name)
os.chdir(WORK)
for ds in ["adsl_exdose", "adsl", "adae", "adadas", "adtte", "adlbc"]:
    run = yamaa.yamaa_domain(ds + ".yaml")
    assert len(run.issues) == 0, ds
    out = run.save() if ds == "adsl_exdose" else run.save(WORK / "derived" / f"{ds}-yamaa.parquet")
    labels = {c.name: c.label for c in run.spec.columns}
    t = pq.read_table(out)
    pq.write_table(t.cast(pa.schema([f.with_metadata({**(f.metadata or {}), b"yamaa:label": labels[f.name].encode()}) for f in t.schema])), out, compression="none")

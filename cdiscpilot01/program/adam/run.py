#!/usr/bin/env python3
"""Pilot 01 SDTM -> ADaM end-to-end driver (native yamaa specs).

Every analysis variable is derived by the yamaa engine from the YAML specs
in this directory. Python only orchestrates: run specs in dependency order,
recast Arrow large_string -> string between stages (the engine reader
requires pa.string()), join the yamaa-derived PREV_AVAL map back onto LB,
and concatenate stage outputs. No analysis variable is derived in Python.

Runtime layout (all git-ignored, created under this directory):
  sdtm/      SDTM input parquets (symlinked from ../../data/sdtm/ on first run)
  expected/  official ADaM parquets for compare.py (symlinked from ../../data/adam/)
  upstream/  promoted predecessor ADaM outputs (plain-string recast)
  output/    per-spec official-shape parquet outputs
  work/      PREV_AVAL join staging + ADQSCIBC stage files

Usage:
  python run.py                  # everything, in dependency order
  python run.py adlbhy           # one dataset (predecessors auto-included)

Then:
  python compare.py              # strict cell-for-cell check vs expected/
"""
import argparse
import shutil
import sys
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

BASE = Path(__file__).resolve().parent
STUDY = BASE.parent.parent  # cdiscpilot01/

ARROW = {
    "str": pa.large_string(),
    "float": pa.float64(),
    "int": pa.int64(),
    "date": pa.date32(),
    "datetime": pa.timestamp("us"),
}

ORDER = ["adsl", "adae", "adtte", "advs", "adlbh",
         "adlbc", "adlbhy", "adqsadas", "adqscibc", "adqsnipx"]
PREDECESSORS = {
    "adae": ["adsl"],
    "adtte": ["adsl", "adae"],
    "advs": ["adsl"],
    "adlbh": ["adsl"],
    "adlbc": ["adsl"],
    "adlbhy": ["adlbc"],
    "adqsadas": ["adsl"],
    "adqscibc": ["adsl"],
    "adqsnipx": ["adsl"],
}

# (spec file,) stages per dataset; "*" stages are recast for interoperability.
STAGES = {
    "adqsadas": ["adqsadas-s1.yaml", "adqsadas-s2.yaml", "adqsadas-s2subj.yaml",
                 "adqsadas-s3.yaml", "adqsadas-final.yaml"],
    "adqscibc": ["adqscibc-s1.yaml", "adqscibc-s2.yaml", "adqscibc-s3a.yaml",
                 "adqscibc-s3b.yaml", "adqscibc-s3c.yaml", "adqscibc-s3d.yaml",
                 "adqscibc-s4j.yaml", "adqscibc-s4.yaml", "adqscibc-s5j.yaml",
                 "adqscibc-s5.yaml"],
    "adqsnipx": ["adqsnpix-s1.yaml", "adqsnpix-s2.yaml", "adqsnpix-final.yaml"],
}


def ensure_inputs() -> None:
    """Copy sdtm/ and expected/ from the study data dir on first run.

    The engine rejects resource paths that resolve through symlinks, so
    the inputs are copied, not linked. (Both dirs are only a few MB.)
    """
    for dirname, target in (("sdtm", STUDY / "data" / "sdtm"),
                            ("expected", STUDY / "data" / "adam")):
        p = BASE / dirname
        if not p.exists():
            if not target.is_dir():
                raise SystemExit(f"missing input dir: {target}")
            shutil.copytree(target, p)
            print(f"copied {target} -> {dirname}/")


def recast(path: Path) -> None:
    """Cast large_string -> string in place (the yamaa reader needs pa.string())."""
    t = pq.read_table(path)
    cols = [c.cast(pa.string()) if pa.types.is_large_string(f.type) else c
            for f, c in zip(t.schema, t.columns)]
    pq.write_table(pa.table(cols, names=t.schema.names), path)


def run_yamaa(spec_file: str, timeout: int = 1800) -> Path:
    """Run one spec in-process and write its official-shape output parquet."""
    from yamaa import yamaa_domain

    spec_path = BASE / spec_file
    print(f"=== {spec_file} ===", flush=True)
    raw = yaml.safe_load(spec_path.read_text())
    domain = raw["domain"].lower()

    frame: pl.DataFrame | None = yamaa_domain(str(spec_path),
                                             project_root=str(BASE)).output
    if frame is None:
        raise SystemExit(f"spec {spec_file} produced no output")

    cols = raw["columns"]
    col_by_name = {c["name"]: c for c in cols}
    order = raw["output"]["columns"]
    if raw["output"].get("order_by"):
        # Sort before selecting: order_by may reference helper columns
        # (e.g. KEYSEQ) absent from the final output. The engine does not
        # implement output.order_by, so the writer applies the spec-declared
        # order here (nulls last, matching official row order).
        sort_cols, desc = [], []
        for entry in raw["output"]["order_by"]:
            if isinstance(entry, dict):
                sort_cols.append(entry["variable"])
                desc.append(entry.get("direction") == "desc")
            else:
                sort_cols.append(entry)
                desc.append(False)
        frame = frame.sort(sort_cols, descending=desc, nulls_last=True)
    frame = frame.select(order)

    # The engine emits plain pa.string() without field labels; restore the
    # official Arrow types and yamaa:label field metadata here.
    fields, arrays = [], []
    for name in order:
        c = col_by_name[name]
        arr = frame[name].to_arrow().cast(ARROW[c["type"]])
        fields.append(pa.field(name, ARROW[c["type"]], nullable=True,
                               metadata={b"yamaa:label": c.get("label", "").encode()}))
        arrays.append(arr)
    table = pa.Table.from_arrays(arrays, schema=pa.schema(fields))

    out = BASE / "output" / f"{domain}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)
    print(f"  -> output/{domain}.parquet: {table.num_rows} x {table.num_columns}",
          flush=True)
    return out


def promote(domain: str) -> Path:
    """Copy output/<domain>.parquet to upstream/<domain>.parquet (plain strings)."""
    src = BASE / "output" / f"{domain}.parquet"
    if not src.exists():
        raise SystemExit(f"promote: expected output {src} not found")
    dst = BASE / "upstream" / f"{domain}.parquet"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    recast(dst)
    t = pq.read_table(dst)
    print(f"  -> upstream/{domain}.parquet: {t.num_rows} x {t.num_columns}", flush=True)
    return dst


def join_prevmap(prev_spec: str, work_name: str, main_spec: str) -> None:
    """PREV_AVAL pipeline (ADLBH/ADLBC): yamaa prevmap -> join onto LB -> main spec."""
    out = run_yamaa(prev_spec)
    lb = pl.read_parquet(BASE / "sdtm" / "lb.parquet")
    prev = pl.read_parquet(out).select(["USUBJID", "LBTESTCD", "LBSEQ", "PREV_AVAL"])
    joined = lb.join(prev, on=["USUBJID", "LBTESTCD", "LBSEQ"], how="left")
    staged = BASE / "work" / work_name
    staged.parent.mkdir(parents=True, exist_ok=True)
    joined.write_parquet(staged)
    print(f"  -> work/{work_name}: {joined.shape[0]} x {joined.shape[1]}", flush=True)
    run_yamaa(main_spec)


def run_stages(dataset: str) -> None:
    """Run a staged pipeline; recast every non-final stage for interoperability."""
    specs = STAGES[dataset]
    for spec in specs[:-1]:
        out = run_yamaa(spec)
        recast(out)
    if dataset == "adqscibc":
        # UNION plumbing: natural + LOCF rows (pure concat, no derivation).
        print("=== union ===", flush=True)
        work = BASE / "work"
        for spec, domain in (("adqscibc-s1.yaml", "adqscibc_s1"),
                             ("adqscibc-s2.yaml", "adqscibc_s2"),
                             ("adqscibc-s3a.yaml", "adqscibc_s3a"),
                             ("adqscibc-s3b.yaml", "adqscibc_s3b"),
                             ("adqscibc-s3c.yaml", "adqscibc_s3c"),
                             ("adqscibc-s3d.yaml", "adqscibc_s3d"),
                             ("adqscibc-s4j.yaml", "adqscibc_s4j"),
                             ("adqscibc-s4.yaml", "adqscibc_s4"),
                             ("adqscibc-s5j.yaml", "adqscibc_s5j"),
                             ("adqscibc-s5.yaml", "adqscibc_s5")):
            src = BASE / "output" / f"{domain}.parquet"
            dst = work / f"{domain.replace('_', '-')}.parquet"
            work.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())  # already recast above
        s2 = pl.read_parquet(work / "adqscibc-s2.parquet")
        s4 = pl.read_parquet(work / "adqscibc-s4.parquet")
        s5 = pl.read_parquet(work / "adqscibc-s5.parquet")
        all_cols = s2.columns
        for name, df in (("s4", s4), ("s5", s5)):
            missing = [c for c in all_cols if c not in df.columns]
            extra = [c for c in df.columns if c not in all_cols]
            if missing or extra:
                raise SystemExit(f"{name} schema mismatch: missing={missing} extra={extra}")
        comb = pl.concat([s2, s4.select(all_cols), s5.select(all_cols)], how="vertical")
        at = comb.to_arrow()
        cols = [c.cast(pa.string()) if pa.types.is_large_string(f.type) else c
                for f, c in zip(at.schema, at.columns)]
        pq.write_table(pa.table(cols, names=at.schema.names),
                       work / "adqscibc-combined.parquet")
        print(f"  -> work/adqscibc-combined.parquet: {comb.shape[0]} x {comb.shape[1]}",
              flush=True)
    run_yamaa(specs[-1])


PIPELINES = {
    "adsl": lambda: (run_yamaa("adsl.yaml"), promote("adsl")),
    "adae": lambda: (run_yamaa("adae.yaml"), promote("adae")),
    "adtte": lambda: run_yamaa("adtte.yaml"),
    "advs": lambda: run_yamaa("advs.yaml"),
    "adlbh": lambda: join_prevmap("adlbh-prevmap.yaml", "lb_h_with_prev.parquet",
                                  "adlbh.yaml"),
    "adlbc": lambda: join_prevmap("adlbc-prevmap.yaml", "lb_with_prev.parquet",
                                  "adlbc.yaml"),
    "adlbhy": lambda: (promote("adlbc"), run_yamaa("adlbhy.yaml")),
    "adqsadas": lambda: run_stages("adqsadas"),
    "adqscibc": lambda: run_stages("adqscibc"),
    "adqsnipx": lambda: run_stages("adqsnipx"),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("datasets", nargs="*", help="subset to run (default: all)")
    args = ap.parse_args()

    only = [d.lower() for d in args.datasets]
    for d in only:
        if d not in ORDER:
            raise SystemExit(f"unknown dataset: {d} (choose from {', '.join(ORDER)})")
    # Auto-include predecessors (e.g. adlbhy pulls in adlbc and adsl).
    wanted: list[str] = []
    for d in (only or ORDER):
        for p in PREDECESSORS.get(d, []):
            if p not in wanted:
                wanted.append(p)
        if d not in wanted:
            wanted.append(d)

    ensure_inputs()
    for name in ORDER:
        if name not in wanted:
            continue
        print(f"########## {name} ##########", flush=True)
        PIPELINES[name]()
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()

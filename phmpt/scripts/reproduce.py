#!/usr/bin/env python3
"""Reproduce the submitted ADaM datasets and Define-XML of a study cut.

    python scripts/reproduce.py fetch  --study mrna-1273-p201 --cut s3-d57   # PHMPT -> <cut>/data/
    python scripts/reproduce.py verify --study mrna-1273-p201 --cut s3-d57   # run specs, compare
    python scripts/reproduce.py define --study mrna-1273-p201 --cut s3-d57   # compose, compare
    python scripts/reproduce.py site                                         # results + pages

Every step reads studies.yaml (the studies, their cuts, comparison rules and
partition counts) and the fixed cut layout:

    <study>/<cut>/data/sdtm/<domain>.parquet     submitted SDTM
    <study>/<cut>/data/adam/<dataset>.parquet    submitted ADaM, the reference
    <study>/<cut>/spec/yamaa/<dataset>.yaml      yamaa specs
    <study>/<cut>/spec/yamaa/helper/<name>.yaml  helper specs (intermediate tables)
    <study>/<cut>/spec/define/                   received define, layers, generated define
    <study>/data/lists/                          study-level list inputs

A spec names its inputs as <sdtm-dir>/<file>, <adam-dir>/<file> or
<list-dir>/<file>; the placeholder is the running cut's folder and the
file name is taken as written; <study-dir>/<cut>/data/... reads another
cut's released data (a program that compares two submissions). An input at <work-dir>/<file> with a
`schema:` link is the output of the helper spec the link names (INPUT-10):
verify runs that helper first, on the same cut, and saves its output in
.local-run/work/<study>/<cut>/. --study / --cut / --dataset narrow the
scope; without them a step covers every study and cut.

Reports (one JSON per dataset or define) go to --out (default
.local-run/reports/); scripts/site/collect_results.py turns them into
data/reproduction/*.json for the site.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDERS = ("<sdtm-dir>/", "<adam-dir>/", "<list-dir>/", "<work-dir>/", "<study-dir>/")


def studies() -> dict:
    return yaml.safe_load((ROOT / "studies.yaml").read_text())


def scope(args, with_data_cuts=False):
    """[(study, cut)] selected by --study / --cut."""
    out = []
    for s, info in studies().items():
        if args.study and s != args.study:
            continue
        cuts = list(info["cuts"]) + (list(info.get("data_cuts", [])) if with_data_cuts else [])
        out += [(s, c) for c in cuts if not args.cut or c == args.cut]
    if not out:
        raise SystemExit(f"nothing in scope for --study {args.study} --cut {args.cut}")
    return out


def cut_dir(study, cut) -> Path:
    return ROOT / study / cut


def work_dir(study, cut) -> Path:
    return ROOT / ".local-run/work" / study / cut


def input_path(study, cut, declared: str) -> Path:
    for ph, d in zip(PLACEHOLDERS, (cut_dir(study, cut) / "data/sdtm", cut_dir(study, cut) / "data/adam",
                                    ROOT / study / "data/lists", work_dir(study, cut), ROOT / study)):
        if ph in declared:
            p = d / declared.split(ph, 1)[1]
            # A cut that resends only some domains (studies.yaml `sdtm_from`)
            # reads the others from the cut it supplements.
            base = studies()[study]["cuts"][cut].get("sdtm_from")
            if base and not p.exists() and ph in ("<sdtm-dir>/", "<adam-dir>/"):
                alt = cut_dir(study, base) / "data" / ("sdtm" if ph == "<sdtm-dir>/" else "adam") / p.name
                if alt.exists():
                    return alt
            return p
    raise SystemExit(f"input {declared!r} names no <sdtm-dir>, <adam-dir>, <list-dir>, <work-dir> or <study-dir>")


def resolved(spec: Path) -> dict:
    import yamaa

    return yamaa.spec(str(spec)).resolve()["entries"][0]["specification"]


def helpers(spec: Path) -> list[Path]:
    """The helper specs `spec` reads through <work-dir> schema links, producers first."""
    out: list[Path] = []
    for v in (resolved(spec).get("input") or {}).values():
        if isinstance(v, dict) and v.get("schema") and "<work-dir>/" in v["path"]:
            producer = (spec.parent / v["schema"]).resolve()
            for h in helpers(producer) + [producer]:
                if h not in out:
                    out.append(h)
    return out


def used_columns(sp: dict, name: str, path: Path) -> list[str]:
    """The columns of input `name` the resolved spec names: NAME.FIELD anywhere, the
    fields of an intermediate over it (pivot name and value, key), and its declared key.
    A field missed here fails the run as unknown, never silently."""
    import re

    import pyarrow.parquet as pq

    have = pq.read_schema(path).names
    decl = (sp.get("input") or {}).get(name)
    if isinstance(decl, dict) and decl.get("schema"):
        return have  # a linked artifact must carry exactly its producer's columns (INPUT-11)
    text = json.dumps(sp)
    want = set(re.findall(rf"\b{re.escape(name)}\.([A-Za-z_][A-Za-z0-9_]*)", text))
    for im in sp.get("intermediates") or []:
        if im.get("dataset") == name:
            piv = im.get("pivot") or {}
            want |= {piv.get("name"), piv.get("value")}
            key = im.get("key") or []
            want |= set(key if isinstance(key, list) else key.keys())
    decl = (sp.get("input") or {}).get(name)
    if isinstance(decl, dict):
        want |= set(decl.get("key") or [])
    cols = [c for c in have if c in want]
    return cols or have


def linked_inputs(sp: dict) -> frozenset:
    """The inputs of a resolved spec that another spec produced (a schema link, INPUT-10)."""
    return frozenset(n for n, v in (sp.get("input") or {}).items() if isinstance(v, dict) and v.get("schema"))


def read_for(name, path, sp, vc):
    """An input as yamaa reads it; a linked artifact keeps its time columns as times."""
    return vc.read_input(path, columns=used_columns(sp, name, path), keep_time=name in linked_inputs(sp))


def run_helper(study, cut, spec: Path) -> int:
    """Run one helper spec (whole-table, or in studies.yaml partitions) and save its output in the
    cut's work dir (child process)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import pyarrow.parquet as pq
    import verify_compare as vc
    import yamaa

    sp = resolved(spec)
    dest = input_path(study, cut, sp["output"]["path"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    paths = {n: input_path(study, cut, v["path"] if isinstance(v, dict) else v)
             for n, v in (sp.get("input") or {}).items()}
    t0 = time.time()
    # A helper too large for one run takes studies.yaml partitions under its own
    # name: its inputs are split by USUBJID as verify splits a dataset, and the
    # partition outputs are written one after another into one file.
    n = studies()[study].get("partitions", {}).get(cut, {}).get(spec.stem, 1)
    if n > 1:
        import shutil
        import tempfile

        work = Path(tempfile.mkdtemp(prefix="helper-parts-", dir=os.environ.get("VERIFY_TMPDIR")))
        writer = None
        try:
            linked = linked_inputs(sp)
            split = {k: vc._split(p, n, work, k, normalise=True, keep_time=k in linked)
                     for k, p in paths.items()}
            whole = {k: read_for(k, p, sp, vc) for k, p in paths.items() if split[k] is None}
            for part in range(n):
                inputs = dict(whole)
                inputs.update({k: pq.read_table(s[part]) for k, s in split.items() if s is not None})
                run = yamaa.spec(str(spec)).run(inputs=inputs)
                inputs.clear()
                if run.status != "succeeded":
                    first = (run.issues.to_pylist() or [{}])[0]
                    print(f"  helper {spec.name}: {run.status}: {first.get('rule', '')} "
                          f"{first.get('message', '')}"[:300])
                    return 2
                out = run.output.to_arrow()
                del run
                writer = writer or pq.ParquetWriter(dest, out.schema)
                writer.write_table(out)
        finally:
            if writer:
                writer.close()
            shutil.rmtree(work, ignore_errors=True)
        print(f"  helper {spec.name}: {pq.ParquetFile(dest).metadata.num_rows:,} rows in {n} partitions, "
              f"{time.time() - t0:.0f} s -> {dest.relative_to(ROOT)}")
        return 0
    inputs = {k: read_for(k, p, sp, vc) for k, p in paths.items()}
    run = yamaa.spec(str(spec)).run(inputs=inputs)
    inputs.clear()
    if run.status != "succeeded":
        first = (run.issues.to_pylist() or [{}])[0]
        print(f"  helper {spec.name}: {run.status}: {first.get('rule', '')} {first.get('message', '')}"[:300])
        return 2
    pq.write_table(run.output.to_arrow(), dest)
    print(f"  helper {spec.name}: {pq.ParquetFile(dest).metadata.num_rows:,} rows in {time.time() - t0:.0f} s "
          f"-> {dest.relative_to(ROOT)}")
    return 0


def expected_path(study, cut, dataset) -> Path | None:
    # A submitted ADaM dataset lives in data/adam/; a few were filed by the
    # sponsor as SDTM (BNT162-01 125742 ADCEVD, ADVA) and live in data/sdtm/.
    for cls in ("adam", "sdtm"):
        p = cut_dir(study, cut) / "data" / cls / f"{dataset}.parquet"
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------- verify
def verify_one(study, cut, spec: Path, report: Path, partitions: int) -> int:
    """Run one spec and compare it with the submitted dataset (child process)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import verify_compare as vc
    import yamaa

    info = studies()[study]
    rules = info["compare"]
    dataset = spec.stem
    rep = {"study": study, "cut": cut, "dataset": dataset.upper(), "spec": str(spec.relative_to(ROOT)),
           "comparison": {**rules, "redacted_not_compared": vc.REDACTED}}
    expected = expected_path(study, cut, dataset)
    if expected is None:
        rep.update(status="no expected", reason=f"no submitted {dataset} in {cut}/data/")
        report.write_text(json.dumps(rep, indent=2, default=str))
        print(f"  {cut}/{dataset}: no submitted dataset")
        return 3
    rep["expected"] = str(expected.relative_to(ROOT))
    hs = helpers(spec)
    if hs:
        rep["helpers"] = [str(h.relative_to(ROOT)) for h in hs]
    try:
        sp = resolved(spec)
    except Exception as e:  # noqa: BLE001
        rep.update(status="error", reason=str(e)[:500])
        report.write_text(json.dumps(rep, indent=2, default=str))
        print(f"  {cut}/{dataset}: error: {str(e)[:200]}")
        return 2
    inputs = {}
    for name, v in (sp.get("input") or {}).items():
        p = input_path(study, cut, v["path"] if isinstance(v, dict) else v)
        if not p.exists():
            rep.update(status="error", reason=f"input {name}: {p.relative_to(ROOT)} does not exist")
            report.write_text(json.dumps(rep, indent=2, default=str))
            print(f"  {cut}/{dataset}: missing input {p.relative_to(ROOT)}")
            return 2
        inputs[name] = p
    t0 = time.time()
    status, issues, cmp, ok, lines, derived, align = vc.verify_run(
        spec, inputs, expected, sp["keys"], float(rules["numeric_tolerance"]),
        bool(rules["string_remove_spaces"]), partitions, linked_inputs(sp))
    rep["seconds"] = round(time.time() - t0, 1)
    rep["partitions"] = partitions
    if status != "succeeded":
        first = issues[0] if issues else {}
        rep.update(status="error", issues=issues[:20],
                   reason=f"{first.get('rule', '')}: {first.get('message', status)}".strip(": "))
        report.write_text(json.dumps(rep, indent=2, default=str))
        print(f"  {cut}/{dataset}: error: {rep['reason'][:200]}")
        return 2
    cols = cmp["columns"].values()
    n_within = sum(c["within_tolerance"] for c in cols)
    n_space = sum(c["space_only_diffs"] for c in cols)
    n_red = sum(c.get("redacted_skipped", 0) for c in cols)
    n_mism = sum(c["mismatches"] for c in cols)
    strict = bool(ok and not (n_within or n_space or n_red))
    rep.update(cmp, derived_keys_set_aside=derived, alignment_keys=align, lines=lines[:200],
               exact_match=bool(ok), strict_exact_match=strict,
               status="exact" if strict else "exact under comparison rules" if ok else "mismatch")
    report.write_text(json.dumps(rep, indent=2, default=str))
    print(f"  {cut}/{dataset}: {rep['status']}  {cmp['expected_rows']:,} rows, {n_mism:,} cells differ"
          + (f", {n_red:,} redacted not compared" if n_red else ""))
    return 0 if ok else 1


def cmd_verify(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    summary = []
    for study, cut in scope(args):
        specs = sorted((cut_dir(study, cut) / "spec/yamaa").glob("*.yaml"))
        wanted = set(args.dataset.split(",")) if args.dataset else None
        specs = [s for s in specs if s.stem != "project" and (not wanted or s.stem in wanted)]
        print(f"== {study} {cut}: {len(specs)} specs")
        parts = studies()[study].get("partitions", {}).get(cut, {})
        built: set[Path] = set()
        for spec in specs:
            report = out / f"{study}-{cut}-{spec.stem}.json"
            failed = None
            try:
                hs = helpers(spec)
            except Exception as e:  # noqa: BLE001  a spec that does not resolve is reported, not raised
                report.write_text(json.dumps({"study": study, "cut": cut, "dataset": spec.stem.upper(),
                                              "spec": str(spec.relative_to(ROOT)), "status": "error",
                                              "reason": str(e)[:500]}, indent=2))
                print(f"  {cut}/{spec.stem}: error: {str(e)[:200]}")
                summary.append("error")
                continue
            for h in hs:
                if h in built:
                    continue
                r = subprocess.run([sys.executable, __file__, "_helper", study, cut, str(h)],
                                   env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")})
                if r.returncode:
                    failed = h
                    break
                built.add(h)
            if failed:
                report.write_text(json.dumps({"study": study, "cut": cut, "dataset": spec.stem.upper(),
                                              "spec": str(spec.relative_to(ROOT)), "status": "error",
                                              "reason": f"helper {failed.relative_to(ROOT)} failed"}, indent=2))
                summary.append("error")
                continue
            n = max(args.partitions, parts.get(spec.stem, 1))
            # One process per dataset, so memory is returned between datasets.
            r = subprocess.run([sys.executable, __file__, "_verify_one", study, cut, str(spec), str(report), str(n)],
                               env={**os.environ, "PYTHONPATH": str(ROOT / "scripts")})
            if r.returncode not in (0, 1, 2, 3):  # killed (out of memory) or crashed
                report.write_text(json.dumps({"study": study, "cut": cut, "dataset": spec.stem.upper(),
                                              "spec": str(spec.relative_to(ROOT)), "status": "error",
                                              "reason": f"the run stopped (exit {r.returncode}); raise its "
                                                        f"partitions in studies.yaml"}, indent=2))
                print(f"  {cut}/{spec.stem}: run stopped (exit {r.returncode})")
            summary.append(json.loads(report.read_text())["status"])
    from collections import Counter
    print("== summary:", dict(Counter(summary)), "| reports in", out)


# ---------------------------------------------------------------- define
def cmd_define(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    bad = 0
    for study, cut in scope(args):
        d = cut_dir(study, cut) / "spec/define"
        received = d / "define-adam.xml"
        if not received.exists():  # a supplement submitted without a define
            print(f"  {study}/{cut}: no define in this deliverable")
            continue
        if args.transcribe:
            over = studies()[study]["cuts"][cut].get("over")
            subprocess.run([sys.executable, str(ROOT / "scripts/define/transcribe_define.py"),
                            "--received", str(received), "--cut-dir", str(cut_dir(study, cut))]
                           + (["--over", str(cut_dir(study, over))] if over else []), check=True)
        subprocess.run([sys.executable, str(ROOT / "scripts/define/compose_define.py"), str(d / "project.yaml")],
                       check=True)
        report = out / f"define-{study}-{cut}.json"
        subprocess.run([sys.executable, str(ROOT / "scripts/define/compare_define.py"), str(received),
                        str(d / "define-adam-yamaa.xml"), "--json", str(report)], capture_output=True, text=True)
        r = json.loads(report.read_text())
        n = len(r["unexplained"])
        bad += n
        print(f"  {study}/{cut}: {r['verdict']} ({n} unexplained)")
    return 1 if bad else 0


# ---------------------------------------------------------------- fetch
def cmd_fetch(args):
    sys.path.insert(0, str(ROOT / "scripts"))
    from fetch_phmpt import fetch  # noqa: PLC0415

    return fetch([(s, c) for s, c in scope(args, with_data_cuts=True)], args.dataset, args.out_data, args.dry_run)


# ---------------------------------------------------------------- site
def cmd_site(args):
    subprocess.run([sys.executable, str(ROOT / "scripts/site/collect_results.py"), "--reports", args.out], check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/site/build_pages.py")], check=True)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "_helper":
        return run_helper(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
    if len(sys.argv) > 1 and sys.argv[1] == "_verify_one":
        study, cut, spec, report, n = sys.argv[2:7]
        return verify_one(study, cut, Path(spec), Path(report), int(n))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "verify", "define", "site"):
        p = sub.add_parser(name)
        p.add_argument("--study"); p.add_argument("--cut")
        p.add_argument("--out", default=str(ROOT / ".local-run/reports"), help="report folder")
        if name in ("fetch", "verify"):
            p.add_argument("--dataset", help="one dataset (spec stem), e.g. adsl; verify also takes a "
                                              "comma-separated list, building shared helpers once")
        if name == "verify":
            p.add_argument("--partitions", type=int, default=1,
                           help="at least this many USUBJID partitions (studies.yaml may ask for more)")
        if name == "define":
            p.add_argument("--transcribe", action="store_true",
                           help="regenerate the reproduced-mode layers from the received define first")
        if name == "fetch":
            p.add_argument("--out-data", default=None,
                           help="write fetched Parquet here instead of the repo's <cut>/data/ (to compare)")
            p.add_argument("--dry-run", action="store_true", help="list what would be fetched")
    args = ap.parse_args()
    return {"fetch": cmd_fetch, "verify": cmd_verify, "define": cmd_define, "site": cmd_site}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())

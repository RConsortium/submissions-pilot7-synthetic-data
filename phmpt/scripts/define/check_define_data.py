#!/usr/bin/env python3
"""Check each received define against the submitted ADaM datasets it describes.

    python scripts/define/check_define_data.py [--data-root DIR]

For every cut with a received define (<study>/<cut>/spec/define/define-adam.xml)
the received define is compared with the ADaM datasets PHMPT released for that
cut (data/sources.csv; two BNT162-01 datasets were released in the SDTM folder).
Both files are the sponsor's; yamaa is not involved. A finding is one place
where the two disagree:

    dataset        a dataset the define describes that the release lacks, or one
                   the release has that the define does not describe
    variable       a variable the define lists that the dataset lacks, or a
                   column of the dataset the define does not list
    type           the define says text and the column is numeric, or the define
                   says integer or float and the column is character
    length         a text value longer than the define's Length
    codelist       values outside the variable's enumerated codelist
    mandatory      a variable the define marks Mandatory="Yes" with missing values
    key            the define's key variables do not identify one record
    label          a column label that differs from the variable's Description
    dataset label  the dataset label differs from the dataset's Description

Release artifacts are kept apart (`artifact`). "redaction": FDA rewrote the
files it redacted (a file holding "(b)(6)" values), so in them a column's type
and label and the dataset label can come from that rewrite, and a redacted
variable can be renamed (BRTHDT to BRTHDT_2, holding only "(b)(6)"). "jmp": the
type, length and labels of a file PHMPT released only as a JMP table come from
the conversion. Redacted values are never counted as codelist or length
findings.

Writes data/reproduction/define_data.json. Reads the Parquet files under
--data-root (default: this folder, after `python scripts/reproduce.py fetch`
of every study; or a folder of the same layout that holds the fetched data).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[2]
REDACTED = "(b)(6)"
CHECKS = {
    "dataset": "Dataset described by the define but not released, or released but not described",
    "variable": "Variable listed by the define but not in the dataset, or in the dataset but not listed",
    "type": "Define data type and column type disagree (text vs numeric)",
    "length": "Text values longer than the define's Length",
    "codelist": "Values outside the variable's enumerated codelist",
    "mandatory": "Mandatory variable with missing values",
    "key": "Define key variables do not identify one record",
    "label": "Column label differs from the define's Description",
    "dataset label": "Dataset label differs from the define's Description",
}


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def attr(el, name: str):
    for k, v in el.attrib.items():
        if local(k) == name:
            return v
    return None


def text_of(el) -> str:
    """The first TranslatedText under an element's Description."""
    for d in el:
        if local(d.tag) == "Description":
            for t in d.iter():
                if local(t.tag) == "TranslatedText":
                    return " ".join((t.text or "").split())
    return ""


def read_define(path: Path) -> dict:
    root = ET.parse(path).getroot()
    items, lists, groups = {}, {}, {}
    for el in root.iter():
        tag = local(el.tag)
        if tag == "ItemDef":
            ref = next((attr(c, "CodeListOID") for c in el if local(c.tag) == "CodeListRef"), None)
            items[attr(el, "OID")] = {"name": attr(el, "Name"), "type": attr(el, "DataType"),
                                      "length": attr(el, "Length"), "label": text_of(el), "codelist": ref}
        elif tag == "CodeList":
            terms = [c for c in el if local(c.tag) in ("EnumeratedItem", "CodeListItem")]
            vals = [attr(c, "CodedValue") for c in terms]
            # A decoded codelist also admits its decodes: some defines bind PARAM to the PARAMCD codelist.
            decodes = [" ".join(t.text.split()) for c in terms for t in c.iter()
                       if local(t.tag) == "TranslatedText" and t.text]
            external = any(local(c.tag) == "ExternalCodeList" for c in el)
            lists[attr(el, "OID")] = {"type": attr(el, "DataType"), "values": vals, "decodes": decodes,
                                      "external": external}
        elif tag == "ItemGroupDef":
            refs = [{"oid": attr(c, "ItemOID"), "order": int(attr(c, "OrderNumber") or 0),
                     "mandatory": attr(c, "Mandatory") == "Yes", "key": int(attr(c, "KeySequence") or 0)}
                    for c in el if local(c.tag) == "ItemRef"]
            groups[attr(el, "Name").upper()] = {"label": text_of(el), "refs": refs}
    return {"items": items, "lists": lists, "groups": groups}


def released(study: str, cut: str) -> dict[str, tuple[str, str]]:
    """{DATASET: (file, format)}: the ADaM datasets the release holds for a cut. ADaM datasets are
    named AD*; BNT162-01 BLA S1 released ADCEVD and ADVA in its SDTM folder."""
    out = {}
    with open(ROOT / "data/sources.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["study"] != study or r["cut"] != cut or not r["path"].endswith(".parquet"):
                continue
            name = Path(r["path"]).stem.upper()
            if "/data/adam/" in r["path"] or ("/data/sdtm/" in r["path"] and name.startswith("AD")):
                out[name] = (r["path"], r["format"])
    return out


def is_char(t) -> bool | None:
    import pyarrow as pa
    if pa.types.is_null(t):
        return None
    return pa.types.is_string(t) or pa.types.is_large_string(t)


def check_dataset(ds: str, path: Path, fmt: str, group: dict, d: dict) -> tuple[list, dict]:
    """The findings for one released dataset the define describes."""
    out: list = []
    pf = pq.ParquetFile(path)
    schema = pf.schema_arrow
    cols = schema.names
    nrows = pf.metadata.num_rows
    jmp = "jmp" if fmt == "jmp" else None

    def add(check, variable=None, artifact=None, **kw):
        out.append({"dataset": ds, "variable": variable, "check": check, "artifact": artifact, **kw})

    refs = [(r, d["items"].get(r["oid"])) for r in sorted(group["refs"], key=lambda r: r["order"])]
    refs = [(r, it) for r, it in refs if it]
    listed = {it["name"].upper(): (r, it) for r, it in refs}
    present = {c.upper(): c for c in cols}
    char = {c: is_char(schema.field(c).type) for c in cols}

    lf = pl.scan_parquet(path)
    exprs = []
    for c in cols:
        col = pl.col(c)
        if char[c]:
            blank = col.is_null() | (col.str.strip_chars() == "")
            exprs += [col.filter(col != REDACTED).str.len_chars().max().alias(f"len|{c}"),
                      blank.sum().alias(f"miss|{c}"), (col == REDACTED).sum().alias(f"red|{c}"),
                      (~blank & (col != REDACTED)).sum().alias(f"kept|{c}")]
            it = listed.get(c.upper(), (None, {}))[1]
            if it.get("type") in ("integer", "float"):
                ok = col.str.strip_chars().cast(pl.Float64, strict=False).is_not_null()
                exprs.append((~blank & (col != REDACTED) & ~ok).sum().alias(f"nonnum|{c}"))
        elif char[c] is False:
            exprs.append(col.is_null().sum().alias(f"miss|{c}"))
    stats = lf.select(exprs).collect(engine="streaming").row(0, named=True) if exprs else {}
    # FDA rewrote the files it redacted: in them a column's type and label, and the dataset label, can come
    # from that rewrite (C4591001 ADMH: dates stored as text, dataset labels set to file names).
    redacted = "redaction" if any(stats.get(f"red|{c}", 0) for c in cols) else None
    rewritten = jmp or redacted

    # A redacted variable FDA renamed: a column holding only (b)(6), named after a define-only variable + _<n>.
    renamed = {}
    for name, c in present.items():
        m = re.fullmatch(r"(.+)_\d+", name)
        if (name not in listed and m and m.group(1) in listed and m.group(1) not in present
                and stats.get(f"red|{c}", 0) and not stats.get(f"kept|{c}", 0)):
            renamed[m.group(1)] = c
    for name in listed:
        if name not in present:
            add("variable", name, "redaction" if name in renamed else None, side="define only")
    for name, c in present.items():
        if name not in listed:
            add("variable", c, "redaction" if c in renamed.values() else None, side="data only")
    meta_label = (schema.metadata or {}).get(b"dataset_label", b"").decode("utf-8", "replace")
    if meta_label and group["label"] and " ".join(meta_label.split()) != group["label"]:
        add("dataset label", None, rewritten, define=group["label"], data=" ".join(meta_label.split()))

    plan = []
    for name, (r, it) in listed.items():
        if name not in present:
            continue
        c = present[name]
        fld = schema.field(c)
        lab = (fld.metadata or {}).get(b"sas_label", b"").decode("utf-8", "replace")
        if lab and it["label"] and " ".join(lab.split()) != it["label"]:
            add("label", c, rewritten, define=it["label"], data=" ".join(lab.split()))
        plan.append((c, r, it, char[c], it["type"]))

    for c, r, it, ch, dtype in plan:
        if ch is True and dtype in ("integer", "float"):
            add("type", c, rewritten, define=dtype, data="character")
        elif ch is False and dtype == "text":
            add("type", c, rewritten, define=dtype, data="numeric")
        if ch and dtype == "text" and it["length"]:
            mx = stats.get(f"len|{c}") or 0
            if mx > int(it["length"]):
                add("length", c, jmp, define=int(it["length"]), data=mx)
        if r["mandatory"]:
            n = nrows if ch is None else stats.get(f"miss|{c}", 0)  # a column of nulls only has no type
            if n:
                add("mandatory", c, None, count=n, rows=nrows)

    for c, r, it, ch, dtype in plan:  # codelists: the distinct values, one column at a time
        cl = d["lists"].get(it["codelist"]) if it["codelist"] else None
        if not cl or cl["external"] or not cl["values"] or ch is None:
            continue
        vals = [v for v in lf.select(pl.col(c).unique()).collect(engine="streaming").to_series().to_list()
                if v is not None]
        if ch:
            allowed = {" ".join(v.split()) for v in cl["values"]} | set(cl["decodes"])
            seen = {" ".join(v.split()) for v in vals if v.strip() and v != REDACTED}
        else:
            try:
                allowed = {round(float(v), 6) for v in cl["values"]}
            except ValueError:
                continue  # a numeric column bound to a text codelist: reported by the type check if at all
            seen = {round(float(v), 6) for v in vals}
        outside = seen - allowed
        if outside:
            add("codelist", c, None, codelist=it["codelist"], values=len(outside), of=len(seen))

    keys = [listed[k][1]["name"] for k in listed if listed[k][0]["key"]]
    keys = [present[k.upper()] for k in sorted(keys, key=lambda k: listed[k.upper()][0]["key"])
            if k.upper() in present]
    if keys and len(keys) == sum(1 for r, _ in refs if r["key"]):
        uniq = lf.select(pl.struct(keys).n_unique()).collect(engine="streaming").item()
        if uniq < nrows:
            add("key", ", ".join(keys), None, count=nrows - uniq, rows=nrows)
    info = {"format": fmt, "rows": nrows, "columns": len(cols), "variables": len(listed)}
    return out, info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=ROOT)
    ap.add_argument("--only", help="study/cut to check (default: every cut with a define)")
    args = ap.parse_args()
    studies = yaml.safe_load((ROOT / "studies.yaml").read_text())
    out_path = ROOT / "data/reproduction/define_data.json"
    result = {"meta": {"collected": dt.date.today().isoformat()}, "checks": CHECKS, "cuts": {}}
    if args.only and out_path.exists():
        result["cuts"] = json.loads(out_path.read_text())["cuts"]
    unfetched = []
    for study, st in studies.items():
        for cut in st["cuts"]:
            key = f"{study}/{cut}"
            if args.only and key != args.only:
                continue
            dpath = args.data_root / study / cut / "spec/define/define-adam.xml"
            if not dpath.exists():
                continue
            d = read_define(dpath)
            rel = released(study, cut)
            findings, datasets = [], {}
            for ds in sorted(set(d["groups"]) | set(rel)):
                if ds not in rel:
                    findings.append({"dataset": ds, "variable": None, "check": "dataset", "artifact": None,
                                     "side": "define only"})
                    continue
                if ds not in d["groups"]:
                    findings.append({"dataset": ds, "variable": None, "check": "dataset", "artifact": None,
                                     "side": "data only"})
                    continue
                path = args.data_root / rel[ds][0]
                if not path.exists() or path.open("rb").read(4) != b"PAR1":  # not fetched
                    unfetched.append(rel[ds][0])
                    continue
                f, info = check_dataset(ds, path, rel[ds][1], d["groups"][ds], d)
                findings += f
                datasets[ds] = info
                print(f"{key} {ds}: {len(f)} findings", flush=True)
            result["cuts"][key] = {"define": f"{study}/{cut}/spec/define/define-adam.xml",
                                   "datasets": datasets, "findings": findings}
    if unfetched:  # partial results would undercount: write nothing
        print(f"{len(unfetched)} datasets are not fetched (scripts/reproduce.py fetch, or --data-root), e.g. {unfetched[0]}; "
              "nothing written", file=sys.stderr)
        return 1
    out_path.write_text(json.dumps(result, indent=1) + "\n")
    print(f"wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

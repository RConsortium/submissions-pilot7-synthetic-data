#!/usr/bin/env python3
"""Check a PHMPT publication bundle: the gate every publication passes twice.

    python scripts/publish/check_bundle.py ROOT [--source REPO]

ROOT is a folder holding the bundle as it lands in Pilot 7: `phmpt/` (the
specs, the scripts and the citations) and `docs/phmpt/` (the pages and
`evidence.json`). yamaa_phmpt runs this on its export with `--source` set
to its own checkout; Pilot 7 runs a vendored copy of this file, unchanged,
on every pull request, without `--source`.

The rules (docs/publication.md, "The publication gate"):

1. every file matches the allowlist below, and no file has a data or
   document suffix;
2. every file is ASCII text and the bundle stays under MAX_BYTES;
3. docs/phmpt/evidence.json has exactly the shape of EVIDENCE: no field
   the schema does not name;
4. no subject identifier appears in any file: the identifier patterns of
   the four studies always, and with --source every USUBJID and SUBJID of
   every cut's DM;
5. with --source, no run of SHINGLE words of the bundle's prose also occurs
   in the sponsor's programs (`<study>/spec/source/program/`) or in the text
   of a received define (`<cut>/spec/define/define-adam.xml`). Prose is what
   a person wrote about the data (prose()): page text outside code, the
   reasons and claims of evidence.json and differences.yaml, the comments of
   the scripts and specs, and any description, method or comment a spec
   keeps. The specs' expressions, names, labels and value maps are left out:
   they state what the submitted data holds, which a reproduction must.

It prints one line per violation and exits 1 if there is any. It needs only
the standard library, plus pyarrow for --source.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

STUDIES = ("mrna-1273-p201", "mrna-1273-p301", "bnt162-01", "c4591001")
_S = "(?:" + "|".join(re.escape(s) for s in STUDIES) + ")"
_CUT = r"[a-z0-9][a-z0-9-]*"

# Every path the bundle may hold, relative to ROOT. Anything else fails.
ALLOWED = [re.compile(p) for p in (
    r"phmpt/(README|NOTICE)\.md",
    r"phmpt/reproduce\.sh",
    r"phmpt/\.gitignore",
    r"phmpt/(studies\.yaml|yamaa\.lock|requirements\.txt)",
    r"phmpt/data/(sources\.csv|zips\.txt|differences\.yaml)",
    r"phmpt/scripts/[a-z0-9_/]+\.py",
    r"phmpt/scripts/define/repro/[a-z0-9_]+\.yaml",
    rf"phmpt/{_S}/spec/yamaa/base/[a-z0-9_-]+\.yaml",
    rf"phmpt/{_S}/{_CUT}/spec/yamaa/(helper/)?[a-z0-9_-]+\.yaml",
    r"docs/phmpt/evidence\.json",
    r"docs/phmpt/(index|coverage|glossary)\.md",
    r"docs/phmpt/findings/[a-z0-9-]+\.md",
    r"docs/phmpt/review/index\.md",
)]
# Never published, whatever the allowlist says (docs/publication.md, tiers).
DENIED_SUFFIXES = {".parquet", ".xpt", ".jmp", ".sas", ".sas7bdat", ".pdf", ".xsl", ".xml",
                   ".zip", ".csv.gz", ".xlsx", ".xls", ".docx", ".rtf"}
MAX_BYTES = 20_000_000
SHINGLE = 12

# Subject identifiers as each study writes them (USUBJID, and SUBJID where
# it is distinctive). Checked even when the data is not at hand.
ID_PATTERNS = [re.compile(p) for p in (
    r"\bBNT162-01-\d{3}-\d{2}-\d{4}\b",
    r"\bC4591001[ _-]\d{4}[ _-]\d{8}\b",
    r"\bmRNA-1273-P\d{3}-[A-Z]{2}\d{3}-\d{4}\b",
    r"\b(?:US|CA)\d{7}\b",
)]

# The closed shape of evidence.json. A dict lists every key it may hold
# ("*" for a map with free keys); a list holds items of its one shape; a
# tuple is one of several shapes; a type is a leaf.
_INT, _STR, _BOOL = int, str, bool
_COUNTS = {"*": _INT}
_DATASET = {
    "dataset": _STR, "verdict": _STR, "spec": _STR, "spec_lines": _INT, "layers": [_STR],
    "rows": _INT, "cols": _INT, "cells": _INT, "out_rows": _INT, "out_cols": _INT,
    "mismatched_cells": _INT, "within_tolerance_cells": _INT, "space_only_cells": _INT,
    "redacted_cells": _INT, "mismatched_columns": _COUNTS, "redacted_columns": _COUNTS,
    "missing_columns": [_STR], "extra_columns": [_STR], "carried_columns": [_STR],
    "multiset": _BOOL, "rows_unpaired": _INT, "partitions": _INT,
    "missing_input": ({"missing": _STR, "reason": _STR, "decided": _STR, "columns": [_STR],
                       "cells": _COUNTS}, None),
    "submitted_defect": ({"defect": _STR, "reason": _STR, "decided": _STR, "columns": [_STR],
                          "cells": _COUNTS}, None),
    "reasons": [{"kind": _STR, "reason": _STR, "cells": _COUNTS}],
    "unexplained_columns": [_STR],
    "note": (_STR, None),
    "source": ({"zip": _STR, "member": _STR}, None),
}
_DEFINE = {
    "verdict": _STR, "received": _INT, "identical": _INT, "gap_only": _INT, "no_spec": _INT,
    "no_spec_datasets": [_STR], "unexplained": _INT, "gaps": _COUNTS,
    "classes": {"*": {"submitted": _INT, "generated": _INT, "match": _INT, "gap_only": _INT,
                      "no_spec": _INT}},
    "source": {"zip": _STR, "member": _STR},
}
EVIDENCE = {
    "schema_version": _INT,
    "meta": {"yamaa_commit": _STR, "source_commit": _STR, "collected": _STR},
    "gaps": {"*": {"title": _STR, "yamaa_issue": _INT}},
    "studies": {"*": {
        "title": _STR, "sponsor": _STR, "product": _STR,
        "cuts": {"*": {"title": _STR, "application": _STR, "sequence": _STR, "over": (_STR, None),
                       "datasets": [_DATASET], "define": (_DEFINE, None)}},
    }},
    "findings": [{"id": _STR, "kind": _STR, "study": _STR, "cut": _STR, "dataset": (_STR, None),
                  "verdict": _STR, "claim": _STR, "page": _STR, "reproduce": [_STR]}],
}
SCHEMA_VERSION = 1


def shape_errors(value, shape, where="evidence.json") -> list[str]:
    """Where `value` leaves `shape`: a missing or unnamed key, or a wrong type."""
    if isinstance(shape, tuple):
        for alt in shape:
            if alt is None and value is None or alt is not None and not shape_errors(value, alt, where):
                return []
        return [f"{where}: {type(value).__name__} matches none of its allowed shapes"]
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            return [f"{where}: expected an object"]
        if set(shape) == {"*"}:
            return [e for k, v in value.items() for e in shape_errors(v, shape["*"], f"{where}.{k}")]
        out = [f"{where}.{k}: not in the published schema" for k in value if k not in shape]
        out += [f"{where}.{k}: missing" for k in shape if k not in value]
        return out + [e for k, v in value.items() if k in shape for e in shape_errors(v, shape[k], f"{where}.{k}")]
    if isinstance(shape, list):
        if not isinstance(value, list):
            return [f"{where}: expected a list"]
        return [e for i, v in enumerate(value) for e in shape_errors(v, shape[0], f"{where}[{i}]")]
    if shape is int and isinstance(value, bool) or not isinstance(value, shape):
        return [f"{where}: expected {shape.__name__}"]
    return []


def bundle_files(root: Path) -> list[Path]:
    out = []
    for top in ("phmpt", "docs/phmpt"):
        base = root / top
        if base.is_dir():
            out += sorted(p for p in base.rglob("*") if p.is_file())
    return out


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def shingles(text: str) -> set[tuple]:
    w = words(text)
    return {tuple(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


PROSE_KEYS = ("reason", "missing", "claim", "note", "description", "method", "comment")
_KEYED = re.compile(r"^(\s*-?\s*)(" + "|".join(PROSE_KEYS) + r"):\s?(.*)$")


def _yaml_prose(text: str) -> str:
    """Comments, and the values of PROSE_KEYS with their continuation lines."""
    out, indent = [], None
    for line in text.splitlines():
        stripped = line.lstrip()
        depth = len(line) - len(stripped)
        if indent is not None and stripped and depth > indent and not stripped.startswith("#"):
            out.append(stripped)
            continue
        indent = None
        m = _KEYED.match(line)
        if m:
            out.append(m.group(3))
            indent = len(m.group(1).replace("-", " ").rstrip(" ")) if m.group(1).strip() else len(m.group(1))
            continue
        hash_at = line.find(" #") if not stripped.startswith("#") else depth - 1
        if hash_at >= 0 or stripped.startswith("#"):
            out.append(line[hash_at + 1:].lstrip("# "))
    return "\n".join(out)


def prose(rel: str, text: str) -> str:
    """The part of a bundle file a person wrote about the data (rule 5)."""
    if rel.endswith(".md"):
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        return re.sub(r"`[^`]*`", " ", text)
    if rel.endswith(".json"):
        found: list[str] = []

        def walk(v, key=None):
            if isinstance(v, dict):
                for k, x in v.items():
                    walk(x, k)
            elif isinstance(v, list):
                for x in v:
                    walk(x, key)
            elif isinstance(v, str) and key in PROSE_KEYS:
                found.append(v)
        walk(json.loads(text))
        return "\n".join(found)
    if rel.endswith((".yaml", ".yml")):
        return _yaml_prose(text)
    return text


def subject_ids(source: Path) -> set[str]:
    """Every USUBJID, and every SUBJID that is not a short number, of every cut's DM."""
    import pyarrow.parquet as pq

    ids: set[str] = set()
    for dm in sorted(source.glob("*/*/data/sdtm/dm.parquet")):
        if dm.stat().st_size < 1024:  # a Git LFS pointer, not the data
            raise SystemExit(f"{dm} is not pulled: git lfs pull -I '**/sdtm/dm.parquet'")
        t = pq.read_table(dm, columns=["USUBJID", "SUBJID"]).to_pydict()
        ids.update(v.strip() for v in t["USUBJID"] if v and v.strip())
        ids.update(v.strip() for v in t["SUBJID"] if v and (len(v.strip()) >= 8 or not v.strip().isdigit()))
    return ids


def sponsor_shingles(source: Path) -> set[tuple]:
    """Word runs of the sponsor's programs and of the text of every received define."""
    import xml.etree.ElementTree as ET

    out: set[tuple] = set()
    for f in sorted(source.glob("*/spec/source/program/**/*")):
        if f.is_file() and f.suffix.lower() in {".txt", ".sas"}:
            out |= shingles(f.read_text(errors="replace"))
    for d in sorted(source.glob("*/*/spec/define/define-adam.xml")):
        text = " ".join(e.text or "" for e in ET.parse(d).iter() if e.tag.endswith("TranslatedText"))
        out |= shingles(text)
    return out


def check(root: Path, source: Path | None = None) -> list[str]:
    errors: list[str] = []
    files = bundle_files(root)
    if not any(f.relative_to(root).as_posix() == "docs/phmpt/evidence.json" for f in files):
        errors.append("docs/phmpt/evidence.json: missing")
    total = 0
    texts: dict[str, str] = {}
    for f in files:
        rel = f.relative_to(root).as_posix()
        total += f.stat().st_size
        if any(rel.lower().endswith(s) for s in DENIED_SUFFIXES):
            errors.append(f"{rel}: a data or document file; never published")
            continue
        if not any(p.fullmatch(rel) for p in ALLOWED):
            errors.append(f"{rel}: not in the publication allowlist")
            continue
        raw = f.read_bytes()
        bad = next((i for i, b in enumerate(raw) if b > 0x7F), None)
        if bad is not None:
            line = raw.count(b"\n", 0, bad) + 1
            errors.append(f"{rel}:{line}: non-ASCII byte 0x{raw[bad]:02X}")
            continue
        texts[rel] = raw.decode("ascii")
    if total > MAX_BYTES:
        errors.append(f"bundle: {total:,} bytes, more than {MAX_BYTES:,}")
    if "docs/phmpt/evidence.json" in texts:
        try:
            ev = json.loads(texts["docs/phmpt/evidence.json"])
        except ValueError as e:
            errors.append(f"docs/phmpt/evidence.json: not JSON ({e})")
        else:
            errors += shape_errors(ev, EVIDENCE)
            if ev.get("schema_version") != SCHEMA_VERSION:
                errors.append(f"docs/phmpt/evidence.json: schema_version is not {SCHEMA_VERSION}")
    for rel, text in texts.items():
        for p in ID_PATTERNS:
            m = p.search(text)
            if m:
                errors.append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}: a subject identifier pattern")
                break
    if source is not None:
        ids = subject_ids(source)
        for rel, text in texts.items():
            tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text)
            grams = set(tokens) | {" ".join(tokens[i:i + 3]) for i in range(len(tokens) - 2)}
            hit = sorted(grams & ids)
            if hit:
                errors.append(f"{rel}: holds {len(hit)} subject identifier(s) of the submitted data")
        sponsor = sponsor_shingles(source)
        for rel, text in texts.items():
            try:
                common = shingles(prose(rel, text)) & sponsor
            except ValueError:  # evidence.json that is not JSON is reported above
                continue
            if common:
                errors.append(f"{rel}: {len(common)} run(s) of {SHINGLE} words copied from a sponsor "
                              f"program or define, e.g. '{' '.join(sorted(common)[0])}'")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", type=Path, help="folder holding phmpt/ and docs/phmpt/")
    ap.add_argument("--source", type=Path, help="the yamaa_phmpt checkout, for the data-backed checks")
    args = ap.parse_args()
    errors = check(args.root.resolve(), args.source.resolve() if args.source else None)
    for e in errors:
        print(f"ERROR: {e}")
    n = len(bundle_files(args.root))
    print(f"PHMPT bundle check: {n} file(s), {len(errors)} error(s)"
          + ("" if args.source else " (no --source: identifier patterns only, no copied-text check)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

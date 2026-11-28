#!/usr/bin/env python3
"""Rewrite a later cut's specs as layers over the earlier cut's specs.

Two cuts of one study usually run the same derivations: the later cut's spec
repeats the earlier one with a few changes (a renamed input file, a new
column, an updated mapping). yamaa composes a spec with its `parent` chain
(LAYER-1..LAYER-9), so the later spec can name the earlier one as its parent
and keep only what differs:

  * keyed members (`columns`, `rows`, `intermediates`, `windows` and
    `input`) are written only when new or changed, and a changed member
    writes only its changed fields (LAYER-5, LAYER-6);
  * `output` and `submission` write only their changed fields;
  * any other root field is written when it differs (it replaces whole);
  * a field the earlier spec writes and the later one does not is listed
    under `clear` (LAYER-9).

Input and output paths are always restated, so every path still resolves
beside the later cut's spec (LAYER-10).

Every rewrite is checked before it is written: yamaa resolves the new layer
and the original file, and the two resolved specifications must be equal.
A dataset whose difference cannot be expressed this way (for example a row
template the earlier spec has and the later one drops) keeps its
standalone file, and the tool says why.

    python scripts/specs/inherit_cut.py --parent-cut mrna-1273-p201/s3-d57 \
        --child-cut mrna-1273-p201/s3-add1 [--write]
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

KEYED = {"columns": "name", "rows": "id", "intermediates": "id"}
KEYED_BY_KEY = {"windows", "input"}
BLOCKS = {"output", "submission"}
SKIP = {"yamaa", "type", "encoding", "parent", "clear", "include"}


class Replace:
    def __init__(self, value):
        self.value = value


def seg(key: str) -> str:
    return f".{key}" if re.fullmatch(r"[A-Za-z0-9_-]+", str(key)) else "['" + str(key).replace("'", "''") + "']"


def is_map(v):
    return isinstance(v, dict)


def delta(p, c, path: str, clears: list):
    """What a layer over `p` writes to obtain `c` (None when equal)."""
    if is_map(p) and is_map(c):
        if len(p) == 1 and len(c) == 1 and list(p)[0] != list(c)[0]:
            # A registry value (one keyword) naming another keyword replaces.
            return Replace(c)
        out = CommentedMap()
        for k, v in c.items():
            if k not in p:
                out[k] = v
                continue
            d = delta(p[k], v, path + seg(k), clears)
            if isinstance(d, Replace):
                out[k] = d.value
            elif d is not None:
                out[k] = d
        for k in p:
            if k not in c:
                clears.append(path + seg(k))
        return out or None
    if plain(p) == plain(c):
        return None
    return Replace(c)


def plain(v):
    return json.loads(json.dumps(v, default=str))


def keyed_delta(pl, cl, idf, root, clears, notes):
    pm = {m[idf]: m for m in (pl or [])}
    out = CommentedSeq()
    for m in cl or []:
        mid = m[idf]
        if mid not in pm:
            out.append(m)
            continue
        d = delta(pm[mid], m, f"{root}{seg(mid)}", clears)
        if isinstance(d, Replace):
            notes.append(f"{root} {mid}: member replaced whole")
            out.append(d.value)
        elif d is not None:
            nm = CommentedMap()
            nm[idf] = mid
            for k, v in d.items():
                nm[k] = v
            out.append(nm)
    dropped = [k for k in pm if k not in {m[idf] for m in (cl or [])}]
    return out, dropped


def by_key_delta(pd, cd, root, clears, restate_paths):
    out = CommentedMap()
    for k, v in (cd or {}).items():
        if k not in (pd or {}):
            out[k] = v
            continue
        d = delta(pd[k], v, f"{root}{seg(k)}", clears)
        if isinstance(d, Replace):
            out[k] = d.value
        elif d is not None:
            out[k] = d
        elif restate_paths:
            # Restate the path so it resolves beside this layer (LAYER-10).
            if isinstance(v, str):
                out[k] = v
            elif is_map(v) and "path" in v:
                out[k] = CommentedMap(path=v["path"])
    dropped = [k for k in (pd or {}) if k not in (cd or {})]
    return out, dropped


def build_layer(pdoc, cdoc, parent_rel):
    clears: list[str] = []
    notes: list[str] = []
    new = CommentedMap()
    new["yamaa"] = cdoc["yamaa"]
    new["type"] = cdoc["type"]
    if "encoding" in cdoc:
        # A file's encoding describes its own bytes (SPEC-8): never inherited.
        new["encoding"] = cdoc["encoding"]
    new["parent"] = parent_rel
    body = CommentedMap()
    for k, v in cdoc.items():
        if k in SKIP:
            continue
        pv = pdoc.get(k)
        if k in KEYED:
            d, dropped = keyed_delta(pv, v, KEYED[k], k, clears, notes)
            if dropped:
                notes.append(f"{k}: the parent has {dropped}, this cut does not")
            if d:
                body[k] = d
        elif k in KEYED_BY_KEY:
            d, dropped = by_key_delta(pv, v, k, clears, restate_paths=(k == "input"))
            if d:
                body[k] = d
        elif k in BLOCKS:
            d = delta(pv or {}, v, k, clears)
            if k == "output":
                d = d if isinstance(d, CommentedMap) else CommentedMap()
                d["path"] = v["path"]  # always beside this layer (LAYER-10)
                d.move_to_end("path", last=False)
            if isinstance(d, Replace):
                d = d.value
            if d:
                body[k] = d
        else:
            if plain(pv) != plain(v):
                body[k] = v
    for k in pdoc:
        if k not in cdoc and k not in SKIP:
            clears.append(k)
    if clears:
        new["clear"] = CommentedSeq(dict.fromkeys(clears))
    for k, v in body.items():
        new[k] = v
    return new, notes


def leading_comment(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("#") or (not line.strip() and lines):
            lines.append(line)
        else:
            break
    return "\n".join(lines).rstrip() + "\n" if lines else ""


def resolved(path: Path):
    import yamaa

    spec = yamaa.spec(str(path)).resolve()["entries"][0]["specification"]
    return canonical(spec)


def canonical(spec):
    s = plain(spec)
    for k, idf in KEYED.items():
        if isinstance(s.get(k), list):
            s[k] = {m[idf]: m for m in s[k]}
    return s


def first_diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return f"{path}/{k}: only in {'new' if k in b else 'original'}"
            d = first_diff(a[k], b[k], f"{path}/{k}")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {json.dumps(a)[:120]} vs {json.dumps(b)[:120]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parent-cut", type=Path, required=True)
    ap.add_argument("--child-cut", type=Path, required=True)
    ap.add_argument("--datasets", nargs="*")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--max-ratio", type=float, default=0.75,
                    help="keep the standalone file when the layer is larger than this share of it")
    args = ap.parse_args()

    y = YAML()
    y.preserve_quotes = True
    y.allow_unicode = False  # keep \uXXXX escapes: the files stay ASCII (SPEC-8)
    y.width = 4096
    y.indent(mapping=2, sequence=2, offset=0)
    rows = []
    cdir, pdir = args.child_cut / "spec" / "yamaa", args.parent_cut / "spec" / "yamaa"
    for cfile in sorted(cdir.glob("*.yaml")):
        name = cfile.stem
        if args.datasets and name not in args.datasets:
            continue
        pfile = pdir / cfile.name
        if not pfile.exists():
            rows.append((name, "standalone", "no spec of this name in the parent cut"))
            continue
        ctext = cfile.read_text()
        cdoc = y.load(ctext)
        pdoc = y.load(pfile.read_text())
        if str(cdoc.get("parent", "")).endswith(f"{args.parent_cut.name}/spec/yamaa/{cfile.name}"):
            rows.append((name, "layer", "already a layer over the parent cut"))
            continue
        if cdoc.get("parent") != pdoc.get("parent"):
            rows.append((name, "standalone", f"different parents {cdoc.get('parent')} / {pdoc.get('parent')}"))
            continue
        rel = f"../../../{args.parent_cut.name}/spec/yamaa/{cfile.name}"
        layer, notes = build_layer(pdoc, cdoc, rel)
        buf = io.StringIO()
        y.dump(layer, buf)
        header = re.sub(r"^# Parent: \.\./\.\./\.\./spec/yamaa/base/([a-z0-9-]+\.yaml)",
                        rf"# Parent: {rel} (which chains to ../../../spec/yamaa/base/\1)",
                        leading_comment(ctext), flags=re.M)
        note = (f"# Layer over {rel}: the derivations are the parent cut's, and\n"
                f"# this file holds only what this cut changes (written by\n"
                f"# scripts/specs/inherit_cut.py; its resolved specification\n"
                f"# equals the standalone file it replaced).\n")
        text = header + note + buf.getvalue()
        tmp = cfile.with_name(f".{name}.layer.yaml")
        tmp.write_text(text)
        try:
            before, after = resolved(cfile), resolved(tmp)
            diff = first_diff(before, after)
        except Exception as e:  # noqa: BLE001
            diff = f"resolve failed: {str(e)[:600]}"
        finally:
            pass
        nl_new, nl_old = text.count("\n"), ctext.count("\n")
        if diff:
            rows.append((name, "standalone", f"not equivalent: {diff}"))
            tmp.unlink()
            continue
        if nl_new > args.max_ratio * nl_old:
            rows.append((name, "standalone", f"layer {nl_new} lines vs {nl_old}: too little shared"))
            tmp.unlink()
            continue
        if args.write:
            tmp.replace(cfile)
        else:
            tmp.unlink()
        rows.append((name, "layer" + ("" if args.write else " (dry run)"),
                     f"{nl_old} -> {nl_new} lines" + (f"; {'; '.join(notes)}" if notes else "")))
    for r in rows:
        print(f"{r[0]:10s} {r[1]:18s} {r[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

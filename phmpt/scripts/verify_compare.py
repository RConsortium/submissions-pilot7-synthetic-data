"""Column-wise comparison of a yamaa output with a submitted ADaM dataset.

Used by scripts/reproduce.py verify (phmpt issue #5). The rules are
the ones verify.py always applied cell by cell (values_equal /
cell_diff_class), evaluated a column at a time so multi-million-row
datasets fit in memory and time:

  * two missing values are equal, and a missing value equals "" (the
    submitted Parquet stores SAS missing character as "");
  * two strings are equal; with remove_spaces they also match when equal
    after removing every ASCII space ("space-only");
  * two numbers (not bools) match when |a - b| <= tol ("within-tolerance"
    when not exactly equal); bools compare exactly;
  * anything else matches only when a == b (dates, mixed types).

Rows align on the key columns through a canonical key text per value
(nulls kept, integral floats equal to ints, dates across dtypes), as P301's
_align_index did; keys must be unique on both sides.

    from verify_compare import compare
    report, ok, lines = compare(out_table, exp_table, keys, tol, remove_spaces)

`out_table` and `exp_table` are pyarrow Tables (or anything with
to_pandas per column via .column(name)). Returns the per-column report
verify.py writes, the verdict, and the lines to print.
"""
from __future__ import annotations

import datetime as _dt
import numbers
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa

EXAMPLES = 5
# FOIA exemption 6: FDA replaced these submitted values before release, so
# the submitted file no longer holds what the sponsor's program wrote. A
# submitted cell holding exactly this text is not compared; it is counted
# per column as `redacted_skipped` (owner decision 2026-11-25).
REDACTED = "(b)(6)"


def _series(table, name: str) -> pd.Series:
    col = table.column(name)
    if pa.types.is_duration(col.type):
        # A time of day stored as a duration (the P301 JMP conversions)
        # compares as the HH:MM:SS text read_input gives submitted times.
        return pd.Series([_hms(v) for v in col.to_pylist()], dtype=object)
    if isinstance(col, pa.ChunkedArray) or isinstance(col, pa.Array):
        return col.to_pandas()
    return pd.Series(col)


def _hms(v) -> str | None:
    if v is None:
        return None
    s = int(v.total_seconds())
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 0 else str(v)


def _key_text(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return "\x00null"
    if isinstance(v, (_dt.date, _dt.datetime, pd.Timestamp, np.datetime64)):
        return "date:" + pd.Timestamp(v).isoformat()
    if isinstance(v, _dt.time):
        return "str:" + v.strftime("%H:%M:%S")
    if isinstance(v, (float, np.floating)):
        return "str:" + str(int(v)) if float(v).is_integer() else "num:" + repr(float(v))
    if isinstance(v, (bool, np.bool_)):
        return "str:" + str(bool(v))
    if isinstance(v, (int, np.integer)):
        return "str:" + str(int(v))
    return "str:" + str(v)


def _keys(table, keys: list[str]) -> pd.Series:
    parts = [_series(table, k).map(_key_text) for k in keys]
    out = parts[0]
    for p in parts[1:]:
        out = out + "\x1f" + p
    return out.reset_index(drop=True)


def _kind(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "bool"
    if pd.api.types.is_numeric_dtype(s):
        return "num"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    return "obj"


def _cell(x, y, tol, remove_spaces) -> int:
    """0 equal, 1 within tolerance, 2 space-only, 3 mismatch (verify.py rules)."""
    # read_input gives submitted times as HH:MM:SS text; a yamaa time column
    # comes back as datetime.time.
    x, y = (v.strftime("%H:%M:%S") if isinstance(v, _dt.time) else v for v in (x, y))
    xn, yn = pd.isna(x), pd.isna(y)
    if xn or yn:
        return 0 if (xn and yn) or (xn and y == "") or (yn and x == "") else 3
    if isinstance(x, str) and isinstance(y, str):
        if x == y:
            return 0
        return 2 if remove_spaces and x.replace(" ", "") == y.replace(" ", "") else 3
    if isinstance(x, (bool, np.bool_)) or isinstance(y, (bool, np.bool_)):
        return 0 if x == y else 3
    if isinstance(x, numbers.Real) and isinstance(y, numbers.Real):
        if x == y:
            return 0
        return 1 if abs(x - y) <= tol else 3
    return 0 if x == y else 3


def _classify(a: pd.Series, b: pd.Series, tol: float, remove_spaces: bool) -> np.ndarray:
    """Per cell: 0 equal, 1 within tolerance, 2 space-only, 3 mismatch, 4 redacted (skipped)."""
    res = _classify_values(a, b, tol, remove_spaces)
    if _kind(b) == "obj":
        red = (b.reset_index(drop=True).astype(object) == REDACTED).to_numpy()
        res[red & (res != 0)] = 4
    return res


def _classify_values(a: pd.Series, b: pd.Series, tol: float, remove_spaces: bool) -> np.ndarray:
    a = a.reset_index(drop=True)
    b = b.reset_index(drop=True)
    n = len(a)
    res = np.full(n, 3, dtype=np.int8)
    na_a = a.isna().to_numpy()
    na_b = b.isna().to_numpy()
    ka, kb = _kind(a), _kind(b)
    # Missing handling (both kinds).
    both = na_a & na_b
    res[both] = 0
    if ka == "obj":
        res[na_b & ~na_a & (a.astype(object) == "").to_numpy()] = 0
    if kb == "obj":
        res[na_a & ~na_b & (b.astype(object) == "").to_numpy()] = 0
    present = ~na_a & ~na_b
    if ka == kb == "num":
        av = a.to_numpy(dtype="float64", na_value=np.nan)
        bv = b.to_numpy(dtype="float64", na_value=np.nan)
        eq = present & (av == bv)
        within = present & ~eq & (np.abs(av - bv) <= tol)
        res[eq] = 0
        res[within] = 1
        return res
    if ka == kb == "date":
        res[present & (a == b).to_numpy()] = 0
        return res
    if ka == kb == "bool":
        res[present & (a == b).to_numpy()] = 0
        return res
    # Object columns: strings fast, anything else per cell.
    idx = np.nonzero(present)[0]
    if len(idx):
        av = a.to_numpy(dtype=object)[idx]
        bv = b.to_numpy(dtype=object)[idx]
        is_str = np.fromiter((isinstance(x, str) and isinstance(y, str) for x, y in zip(av, bv)),
                             dtype=bool, count=len(idx))
        s_idx = idx[is_str]
        if len(s_idx):
            sa = pd.Series(av[is_str], dtype=object)
            sb = pd.Series(bv[is_str], dtype=object)
            eq = (sa == sb).to_numpy()
            res[s_idx[eq]] = 0
            if remove_spaces:
                rest = ~eq
                sp = (sa[rest].str.replace(" ", "", regex=False)
                      == sb[rest].str.replace(" ", "", regex=False)).to_numpy()
                res[s_idx[rest][sp]] = 2
            # Numbers stored as text (P301 ADVS CHG/PCHG) follow the numeric
            # tolerance: both sides must parse, and differ by at most tol.
            left = res[s_idx] == 3
            if left.any():
                na = pd.to_numeric(sa[left], errors="coerce").to_numpy(dtype="float64")
                nb = pd.to_numeric(sb[left], errors="coerce").to_numpy(dtype="float64")
                close = ~np.isnan(na) & ~np.isnan(nb) & (np.abs(na - nb) <= tol)
                res[s_idx[left][close]] = 1
        for j in idx[~is_str]:
            res[j] = _cell(a.iat[j], b.iat[j], tol, remove_spaces)
    return res


def _norm(v, digits: int, remove_spaces: bool):
    """A cell as a hashable value under the comparison rules (multiset rows)."""
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT or v == "":
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer, float, np.floating)):
        return round(float(v), digits) + 0.0
    if isinstance(v, str):
        return v.replace(" ", "") if remove_spaces else v
    if isinstance(v, (_dt.date, _dt.datetime, pd.Timestamp, np.datetime64)):
        return pd.Timestamp(v).isoformat()
    if isinstance(v, _dt.time):  # read_input gives submitted times as HH:MM:SS
        return v.strftime("%H:%M:%S")
    if isinstance(v, (_dt.timedelta, pd.Timedelta)):  # a time of day stored as a duration
        return _hms(v)
    return str(v)


def _digits(tol: float) -> int:
    return max(0, int(round(-np.log10(tol)))) - 1 if tol > 0 else 12


def _row_hashes(table, cols, tol, remove_spaces):
    digits = _digits(tol)

    def norm(v):
        return _norm(v, digits, remove_spaces)

    acc = None
    for c in cols:
        h = np.fromiter((hash(norm(v)) for v in table.column(c).to_pylist()), dtype=np.int64,
                        count=table.num_rows)
        acc = h if acc is None else (acc * np.int64(1000003)) ^ h
    return acc


def _surplus_rows(out_table, exp_table, cols, tol, remove_spaces):
    """Row indices on each side with no equal row on the other (multiset difference)."""
    import collections

    def index(h):
        d = collections.defaultdict(list)
        for i, x in enumerate(h.tolist()):
            d[x].append(i)
        return d

    eo = index(_row_hashes(out_table, cols, tol, remove_spaces))
    ee = index(_row_hashes(exp_table, cols, tol, remove_spaces))
    only_out = sorted(i for h, ix in eo.items() for i in ix[len(ee.get(h, ())):])
    only_exp = sorted(i for h, ix in ee.items() for i in ix[len(eo.get(h, ())):])
    return only_out, only_exp


def _pair_rows(o_tab, x_tab, keys, cols, tol, remove_spaces):
    """Pair unmatched rows that share the alignment keys, most agreeing cells first."""
    digits = _digits(tol)
    on = [[_norm(v, digits, remove_spaces) for v in o_tab.column(c).to_pylist()] for c in cols]
    xn = [[_norm(v, digits, remove_spaces) for v in x_tab.column(c).to_pylist()] for c in cols]
    ko, kx = _keys(o_tab, keys).tolist(), _keys(x_tab, keys).tolist()
    by_key: dict = {}
    for i, k in enumerate(ko):
        by_key.setdefault(k, []).append(i)
    pairs = []
    for j, k in enumerate(kx):
        cand = by_key.get(k)
        if not cand:
            continue
        best = max(cand, key=lambda i: sum(on[c][i] == xn[c][j] for c in range(len(cols))))
        cand.remove(best)
        pairs.append((best, j))
    return pairs


def _column_entry(cls, a: pd.Series, b: pd.Series, keys: pd.Series) -> dict:
    """One column's counts and first examples from its per-cell classes."""
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    mism = np.nonzero(cls == 3)[0]
    within = int((cls == 1).sum())
    max_abs = 0.0
    if within:
        w = np.nonzero(cls == 1)[0]
        num = lambda s: pd.to_numeric(s.iloc[w], errors="coerce").to_numpy(dtype="float64")  # noqa: E731
        max_abs = float(np.nanmax(np.abs(num(a) - num(b))))
    entry = {"mismatches": int(len(mism)), "within_tolerance": within, "max_abs_diff": max_abs,
             "space_only_diffs": int((cls == 2).sum()), "redacted_skipped": int((cls == 4).sum())}
    if len(mism):
        entry["examples"] = [{"key": keys.iat[i].replace("\x1f", " | "), "out": a.iat[i], "expected": b.iat[i]}
                             for i in mism[:EXAMPLES]]
    return entry


def compare(out_table, exp_table, keys: list[str], tol: float, remove_spaces: bool,
            exclude: tuple = ()):
    """Compare `out_table` with `exp_table` aligned on `keys` (verify.py rules)."""
    lines: list[str] = []
    out_cols = [c for c in out_table.column_names if c not in exclude]
    exp_cols = list(exp_table.column_names)
    report = {"out_rows": out_table.num_rows, "expected_rows": exp_table.num_rows,
              "out_cols": out_cols, "expected_cols": exp_cols, "columns": {}}
    ok = True
    if out_cols != exp_cols:
        lines.append(f"COLUMN ORDER/SET DIFFERS\n  out: {out_cols}\n  exp: {exp_cols}")
        ok = False
    if out_table.num_rows != exp_table.num_rows:
        lines.append(f"ROW COUNT DIFFERS: out={out_table.num_rows} expected={exp_table.num_rows}")
        ok = False
    # Rows are still compared when only their count differs: the key sets
    # (or the multiset comparison) report the surplus rows, and the common
    # rows are compared cell by cell.
    if set(out_cols) != set(exp_cols):
        return report, ok, lines
    ko, ke = _keys(out_table, keys), _keys(exp_table, keys)
    if ko.duplicated().any() or ke.duplicated().any():
        # Without a unique key the rows cannot be paired, so the datasets are
        # compared as multisets of rows under the same rules (a missing value
        # equals "", numbers on the tolerance grid, spaces removed when the
        # rules say so). Equal multisets are an exact match; a difference is
        # reported as rows on one side only, not per column.
        lines.append(f"keys {keys} are not unique: comparing rows as multisets")
        o_idx, x_idx = _surplus_rows(out_table, exp_table, exp_cols, tol, remove_spaces)
        report["multiset_comparison"] = True
        report["rows_only_in_out"] = len(o_idx)
        report["rows_only_in_expected"] = len(x_idx)
        if not (o_idx or x_idx):
            return report, ok, lines
        # Pair the unmatched rows within their keys, so each difference is
        # reported per column like a keyed comparison; rows with no partner
        # are counted on their own.
        o_tab = out_table.take(pa.array(o_idx, type=pa.int64()))
        x_tab = exp_table.take(pa.array(x_idx, type=pa.int64()))
        pairs = _pair_rows(o_tab, x_tab, keys, exp_cols, tol, remove_spaces)
        report["rows_paired"] = len(pairs)
        report["rows_unpaired_out"] = len(o_idx) - len(pairs)
        report["rows_unpaired_expected"] = len(x_idx) - len(pairs)
        lines.append(f"{len(o_idx)} rows only in out, {len(x_idx)} only in expected; {len(pairs)} paired by {keys}")
        ok = report["rows_unpaired_out"] == 0 and report["rows_unpaired_expected"] == 0
        if pairs:
            po = o_tab.take([i for i, _ in pairs])
            px = x_tab.take([j for _, j in pairs])
            kp = _keys(po, keys)
            for col in exp_cols:
                if col in keys:
                    continue
                cls = _classify(_series(po, col), _series(px, col), tol, remove_spaces)
                entry = _column_entry(cls, _series(po, col), _series(px, col), kp)
                if entry["mismatches"]:
                    ok = False
                    lines.append(f"{col}: {entry['mismatches']} mismatches in paired rows, e.g. {entry['examples'][:2]}")
                report["columns"][col] = entry
        return report, ok, lines
    pos_e = pd.Series(np.arange(len(ke)), index=ke)
    missing = ke[~ke.isin(ko)]
    extra = ko[~ko.isin(ke)]
    if len(missing) or len(extra):
        lines.append(f"KEY SET DIFFERS: missing={len(missing)} extra={len(extra)}")
        lines.append(f"  missing sample: {[m.replace(chr(31), ' | ') for m in missing[:5]]}")
        lines.append(f"  extra sample: {[m.replace(chr(31), ' | ') for m in extra[:5]]}")
        ok = False
    common = ko.isin(ke).to_numpy()
    o_idx = np.nonzero(common)[0]
    e_idx = pos_e.loc[ko[common]].to_numpy()
    for col in exp_cols:
        if col in keys:
            continue
        a = _series(out_table, col).iloc[o_idx]
        b = _series(exp_table, col).iloc[e_idx]
        cls = _classify(a, b, tol, remove_spaces)
        entry = _column_entry(cls, a, b, ko.iloc[o_idx].reset_index(drop=True))
        if entry["mismatches"]:
            ok = False
            lines.append(f"{col}: {entry['mismatches']} mismatches, e.g. {entry['examples'][:2]}")
        elif entry["within_tolerance"] or entry["space_only_diffs"]:
            lines.append(f"{col}: {entry['within_tolerance']} within tolerance (max abs diff "
                         f"{entry['max_abs_diff']:.3g}), {entry['space_only_diffs']} space-only")
        if entry["redacted_skipped"]:
            lines.append(f"{col}: {entry['redacted_skipped']} submitted {REDACTED} cells not compared")
        report["columns"][col] = entry
    return report, ok, lines


# --------------------------------------------------------------------------
# Inputs and partitioned runs (shared by every study's verify.py).
# --------------------------------------------------------------------------
def read_input(path, columns=None, keep_time: bool = False) -> pa.Table:
    """A submitted Parquet file as yamaa input, kept in Arrow.

    The conversions verify.py always made, without a pandas round trip
    (which multiplied memory on the 2-million-row C4591001 inputs):
    timestamps to whole seconds (yamaa's bridge takes Timestamp(Second); the
    submitted datetimes carry whole seconds), times to HH:MM:SS text, and
    all-null columns to text.
    """
    import pyarrow.parquet as pq

    return _normalise(pq.read_table(path, columns=columns), keep_time)


def _normalise(t: pa.Table, keep_time: bool = False) -> pa.Table:
    """read_input's conversions, for one table or one batch of a file. keep_time leaves time
    columns as times: an artifact another yamaa spec produced (a schema link) declares them so."""
    cols = []
    for i, field in enumerate(t.schema):
        c = t.column(i)
        if pa.types.is_timestamp(field.type):
            c = c.cast(pa.timestamp("s", tz=field.type.tz), safe=False)
        elif pa.types.is_time(field.type) and not keep_time:
            c = pa.array([v.strftime("%H:%M:%S") if v is not None else None for v in c.to_pylist()],
                         pa.string())
        elif pa.types.is_null(field.type):
            c = c.cast(pa.string())
        cols.append(c)
    return pa.table(cols, names=t.column_names)


def _stable(value) -> int:
    import zlib

    return zlib.crc32(str(value).encode("utf-8"))


def verify_run(spec_path, input_paths: dict, expected_path, keys: list[str], tol: float,
               remove_spaces: bool, partitions: int = 1, linked: frozenset = frozenset()):
    """Run a spec on its input files and compare the output with the expected file.

    Every study's verify.py resolves its input files and calls this. With
    partitions > 1 the data never sits in memory whole: each input that
    carries USUBJID, and the expected file, are split by a stable hash of
    USUBJID into N Parquet files on disk (streamed one batch at a time),
    then each partition is run and compared on its own and the per-partition
    reports are added up. Memory is then about 1/N of a whole run, so a
    larger N fits a larger dataset. A derivation that reads across subjects
    shows up as a mismatch, never as a false match.

    Inputs named in `linked` are artifacts another yamaa spec produced (a
    schema link, INPUT-10): their time columns stay times, as the producing
    contract declares them.

    Returns (status, issues, report, ok, lines, derived_keys, align_keys).
    """
    import pyarrow.parquet as pq
    import yamaa

    spec = yamaa.spec(str(spec_path))
    exp_names = pq.read_schema(expected_path).names
    lines: list[str] = []

    def keys_for(out_names):
        derived = [k for k in keys if k in out_names and k not in exp_names]
        align = [k for k in keys if k in exp_names]
        if not align:
            raise SystemExit(f"keys {keys} share no column with the expected file -- nothing to align rows on")
        return derived, align

    if partitions <= 1:
        inputs = {n: read_input(p, keep_time=n in linked) for n, p in input_paths.items()}
        run = spec.run(inputs=inputs)
        inputs.clear()
        if run.status != "succeeded":
            return run.status, run.issues.to_pylist(), None, False, lines, [], []
        out = run.output.to_arrow()
        del run
        _save_output(spec_path, out)
        derived, align = keys_for(out.column_names)
        if derived:
            lines.append(f"derived row-identity key column(s) set aside: {derived}; aligning on {align}")
        rep, ok, more = compare(out, pq.read_table(expected_path), align, tol, remove_spaces,
                                exclude=tuple(derived))
        return "succeeded", [], rep, ok, lines + more, derived, align

    import shutil
    import tempfile

    work = Path(tempfile.mkdtemp(prefix="verify-parts-", dir=os.environ.get("VERIFY_TMPDIR")))
    try:
        split = {n: _split(p, partitions, work, n, normalise=True, keep_time=n in linked)
                 for n, p in input_paths.items()}
        exp_parts = _split(expected_path, partitions, work, "_EXPECTED", normalise=False)
        if exp_parts is None:
            raise SystemExit("the expected file carries no USUBJID: run without --partitions")
        whole = {n: read_input(p, keep_time=n in linked) for n, p in input_paths.items() if split[n] is None}
        report, ok, derived, align = None, True, [], []
        for k in range(partitions):
            inputs = dict(whole)
            for n, parts in split.items():
                if parts is not None:
                    inputs[n] = pq.read_table(parts[k])
            run = spec.run(inputs=inputs)
            inputs.clear()
            if run.status != "succeeded":
                return run.status, run.issues.to_pylist(), None, False, lines, [], []
            out = run.output.to_arrow()
            del run
            _save_output(spec_path, out, k)
            if k == 0:
                derived, align = keys_for(out.column_names)
                if derived:
                    lines.append(f"derived row-identity key column(s) set aside: {derived}; aligning on {align}")
            rep, ok_k, more = compare(out, pq.read_table(exp_parts[k]), align, tol, remove_spaces,
                                      exclude=tuple(derived))
            del out
            ok = ok and ok_k
            lines += [f"[partition {k + 1}/{partitions}] {m}" for m in more]
            report = rep if report is None else _merge_reports(report, rep)
            print(f"partition {k + 1}/{partitions}: {rep['expected_rows']} rows, "
                  f"{'match' if ok_k else 'differs'}", flush=True)
        return "succeeded", [], report, ok, lines, derived, align
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _save_output(spec_path, out: pa.Table, part: int | None = None) -> None:
    """With VERIFY_SAVE_OUTPUT=<dir>, keep the yamaa output for inspection."""
    import pyarrow.parquet as pq

    d = os.environ.get("VERIFY_SAVE_OUTPUT")
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
        stem = Path(spec_path).stem + ("" if part is None else f"-part{part}")
        pq.write_table(out, Path(d) / f"{stem}.parquet")


def _split(path, partitions: int, work: Path, name: str, normalise: bool, keep_time: bool = False):
    """Stream `path` into N USUBJID-hash partition files; None if it has no USUBJID."""
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    if "USUBJID" not in pf.schema_arrow.names:
        return None
    paths = [work / f"{name}-{k}.parquet" for k in range(partitions)]
    writers = None
    for batch in pf.iter_batches(batch_size=200_000):
        t = pa.Table.from_batches([batch])
        if normalise:
            t = _normalise(t, keep_time)
        part = np.fromiter((_stable(u) % partitions for u in t.column("USUBJID").to_pylist()),
                           dtype=np.int64, count=t.num_rows)
        if writers is None:
            writers = [pq.ParquetWriter(p, t.schema) for p in paths]
        for k in range(partitions):
            writers[k].write_table(t.filter(pa.array(part == k)))
    if writers is None:  # an empty file: one empty partition each
        empty = pf.schema_arrow.empty_table()
        writers = [pq.ParquetWriter(p, empty.schema) for p in paths]
    for w in writers:
        w.close()
    return paths


def _merge_reports(a: dict, b: dict) -> dict:
    """Add up two partitions' compare() reports."""
    a["out_rows"] += b["out_rows"]
    a["expected_rows"] += b["expected_rows"]
    for col, e in b["columns"].items():
        if col not in a["columns"]:
            a["columns"][col] = e
            continue
        x = a["columns"][col]
        for f in ("mismatches", "within_tolerance", "space_only_diffs", "redacted_skipped"):
            x[f] = x.get(f, 0) + e.get(f, 0)
        x["max_abs_diff"] = max(x["max_abs_diff"], e["max_abs_diff"])
        if e.get("examples"):
            x["examples"] = (x.get("examples", []) + e["examples"])[:EXAMPLES]
    if b.get("multiset_comparison"):
        a["multiset_comparison"] = True
        for f in ("rows_only_in_out", "rows_only_in_expected", "rows_paired",
                  "rows_unpaired_out", "rows_unpaired_expected"):
            a[f] = a.get(f, 0) + b.get(f, 0)
    return a

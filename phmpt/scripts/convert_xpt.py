#!/usr/bin/env python3
"""Convert one SAS transport (.xpt) file to Parquet (used by scripts/fetch_phmpt.py).

SAS variable labels and formats are kept as Parquet field metadata and the
dataset's provenance (source zip, source file, row count) as schema metadata.
Large files are read in row chunks and streamed into one ParquetWriter, so
memory stays bounded. Needs pyreadstat.
"""
import json
import os
import struct
import sys
import time

# Rough bytes per cell in a pyreadstat DataFrame (measured: 500k x 126 -> 2.7 GB RSS).
BYTES_PER_CELL = 45
DEFAULT_MEM_BUDGET = 3_000_000_000  # bytes per conversion (XPT_MEM_BUDGET_MB overrides)
CHUNK_ROWS_CAP = 500_000
CHUNK_ROWS_MIN = 50_000

def mem_budget():
    try:
        return int(os.environ.get("XPT_MEM_BUDGET_MB", "")) * 1_000_000
    except (TypeError, ValueError):
        return DEFAULT_MEM_BUDGET


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)


# ---------------------------------------------------------------- XPT header
def xpt_info(path):
    """Parse the XPT v5 header only. Returns (nrows, ncols, record_length)."""
    with open(path, "rb") as f:
        head = f.read(300000)
    hdr = head.find(b"HEADER RECORD*******NAMESTR")
    if hdr < 0:
        raise ValueError("NAMESTR header not found")
    rec = head[hdr:hdr + 80]
    nvars = int(rec[54:58])
    struct_start = hdr + 80
    total_len = 0
    for i in range(nvars):
        s = head[struct_start + i * 140: struct_start + (i + 1) * 140]
        total_len += struct.unpack(">h", s[4:6])[0]
    obs = head.find(b"HEADER RECORD*******OBS")
    data_start = obs + 80
    nrows = (os.path.getsize(path) - data_start) // total_len
    return nrows, nvars, total_len


# ---------------------------------------------------------------- downloads
# ---------------------------------------------------------------- conversion (child)
READ_ENCODINGS = [None, "cp1252", "latin-1"]


def read_xport_fallback(pyreadstat, path, encoding, **kw):
    """Read with pyreadstat, falling back through encodings on decode errors.

    Some submission files carry Windows-1252 bytes (e.g. an en dash 0x96 in a
    label or value) that fail UTF-8 decoding. The first encoding that reads
    wins; it is then reused for every chunk of the same file.
    """
    candidates = [encoding] + [e for e in READ_ENCODINGS if e != encoding]
    last = None
    for enc in candidates:
        try:
            df, meta = pyreadstat.read_xport(path, encoding=enc, **kw)
            return df, meta, enc
        except UnicodeDecodeError as e:
            last = e
    raise last


def convert_file(xpt_path, parquet_path, source_zip):
    import pyreadstat
    import pyarrow as pa
    import pyarrow.parquet as pq

    t0 = time.time()
    nrows_est, ncols, _ = xpt_info(xpt_path)
    _, meta, encoding = read_xport_fallback(pyreadstat, xpt_path, None, metadataonly=True)
    labels = list(getattr(meta, "column_labels", []) or [])
    formats = {}
    for attr in ("variable_formats", "formats"):
        v = getattr(meta, attr, None)
        if isinstance(v, dict):
            formats = v
            break
    file_label = getattr(meta, "file_label", None)

    def arrow_table(df, target_types=None):
        table = pa.Table.from_pandas(df, preserve_index=False)
        fields = []
        for i, field in enumerate(table.schema):
            md = {}
            if i < len(labels) and labels[i]:
                md["sas_label"] = str(labels[i])
            fmt = formats.get(field.name)
            if fmt:
                md["sas_format"] = str(fmt)
            t = field.type
            if target_types is not None and field.name in target_types:
                t = target_types[field.name]
                if t == pa.null() and field.type != pa.null():
                    raise RuntimeError(
                        f"column {field.name}: target type is null but this chunk has "
                        f"{field.type} (all-null in probed windows, typed later) - "
                        "refusing to silently drop values")
            fields.append(pa.field(field.name, t,
                                   metadata={k: v.encode("utf-8") for k, v in md.items()} or None))
        schema = pa.schema(fields, metadata={
            b"source_xpt": os.path.basename(xpt_path).encode("utf-8"),
            b"source_zip": (source_zip or "").encode("utf-8"),
            b"converter": b"download_and_convert_xpt_to_parquet.py (pyreadstat + pyarrow)",
            b"dataset_label": (str(file_label) if file_label else "").encode("utf-8"),
            b"encoding": (encoding or "utf-8").encode("utf-8"),
        })
        return table.cast(schema)

    est_rss = nrows_est * max(ncols, 1) * BYTES_PER_CELL
    budget = mem_budget()
    rows_written = 0
    if est_rss <= budget:
        df, _, encoding = read_xport_fallback(pyreadstat, xpt_path, encoding)
        table = arrow_table(df)
        pq.write_table(table, parquet_path, compression="zstd")
        rows_written = len(df)
        del df, table
    else:
        chunk_rows = max(CHUNK_ROWS_MIN, min(CHUNK_ROWS_CAP, int(budget / max(ncols * BYTES_PER_CELL, 1))))
        # Resolve ONE target schema before writing. A column can be all-null
        # (arrow type null) or integer-valued in one chunk and typed/float in
        # another - 2026-11-21: ADFACEVD's VAX10UDT was date32 in chunk 1
        # and null in chunk 2 - and ParquetWriter rejects a schema change
        # mid-file (the failure surfaced as a bare schema dump). Probe
        # chunk-boundary windows and merge types by promotion, then cast
        # every chunk to that schema.
        def _promote(a, b):
            if a == pa.null():
                return b
            if b == pa.null():
                return a
            if pa.types.is_integer(a) and pa.types.is_floating(b):
                return b
            if pa.types.is_floating(a) and pa.types.is_integer(b):
                return a
            if pa.types.is_string(a) and pa.types.is_large_string(b):
                return b
            if pa.types.is_large_string(a) and pa.types.is_string(b):
                return a
            return a

        # Probe with FULL chunks, not small windows: a column can be so sparse
        # that a 10k-row window misses it entirely (2026-11-21: VAX10UDT has
        # only 289 values in 411,522 rows, the first at row 255,951 - a 10k
        # window saw null, the full chunk saw date32, and the guard below
        # then refused the file). Each probe reads one chunk and drops it,
        # so peak memory stays at one chunk.
        target_types = {}
        _off = 0
        _nprobes = 0
        for _probe in range(4):
            _df, _, _ = read_xport_fallback(pyreadstat, xpt_path, encoding,
                                            row_limit=chunk_rows, row_offset=_off)
            if len(_df) == 0:
                break
            _t = pa.Table.from_pandas(_df, preserve_index=False)
            for _f in _t.schema:
                target_types[_f.name] = _promote(target_types.get(_f.name, pa.null()), _f.type)
            del _df, _t
            _nprobes += 1
            if _nprobes >= 2 and not any(t == pa.null() for t in target_types.values()):
                break
            _off += chunk_rows
            if _off >= nrows_est:
                break
        writer = None
        try:
            offset = 0
            while True:
                df, _, encoding = read_xport_fallback(pyreadstat, xpt_path, encoding,
                                                      row_limit=chunk_rows, row_offset=offset)
                if len(df) == 0:
                    break
                n_chunk = len(df)
                table = arrow_table(df, target_types)
                if writer is None:
                    writer = pq.ParquetWriter(parquet_path, table.schema, compression="zstd")
                writer.write_table(table)
                rows_written += n_chunk
                offset += n_chunk
                del df, table
                if rows_written >= nrows_est and n_chunk < chunk_rows:
                    break
        finally:
            if writer is not None:
                writer.close()
    # verify by reading back the footer
    pf = pq.ParquetFile(parquet_path)
    if pf.metadata.num_rows != rows_written:
        raise RuntimeError(f"row mismatch after write: footer {pf.metadata.num_rows} != written {rows_written}")
    if pf.metadata.num_rows != nrows_est:
        log(f"  WARNING row count differs from header estimate: footer {pf.metadata.num_rows} vs header {nrows_est}")
    return {
        "xpt": xpt_path, "parquet": parquet_path, "rows": rows_written,
        "cols": ncols, "seconds": round(time.time() - t0, 1),
        "xpt_mb": round(os.path.getsize(xpt_path) / 1e6, 1),
        "parquet_mb": round(os.path.getsize(parquet_path) / 1e6, 1),
        "encoding": encoding or "utf-8",
    }

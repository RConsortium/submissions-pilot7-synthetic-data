"""Execute a YAMAA spec and write the official-shape parquet.

Usage: python run_spec.py spec/<domain>.yaml

Runs the spec with yamaa_domain, then writes output/<domain>.parquet with:
- exact official column order (from the spec's output.columns),
- Arrow physical/logical types matching the official ADaM parquet
  (large_string / double / date32[day]),
- yamaa:label field metadata from the spec's column labels,
- strict null-vs-empty preservation (empty strings stay empty strings),
- deterministic row order: if the spec declares output.order_by, the frame is
  sorted by those columns (the engine does not implement output.order_by;
  upstream yamaa has no final-frame ordering construct, so the writer applies
  the spec-declared order).

The label/large_string/order_by handling is a writer step because the YAMAA
engine emits pa.string() without field labels and preserves input row order
(upstream yamaa issue #74 tracks plain-string parquet output).
"""

import sys
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

BASE = Path(__file__).resolve().parent

ARROW = {
    "str": pa.large_string(),
    "float": pa.float64(),
    "int": pa.int64(),
    "date": pa.date32(),
    "datetime": pa.timestamp("us"),
}


def main() -> None:
    from yamaa import yamaa_domain

    spec_path = Path(sys.argv[1])
    raw = yaml.safe_load(spec_path.read_text())
    domain = raw["domain"].lower()

    run = yamaa_domain(str(spec_path), project_root=str(BASE))
    frame: pl.DataFrame | None = run.output
    if frame is None:
        raise SystemExit(f"spec {spec_path} produced no output")

    cols = raw["columns"]
    col_by_name = {c["name"]: c for c in cols}
    order = raw["output"]["columns"]
    if raw["output"].get("order_by"):
        sort_cols, desc = [], []
        for entry in raw["output"]["order_by"]:
            if isinstance(entry, dict):
                sort_cols.append(entry["variable"])
                desc.append(entry.get("direction") == "desc")
            else:
                sort_cols.append(entry)
                desc.append(False)
        # sort before selecting: order_by may reference helper columns
        # (e.g. KEYSEQ) not present in the final output. nulls_last keeps
        # null keys at the end, matching the official row order.
        frame = frame.sort(sort_cols, descending=desc, nulls_last=True)
    frame = frame.select(order)

    fields = []
    arrays = []
    for name in order:
        c = col_by_name[name]
        ctype, label = c["type"], c.get("label", "")
        arr = frame[name].to_arrow().cast(ARROW[ctype])
        fields.append(
            pa.field(name, ARROW[ctype], nullable=True,
                     metadata={b"yamaa:label": label.encode()})
        )
        arrays.append(arr)
    table = pa.Table.from_arrays(arrays, schema=pa.schema(fields))

    out = BASE / "output" / f"{domain}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)
    print(f"wrote {out}: {table.num_rows} rows x {table.num_columns} cols")


if __name__ == "__main__":
    main()

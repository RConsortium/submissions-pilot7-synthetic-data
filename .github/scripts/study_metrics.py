"""Shared agreement metrics with independent official-reference denominators."""


def matched_totals(report):
    passed = [d for d in report["datasets"] if d["comparison"] == "passed"]
    return (
        len(passed),
        sum(d["columns"] for d in passed),
        sum(d["rows"] * d["columns"] for d in passed),
    )


def reference_totals(root, study):
    try:
        import pyarrow.parquet as pq
    except ImportError as err:
        raise ImportError(
            "build_index_table.py needs pyarrow to read " "reference parquet dimensions"
        ) from err
    adam = root / study / "data" / "adam"
    if not adam.is_dir():
        return (0, 0, 0)
    datasets = columns = cells = 0
    for path in sorted(adam.glob("*.parquet")):
        if "-yamaa" in path.name:
            continue
        table = pq.read_metadata(path)
        datasets += 1
        columns += table.num_columns
        cells += table.num_rows * table.num_columns
    return datasets, columns, cells

"""Shared execution and artifact publication; no clinical derivations here."""

import json
import os
from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq
import pyreadstat
import yaml
import yamaa
from lxml import etree

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY.parent / ".github/scripts"))
from resolved_specs import process_study, specification_packet

PROJECT = STUDY / "spec/yamaa/project.yaml"
SCHEMAS = Path(os.environ.get("YAMAA_XML_SCHEMAS", str(
    STUDY.parent / ".build/define-engine/rust/tests/schemas"))).resolve()
# Define-XML uses the source snapshot time. ReadStat timestamps XPT at export;
# reproducibility of XPT is assessed on data and labels, not header bytes.
CREATED = "2025-10-28T14:40:02"


def declaration():
    return yaml.safe_load(PROJECT.read_text())


def specifications(section):
    # Let the engine expand copy entries and producer contracts. Export and
    # review must not implement a second interpretation of the YAML language.
    result = []
    for relative in declaration()[section]["specs"]:
        path = (PROJECT.parent / relative).resolve()
        result.append((path, specification_packet(STUDY.parent, path)["model"]))
    return result


def require_success(result):
    if result.status != "succeeded":
        raise RuntimeError(json.dumps(result.issues.to_pylist(), indent=2))


def run_section(section):
    process_study(STUDY.parent, STUDY.name, check=True)
    project = yamaa.project(PROJECT)
    check = project.check()
    require_success(check)
    runs = project.run(section)
    # Keep diagnostics from every attempted dataset, including a failed one.
    for _, spec in specifications(section):
        domain = spec["domain"]
        run = runs[domain]
        (STUDY / "log" / f"{section}-{domain.lower()}.log").write_text(
            str(run) + "\n" + json.dumps(run.issues.to_pylist(), indent=2) + "\n")
    require_success(runs)
    runs.save()
    records = []
    for path, spec in specifications(section):
        run = runs[spec["domain"]]
        artifact = (path.parent / spec["output"]["path"]).resolve()
        records.append({"domain": spec["domain"], "rows": run.output.num_rows,
                        "columns": len(run.output.column_names), "build": "succeeded"})
    print(runs, flush=True)
    return records


def export_xpt(path, spec):
    """Write incomplete review data without certifying its CDISC conformance.

    yamaa intentionally refuses native transport for historical metadata.
    pyreadstat writes the review XPT, with the same labels and date formats.
    Every cell and label is read back; conversion failures stop the pipeline.
    """
    artifact = (path.parent / spec["output"]["path"]).resolve()
    frame = pq.read_table(artifact).to_pandas()
    columns = {c["name"]: c for c in spec["columns"]}
    labels, formats = {}, {}
    for name in frame.columns:
        column = columns[name]
        labels[name] = column["label"]
        if column["type"] == "str":
            frame[name] = frame[name].fillna("")
            width = column["submission"]["length"]
            if width > 200 or frame[name].map(lambda x: len(x.encode("utf-8"))).max() > width:
                raise ValueError(f"{spec['domain']}.{name}: XPT v5 width exceeds 200 bytes")
            # ReadStat infers widths from cells. Explicit SAS padding makes
            # the physical column width equal the Define-XML declaration.
            frame[name] = frame[name].map(
                lambda value: value + " " * (width - len(value.encode("utf-8"))))
        elif column["type"] == "date":
            dates = pd.to_datetime(frame[name])
            frame[name] = (dates - pd.Timestamp("1960-01-01")).dt.days.astype(float)
            formats[name] = "DATE9."
        else:
            frame[name] = pd.to_numeric(frame[name]).astype(float)
    target = artifact.with_name(spec["domain"].lower() + ".xpt")
    temporary = target.with_suffix(".tmp.xpt")
    try:
        pyreadstat.write_xport(frame, temporary, file_label=spec["submission"]["label"],
                              column_labels=labels, table_name=spec["domain"],
                              file_format_version=5, variable_format=formats)
        returned, metadata = pyreadstat.read_xport(temporary, disable_datetime_conversion=True)
        expected = frame.copy()
        # SAS character fields are padded with blanks. Its reader cannot
        # distinguish collected trailing blanks from that physical padding.
        # Keep exact collected strings in Parquet and compare XPT by SAS
        # semantics. Leading blanks and every other character must agree.
        for name in frame.columns:
            if columns[name]["type"] == "str":
                expected[name] = expected[name].str.rstrip(" ")
        pd.testing.assert_frame_equal(expected.reset_index(drop=True), returned,
                                      check_dtype=False, check_exact=False,
                                      rtol=1e-12, atol=1e-12)
        if metadata.column_names_to_labels != labels:
            raise ValueError(f"{spec['domain']}: XPT labels changed on round-trip")
        for name in frame.columns:
            if columns[name]["type"] == "str":
                if metadata.variable_storage_width[name] != columns[name]["submission"]["length"]:
                    raise ValueError(f"{spec['domain']}.{name}: XPT and Define-XML widths differ")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return {"dataset": spec["domain"], "rows": len(frame), "round_trip": "passed"}


def export_definitions():
    records = []
    project = yamaa.project(PROJECT)
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    schema_path = SCHEMAS / "define/2.0/define2-0-0.xsd"
    if not schema_path.is_file():
        raise FileNotFoundError(
            "Check out rust/tests/schemas from the pinned yamaa revision into "
            ".build/define-engine, as in the pilot Define-XML workflow; "
            "or set YAMAA_XML_SCHEMAS to that schema root. See cart-t/README.md.")
    schema = etree.XMLSchema(etree.parse(str(schema_path), parser))
    for section in ("sdtm", "adam"):
        for path, spec in specifications(section):
            export_xpt(path, spec)
        submission = project.submission(section, created=CREATED)
        require_success(submission)
        paths = submission.save()
        definition = Path(paths[-1])
        tree = etree.parse(str(definition), parser)
        schema.assertValid(tree)
        links = tree.xpath("//@xlink:href", namespaces={"xlink": "http://www.w3.org/1999/xlink"})
        for href in links:
            if not (definition.parent / href).is_file():
                raise ValueError(f"Define-XML has a missing local artifact: {href}")
        records.append({"section": section, "path": str(definition.relative_to(STUDY)),
                        "version": "2.0.0", "xsd": "passed", "links": "passed",
                        "metadata_mode": "historical", "reference_comparison": "unavailable"})
    return records

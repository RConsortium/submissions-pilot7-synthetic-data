"""Record native Define-XML metadata agreement with the retained reference."""

import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

from define_metadata import compare
from compare_legacy_define import compare_legacy


def version(path):
    if not path.is_file():
        return None
    return next(
        (value for element in ET.parse(path).iter()
         for key, value in element.attrib.items()
         if key.rsplit("}", 1)[-1] == "DefineVersion"),
        None,
    )


def check_define(root, study, project):
    """Compare freshly composed metadata; never infer a match from ADaM data."""
    root = Path(root).resolve()
    base = root / study
    reference = base / "spec/define/define-adam.xml"
    record = {
        "sdtm_version": version(base / "spec/define/define-sdtm.xml"),
        "adam_version": version(reference),
        "comparison": "not_compared",
    }
    project_file = base / "spec/yamaa/project.yaml"
    declaration = yaml.safe_load(project_file.read_text())["adam"]
    if not declaration.get("define") or not reference.is_file():
        return record
    candidate = (project_file.parent / declaration["define"]).resolve()
    candidate.relative_to(root)
    if candidate == reference.resolve():
        raise ValueError("Generated Define-XML must be separate from the reference")
    candidate.unlink(missing_ok=True)
    submission = project.submission("adam")
    if submission.status != "succeeded":
        raise ValueError(str(submission.issues.to_pylist()))
    submission.save()
    if record["adam_version"] == "1.0.0":
        legacy = compare_legacy(reference, candidate)
        # The full field inventory belongs in the reproduction artifact. Keep
        # dashboard evidence small without turning a partial migration into a
        # metadata match, even when all comparable fields agree.
        comparison = {key: legacy[key] for key in (
            "comparison_completed", "comparable_metadata_equal",
            "reference_define_version", "candidate_define_version",
            "full_reference_reproduced", "coverage", "field_counts",
            "differences", "unexpected_differences", "known_gap_difference_count",
            "unresolved", "mapping_policy",
        )}
        comparison["metadata_equivalent"] = False
        comparison["unsupported"] = [
            {key: value for key, value in entry.items() if key != "xml"}
            for entry in legacy["unsupported"]
        ]
    else:
        comparison = compare(reference, candidate)
    record.update(
        comparison="matched" if comparison["metadata_equivalent"] else "different",
        candidate_version=comparison["candidate_define_version"],
        candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
        metadata=comparison,
    )
    return record

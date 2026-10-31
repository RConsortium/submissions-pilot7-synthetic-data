"""Catalog-driven dashboard configuration and the browser artifact contract."""

import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULTS = {"subject_key": "USUBJID", "default_subject_count": 3}


def settings(root, entry):
    path = Path(root) / ".github/dashboard.json"
    shared = json.loads(path.read_text()) if path.exists() else {}
    if shared and shared.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported dashboard configuration schema_version")
    options = {**DEFAULTS, **shared.get("defaults", {}), **entry.get("dashboard", {})}
    unknown = set(options) - {"subject_key", "default_subject_count", "references"}
    if unknown:
        raise ValueError(f"Unknown dashboard settings: {sorted(unknown)}")
    if not isinstance(options["subject_key"], str) or not options["subject_key"]:
        raise ValueError("dashboard.subject_key must be a nonempty column name")
    count = options["default_subject_count"]
    if type(count) is not int or count < 1:
        raise ValueError("dashboard.default_subject_count must be a positive integer")
    if not isinstance(options.get("references", {}), dict):
        raise ValueError(
            "dashboard.references must map domain names to study-relative files"
        )
    return options


def comments(root):
    path = Path(root) / ".github/dashboard.json"
    return json.loads(path.read_text()).get("comments", {}) if path.exists() else {}


def study_path(root, study):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", study):
        raise ValueError(f"Invalid study identifier: {study}")
    return Path(root) / study


def reference_path(root, study, domain, options):
    base = study_path(root, study)
    relative = options.get("references", {}).get(
        domain, f"data/adam/{domain.lower()}.parquet"
    )
    path = (base / relative).resolve()
    path.relative_to(base.resolve())
    return path

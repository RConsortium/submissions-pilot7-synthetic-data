#!/usr/bin/env python3
"""Standardize the immutable CAR-T ODM snapshot and check dataset integrity."""

import argparse
from datetime import datetime, timezone
import json
import sys

import yamaa

from engine import STUDY, export_definitions, run_section
from odm.prepare import prepare


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    log = STUDY / "log"
    log.mkdir(parents=True, exist_ok=True)
    manifest = {"study": "cart-t", "status": "failed", "engine": yamaa.info(),
                "yamaa_revision": "5976b74fddfbcbcad4d53ba550cb1e3773e07a5b",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "reference_comparison": "unavailable", "submission_ready": False}
    # Delete stale success evidence before beginning a new run.
    record = log / "run.json"
    record.unlink(missing_ok=True)
    try:
        inventory = prepare()
        manifest["source"] = inventory
        (log / "odm.log").write_text(json.dumps(inventory, indent=2) + "\n")
        manifest["sdtm"] = run_section("sdtm")
        manifest["adam"] = run_section("adam")
        manifest["define_xml"] = export_definitions()
        from audit import audit
        manifest["audit"] = audit()
        from verify_issue_98 import verify
        manifest["issue_98"] = verify()
        manifest["status"] = "succeeded"
    except Exception as error:
        manifest["status"] = "failed"
        manifest["reason"] = str(error)
        raise
    finally:
        record.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"CAR-T pipeline: succeeded; audit: {manifest['audit']['status']}; "
          "submission readiness: not established", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

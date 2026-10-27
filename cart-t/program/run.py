#!/usr/bin/env python3
"""Rebuild the CAR-T review package from the immutable ODM snapshot."""

import argparse
from datetime import datetime, timezone
import json
import sys

import yamaa

from engine import STUDY, export_definitions, run_section
from odm.extract import extract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-only", action="store_true",
                        help="Build and audit artifacts without rendering the review HTML")
    parser.add_argument("--review-only", action="store_true",
                        help="Render the workbook from the successful build in this workspace")
    args = parser.parse_args()
    log = STUDY / "log"
    log.mkdir(parents=True, exist_ok=True)
    if args.review_only:
        from review import render
        manifest = json.loads((log / "run.json").read_text())
        if manifest["status"] != "succeeded":
            raise ValueError("A successful full pipeline run is required before rendering")
        render(manifest)
        return 0
    manifest = {"study": "cart-t", "status": "failed", "engine": yamaa.info(),
                "yamaa_revision": "1d78496c0cbd4fe89462596a738db3adbd72c8ad",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "reference_comparison": "unavailable", "submission_ready": False}
    # Delete stale success evidence before beginning a new run.
    record = log / "run.json"
    record.unlink(missing_ok=True)
    (STUDY / "tlf/review.html").unlink(missing_ok=True)
    try:
        inventory = extract()
        manifest["source"] = inventory
        (log / "odm.log").write_text(json.dumps(inventory, indent=2) + "\n")
        manifest["sdtm"] = run_section("sdtm")
        manifest["adam"] = run_section("adam")
        manifest["define_xml"] = export_definitions()
        from review import audit, render
        manifest["audit"] = audit()
        manifest["status"] = "succeeded"
        if not args.build_only:
            render(manifest)
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

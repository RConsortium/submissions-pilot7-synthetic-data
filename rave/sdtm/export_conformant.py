"""Export the derived RAVE SDTM to conformant XPT + Define-XML.

Reads the per-domain CSVs written by run_all.R and writes typed XPT v5 + a
Define-XML 2.0 to ``sdtm-derived/xpt/`` via the shared exporter. No remediation
(the R derivations already finalize the data).

    python sdtm/export_conformant.py
Override the input dir with RAVE_SDTM_OUT (default: sdtm/sdtm-derived/).
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_ROOT = HERE.parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
from cdt.environments.sdtm_export import export_conformant  # noqa: E402

SRC = Path(os.environ.get("RAVE_SDTM_OUT", HERE / "sdtm-derived"))
OUT = Path(os.environ.get("RAVE_SDTM_XPT", SRC / "xpt"))
STUDY_ID = "RAVE"
STUDY_NAME = "RAVE Rituximab in ANCA-Associated Vasculitis (NCT00104299)"


def export(src=SRC, out=OUT) -> Path:
    return export_conformant(src, out, STUDY_ID, STUDY_NAME)


if __name__ == "__main__":
    export()

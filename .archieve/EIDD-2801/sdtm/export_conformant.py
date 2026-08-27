"""Export the derived EIDD-2801 SDTM to conformant XPT + Define-XML.

Reads the per-domain CSVs written by run_all.R and writes typed XPT v5 + a
Define-XML 2.0 to ``sdtm-derived/xpt/`` via the shared exporter
(``cdt.environments.sdtm_export``). No remediation — the R derivations already
finalize the data (EPOCH, --DY, --SEQ, controlled terms, column order).

    python sdtm/export_conformant.py
Override the input dir with EIDD_SDTM_OUT (default: sdtm/sdtm-derived/).
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Ensure the vendored cdt package is importable (installed editable in the
# cdisc-engine env; fall back to the sibling clinical-data-terminal-dev checkout).
try:
    from cdt.environments.sdtm_export import export_conformant  # noqa: E402
except ModuleNotFoundError:
    for cand in (HERE.parents[3], Path.home() / "Documents/github/clinical-data-terminal-dev/src"):
        if (Path(cand) / "cdt" / "environments" / "sdtm_export.py").is_file():
            sys.path.insert(0, str(cand)); break
    from cdt.environments.sdtm_export import export_conformant  # noqa: E402

SRC = Path(os.environ.get("EIDD_SDTM_OUT", HERE / "sdtm-derived"))
OUT = Path(os.environ.get("EIDD_SDTM_XPT", SRC / "xpt"))
STUDY_ID = "2020-001407-17-00"
STUDY_NAME = "EIDD-2801-1001-UK Single-Dose PK Study of Molnupiravir (2020-001407-17-00)"


def export(src=SRC, out=OUT) -> Path:
    return export_conformant(src, out, STUDY_ID, STUDY_NAME)


if __name__ == "__main__":
    export()

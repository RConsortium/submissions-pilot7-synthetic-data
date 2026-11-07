"""Check the committed ODM snapshot and write native item QC evidence.

All clinical reshaping is executed by yamaa specifications reading the XML.
The native item Parquet and inventory are QC evidence, not SDTM inputs.
"""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yamaa

STUDY = Path(__file__).resolve().parents[2]
SCOPE = ("StudyOID", "MetaDataVersionOID", "SubjectKey", "StudyEventOID",
         "StudyEventRepeatKey", "FormOID", "FormRepeatKey", "ItemGroupOID",
         "ItemGroupRepeatKey")
INSTANCE = SCOPE + ("FormLayoutOID",)


def prepare(study=STUDY):
    destination = study / "data/odm"
    original = destination / "car-t-openclinica.xml"
    # The committed XML is the only source. It is read in place, never copied
    # or rewritten, so the checkout and the downloadable package are identical.
    if not original.is_file():
        raise FileNotFoundError(f"Missing source ODM snapshot: {original}")
    payload = original.read_bytes()
    # Remove the generated declaration copy left by earlier pipeline versions.
    (destination / "car-t-utf8.xml").unlink(missing_ok=True)
    native = yamaa.read_odm(original)
    rows = native.to_pylist()
    identifiers = [tuple(row[field] for field in INSTANCE) + (row["ItemOID"],)
                   for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Repeated ItemOID within an ODM instance")
    layouts = defaultdict(set)
    for row in rows:
        layouts[tuple(row[field] for field in SCOPE if field != "MetaDataVersionOID")].add(
            (row["MetaDataVersionOID"], row["FormLayoutOID"]))
    if any(len({version for version, _ in values}) > 1 for values in layouts.values()):
        raise ValueError("Distinct metadata versions share one native ODM scope; resolve before mapping")
    if any(len(values) > 1 for values in layouts.values()):
        raise ValueError("Distinct form layouts share one native ODM scope; resolve before mapping")
    subjects = {(row["StudyOID"], row["SubjectKey"]) for row in rows}
    if len({subject for _, subject in subjects}) != len(subjects):
        raise ValueError("SubjectKey is not globally unique; revise study join keys")
    pq.write_table(pa.table(native), destination / "items.parquet")
    forms = Counter(row["FormName"] for row in rows)
    inventory = {"source": original.name, "source_sha256": hashlib.sha256(payload).hexdigest(),
                 "items": len(rows), "subjects": len(subjects),
                 "groups": len({tuple(row[field] for field in INSTANCE) for row in rows}),
                 "native_columns": native.column_names, "form_item_counts": dict(forms),
                 "sdtm_input": original.name, "item_parquet_role": "QC only"}
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    return inventory


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))

"""Compose the synthetic define and print the elements each gap concerns."""
import re
import sys
from pathlib import Path

import yamaa

here = Path(__file__).resolve().parent
spec = (here / "adxx.yaml").read_text()
control = spec.replace('where: {SRCVAR: [""]}', "where: {SRCVAR: [AVAL]}")
cases = {
    "G7 empty CheckValue as received": spec,
    "G4 NOTIN with one value as received": control.replace("comparator: NE, values", "comparator: NOTIN, values"),
    "control (closest admissible forms)": control,
}
for name, text in cases.items():
    (here / "adxx.yaml").write_text(text)
    sub = yamaa.project(str(here / "project.yaml")).submission("adam", created="2026-01-01T00:00:00")
    print(f"== {name}: {sub.status}")
    for i in sub.issues.to_pylist():
        print(f"   {i['rule']} {i['condition']} {i['spec_paths']} {i['message']}")
    if sub.status == "succeeded":
        sub.save()
        xml = (here / "define.xml").read_text()
        for pat in [r"<CodeList .*?</CodeList>", r'<ItemDef OID="IT\.ADXX\.AVAL\.ADXX[^>]*>',
                    r'<def:WhereClauseDef OID="[^"]*">.*?</def:WhereClauseDef>', r"<TranslatedText [^>]*>"]:
            for m in re.findall(pat, xml, flags=re.S)[:3]:
                print("   " + " ".join(m.split())[:220])
(here / "adxx.yaml").write_text(spec)

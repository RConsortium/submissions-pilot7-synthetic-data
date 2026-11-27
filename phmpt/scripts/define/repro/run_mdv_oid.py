"""G8: a received MetaDataVersion OID with a comma. Compose with: python run_mdv_oid.py"""
import re, yamaa, pathlib
here = pathlib.Path(__file__).resolve().parent
base = (here / "project.yaml").read_text()
cases = {
  "control: metadata_version id without a comma": "  metadata_version: {id: SYNTH-Acme_-Inc.ADaM-IG.1.1, name: Synthetic data definitions}\n",
  "received: metadata_version id with a comma": "  metadata_version: {id: 'SYNTH-Acme,-Inc.ADaM-IG.1.1', name: Synthetic data definitions}\n",
}
for name, extra in cases.items():
    (here / "project.yaml").write_text(base.replace("  context: Other\n", "  context: Other\n  study_oid: 'SYNTH-Acme,-Inc.ADaM-IG.1.1'\n" + extra))
    sub = yamaa.project(str(here / "project.yaml")).submission("adam", created="2026-01-01T00:00:00")
    print(f"== {name}: {sub.status}")
    for i in sub.issues.to_pylist():
        print(f"   {i['rule']} {i['condition']} {i['spec_paths']} {i['message']}")
    if sub.status == "succeeded":
        sub.save()
        xml = (here / "define.xml").read_text()
        print("   " + " | ".join(re.findall(r'<(?:Study|MetaDataVersion) OID="[^"]*"', xml)))
(here / "project.yaml").write_text(base)

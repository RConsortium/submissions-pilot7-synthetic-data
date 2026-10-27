"""Source inventories for synthetic workflow development, separate from verification."""

import hashlib
import html
import json
from pathlib import PurePosixPath
import shutil
import tarfile

from synthetic_evidence import package, verified_report

from .config import SCHEMA_VERSION, study_path


def synthetic_catalog(root):
    path = root / ".github/synthetic-studies.json"
    return json.loads(path.read_text()) if path.exists() else {}


def inventory(root, study, entry, revision):
    base = study_path(root, study).resolve()
    archives = []
    for relative in entry.get("archives", []):
        path = (base / relative).resolve()
        path.relative_to(base)
        record = {
            "path": path.relative_to(root).as_posix(),
            "available": path.is_file(),
        }
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            members = []
            # Inspect member headers; never extract the archive or load clinical XML.
            with tarfile.open(path, "r:gz") as archive:
                for member in archive:
                    name = PurePosixPath(member.name)
                    if not member.isfile() or any(
                        part.startswith(".") for part in name.parts
                    ):
                        continue
                    if name.is_absolute() or ".." in name.parts:
                        raise ValueError(
                            f"{path}: archive member is not a relative source path"
                        )
                    members.append({"name": member.name, "bytes": member.size})
            record.update(
                bytes=path.stat().st_size, sha256=digest.hexdigest(), files=members
            )
        archives.append(record)
    stages = [
        {
            "id": "odm",
            "title": "EDC / ODM sources",
            "count": sum(a["available"] for a in archives),
            "unit": "source archives",
        }
    ]
    for name, title, folder, patterns in [
        ("sdtm", "SDTM mapping", "data/sdtm", ("*.parquet", "*.xpt", "*.csv")),
        ("adam", "ADaM derivation", "data/adam", ("*.parquet", "*.xpt", "*.csv")),
        ("define", "Submission metadata", "spec/define", ("*.xml",)),
    ]:
        stages.append(
            {
                "id": name,
                "title": title,
                "count": len(
                    {
                        path
                        for pattern in patterns
                        for path in (base / folder).glob(pattern)
                        if path.is_file()
                    }
                ),
                "unit": "staged files",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "id": study,
        "title": entry["title"],
        "description": entry["description"],
        "kind": "synthetic",
        "revision": revision,
        "archives": archives,
        "stages": stages,
    }


def development(root, study, target, revision, *, required=False):
    """Publish measured development results separately from official comparisons."""
    report = verified_report(root, study, revision)
    if not report:
        if required:
            raise ValueError(f'{study}: required synthetic validation is missing')
        return {"status": "not_run", "human_review": "pending"}
    if report['status'] != 'succeeded':
        raise ValueError(f'{study}: failed synthetic validation cannot be published')
    from .datasets import write_json

    target.mkdir(parents=True, exist_ok=True)
    write_json(target / 'build-report.json', report)
    package(root, study, target / f'{study}-development.zip', report)
    source = root / study / 'spec/source/protocol-sap.mmd'
    body = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Retained protocol/SAP MMD</title>'
    body += '<style>body{font:14px/1.5 monospace;margin:2rem}pre{white-space:pre-wrap}a{color:#52647b}.line{display:block;scroll-margin:2rem}.line:target{background:#fff1bd}</style>'
    body += '<h1>Retained protocol/SAP MMD conversion</h1><p>Check transcription and figures against the original publisher PDF before final analysis.</p><pre>'
    for number, line in enumerate(source.read_text().splitlines(), 1):
        body += f'<span class="line" id="L{number}"><a href="#L{number}">{number}</a> {html.escape(line)}</span>\n'
    (target / 'protocol-sap.html').write_text(body+'</pre></html>', encoding='ascii', errors='xmlcharrefreplace')
    specs = target / 'specs'
    specs.mkdir(exist_ok=True)
    for dataset in report['datasets']:
        shutil.copyfile(root / dataset['spec'], specs / (dataset['domain'].lower()+'.yaml'))
        dataset['spec_view'] = f"specs/{dataset['domain'].lower()}.yaml"
    for section in ['sdtm', 'adam']:
        shutil.copyfile(root / study / 'data' / section / 'define.xml', target / f'define-{section}.xml')
    verified_report(root, study, revision)
    return {key: report[key] for key in ['status','created_utc','engine','source_subjects',
            'datasets','define_xml','reference_comparison','human_review','review','summaries']} | {
                'report': 'build-report.json', 'package': f'{study}-development.zip',
                'protocol': 'protocol-sap.html'}


def build_synthetic(root, destination, revision, *, allow_unbuilt=False):
    from .datasets import write_json

    records = []
    for study, entry in synthetic_catalog(root).items():
        record = inventory(root, study, entry, revision)
        record['development'] = development(root, study, destination / 'synthetic' / study, revision,
                                             required=entry.get('build_required', False) and not allow_unbuilt)
        # Submission metadata is generated beside the transport files it describes.
        record['stages'][-1]['count'] += sum(
            (root / study / 'data' / section / 'define.xml').is_file() for section in ['sdtm', 'adam'])
        write_json(destination / "synthetic" / study / "catalog.json", record)
        records.append(
            {
                "id": study,
                "title": entry["title"],
                "archives": sum(a["available"] for a in record["archives"]),
                "url": f"synthetic/{study}/catalog.json",
            }
        )
    write_json(
        destination / "synthetic/index.json",
        {"schema_version": SCHEMA_VERSION, "revision": revision, "studies": records},
    )
    return records

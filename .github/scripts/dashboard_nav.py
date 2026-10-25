"""Populate native MkDocs study navigation from the publication catalog."""

from pathlib import Path
from study_evidence import catalog

ROOT = Path(__file__).resolve().parents[2]


def study_navigation(root, manual):
    entries = catalog(root)
    owned = {"studies/index.md", *(f"studies/{name}.md" for name in entries)}
    tail = [item for item in manual if not any(path in owned for path in item.values())]
    return [
        {"Study verification": "studies/index.md"},
        *({entry["title"]: f"studies/{name}.md"} for name, entry in entries.items()),
        *tail,
    ]


def on_config(config):
    for item in config.get("nav", []):
        if "Studies" in item:
            item["Studies"] = study_navigation(ROOT, item["Studies"])
    return config

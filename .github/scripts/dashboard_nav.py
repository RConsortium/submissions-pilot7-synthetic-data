"""Populate native MkDocs study navigation from the publication catalog."""

from pathlib import Path
from study_evidence import catalog
from study_dashboard.synthetic import synthetic_catalog

ROOT = Path(__file__).resolve().parents[2]


def study_navigation(root, manual):
    entries = catalog(root)
    owned = {"studies/index.md", *(f"studies/{name}.md" for name in entries)}
    entries = {name: entry for name, entry in entries.items()
               if entry.get("category") != "synthetic"}
    tail = [item for item in manual if not any(path in owned for path in item.values())]
    return [
        {"Study report": "studies/index.md"},
        *({entry["title"]: f"studies/{name}.md"} for name, entry in entries.items()),
        *tail,
    ]


def synthetic_navigation(root):
    entries = {**synthetic_catalog(root), **{
        name: entry for name, entry in catalog(root).items()
        if entry.get("category") == "synthetic"
    }}
    return [
        {"Synthetic report": "synthetic/index.md"},
        *(
            {entry["title"]: f"studies/{name}.md"}
            for name, entry in entries.items()
        ),
    ]


def on_config(config):
    for item in config.get("nav", []):
        for title in ("Pilot studies", "Studies"):
            if title in item:
                item[title] = study_navigation(ROOT, item[title])
        if "Synthetic data" in item:
            item["Synthetic data"] = synthetic_navigation(ROOT)
    return config

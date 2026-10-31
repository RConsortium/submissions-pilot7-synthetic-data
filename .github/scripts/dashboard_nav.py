"""Populate native MkDocs study navigation from the publication catalog."""

from pathlib import Path
from study_evidence import catalog
from study_dashboard.synthetic import synthetic_catalog

ROOT = Path(__file__).resolve().parents[2]
PILOT_SECTION = "Pilot studies"
SYNTHETIC_SECTION = "Synthetic studies"


def study_navigation(root, manual):
    entries = catalog(root)
    owned = {"studies/index.md", *(f"studies/{name}.md" for name in entries)}
    entries = {name: entry for name, entry in entries.items()
               if entry.get("category") != "synthetic"}
    tail = [item for item in manual if not any(path in owned for path in item.values())]
    return [
        {"Pilot study report": "studies/index.md"},
        *({entry["title"]: f"studies/{name}.md"} for name, entry in entries.items()),
        *tail,
    ]


def synthetic_navigation(root):
    entries = {**synthetic_catalog(root), **{
        name: entry for name, entry in catalog(root).items()
        if entry.get("category") == "synthetic"
    }}
    return [
        {"Synthetic data report": "synthetic/index.md"},
        *(
            {entry["title"]: f"studies/{name}.md"}
            for name, entry in entries.items()
        ),
    ]


def populate(nav, root):
    """Fill the pilot and synthetic sections of a navigation list in place."""
    for item in nav:
        if PILOT_SECTION in item:
            item[PILOT_SECTION] = study_navigation(root, item[PILOT_SECTION])
        if SYNTHETIC_SECTION in item:
            item[SYNTHETIC_SECTION] = synthetic_navigation(root)
    return nav


def on_config(config):
    populate(config.get("nav", []), ROOT)
    return config

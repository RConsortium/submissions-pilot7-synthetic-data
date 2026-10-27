"""Publish the exact compared XML bytes and escaped, line-numbered source views."""

import hashlib
import html
import shutil

from lxml import etree

from study_define import candidate_path

from .datasets import write_json
from .documents import document_html


def export_comparison(root, study, target, validation):
    candidate = candidate_path(root, study)
    if candidate is None:
        return None
    evidence = validation.get("define_xml", {})
    folder = target / "define"
    folder.mkdir()
    result = {"evidence": "define/comparison.json"}
    write_json(target / result["evidence"], evidence)
    for side, path, digest in (
        ("reference", root / study / "spec/define/define-adam.xml", "reference_sha256"),
        ("candidate", candidate, "candidate_sha256"),
    ):
        record = {"path": path.relative_to(root).as_posix(), "available": False}
        result[side] = record
        if not evidence.get(digest):
            continue
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != evidence[digest]:
            raise ValueError(f"{study}: {side} Define-XML changed after validation")
        original = folder / f"{side}.xml"
        shutil.copyfile(path, original)
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        encoding = etree.parse(str(path), parser).docinfo.encoding
        lines = "".join(
            f'<li id="L{number}"><code>{html.escape(line) or " "}</code></li>'
            for number, line in enumerate(path.read_text(encoding=encoding).lstrip("\ufeff").splitlines(), 1)
        )
        view = folder / f"{side}.html"
        view.write_text(document_html(
            "Original Define-XML" if side == "reference" else "yamaa-generated Define-XML",
            '<style>body{max-width:none;margin:16px;font:13px/1.5 monospace}'
            'h1{font:600 16px system-ui}ol{padding-left:5em}'
            'li{padding-left:8px;white-space:pre}li::marker{color:#687587}'
            'code{font:inherit}:target{background:#fff5d6}</style>'
            f'<ol aria-label="XML source lines">{lines}</ol>',
        ), encoding="utf-8")
        record.update(available=True, original=original.relative_to(target).as_posix(),
                      view=view.relative_to(target).as_posix())
    return result

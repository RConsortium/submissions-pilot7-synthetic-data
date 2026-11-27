#!/usr/bin/env python3
"""Transcribe a received ADaM Define-XML 2.0 into a yamaa reproduced-mode layer.

The executable specs of a cut (``<cut>/<dataset>.yaml``) derive the data and
are verified against the submitted datasets. This tool writes the *metadata*
layer that lets yamaa compose the submitted define.xml from those same specs:

    <cut>/define/project.yaml           one adam section (DEFINE-1, DEFINE-30)
    <cut>/define/codelists.yaml         every CodeList of the received file
    <cut>/define/analysis-results.yaml  its arm:AnalysisResultDisplays, if any
    <cut>/define/<dataset>.yaml         one wrapper per ItemGroupDef

Each wrapper names the cut spec as its ``parent`` (LAYER-1) and writes only
what the received document says differently from what the spec already
declares: a field the spec carries with the same value is inherited, a field
it carries with another value is restated, and a field it carries that the
received document lacks is listed under ``clear`` (LAYER-9). The spec's own
derivations, keys and output stay untouched, so the composed define describes
exactly the datasets the specs produce.

Usage (from the repo root, with a python that imports yamaa):

    python scripts/define/transcribe_define.py \
        --received mrna-1273-p201/s3-d57/spec/define/define-adam.xml \
        --cut-dir mrna-1273-p201/s3-d57

The received file is read only. Wrappers, codelists and the project go to
<cut-dir>/spec/define/ (or python scripts/reproduce.py define --transcribe).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

import yaml
from lxml import etree

NS = {
    "odm": "http://www.cdisc.org/ns/odm/v1.3",
    "def": "http://www.cdisc.org/ns/def/v2.0",
    "arm": "http://www.cdisc.org/ns/arm/v1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

# Whether the yamaa in yamaa.lock admits a received codelist numbered from 0
# (elong0527/yamaa#5062). Set it to True in the commit that moves yamaa.lock
# to a yamaa that includes #5062, together with the re-transcribed layers;
# before that, such a codelist is written without OrderNumber (gap G1).
ADMITS_ORDER_ZERO = False

# A where value has at least one character (SUB-12); a received empty
# CheckValue is written as this visible placeholder and recorded, so the
# comparison shows the difference instead of hiding it.
EMPTY_PLACEHOLDER = "(empty)"

# ARM 1.0 published reasons and purposes (DEFINE-31). A received value
# outside them is written as the published value it names and recorded.
PUBLISHED_REASONS = {
    "SAP": "SPECIFIED IN SAP",
}
PUBLISHED_PURPOSES = {
    "PRIMARY OUTCOME MEASURE": "PRIMARY OUTCOME MEASURE",
    "KEY SECONDARY OUTCOME MEASURE": "SECONDARY OUTCOME MEASURE",
}

# Define-XML 2.0 ADaM-IG StandardName -> yamaa implementation guide name.
STANDARD_NAMES = {"ADaM-IG": "ADaMIG"}


# --------------------------------------------------------------------------
# YAML output: block style, insertion order, quoted where YAML would retype.
# --------------------------------------------------------------------------
class _Dumper(yaml.SafeDumper):
    pass


def _str_rep(dumper, value):
    style = None
    if "\n" in value:
        style = "|"
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_rep)
_Dumper.add_representer(
    OrderedDict, lambda d, v: d.represent_mapping("tag:yaml.org,2002:map", v.items())
)


def dump(doc: dict, header: str) -> str:
    body = yaml.dump(doc, Dumper=_Dumper, sort_keys=False, allow_unicode=True,
                     width=4096, default_flow_style=False)
    return header + body


def needs_utf8(text: str) -> bool:
    return any(ord(c) > 127 for c in text)


def with_encoding(doc: dict) -> dict:
    """Insert `encoding: utf-8` after `type` when the document holds non-ASCII."""
    probe = yaml.dump(doc, Dumper=_Dumper, allow_unicode=True)
    if not needs_utf8(probe):
        return doc
    out = OrderedDict()
    for k, v in doc.items():
        out[k] = v
        if k == "type":
            out["encoding"] = "utf-8"
    return out


# --------------------------------------------------------------------------
# Reading the received document.
# --------------------------------------------------------------------------
def text_of(el) -> str | None:
    """TranslatedText of a Description child, tabs and CRs made spaces."""
    if el is None:
        return None
    tt = el.find("odm:Description/odm:TranslatedText", NS)
    if tt is None:
        return None
    t = (tt.text or "")
    return t.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")


def strip_prefix(oid: str, prefix: str) -> str:
    assert oid.startswith(prefix), (oid, prefix)
    return oid[len(prefix):]


def document_id(leaf_id: str) -> str:
    """Document id for a received leaf ID (LF.<id>, DEFINE-9).

    A document id may start with a digit (LF.201114-..., yamaa#4853).
    """
    return strip_prefix(leaf_id, "LF.")


def doc_refs(el) -> list:
    refs = []
    for dr in el.findall("def:DocumentRef", NS):
        ref = OrderedDict(document=document_id(dr.get("leafID")))
        pr = dr.find("def:PDFPageRef", NS)
        if pr is not None:
            pages = OrderedDict(type=pr.get("Type"))
            pages["refs"] = pr.get("PageRefs") or f"{pr.get('FirstPage')}-{pr.get('LastPage')}"
            if pr.get("Title"):
                pages["title"] = pr.get("Title")
            ref["pages"] = pages
        refs.append(ref if len(ref) > 1 else ref["document"])
    return refs


class Received:
    def __init__(self, path: Path):
        self.tree = etree.parse(str(path))
        self.root = self.tree.getroot()
        self.study = self.root.find("odm:Study", NS)
        self.mdv = self.study.find("odm:MetaDataVersion", NS)
        self.items = {e.get("OID"): e for e in self.mdv.findall("odm:ItemDef", NS)}
        self.methods = {e.get("OID"): e for e in self.mdv.findall("odm:MethodDef", NS)}
        self.comments = {e.get("OID"): e for e in self.mdv.findall("def:CommentDef", NS)}
        self.codelists = self.mdv.findall("odm:CodeList", NS)
        self.vlds = {e.get("OID"): e for e in self.mdv.findall("def:ValueListDef", NS)}
        self.wcs = {e.get("OID"): e for e in self.mdv.findall("def:WhereClauseDef", NS)}
        self.groups = self.mdv.findall("odm:ItemGroupDef", NS)
        # Received codelists no ItemDef binds (such as an ExternalCodeList of
        # MedDRA). yamaa writes one only when a dataset lists it under
        # `submission.codelists` (CT-10, elong0527/yamaa#4887); the first
        # dataset with a spec carries them (see main).
        bound = {r.get("CodeListOID") for r in self.mdv.iter("{%s}CodeListRef" % NS["odm"])}
        self.unbound_codelists = [strip_prefix(c.get("OID"), "CL.") for c in self.codelists
                                  if c.get("OID") not in bound]
        self.unbound_owner = None
        self.stylesheet = None
        for node in self.root.itersiblings(preceding=True):
            if isinstance(node, etree._ProcessingInstruction) and node.target == "xml-stylesheet":
                m = re.search(r'href="([^"]+)"', node.text or "")
                self.stylesheet = m.group(1) if m else None

    # -- methods and comments ------------------------------------------------
    def method(self, oid: str) -> OrderedDict:
        m = self.methods[oid]
        out = OrderedDict()
        if oid != oid.strip():
            # A received OID with surrounding spaces (C4591001 ADCM
            # "MT.ADCM.ONPERFL "); the OID pattern admits none (yamaa#4853).
            self.deviations.append(f"{oid!r}: method OID with surrounding spaces written stripped")
        out["oid"] = oid.strip()
        out["name"] = m.get("Name")
        out["type"] = m.get("Type")
        out["description"] = text_of(m) or ""
        fe = m.find("odm:FormalExpression", NS)
        if fe is not None:
            out["expression"] = OrderedDict(context=fe.get("Context"), code=fe.text or "")
        refs = doc_refs(m)
        if refs:
            out["documents"] = refs
        return out

    def comment(self, oid: str) -> OrderedDict:
        c = self.comments[oid]
        out = OrderedDict(oid=oid, text=text_of(c) or "")
        refs = doc_refs(c)
        if refs:
            out["documents"] = refs
        return out

    # -- where clauses -------------------------------------------------------
    def where(self, wc_oid: str, dataset: str) -> OrderedDict:
        wc = self.wcs[wc_oid]
        out = OrderedDict()
        for rc in wc.findall("odm:RangeCheck", NS):
            col = strip_prefix(rc.get("{%s}ItemOID" % NS["def"]), f"IT.{dataset}.")
            vals = [cv.text or "" for cv in rc.findall("odm:CheckValue", NS)]
            out[col] = self._condition(rc.get("Comparator"), vals, wc_oid)
        return out

    def published(self, ar, attr: str, mapping: dict) -> str:
        """A published ARM value for a received reason or purpose (DEFINE-31).

        An exact published value is kept; otherwise the keyword it carries
        (PRIMARY / SECONDARY / EXPLORATORY, SAP / PROTOCOL) picks one.
        """
        received = ar.get(attr)
        flat = " ".join(received.split())
        up = flat.upper()
        value = mapping.get(up)
        if value is None:
            for word, published in (("PRIMARY", "PRIMARY OUTCOME MEASURE"),
                                    ("SECONDARY", "SECONDARY OUTCOME MEASURE"),
                                    ("EXPLORATORY", "EXPLORATORY OUTCOME MEASURE"),
                                    ("SAP", "SPECIFIED IN SAP"),
                                    ("PROTOCOL", "SPECIFIED IN PROTOCOL")):
                if word in up and (published.endswith("MEASURE") == (attr == "AnalysisPurpose")):
                    value = published
                    break
        value = value or flat
        if value != received:
            self.deviations.append(f"{ar.get('OID')}: {attr} {received!r} written as {value!r}")
        return value

    # Received comparators yamaa writes differently, recorded per run.
    deviations: list = []

    def _condition(self, comp: str, vals: list, wc_oid: str):
        """yamaa where condition for one received RangeCheck (SUB-12).

        A list is EQ for one value and IN for several, so those need no
        comparator. A received IN or NOTIN with a single CheckValue
        (Pinnacle 21 joins the list with spaces into one value) states its
        comparator (yamaa#4849); an empty CheckValue is written as ''.
        """
        if comp == "EQ" and len(vals) == 1 or comp == "IN" and len(vals) > 1:
            return vals
        return OrderedDict(comparator=comp, values=vals)

    def analysis_where(self, wc_oid: str) -> tuple[str, OrderedDict]:
        wc = self.wcs[wc_oid]
        out = OrderedDict()
        for rc in wc.findall("odm:RangeCheck", NS):
            oid = rc.get("{%s}ItemOID" % NS["def"])
            _, ds, col = oid.split(".", 2)
            vals = [cv.text or "" for cv in rc.findall("odm:CheckValue", NS)]
            out[col] = self._condition(rc.get("Comparator"), vals, wc_oid)
        return out

    # -- one ItemDef's own metadata (shared by columns and value-level) ------
    def item_metadata(self, item) -> OrderedDict:
        out = OrderedDict()
        out["data_type"] = item.get("DataType")
        if item.get("Length") is not None:
            out["length"] = int(item.get("Length"))
        if item.get("SignificantDigits") is not None:
            out["significant_digits"] = int(item.get("SignificantDigits"))
        fmt = item.get("{%s}DisplayFormat" % NS["def"])
        if fmt is not None:
            out["display_format"] = fmt
        cl = item.find("odm:CodeListRef", NS)
        if cl is not None:
            out["codelist"] = strip_prefix(cl.get("CodeListOID"), "CL.")
        origins = []
        for o in item.findall("def:Origin", NS):
            org = OrderedDict(type=o.get("Type"))
            d = text_of(o)
            if d:
                org["description"] = d
            refs = doc_refs(o)
            if refs:
                org["documents"] = refs
            origins.append(org)
        if origins:
            out["origins"] = origins
        com = item.get("{%s}CommentOID" % NS["def"])
        if com:
            out["comment"] = self.comment(com)
        return out


# --------------------------------------------------------------------------
# The resolved parent (the cut spec), with provenance.
# --------------------------------------------------------------------------
def resolve_parent(spec_path: Path):
    import yamaa  # noqa: PLC0415  (needs the yamaa python)

    entry = yamaa.spec(str(spec_path)).resolve()["entries"][0]
    spec = entry["specification"]
    authored = {p for p, o in entry["origins"].items() if o.get("source_kind") == "authored"}
    return spec, authored


def authored_paths(prefix: str, value, authored: set) -> list[str]:
    """Pointer paths under prefix that a layer wrote (not schema defaults)."""
    return [p for p in authored if p == prefix or p.startswith(prefix + "/")]


def spec_path_for(pointer_prefix: str, name: str, field: str) -> str:
    return f"columns.{name}.submission.{field}" if field else f"columns.{name}.submission"


def plain(v):
    """Normalise a resolved value for comparison with a transcribed one."""
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [plain(x) for x in v]
    return v


def method_equal(inherited, wanted) -> bool:
    if inherited is None:
        return False
    if isinstance(inherited, str):
        inherited = {"description": inherited}
    inh = {k: v for k, v in plain(inherited).items() if v is not None}
    want = {k: v for k, v in plain(wanted).items() if v is not None}
    inh.setdefault("type", "Computation")
    want.setdefault("type", "Computation")
    return inh == want


# --------------------------------------------------------------------------
# Wrapper generation.
# --------------------------------------------------------------------------
# yamaa column type for a define-only column of a received data type.
COLUMN_TYPES = {"text": "str", "integer": "int", "float": "float", "date": "date",
                "datetime": "datetime", "time": "time"}

# Submission fields Define-XML 2.0 never writes for ADaM: an inherited value
# changes nothing in the document, so the wrapper leaves it inherited.
NOT_IN_DEFINE_20 = {"core", "role", "inventory_vocabulary"}

SUBMISSION_FIELDS = [
    "order", "key_sequence", "mandatory", "data_type", "length",
    "significant_digits", "display_format", "codelist", "origins", "method",
    "comment", "value_level",
]


def column_wanted(rec: Received, ds: str, ref, item) -> tuple[str, OrderedDict]:
    """(label, submission) the received document gives one described column."""
    sub = OrderedDict()
    sub["order"] = int(ref.get("OrderNumber"))
    if ref.get("KeySequence") is not None:
        sub["key_sequence"] = int(ref.get("KeySequence"))
    sub["mandatory"] = ref.get("Mandatory") == "Yes"
    sub.update(rec.item_metadata(item))
    if ref.get("MethodOID"):
        sub["method"] = rec.method(ref.get("MethodOID"))
    vlr = item.find("def:ValueListRef", NS)
    if vlr is not None:
        sub["value_level"] = value_level(rec, ds, item.get("Name"), vlr.get("ValueListOID"))
    # Keep a stable field order.
    ordered = OrderedDict((k, sub[k]) for k in SUBMISSION_FIELDS if k in sub)
    return text_of(item) or "", ordered


def value_level(rec: Received, ds: str, col: str, vl_oid: str) -> list:
    entries = []
    for ir in rec.vlds[vl_oid].findall("odm:ItemRef", NS):
        item = rec.items[ir.get("ItemOID")]
        e = OrderedDict()
        oid = ir.get("ItemOID")
        if oid.startswith(f"IT.{ds}.{col}."):
            e["id"] = strip_prefix(oid, f"IT.{ds}.{col}.")
        else:
            # Pinnacle 21 sometimes spells a per-value OID after another
            # column (P301 S3 VL.ADTTEB.ADT cites IT.ADTTEB.AVAL.<...>): the
            # entry keeps the received OID (yamaa#4847).
            e["id"] = oid.split(".", 3)[3]
            e["oid"] = oid
        if item.get("Name") != col:
            e["name"] = item.get("Name")
        wcr = ir.find("def:WhereClauseRef", NS)
        e["where"] = rec.where(wcr.get("WhereClauseOID"), ds)
        e["where_oid"] = wcr.get("WhereClauseOID")
        lab = text_of(item)
        if lab:
            e["label"] = lab
        if ir.get("KeySequence") is not None:
            e["key_sequence"] = int(ir.get("KeySequence"))
        e["mandatory"] = ir.get("Mandatory") == "Yes"
        e.update(rec.item_metadata(item))
        if ir.get("MethodOID"):
            e["method"] = rec.method(ir.get("MethodOID"))
        entries.append(e)
    return entries


def dataset_wanted(rec: Received, ig) -> OrderedDict:
    sub = OrderedDict()
    sub["mode"] = "reproduced"
    sub["label"] = text_of(ig) or ""
    sub["class"] = ig.get("{%s}Class" % NS["def"])
    sub["structure"] = ig.get("{%s}Structure" % NS["def"])
    sub["repeating"] = ig.get("Repeating") == "Yes"
    sub["reference_data"] = ig.get("IsReferenceData") == "Yes"
    leaf = ig.find("def:leaf", NS)
    if leaf is not None:
        sub["artifact"] = leaf.get(XLINK_HREF)
    com = ig.get("{%s}CommentOID" % NS["def"])
    if com:
        sub["comment"] = rec.comment(com)
    if rec.unbound_codelists and ig.get("Name") == rec.unbound_owner:
        sub["codelists"] = list(rec.unbound_codelists)
    return sub


def build_wrapper(rec: Received, ig, spec_file: Path, rel_parent: str, notes: list) -> OrderedDict:
    ds = ig.get("Name")
    parent, authored = resolve_parent(spec_file)
    pcols = {c["name"]: (i, c) for i, c in enumerate(parent.get("columns", []))}
    outcols = parent["output"]["columns"]
    clear: list[str] = []

    # Dataset submission: restate every field (the block composes field by
    # field, so inherited fields the received file lacks are cleared).
    want_ds = dataset_wanted(rec, ig)
    have_ds = parent.get("submission") or {}
    ds_sub = OrderedDict()
    for k, v in want_ds.items():
        if plain(have_ds.get(k)) != plain(v) or "/submission/" + k not in authored:
            if k == "comment" and "/submission/comment" in authored:
                clear.append("submission.comment")
            ds_sub[k] = v
    for p in sorted(authored):
        m = re.fullmatch(r"/submission/([a-z_]+)", p)
        if m and m.group(1) not in want_ds and m.group(1) not in ("label", "class", "structure", "repeating"):
            clear.append(f"submission.{m.group(1)}")

    described = {}
    for ref in ig.findall("odm:ItemRef", NS):
        item = rec.items[ref.get("ItemOID")]
        described[item.get("Name")] = (ref, item)

    columns = []
    for name in outcols:
        if name not in pcols:
            notes.append(f"{ds}: output column {name} has no declaration in the spec")
            continue
        idx, pc = pcols[name]
        base = f"/columns/{idx}/submission"
        col = OrderedDict(name=name)
        if name not in described:
            # The received document leaves this column out (DEFINE-30).
            if any(p.startswith(base + "/") or p == base for p in authored):
                clear.append(f"columns.{name}.submission")
            col["submission"] = OrderedDict(omitted=True)
            columns.append(col)
            continue
        ref, item = described.pop(name)
        label, want = column_wanted(rec, ds, ref, item)
        if pc.get("label") != label:
            col["label"] = label
        have = pc.get("submission") or {}
        sub = OrderedDict()
        for k, v in want.items():
            inherited = f"{base}/{k}" in authored
            if k in ("method",) and inherited and method_equal(have.get(k), v):
                continue
            if inherited and plain(have.get(k)) == plain(v):
                continue
            if inherited and isinstance(have.get(k), dict):
                # A class merges field by field; replace it whole instead.
                clear.append(f"columns.{name}.submission.{k}")
            sub[k] = v
        for p in sorted(authored):
            m = re.fullmatch(re.escape(base) + r"/([a-z_]+)", p)
            if m and m.group(1) not in want and m.group(1) not in NOT_IN_DEFINE_20:
                clear.append(f"columns.{name}.submission.{m.group(1)}")
        if sub:
            col["submission"] = sub
        if len(col) > 1:
            columns.append(col)
    # A column the received define describes but the spec does not output
    # (the submitted data may not carry it either: C4591001 ADMH ADTF and
    # VAX20U are define-only). The wrapper declares it with a missing-value
    # derivation and lists it in this layer's own output, so the composed
    # define describes it; the verified spec's output is unchanged.
    extra_out = []
    for name, (ref, item) in described.items():
        label, want = column_wanted(rec, ds, ref, item)
        col = OrderedDict(name=name, type=COLUMN_TYPES.get(want["data_type"], "str"),
                          label=label, derivation=None)
        col["submission"] = want
        columns.append(col)
        extra_out.append(name)
        notes.append(f"{ds}: received column {name} is not an output column of the spec; "
                     f"declared define-only in the layer")

    doc = OrderedDict()
    doc["yamaa"] = "1.0"
    doc["type"] = "spec"
    doc["parent"] = rel_parent
    if clear:
        doc["clear"] = sorted(set(clear), key=clear.index)
    doc["submission"] = ds_sub
    if extra_out:
        doc["output"] = OrderedDict(columns=list(outcols) + extra_out)
    if columns:
        doc["columns"] = columns
    return with_encoding(doc)


# --------------------------------------------------------------------------
# Codelists, documents, analysis results, project.
# --------------------------------------------------------------------------
def coded_value(text: str, data_type: str):
    """A coded value of its codelist's data type (CT-4)."""
    if data_type == "integer":
        return int(text)
    if data_type == "float":
        return float(text)
    return text


def codelists_docs(rec: Received) -> list[tuple[str, OrderedDict]]:
    """Two codelist files: published (CDISC/NCI) and sponsor-defined.

    A codelist the received file ties to published terminology -- it carries
    an NCI Alias on the list or an item, or a sponsor-extended item -- goes
    to a source declaring `standard` (CT-2). Define-XML 2.0 records no
    terminology standard (DEFINE-29), so the version is never written; it
    only lets CT-6 admit the extended items the received file marks.
    """
    published, sponsor = [], []
    for cl in rec.codelists:
        c = OrderedDict()
        c["id"] = strip_prefix(cl.get("OID"), "CL.")
        c["name"] = cl.get("Name")
        c["data_type"] = cl.get("DataType")
        if cl.get("SASFormatName"):
            c["format_name"] = cl.get("SASFormatName")
        ext = cl.find("odm:ExternalCodeList", NS)
        if ext is not None:
            e = OrderedDict(dictionary=ext.get("Dictionary"), version=ext.get("Version"))
            if ext.get("href"):
                e["href"] = ext.get("href")
            c["external"] = e
        items = []
        for it in cl:
            if etree.QName(it).localname not in ("CodeListItem", "EnumeratedItem"):
                continue
            i = OrderedDict(value=coded_value(it.get("CodedValue"), cl.get("DataType")))
            dec = it.find("odm:Decode/odm:TranslatedText", NS)
            if dec is not None:
                i["decode"] = dec.text or ""
            if it.get("Rank") is not None:
                i["rank"] = int(it.get("Rank"))
            al = it.find("odm:Alias", NS)
            if al is not None:
                i["alias"] = al.get("Name")
            if it.get("{%s}ExtendedValue" % NS["def"]) == "Yes":
                i["extended"] = True
            if it.get("OrderNumber") is not None:
                i["order"] = int(it.get("OrderNumber"))
            items.append(i)
        orders = [i.get("order") for i in items]
        lowest = 0 if ADMITS_ORDER_ZERO else 1
        if None in orders or len(set(orders)) != len(orders) or any(o is not None and o < lowest for o in orders):
            # Every item or none declares order (CT-5), and ODM's xs:unique
            # UC-CL-2/UC-CL-4 forbid a repeated number: a codelist that
            # repeats one keeps none, and the comparison shows it. A number
            # from 0 is declared as received only once the pinned yamaa
            # admits it (ADMITS_ORDER_ZERO, yamaa#5062 for yamaa#5022).
            for i in items:
                i.pop("order", None)
            if any(o is not None for o in orders):
                rec.deviations.append(f"{cl.get('OID')}: OrderNumber repeated, partial or below {lowest}; not declared")
        extended = any(i.get("extended") for i in items)
        if items:
            if extended:
                c["extensible"] = True
            c["items"] = items
        al = cl.find("odm:Alias", NS)
        if al is not None:
            c["alias"] = al.get("Name")
        is_published = extended or al is not None or any("alias" in i for i in items)
        (published if is_published else sponsor).append(c)
    out = []
    if published:
        out.append(("codelists-published.yaml", with_encoding(OrderedDict(
            yamaa="1.0", type="codelists",
            standard=OrderedDict(name="CDISC/NCI", publishing_set="ADaM",
                                 version="not recorded in the received Define-XML 2.0"),
            codelists=published))))
    if sponsor:
        out.append(("codelists-sponsor.yaml", with_encoding(OrderedDict(
            yamaa="1.0", type="codelists", codelists=sponsor))))
    return out


def documents(rec: Received) -> list:
    supp = {document_id(d.get("leafID"))
            for d in rec.mdv.findall("def:SupplementalDoc/def:DocumentRef", NS)}
    acrf = {document_id(d.get("leafID"))
            for d in rec.mdv.findall("def:AnnotatedCRF/def:DocumentRef", NS)}
    out = []
    for leaf in rec.mdv.findall("def:leaf", NS):
        did = document_id(leaf.get("ID"))
        kind = "annotated_crf" if did in acrf else "supplemental" if did in supp else "other"
        title = leaf.find("def:title", NS)
        out.append(OrderedDict(id=did, kind=kind, link=leaf.get(XLINK_HREF),
                               title=(title.text if title is not None else did)))
    # SupplementalDoc lists its references in its own order; keep it.
    order = [document_id(d.get("leafID"))
             for d in rec.mdv.findall("def:SupplementalDoc/def:DocumentRef", NS)]
    out.sort(key=lambda d: order.index(d["id"]) if d["id"] in order else len(order))
    return out


def analysis_results(rec: Received) -> OrderedDict | None:
    ard = rec.mdv.find("arm:AnalysisResultDisplays", NS)
    if ard is None:
        return None
    displays = []
    for rd in ard.findall("arm:ResultDisplay", NS):
        d = OrderedDict()
        d["id"] = re.sub(r"[^A-Za-z0-9_.]", "", strip_prefix(rd.get("OID"), "RD."))
        d["oid"] = rd.get("OID")
        d["name"] = rd.get("Name")
        d["description"] = text_of(rd) or ""
        refs = doc_refs(rd)
        if refs:
            d["documents"] = refs
        results = []
        for n, ar in enumerate(rd.findall("arm:AnalysisResult", NS), 1):
            r = OrderedDict()
            r["id"] = f"R{n}"
            r["oid"] = ar.get("OID")
            r["description"] = text_of(ar) or ""
            r["reason"] = rec.published(ar, "AnalysisReason", PUBLISHED_REASONS)
            r["purpose"] = rec.published(ar, "AnalysisPurpose", PUBLISHED_PURPOSES)
            dsets = OrderedDict()
            ads = ar.find("arm:AnalysisDatasets", NS)
            for ad in ads.findall("arm:AnalysisDataset", NS):
                dsn = strip_prefix(ad.get("ItemGroupOID"), "IG.")
                one = OrderedDict()
                wcr = ad.find("def:WhereClauseRef", NS)
                if wcr is not None:
                    one["where"] = rec.analysis_where(wcr.get("WhereClauseOID"))
                    one["where_oid"] = wcr.get("WhereClauseOID")
                vars_ = [strip_prefix(v.get("ItemOID"), f"IT.{dsn}.")
                         for v in ad.findall("arm:AnalysisVariable", NS)]
                if vars_:
                    one["variables"] = vars_
                dsets[dsn] = one
            r["datasets"] = dsets
            if ads.get("{%s}CommentOID" % NS["def"]):
                c = rec.comment(ads.get("{%s}CommentOID" % NS["def"]))
                r["join"] = OrderedDict((k, v) for k, v in c.items() if k != "oid")
            doc = ar.find("arm:Documentation", NS)
            if doc is not None:
                text = text_of(doc) or ""
                if not text.strip():
                    rec.deviations.append(f"{ar.get('OID')}: empty arm:Documentation written as {EMPTY_PLACEHOLDER!r}")
                    text = EMPTY_PLACEHOLDER
                dd = OrderedDict(text=text)
                refs = doc_refs(doc)
                if refs:
                    dd["documents"] = refs
                r["documentation"] = dd if len(dd) > 1 else dd["text"]
            pc = ar.find("arm:ProgrammingCode", NS)
            if pc is not None:
                p = OrderedDict()
                if pc.get("Context"):
                    p["context"] = pc.get("Context")
                code = pc.find("arm:Code", NS)
                if code is not None and code.text:
                    p["code"] = code.text
                refs = doc_refs(pc)
                if refs:
                    p["documents"] = refs
                if "code" not in p and not refs:
                    rec.deviations.append(f"{ar.get('OID')}: empty arm:ProgrammingCode written with code {EMPTY_PLACEHOLDER!r}")
                    p["code"] = EMPTY_PLACEHOLDER
                if "context" not in p:
                    p["context"] = EMPTY_PLACEHOLDER
                r["programming_code"] = p
            results.append(r)
        d["results"] = results
        displays.append(d)
    return with_encoding(OrderedDict(yamaa="1.0", type="analysis_results", displays=displays))


def xml_lang_scope(rec: Received) -> str:
    """Where the received document writes xml:lang on TranslatedText (yamaa#4850)."""
    lang = "{http://www.w3.org/XML/1998/namespace}lang"
    arm = rec.mdv.find("arm:AnalysisResultDisplays", NS)
    in_arm = set(arm.iter("{%s}TranslatedText" % NS["odm"])) if arm is not None else set()
    tts = list(rec.root.iter("{%s}TranslatedText" % NS["odm"]))
    with_lang = [t for t in tts if t.get(lang) is not None]
    if not with_lang:
        return "none"
    if in_arm and all(t.get(lang) is None for t in in_arm) and all(
            t.get(lang) is not None for t in tts if t not in in_arm):
        return "outside_analysis_results"
    return "all"


def project_doc(rec: Received, wrappers: list[str], has_ard: bool,
                codelist_files: list[str]) -> OrderedDict:
    gv = rec.study.find("odm:GlobalVariables", NS)
    mdv = rec.mdv
    std_name = mdv.get("{%s}StandardName" % NS["def"])
    std_version = mdv.get("{%s}StandardVersion" % NS["def"])
    sec = OrderedDict()
    sec["specs"] = wrappers
    sec["standards"] = [OrderedDict(name=STANDARD_NAMES.get(std_name, std_name),
                                    version=std_version, status="Final")]
    sec["define"] = "define-adam-yamaa.xml"
    sec["define_version"] = mdv.get("{%s}DefineVersion" % NS["def"])
    sec["context"] = "Other"
    sec["file_oid"] = rec.root.get("FileOID")
    sec["study_oid"] = rec.study.get("OID")
    mv_id = strip_prefix(mdv.get("OID"), "MDV.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", mv_id):
        # yamaa's metadata-version id is an identifier (SCHEMA-12); a received
        # OID with other characters (the EUA 27034 S1 define has a comma) is
        # written with them replaced by '_' and reported as a deviation.
        fixed = re.sub(r"[^A-Za-z0-9_.-]", "_", mv_id)
        rec.deviations.append(f"{mv_id!r}: metadata-version OID written as {fixed!r}")
        mv_id = fixed
    mv = OrderedDict(id=mv_id, name=mdv.get("Name"))
    if mdv.get("Description"):
        mv["description"] = mdv.get("Description")
    sec["metadata_version"] = mv
    if rec.root.get("Originator"):
        sec["originator"] = rec.root.get("Originator")
    if rec.stylesheet:
        sec["stylesheet"] = rec.stylesheet
    sec["source_system"] = rec.root.get("SourceSystem")
    sec["source_system_version"] = rec.root.get("SourceSystemVersion")
    scope = xml_lang_scope(rec)
    if scope != "all":
        sec["xml_lang_scope"] = scope
    docs = documents(rec)
    if docs:
        sec["documents"] = docs
    if has_ard:
        sec["analysis_results"] = ["analysis-results.yaml"]
    doc = OrderedDict()
    doc["yamaa"] = "1.0"
    doc["type"] = "project"
    doc["codelists"] = codelist_files
    doc["study"] = OrderedDict(
        id=re.sub(r"[^A-Za-z0-9_]", "_", gv.findtext("odm:ProtocolName", namespaces=NS)),
        name=gv.findtext("odm:StudyName", namespaces=NS),
        description=" ".join(gv.findtext("odm:StudyDescription", namespaces=NS).split()),
        protocol_name=gv.findtext("odm:ProtocolName", namespaces=NS),
    )
    doc["adam"] = sec
    return with_encoding(doc)


HEADER = (
    "# Generated by scripts/define/transcribe_define.py from the received\n"
    "# define.xml {received}.\n"
    "# Reproduced-mode metadata (DEFINE-30): a literal record of what the\n"
    "# received document declares. Regenerate rather than edit by hand.\n"
)


def _body(path: Path) -> str:
    return "\n".join(l for l in path.read_text().split("\n") if not l.startswith("#"))


def _resolved(spec: Path) -> str:
    """The specification `spec` resolves to, without its inputs and output path.

    Define-XML records the output columns and their metadata, never where the
    inputs are read from, so two specs that differ only in their inputs (a cut
    that reads one SDTM domain through a normalizing helper) give one define.
    """
    import json

    import yamaa

    s = yamaa.spec(str(spec)).resolve()["entries"][0]["specification"]
    s.pop("input", None)
    s.get("output", {}).pop("path", None)
    s.get("output", {}).pop("relative_to", None)
    return json.dumps(s, sort_keys=True, default=str)


def _target(path: Path) -> Path:
    """Follow a wrapper that is only a reference (`parent:` and nothing else) to its target."""
    import yaml

    seen = set()
    while path.exists() and path not in seen:
        seen.add(path)
        doc = yaml.safe_load(path.read_text()) or {}
        if set(doc) == {"yamaa", "type", "parent"}:
            path = (path.parent / doc["parent"]).resolve()
            continue
        break
    return path


def _over_codelists(odef: Path) -> dict:
    """{file name: path} of the codelist files the earlier cut's project uses."""
    import yaml

    proj = odef / "project.yaml"
    if not proj.exists():
        return {}
    files = (yaml.safe_load(proj.read_text()) or {}).get("codelists") or []
    return {Path(f).name: (odef / f).resolve() for f in files}


def share_with_over(cut_dir: Path, over: Path, out: Path, wrappers: list, cl_files: list, header: str) -> list:
    """Reference the earlier cut's define files instead of repeating identical ones.

    A wrapper is shared when its text equals the earlier cut's wrapper and the
    cut's spec resolves to the same specification as the earlier cut's: the
    earlier wrapper over the earlier spec then resolves to exactly what this
    wrapper over this spec would. A codelist file is shared when its text is equal.
    """
    import os

    odef = over / "spec" / "define"
    rel = os.path.relpath(odef, out)
    for name in wrappers:
        mine, theirs = out / name, _target(odef / name)
        if not theirs.exists() or _body(mine) != _body(theirs):
            continue
        if _resolved(cut_dir / "spec" / "yamaa" / name) != _resolved(over / "spec" / "yamaa" / name):
            continue
        mine.write_text(header + "# Identical to the earlier cut's wrapper over an identical spec, so it\n"
                        "# is that wrapper (scripts/define/transcribe_define.py --over).\n"
                        f"yamaa: '1.0'\ntype: spec\nparent: {rel}/{name}\n")
        print(f"SHARED {name} with {odef}")
    shared = []
    theirs_cl = _over_codelists(odef)
    for name in cl_files:
        theirs = theirs_cl.get(name, odef / name)
        if theirs.exists() and _body(out / name) == _body(theirs):
            (out / name).unlink()
            shared.append(os.path.relpath(theirs, out))
            print(f"SHARED {name} with {theirs.parent}")
        else:
            shared.append(name)
    return shared


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--received", type=Path, required=True)
    ap.add_argument("--cut-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None, help="default <cut-dir>/spec/define")
    ap.add_argument("--over", type=Path, default=None,
                    help="the cut this cut's specs layer over (studies.yaml `over`): a wrapper or "
                         "codelist file identical to that cut's, over a spec that resolves identically, "
                         "is written as a reference to it instead of a copy")
    args = ap.parse_args()

    rec = Received(args.received)
    out = args.out or args.cut_dir / "spec" / "define"
    out.mkdir(parents=True, exist_ok=True)
    header = HEADER.format(received=args.received.name)
    notes: list[str] = []
    wrappers = []
    rec.unbound_owner = next((ig.get("Name") for ig in rec.groups
                              if (args.cut_dir / "spec" / "yamaa" / f"{ig.get('Name').lower()}.yaml").exists()), None)
    for ig in rec.groups:
        ds = ig.get("Name")
        spec_file = args.cut_dir / "spec" / "yamaa" / f"{ds.lower()}.yaml"
        if not spec_file.exists():
            notes.append(f"{ds}: no spec {spec_file}")
            continue
        doc = build_wrapper(rec, ig, spec_file, f"../yamaa/{spec_file.name}", notes)
        (out / spec_file.name).write_text(dump(doc, header))
        wrappers.append(spec_file.name)
    cl_files = []
    for name, doc in codelists_docs(rec):
        (out / name).write_text(dump(doc, header))
        cl_files.append(name)
    ard = analysis_results(rec)
    if ard is not None:
        (out / "analysis-results.yaml").write_text(dump(ard, header))
    if args.over:
        cl_files = share_with_over(args.cut_dir, args.over, out, wrappers, cl_files, header)
    (out / "project.yaml").write_text(dump(project_doc(rec, wrappers, ard is not None, cl_files), header))
    creation = rec.root.get("CreationDateTime")
    (out / "CREATED").write_text(creation + "\n")
    for n in notes:
        print("NOTE", n)
    for d in sorted(set(rec.deviations)):
        print("DEVIATION", d)
    print(f"wrote {len(wrappers)} wrappers to {out} (created {creation})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

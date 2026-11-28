#!/usr/bin/env python3
"""Independent element-by-element comparison of two Define-XML files.

Every OID-bearing element under MetaDataVersion (and the ODM, Study,
GlobalVariables and MetaDataVersion headers) is canonicalised -- attributes
sorted, text whitespace-normalised, children kept in document order -- and
compared by (tag, OID). The report counts, per element class, the elements
that are identical, differ, or appear on one side only.

Every difference is then attributed to a defect of the submitted define
(DEFECTS below) or counted as *unexplained*. Where-clause definitions are
matched through the ItemRef or AnalysisResult that cites them, so their
contents are compared even when their OIDs differ. A cut matches its received
define "except for submitted-define defects" when the unexplained count is
zero.

    python scripts/define/compare_define.py <received.xml> <generated.xml> \
        [--detail N] [--json report.json]

Exit code 0 on a full match (no difference at all), 2 when every difference
is a submitted-define defect, 1 otherwise.
"""
import argparse
import ast
import collections
import json
import re
import sys

from lxml import etree

# Defects of the submitted define: received content that is invalid or
# nonstandard and that yamaa does not write, by an owner decision. A
# difference matched by none of these is "unexplained". Before yamaa ac826f0b
# the list also held engine gaps, things yamaa could not declare yet; all are
# fixed, so a difference of that kind is now unexplained. The report keeps the
# key names `gaps` and `gap_only`, which the Pilot 7 bundle schema reads.
DEFECTS = {
    "repeated-order": "a received codelist repeats an item OrderNumber, which the ODM 1.3.2 schema forbids "
                      "(xs:unique UC-CL-2/UC-CL-4); yamaa writes no schema-invalid document, so the codelist is "
                      "written without OrderNumber (owner decision on elong0527/yamaa#5022)",
    "arm-terms": "a received AnalysisReason or AnalysisPurpose outside the published ARM 1.0 terms, or an empty "
                 "arm:Documentation or arm:ProgrammingCode; yamaa writes the published term the value names and "
                 "no empty element (owner decision on elong0527/yamaa#4824)",
    "method-oid-nbsp": "a received method OID ending in a non-breaking space (U+00A0), which is not an identifier "
                       "character; yamaa writes the OID without it (owner decision D398, elong0527/yamaa#4935)",
}

# ARM 1.0 published AnalysisReason and AnalysisPurpose terms (DEFINE-31).
ARM_TERMS = {"SPECIFIED IN PROTOCOL", "SPECIFIED IN SAP", "DATA DRIVEN", "REQUESTED BY REGULATORY AGENCY",
             "PRIMARY OUTCOME MEASURE", "SECONDARY OUTCOME MEASURE", "EXPLORATORY OUTCOME MEASURE"}

# Elements that belong only to received datasets this repo has no spec for
# are neither defects nor unexplained: they are coverage still to build.
NOSPEC = "no spec yet"


def local(tag):
    return etree.QName(tag).localname if isinstance(tag, str) else str(tag)


def prefix(el):
    ns = etree.QName(el).namespace or ""
    if "def" in ns:
        return "def:"
    if "arm" in ns:
        return "arm:"
    return ""


def canon(el):
    if not isinstance(el.tag, str):
        return None
    attrs = tuple(sorted((local(k), v) for k, v in el.attrib.items()))
    text = " ".join((el.text or "").split())
    kids = tuple(c for c in (canon(k) for k in el) if c is not None)
    return (prefix(el) + local(el.tag), attrs, text, kids)


def oid_of(el):
    for k in ("OID", "ID", "leafID"):
        if el.get(k):
            return el.get(k)
    return None


def collect(path):
    root = etree.parse(path).getroot()
    out = collections.OrderedDict()
    hdr = {}
    hdr["ODM"] = tuple(sorted((local(k), v) for k, v in root.attrib.items()))
    study = root.find("{*}Study")
    hdr["Study"] = tuple(sorted(study.attrib.items()))
    hdr["GlobalVariables"] = canon(study.find("{*}GlobalVariables"))
    mdv = study.find("{*}MetaDataVersion")
    hdr["MetaDataVersion"] = tuple(sorted((local(k), v) for k, v in mdv.attrib.items()))
    for el in mdv:
        if not isinstance(el.tag, str):
            continue
        name = prefix(el) + local(el.tag)
        if name == "arm:AnalysisResultDisplays":
            for rd in el:
                if isinstance(rd.tag, str):
                    out[("arm:ResultDisplay", oid_of(rd))] = canon(rd)
            continue
        if name in ("def:Standards", "def:SupplementalDoc", "def:AnnotatedCRF"):
            out[(name, "-")] = canon(el)
            continue
        out[(name, oid_of(el))] = canon(el)
    # Where clauses by the ItemRef / AnalysisResult that cites them.
    cites = {}
    for vl in mdv.iter("{*}ValueListDef"):
        for ir in vl.findall("{*}ItemRef"):
            w = ir.find("{*}WhereClauseRef")
            if w is not None:
                cites[("VL", vl.get("OID"), ir.get("ItemOID"))] = w.get("WhereClauseOID")
    for ar in mdv.iter("{*}AnalysisResult"):
        for n, w in enumerate(ar.iter("{*}WhereClauseRef")):
            cites[("AR", ar.get("OID"), n)] = w.get("WhereClauseOID")
    return hdr, out, cites


def references(path):
    """{oid: set of oids it references} over one document's definitions."""
    root = etree.parse(path).getroot()
    mdv = root.find("{*}Study/{*}MetaDataVersion")
    refs = collections.defaultdict(set)
    attrs = ("ItemOID", "MethodOID", "CodeListOID", "ValueListOID", "WhereClauseOID",
             "CommentOID", "leafID")
    for el in mdv:
        if not isinstance(el.tag, str):
            continue
        oid = oid_of(el)
        if not oid:
            continue
        for sub in el.iter():
            if not isinstance(sub.tag, str):
                continue
            for k, v in sub.attrib.items():
                if local(k) in attrs and v != oid:
                    refs[oid].add(v)
            if local(sub.tag) == "leaf" and sub.get("ID") and sub.get("ID") != oid:
                refs[oid].add(sub.get("ID"))
    return refs


def reach(start, refs):
    seen, todo = set(), list(start)
    while todo:
        o = todo.pop()
        if o in seen:
            continue
        seen.add(o)
        todo.extend(refs.get(o, ()))
    return seen


def all_diffs(a, b, path=""):
    """Every difference between two canon tuples, as path strings."""
    if a is None or b is None:
        return [f"{path}: present on one side only"]
    if a[0] != b[0]:
        return [f"{path}: tag {a[0]} vs {b[0]}"]
    p = f"{path}/{a[0]}"
    out = []
    da, db = dict(a[1]), dict(b[1])
    for k in sorted(set(da) | set(db)):
        if da.get(k) != db.get(k):
            out.append(f"{p}@{k}: {da.get(k)!r} vs {db.get(k)!r}")
    if a[2] != b[2]:
        out.append(f"{p} text {a[2][:120]!r} vs {b[2][:120]!r}")
    ka, kb = list(a[3]), list(b[3])
    for i in range(max(len(ka), len(kb))):
        x = ka[i] if i < len(ka) else None
        y = kb[i] if i < len(kb) else None
        if x != y:
            out.extend(all_diffs(x, y, p))
    return out


def repeated_orders(path):
    """OIDs of the received codelists that repeat an item OrderNumber."""
    out = set()
    for cl in etree.parse(path).getroot().iter("{*}CodeList"):
        orders = [it.get("OrderNumber") for it in cl
                  if local(it.tag) in ("CodeListItem", "EnumeratedItem") and it.get("OrderNumber") is not None]
        if len(set(orders)) < len(orders):
            out.add(cl.get("OID"))
    return out


def classify(cls, oid, diff, repeated):
    """Defect id a single difference path belongs to, or None."""
    if (cls == "CodeList" and oid in repeated
            and re.search(r"/CodeList/(EnumeratedItem|CodeListItem)@OrderNumber: '\d+' vs None$", diff)):
        return "repeated-order"
    m = re.search(r"arm:AnalysisResult@Analysis(?:Reason|Purpose): ('.*') vs '.*'$", diff)
    if m and ast.literal_eval(m.group(1)) not in ARM_TERMS:
        return "arm-terms"
    if cls == "arm:ResultDisplay" and ("(empty)" in diff or re.search(
            r"arm:(Documentation|ProgrammingCode): present on one side only$", diff)):
        return "arm-terms"
    m = re.search(r"@MethodOID: ('.*') vs ('.*')$", diff)
    if m:
        a, b = ast.literal_eval(m.group(1)), ast.literal_eval(m.group(2))
        if a != b and a.rstrip("\xa0") == b:
            return "method-oid-nbsp"
    return None


def strip_oid(c):
    return (c[0], tuple(a for a in c[1] if a[0] != "OID"), c[2], c[3])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("submitted")
    ap.add_argument("generated")
    ap.add_argument("--detail", type=int, default=0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    hs, s, scites = collect(a.submitted)
    hg, g, gcites = collect(a.generated)

    gaps = collections.Counter()  # differences by submitted-define defect
    unexplained = []
    sref = references(a.submitted)
    repeated = repeated_orders(a.submitted)
    s_igs = {k[1] for k in s if k[0] == "ItemGroupDef"}
    g_igs = {k[1] for k in g if k[0] == "ItemGroupDef"}
    missing_igs = sorted(s_igs - g_igs)
    nospec = reach(missing_igs, sref) - reach(s_igs & g_igs, sref)
    nospec_count = collections.Counter()

    print("== headers")
    for k in hs:
        ok = hs[k] == hg.get(k)
        print(f"  {k:16s} {'MATCH' if ok else 'DIFF'}")
        if not ok:
            unexplained.append(f"header {k}")

    classes = sorted({k[0] for k in s} | {k[0] for k in g})
    print(f"== {'class':24s} {'sub':>5s} {'gen':>5s} {'match':>6s} {'diff':>5s} {'sub-only':>8s} {'gen-only':>8s}")
    total = collections.Counter()
    report = {}
    for c in classes:
        ks = [k for k in s if k[0] == c]
        kg = [k for k in g if k[0] == c]
        both = [k for k in ks if k in g]
        match = [k for k in both if s[k] == g[k]]
        diff = [k for k in both if s[k] != g[k]]
        so = [k for k in ks if k not in g]
        go = [k for k in kg if k not in s]
        print(f"   {c:24s} {len(ks):5d} {len(kg):5d} {len(match):6d} {len(diff):5d} {len(so):8d} {len(go):8d}")
        total.update(sub=len(ks), gen=len(kg), match=len(match), diff=len(diff), so=len(so), go=len(go))
        diffs_all = []
        gap_only = 0  # elements whose every difference is a submitted-define defect
        for k in diff:
            ds = all_diffs(s[k], g[k])
            diffs_all.append([k[1], ds])
            explained = True
            for d in ds:
                gid = classify(c, k[1], d, repeated)
                if gid:
                    gaps[gid] += 1
                else:
                    explained = False
                    unexplained.append(f"{c} {k[1]} {d}")
            gap_only += explained
        if c != "def:WhereClauseDef":
            gen_only = {x[1] for x in go}
            for k in so:
                if k[1] in nospec:
                    nospec_count[c] += 1
                elif c == "MethodDef" and k[1] != k[1].rstrip("\xa0") and k[1].rstrip("\xa0") in gen_only:
                    # The same method, written without the received trailing U+00A0.
                    gaps["method-oid-nbsp"] += 1
                    gap_only += 1
                    gen_only.discard(k[1].rstrip("\xa0"))
                    go = [x for x in go if x[1] != k[1].rstrip("\xa0")]
                else:
                    unexplained.append(f"{c} {k[1]} submitted only")
            unexplained.extend(f"{c} {k[1]} generated only" for k in go)
        total.update(gap_only=gap_only)
        report[c] = {
            "submitted": len(ks), "generated": len(kg), "match": len(match), "gap_only": gap_only,
            "diff_all": diffs_all,
            "submitted_only": [k[1] for k in so], "generated_only": [k[1] for k in go],
        }
        if a.detail:
            for k, ds in diffs_all[: a.detail]:
                print("      DIFF", k, "->", ds[:2])

    # Where clauses: pair them through what cites them and compare contents.
    wc_pairs = {}
    nospec_wcs = set()
    for key, soid in scites.items():
        goid = gcites.get(key)
        if goid is None:
            if soid in nospec:
                nospec_wcs.add(soid)
            else:
                unexplained.append(f"where clause cited by {key} not generated")
            continue
        wc_pairs.setdefault(soid, set()).add(goid)
    wc_same = 0
    for soid, goids in wc_pairs.items():
        sc = s[("def:WhereClauseDef", soid)]
        for goid in goids:
            gc = g[("def:WhereClauseDef", goid)]
            ds = all_diffs(strip_oid(sc), strip_oid(gc))
            if not ds:
                wc_same += 1
            unexplained.extend(f"WhereClauseDef {soid} {d}" for d in ds)
            if goid != soid:
                unexplained.append(f"WhereClauseDef {soid} written as {goid}")
    nospec_count["def:WhereClauseDef"] += len(nospec_wcs - set(wc_pairs))
    used_g = {o for v in wc_pairs.values() for o in v}
    for k in g:
        if k[0] == "def:WhereClauseDef" and k[1] not in used_g:
            unexplained.append(f"WhereClauseDef {k[1]} generated but cited by nothing received")

    print(f"   {'TOTAL':24s} {total['sub']:5d} {total['gen']:5d} {total['match']:6d} {total['diff']:5d} {total['so']:8d} {total['go']:8d}")
    print(f"== identical or differing only by submitted-define defects: {total['match'] + total['gap_only']} of "
          f"{total['sub']} ({sum(nospec_count.values())} more belong to datasets with no spec)")
    print(f"== where clauses: {len(wc_pairs)} received, {wc_same} pairs identical in content")
    print("== differences by submitted-define defect")
    for gid in sorted(gaps):
        print(f"   {gid:16s} {gaps[gid]:6d}  {DEFECTS[gid]}")
    if missing_igs:
        print(f"== received datasets with no spec yet: {', '.join(i[3:] for i in missing_igs)} "
              f"({sum(nospec_count.values())} elements)")
    print(f"== unexplained differences: {len(unexplained)}")
    for u in unexplained[: max(a.detail, 10)]:
        print("   ", u[:220])
    full = total["diff"] == total["so"] == total["go"] == 0 and not unexplained
    if full:
        verdict, code = "FULL MATCH", 0
    elif not unexplained:
        verdict, code = ("MATCH EXCEPT SUBMITTED-DEFINE DEFECTS" +
                         (" AND DATASETS WITHOUT A SPEC" if missing_igs else "")), 2
    else:
        verdict, code = "NOT A MATCH", 1
    print("VERDICT:", verdict)
    if a.json:
        json.dump({
            "verdict": verdict,
            "headers": {k: hs[k] == hg.get(k) for k in hs},
            "totals": dict(total),
            "classes": {c: {k: v for k, v in r.items() if k != "diff_all"} | {"diff": len(r["diff_all"])}
                        for c, r in report.items()},
            "where_clauses": {"received": len(wc_pairs), "identical_content": wc_same},
            "gaps": {gid: {"count": n, "title": DEFECTS[gid]} for gid, n in sorted(gaps.items())},
            "unexplained": unexplained,
            "datasets_without_spec": [i[3:] for i in missing_igs],
            "no_spec_elements": dict(nospec_count),
        }, open(a.json, "w"), indent=1)
    return code


if __name__ == "__main__":
    sys.exit(main())

"""
RAVE Step-6 metrics + DAG gates.

compute_marginals(crfs) → simulated stats vs. published CTGov targets.
run_dag_gates(crfs)     → causal-structure checks that must hold (fail-closed).

Published targets (ctgov NCT00104299 resultsSection):
  primary complete remission @6mo: RTX 63/99=63.6%, CYC 52/98=53.1%
  leukopenia (any, other-event): RTX 13/99=13.1%, CYC 39/98=39.8%
  >=1 serious AE: RTX 60/99=60.6%, CYC 47/98=48.0%
  non-completion: RTX 9/99=9.1%, CYC 10/98=10.2%
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

TARGETS = {
    "cr6mo_RTX": 0.636, "cr6mo_CYC": 0.531,
    "leuko_RTX": 0.131, "leuko_CYC": 0.398,
    "sae_RTX": 0.606, "sae_CYC": 0.480,
    "noncomplete_RTX": 0.091, "noncomplete_CYC": 0.102,
}
TOL = 0.07   # absolute tolerance on proportions


def _load(crfs: str | Path) -> dict:
    crfs = Path(crfs)
    out = {}
    for f in crfs.glob("RAVE_CRF_*.csv"):
        out[f.stem.replace("RAVE_CRF_", "")] = pd.read_csv(f)
    return out


def compute_marginals(crfs: str | Path) -> dict:
    d = _load(crfs)
    dm, re, ae = d["DM"], d["RE"], d["AE"]
    n = dm.groupby("ARMCD").size().to_dict()
    m = {"N_RTX": n.get("RTX", 0), "N_CYC": n.get("CYC", 0)}

    # primary: complete remission @ 6 mo
    cr = re.groupby("ARMCD")["CR6MO"].mean().to_dict()
    m["cr6mo_RTX"], m["cr6mo_CYC"] = cr.get("RTX", 0), cr.get("CYC", 0)

    # serious AE
    sae = re.groupby("ARMCD")["SERIOUS_AE"].mean().to_dict()
    m["sae_RTX"], m["sae_CYC"] = sae.get("RTX", 0), sae.get("CYC", 0)

    # leukopenia (any patient with >=1 leukopenia AE)
    leuko_ids = set(ae.loc[ae["AEDECOD"] == "LEUKOPENIA", "USUBJID"])
    dm_arm = dm.set_index("USUBJID")["ARMCD"]
    leuko_by_arm = dm_arm.index.to_series().map(lambda u: u in leuko_ids).groupby(dm_arm.values).mean()
    m["leuko_RTX"], m["leuko_CYC"] = float(leuko_by_arm.get("RTX", 0)), float(leuko_by_arm.get("CYC", 0))

    # non-completion
    nc = re.assign(nc=(re["DISPOSITION"] != "COMPLETED").astype(int)).groupby("ARMCD")["nc"].mean().to_dict()
    m["noncomplete_RTX"], m["noncomplete_CYC"] = nc.get("RTX", 0), nc.get("CYC", 0)

    # secondary descriptive: flare rate by ANCA type
    fl = re.groupby("ANCATYPE")["FLARE_EVENT"].mean().to_dict()
    m["flare_PR3"], m["flare_MPO"] = fl.get("PR3", 0), fl.get("MPO", 0)
    return m


def compare_table(m: dict) -> list:
    rows = []
    for k, tgt in TARGETS.items():
        sim = m.get(k, float("nan"))
        rows.append((k, tgt, round(sim, 3), round(sim - tgt, 3), abs(sim - tgt) <= TOL))
    return rows


def run_dag_gates(crfs: str | Path) -> dict:
    d = _load(crfs)
    ae, lb, re, dm = d["AE"], d["LB_HEM"], d["RE"], d["DM"]
    gates = {}

    # Gate 1: AE↔lab linkage — mean WBC at Leukopenia AE rows ≪ overall
    leuko = ae[ae["AEDECOD"] == "LEUKOPENIA"][["USUBJID", "VISIT"]]
    merged = leuko.merge(lb[["USUBJID", "VISIT", "WBC"]], on=["USUBJID", "VISIT"], how="inner")
    wbc_at_leuko = merged["WBC"].mean() if len(merged) else float("nan")
    wbc_overall = lb["WBC"].mean()
    gates["g1_ae_lab_linkage"] = {
        "wbc_at_leukopenia": round(float(wbc_at_leuko), 2), "wbc_overall": round(float(wbc_overall), 2),
        "pass": bool(wbc_at_leuko < 4.0 and wbc_at_leuko < wbc_overall - 1.0),
    }

    # Gate 2: arm→myelosuppression mediation (CYC leukopenia > RTX)
    leuko_ids = set(ae.loc[ae["AEDECOD"] == "LEUKOPENIA", "USUBJID"])
    arm = dm.set_index("USUBJID")["ARMCD"]
    rate = arm.index.to_series().map(lambda u: u in leuko_ids).groupby(arm.values).mean()
    gates["g2_arm_myelosuppression"] = {
        "leuko_CYC": round(float(rate.get("CYC", 0)), 3), "leuko_RTX": round(float(rate.get("RTX", 0)), 3),
        "pass": bool(rate.get("CYC", 0) > rate.get("RTX", 0)),
    }

    # Gate 3: within-patient GI AE correlation > 0 (shared f_GI)
    gi = ae[ae["AEDECOD"].isin(["NAUSEA", "VOMITING", "DIARRHOEA"])]
    cnt = gi.groupby(["USUBJID", "AEDECOD"]).size().unstack(fill_value=0)
    if {"NAUSEA", "VOMITING"}.issubset(cnt.columns) and len(cnt) > 5:
        r = np.corrcoef(cnt["NAUSEA"], cnt["VOMITING"])[0, 1]
    else:
        r = float("nan")
    gates["g3_gi_within_patient_corr"] = {"r_nausea_vomiting": round(float(r), 3),
                                          "pass": bool(r > 0.0)}

    # Gate 4: primary endpoint = trajectory (recompute cr6mo from DA + GC at V8)
    da, gc = d["DA"], d["GC"]
    v8 = da[da["VISIT"] == "V8"].set_index("USUBJID")
    gc8 = gc[gc["VISIT"] == "V8"].set_index("USUBJID")["PREDDOSE"]
    recomputed = {}
    for u in re["USUBJID"]:
        b = v8["BVASWG"].get(u, None)
        p = gc8.get(u, None)
        recomputed[u] = int((b == 0.0) and (p == 0.0)) if (b is not None and p is not None) else 0
    re2 = re.set_index("USUBJID")
    agree = np.mean([recomputed[u] == re2.loc[u, "CR6MO"] for u in re2.index])
    gates["g4_endpoint_is_trajectory"] = {"agreement": round(float(agree), 3),
                                          "pass": bool(agree > 0.98)}

    # Gate 5: stratifier→outcome direction (PR3 flare > MPO flare)
    fl = re.groupby("ANCATYPE")["FLARE_EVENT"].mean()
    gates["g5_pr3_higher_flare"] = {"flare_PR3": round(float(fl.get("PR3", 0)), 3),
                                    "flare_MPO": round(float(fl.get("MPO", 0)), 3),
                                    "pass": bool(fl.get("PR3", 0) >= fl.get("MPO", 0))}

    # Gate 6 (issue #184): AE↔DS cross-layer traceability — every patient discontinued
    # for an adverse event (DS.DSTERM) must have exactly one AE flagged AEACN="DRUG WITHDRAWN"
    # naming the cause, and vice-versa. Keyed on DSTERM (not DSDECOD) so a DEATH-disposition
    # patient whose reason stayed "ADVERSE EVENT" is still required to carry the link.
    ds = d["DS"]
    D = set(ds.loc[ds["DSTERM"].astype(str).str.upper() == "ADVERSE EVENT", "USUBJID"])
    wd = ae.loc[ae["AEACN"].astype(str).str.upper() == "DRUG WITHDRAWN"]
    W = set(wd["USUBJID"])
    wc = wd.groupby("USUBJID").size()
    gates["g6_ae_ds_traceability"] = {
        "n_ds_ae": len(D), "n_ae_withdrawn": len(W),
        "missing_withdrawn": sorted(D - W),
        "multi_withdrawn": sorted(u for u in D if wc.get(u, 0) > 1),
        "pass": bool(D == W and all(wc.get(u, 0) == 1 for u in D)),
    }

    gates["all_pass"] = all(g["pass"] for k, g in gates.items() if isinstance(g, dict))
    return gates


if __name__ == "__main__":
    import sys, json
    crfs = sys.argv[1] if len(sys.argv) > 1 else "RAVE_output/crfs"
    m = compute_marginals(crfs)
    print(f"N: RTX={m['N_RTX']} CYC={m['N_CYC']}\n")
    print(f"{'metric':22} {'target':>8} {'sim':>8} {'diff':>8}  within_tol")
    for k, tgt, sim, diff, ok in compare_table(m):
        print(f"{k:22} {tgt:8.3f} {sim:8.3f} {diff:+8.3f}  {'OK' if ok else 'X'}")
    print(f"\nflare PR3={m['flare_PR3']:.3f} vs MPO={m['flare_MPO']:.3f}")
    print("\nDAG GATES:")
    print(json.dumps(run_dag_gates(crfs), indent=2))

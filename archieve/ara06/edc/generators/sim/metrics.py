"""
ARA06 Step-6 metrics + DAG gates.

compute_marginals(crfs) -> simulated stats vs published ctgov NCT00837434 targets.
run_dag_gates(crfs)     -> causal-structure checks that must hold (fail-closed).

Denominators mirror ctgov: response/primary endpoints are computed among patients
who reached the relevant visit (V5=wk12, V8=wk24), matching the published
per-timepoint analysis populations.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

# Published targets (ctgov NCT00837434 resultsSection)
TARGETS = {
    "mem_wk12_ETN_mean": 13.2, "mem_wk12_ADA_mean": 13.8,
    "das28resp_wk12_ETN": 0.865, "das28resp_wk12_ADA": 0.895,
    "das28resp_wk24_ETN": 0.882, "das28resp_wk24_ADA": 0.842,
    "acr20_wk12_ETN": 0.676, "acr20_wk12_ADA": 0.737,
    "acr20_wk24_ETN": 0.735, "acr20_wk24_ADA": 0.842,
    "acr50_wk12_ETN": 0.297, "acr50_wk12_ADA": 0.474,
    "acr50_wk24_ETN": 0.382, "acr50_wk24_ADA": 0.632,
    "anyae_ETN": 0.795, "anyae_ADA": 0.895,
    "sae_ETN": 0.051, "sae_ADA": 0.053,
    "anaemia_ETN": 0.231, "anaemia_ADA": 0.158,
    "ast_ETN": 0.256, "ast_ADA": 0.158,
    "noncomplete_ETN": 0.209, "noncomplete_ADA": 0.050,
}
TOL = 0.12          # absolute tolerance on proportions (arms n=19-39 → wide CIs)
TOL_MEAN = 2.0      # absolute tolerance on memory-B mean (%)


def _load(crfs):
    crfs = Path(crfs)
    return {f.stem.replace("ARA06_CRF_", ""): pd.read_csv(f) for f in crfs.glob("ARA06_CRF_*.csv")}


def _reached(da: pd.DataFrame, visit: str) -> set:
    return set(da.loc[da["VISIT"] == visit, "USUBJID"])


def compute_marginals(crfs) -> dict:
    d = _load(crfs)
    dm, re, ae, da, bc = d["DM"], d["RE"], d["AE"], d["DA"], d["BC"]
    arm = dm.set_index("USUBJID")["ARMCD"]
    m = {"N_ETN": int((arm == "ETN").sum()), "N_ADA": int((arm == "ADA").sum())}

    re = re.set_index("USUBJID")
    ids = {a: set(arm[arm == a].index) for a in ("ETN", "ADA")}
    wk12_reached = _reached(da, "V5"); wk24_reached = _reached(da, "V8")
    bc12 = set(bc.loc[bc["VISIT"] == "V5", "USUBJID"])

    # primary: switched-memory-B mean at wk12 (among those with the V5 B-cell draw)
    bcv5 = bc[bc["VISIT"] == "V5"].set_index("USUBJID")["MEMSWPCT"]
    for a in ("ETN", "ADA"):
        sub = [bcv5[u] for u in ids[a] & bc12]
        m[f"mem_wk12_{a}_mean"] = float(np.mean(sub)) if sub else float("nan")
        m[f"mem_wk12_{a}_sd"] = float(np.std(sub, ddof=1)) if len(sub) > 1 else float("nan")

    def _rate(flag, reached, a):
        sub = [re.loc[u, flag] for u in ids[a] & reached if u in re.index]
        return float(np.mean(sub)) if sub else float("nan")

    for a in ("ETN", "ADA"):
        m[f"das28resp_wk12_{a}"] = _rate("DAS28RESP_WK12", wk12_reached, a)
        m[f"das28resp_wk24_{a}"] = _rate("DAS28RESP_WK24", wk24_reached, a)
        m[f"acr20_wk12_{a}"] = _rate("ACR20_WK12", wk12_reached, a)
        m[f"acr20_wk24_{a}"] = _rate("ACR20_WK24", wk24_reached, a)
        m[f"acr50_wk12_{a}"] = _rate("ACR50_WK12", wk12_reached, a)
        m[f"acr50_wk24_{a}"] = _rate("ACR50_WK24", wk24_reached, a)

    # safety: any-AE, serious-AE, anaemia, AST-increased, non-completion (full mITT)
    any_ids = set(ae["USUBJID"])
    anaemia_ids = set(ae.loc[ae["AEDECOD"] == "ANAEMIA", "USUBJID"])
    ast_ids = set(ae.loc[ae["AEDECOD"] == "ASPARTATE AMINOTRANSFERASE INCREASED", "USUBJID"])
    for a in ("ETN", "ADA"):
        g = ids[a]
        m[f"anyae_{a}"] = np.mean([u in any_ids for u in g]) if g else float("nan")
        m[f"sae_{a}"] = float(re.loc[list(g), "SERIOUS_AE"].mean())
        m[f"anaemia_{a}"] = np.mean([u in anaemia_ids for u in g]) if g else float("nan")
        m[f"ast_{a}"] = np.mean([u in ast_ids for u in g]) if g else float("nan")
        m[f"noncomplete_{a}"] = float((re.loc[list(g), "DISPOSITION"] != "COMPLETED").mean())
    return m


def compare_table(m: dict) -> list:
    rows = []
    for k, tgt in TARGETS.items():
        sim = m.get(k, float("nan"))
        tol = TOL_MEAN if k.endswith("_mean") else TOL
        rows.append((k, tgt, round(sim, 3), round(sim - tgt, 3), abs(sim - tgt) <= tol))
    return rows


def run_dag_gates(crfs) -> dict:
    d = _load(crfs)
    ae, chem, re, dm, da, bc, ds = d["AE"], d["LB_CHEM"], d["RE"], d["DM"], d["DA"], d["BC"], d["DS"]
    arm = dm.set_index("USUBJID")["ARMCD"]
    gates = {}

    # Gate 1: AE<->lab linkage — mean AST at "AST increased" AE rows > ULN & > overall
    ast_ae = ae[ae["AEDECOD"] == "ASPARTATE AMINOTRANSFERASE INCREASED"][["USUBJID", "VISIT"]]
    merged = ast_ae.merge(chem[["USUBJID", "VISIT", "AST"]], on=["USUBJID", "VISIT"], how="inner")
    ast_at = merged["AST"].mean() if len(merged) else float("nan")
    ast_overall = chem["AST"].mean()
    gates["g1_ae_lab_linkage"] = {
        "ast_at_ae": round(float(ast_at), 1), "ast_overall": round(float(ast_overall), 1),
        "pass": bool(ast_at > 40.0 and ast_at > ast_overall + 5.0)}

    # Gate 2: arm->hepatotoxicity mediation (ETN AST-increased rate > ADA; ctgov 25.6% vs 15.8%)
    ast_ids = set(ae.loc[ae["AEDECOD"] == "ASPARTATE AMINOTRANSFERASE INCREASED", "USUBJID"])
    rate = arm.index.to_series().map(lambda u: u in ast_ids).groupby(arm.values).mean()
    gates["g2_arm_hepatic"] = {
        "ast_ETN": round(float(rate.get("ETN", 0)), 3), "ast_ADA": round(float(rate.get("ADA", 0)), 3),
        "pass": bool(rate.get("ETN", 0) >= rate.get("ADA", 0))}

    # Gate 3: within-patient hepatic-cluster AE correlation > 0 (shared f_hepatic) —
    # AST-increased and ALT-increased co-occur within patient (correlated labs + frailty)
    hep = ae[ae["AEDECOD"].isin(["ASPARTATE AMINOTRANSFERASE INCREASED",
                                 "ALANINE AMINOTRANSFERASE INCREASED"])]
    # count over ALL patients (fill 0 for those with no hepatic AE) so the shared-frailty
    # signal is measured, not the threshold trade-off within the AE-positive subset
    cnt = hep.groupby(["USUBJID", "AEDECOD"]).size().unstack(fill_value=0).reindex(arm.index, fill_value=0)
    cols = [c for c in ["ASPARTATE AMINOTRANSFERASE INCREASED", "ALANINE AMINOTRANSFERASE INCREASED"]
            if c in cnt.columns]
    r = np.corrcoef(cnt[cols[0]], cnt[cols[1]])[0, 1] if (len(cols) == 2 and len(cnt) > 5) else float("nan")
    gates["g3_hepatic_within_patient_corr"] = {"pair": cols, "r": round(float(r), 3),
                                               "pass": bool((not np.isnan(r)) and r > 0.0)}

    # Gate 4: primary + clinical endpoints == trajectory (recompute from DA/BC, agree)
    bcv5 = bc[bc["VISIT"] == "V5"].set_index("USUBJID")["MEMSWPCT"]
    re_i = re.set_index("USUBJID")
    mem_agree = []
    for u in re_i.index:
        if u in bcv5.index and re_i.loc[u, "MEMSW_WK12"] != "":
            mem_agree.append(abs(float(bcv5[u]) - float(re_i.loc[u, "MEMSW_WK12"])) < 1e-6)
    # recompute ACR20 wk12 from DA baseline (V2) vs V5
    v2 = da[da["VISIT"] == "V2"].set_index("USUBJID")
    v5 = da[da["VISIT"] == "V5"].set_index("USUBJID")
    comps = ["PTGLOBAL", "PHYSGLOBAL", "PAINVAS", "HAQDI", "CRP"]
    acr_agree = []
    for u in v5.index:
        if u not in v2.index or u not in re_i.index:
            continue
        b, c = v2.loc[u], v5.loc[u]
        def imp(bb, cc):
            return (bb - cc) / bb if bb > 0 else 0.0
        tjc_ok = imp(b["TJC28"], c["TJC28"]) >= 0.20
        sjc_ok = imp(b["SJC28"], c["SJC28"]) >= 0.20
        nfive = sum(1 for k in comps if imp(b[k], c[k]) >= 0.20)
        recomputed = int(tjc_ok and sjc_ok and nfive >= 3)
        acr_agree.append(recomputed == int(re_i.loc[u, "ACR20_WK12"]))
    mem_a = float(np.mean(mem_agree)) if mem_agree else 1.0
    acr_a = float(np.mean(acr_agree)) if acr_agree else 1.0
    gates["g4_endpoint_is_trajectory"] = {"mem_agreement": round(mem_a, 3),
                                          "acr20_agreement": round(acr_a, 3),
                                          "pass": bool(mem_a > 0.999 and acr_a > 0.999)}

    # Gate 5: arm->deep-response direction (ADA ACR50 wk12 >= ETN; ctgov 47.4% vs 29.7%)
    wk12 = set(da.loc[da["VISIT"] == "V5", "USUBJID"])
    ids = {a: set(arm[arm == a].index) for a in ("ETN", "ADA")}
    def acr50_rate(a):
        sub = [int(re_i.loc[u, "ACR50_WK12"]) for u in ids[a] & wk12 if u in re_i.index]
        return float(np.mean(sub)) if sub else 0.0
    a_ada, a_etn = acr50_rate("ADA"), acr50_rate("ETN")
    gates["g5_ada_deeper_acr50"] = {"acr50_ADA": round(a_ada, 3), "acr50_ETN": round(a_etn, 3),
                                    "pass": bool(a_ada >= a_etn)}

    # Gate 6: AE<->DS traceability (every AE-driven discontinuation named by a
    # DRUG WITHDRAWN AE, and vice-versa). ARA06 has none → both sets empty → pass.
    D = set(ds.loc[ds["DSTERM"].astype(str).str.upper() == "ADVERSE EVENT", "USUBJID"])
    wd = ae.loc[ae["AEACN"].astype(str).str.upper() == "DRUG WITHDRAWN"]
    W = set(wd["USUBJID"]); wc = wd.groupby("USUBJID").size()
    gates["g6_ae_ds_traceability"] = {"n_ds_ae": len(D), "n_ae_withdrawn": len(W),
                                      "missing": sorted(D - W),
                                      "pass": bool(D == W and all(wc.get(u, 0) == 1 for u in D))}

    gates["all_pass"] = all(g["pass"] for k, g in gates.items() if isinstance(g, dict))
    return gates


if __name__ == "__main__":
    import sys, json
    crfs = sys.argv[1] if len(sys.argv) > 1 else "ARA06_output/crfs"
    m = compute_marginals(crfs)
    print(f"N: ETN={m['N_ETN']} ADA={m['N_ADA']}\n")
    print(f"{'metric':24} {'target':>8} {'sim':>8} {'diff':>8}  ok")
    for k, tgt, sim, diff, ok in compare_table(m):
        print(f"{k:24} {tgt:8.3f} {sim:8.3f} {diff:+8.3f}  {'OK' if ok else 'X'}")
    print(f"\nmem wk12 SD: ETN={m.get('mem_wk12_ETN_sd'):.2f} ADA={m.get('mem_wk12_ADA_sd'):.2f}")
    print("\nDAG GATES:")
    print(json.dumps(run_dag_gates(crfs), indent=2))

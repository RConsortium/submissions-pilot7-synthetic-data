"""
CATH Step-6 metrics + DAG gates.

compute_marginals(crfs) → simulated stats vs. published CTGov targets (targets.json).
run_dag_gates(crfs)     → causal-structure checks that must hold (fail-closed).

Published targets: resultsSection of NCT00789880 (baseline per cell, change baseline→Day21
per peptide/compartment/arm, participant flow, AEs). See CATH_output/intake/targets.json.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import numpy as np

_TARGETS = json.loads((Path(__file__).resolve().parent.parent
                       / "CATH_output" / "intake" / "targets.json").read_text())

GLBL = {"NONAD": "NonAD", "AD": "AD", "PSO": "Pso"}
ALBL = {"VITD": "VitD", "PLAC": "Plac"}
SKINCOL = {"LES": "Lesional", "NL": "NonLesional"}


def _load(crfs) -> dict:
    crfs = Path(crfs)
    out = {}
    for f in crfs.glob("CATH_CRF_*.csv"):
        out[f.stem.replace("CATH_CRF_", "")] = pd.read_csv(f)
    return out


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def compute_marginals(crfs) -> dict:
    d = _load(crfs)
    dm, lb, re, ds = d["DM"], d["LB"], d["RE"], d["DS"]
    m = {"N": len(dm)}

    # ---- pooled baseline ----
    m["age_mean"] = round(float(dm["AGE"].mean()), 2)
    m["bmi_mean"] = round(float(dm["BMI"].mean()), 2)
    m["female_frac"] = round(float((dm["SEX"] == "F").mean()), 3)
    scrn = lb[lb["VISIT"] == "SCRN"]
    m["vitd_base_mean"] = round(float(_num(scrn["VITD25OH"]).mean()), 2)
    m["calcium_base_mean"] = round(float(_num(scrn["CALCIUM"]).mean()), 2)

    # ---- participant flow ----
    m["n_completed"] = int((ds["DSDECOD"] == "COMPLETED").sum())
    m["n_dropped"] = int((ds["DSDECOD"] != "COMPLETED").sum())
    m["dropout_reasons"] = ds.loc[ds["DSDECOD"] != "COMPLETED", "DSTERM"].value_counts().to_dict()

    # ---- adverse events ----
    ae = d.get("AE", pd.DataFrame(columns=["AESER"]))
    m["n_serious_ae"] = int((ae.get("AESER", pd.Series(dtype=str)) == "Y").sum())
    m["n_ae_rows"] = int(len(ae.dropna(how="all")))

    # ---- outcome change means per peptide/group/skin/arm (completers) ----
    m["outcomes"] = compare_outcomes(re)
    return m


def compare_outcomes(re: pd.DataFrame) -> list:
    """Per-cell change mean vs target with sampling-aware tolerance (2 SE)."""
    comp = re[re["COMPLETER"] == "Y"].copy()
    out = []
    colmap = {"CAMP": {"LES": "dCAMP_LES", "NL": "dCAMP_NL"},
              "HBD3": {"LES": "dHBD3_LES", "NL": "dHBD3_NL"},
              "IL13": {"LES": "dIL13_LES", "NL": "dIL13_NL"}}
    for pep, skincols in colmap.items():
        for g in ("NONAD", "AD", "PSO"):
            skins = ("NL",) if g == "NONAD" else ("LES", "NL")
            for sk in skins:
                for arm in ("VITD", "PLAC"):
                    key = f"{GLBL[g]}|{SKINCOL[sk]}|{ALBL[arm]}"
                    tgt = _TARGETS["outcomes"][pep].get(key)
                    if tgt is None:
                        continue
                    col = skincols[sk]
                    vals = _num(comp.loc[(comp["DXGROUP"] == g) & (comp["ARMCD"] == arm), col]).dropna()
                    if len(vals) == 0:
                        continue
                    sim_m, sim_sd, n = float(vals.mean()), float(vals.std(ddof=1)), len(vals)
                    se = (tgt[1] / np.sqrt(n)) if n > 0 else np.inf
                    tol = max(0.6, 2.0 * se)         # within 2 SE (sampling) or 0.6 abs
                    out.append({
                        "cell": f"{pep} {key}", "n": n,
                        "target_mean": tgt[0], "sim_mean": round(sim_m, 2),
                        "target_sd": tgt[1], "sim_sd": round(sim_sd, 2),
                        "abs_diff": round(abs(sim_m - tgt[0]), 2), "tol": round(tol, 2),
                        "within": bool(abs(sim_m - tgt[0]) <= tol),
                    })
    return out


def run_dag_gates(crfs) -> dict:
    d = _load(crfs)
    dm, lb, re, ds, sb = d["DM"], d["LB"], d["RE"], d["DS"], d["SB"]
    ae = d.get("AE", pd.DataFrame(columns=["USUBJID", "AEACN", "AESER"]))
    gates = {}

    # g1: endpoint = trajectory. RE.dCAMP_* reproducible from SB(D21)-SB(BASE).
    sbn = sb.copy()
    for c in ("CAMP", "HBD3", "IL13"):
        sbn[c] = _num(sbn[c])
    piv = sbn.pivot_table(index=["USUBJID", "COMPART"], columns="VISIT",
                          values="CAMP", aggfunc="first")
    agree, total = 0, 0
    rei = re.set_index("USUBJID")
    for (u, comp), row in piv.iterrows():
        if "BASE" in row and "D21" in row and pd.notna(row.get("D21")) and pd.notna(row.get("BASE")):
            recomputed = round(float(row["D21"] - row["BASE"]), 2)
            col = "dCAMP_LES" if comp == "LESIONAL" else "dCAMP_NL"
            if u in rei.index:
                emitted = _num(pd.Series([rei.loc[u, col]])).iloc[0]
                if pd.notna(emitted):
                    total += 1
                    agree += int(abs(recomputed - float(emitted)) < 0.011)
    gates["g1_endpoint_is_trajectory"] = {"agreement": round(agree / total, 3) if total else 0.0,
                                          "n": total, "pass": bool(total > 0 and agree == total)}

    # g2 / g5: arm→25OHD mediator. VitD Δ25OHD ≫ placebo and clean separation across threshold.
    re2 = re.copy()
    re2["dVITD25OH"] = _num(re2["dVITD25OH"])
    mv = re2.loc[re2["ARMCD"] == "VITD", "dVITD25OH"].dropna()
    mp = re2.loc[re2["ARMCD"] == "PLAC", "dVITD25OH"].dropna()
    gates["g2_arm_mediator"] = {"d25_VITD": round(float(mv.mean()), 2),
                                "d25_PLAC": round(float(mp.mean()), 2),
                                "pass": bool(mv.mean() > mp.mean() + 4.0)}
    gates["g5_mediation_separation"] = {"vitd_mean": round(float(mv.mean()), 2),
                                        "plac_mean": round(float(mp.mean()), 2),
                                        "pass": bool(mv.mean() > 4.0 and mp.mean() < 4.0)}

    # g3: within-patient AMP cluster correlation (ΔCAMP vs ΔHBD3) > 0 via f_amp.
    pairs = []
    for les, hl in (("dCAMP_LES", "dHBD3_LES"), ("dCAMP_NL", "dHBD3_NL")):
        sub = re[[les, hl]].apply(_num).dropna()
        pairs.append(sub.rename(columns={les: "c", hl: "h"}))
    allp = pd.concat(pairs, ignore_index=True) if pairs else pd.DataFrame()
    r = float(np.corrcoef(allp["c"], allp["h"])[0, 1]) if len(allp) > 5 else float("nan")
    gates["g3_amp_within_patient_corr"] = {"r_camp_hbd3": round(r, 3), "n": len(allp),
                                           "pass": bool(r > 0.0)}

    # g4: L0 group→IgE direction. baseline IgE (SCRN) AD ≫ NonAD & PSO.
    scrn = lb[lb["VISIT"] == "SCRN"].merge(dm[["USUBJID", "DXGROUP"]], on="USUBJID")
    ige = scrn.groupby("DXGROUP")["IGE"].apply(lambda s: float(_num(s).mean())).to_dict()
    gates["g4_group_ige_direction"] = {k: round(v, 1) for k, v in ige.items()}
    gates["g4_group_ige_direction"]["pass"] = bool(
        ige.get("AD", 0) > ige.get("NONAD", 0) and ige.get("AD", 0) > ige.get("PSO", 0))

    # g6: AE↔DS traceability. each DSTERM=='ADVERSE EVENT' patient has exactly one DRUG WITHDRAWN AE.
    D = set(ds.loc[ds["DSTERM"].astype(str).str.upper() == "ADVERSE EVENT", "USUBJID"])
    wd = ae.loc[ae.get("AEACN", pd.Series(dtype=str)).astype(str).str.upper() == "DRUG WITHDRAWN"]
    W = set(wd["USUBJID"])
    wc = wd.groupby("USUBJID").size() if len(wd) else pd.Series(dtype=int)
    gates["g6_ae_ds_traceability"] = {"n_ds_ae": len(D), "n_ae_withdrawn": len(W),
                                      "missing": sorted(D - W),
                                      "pass": bool(D == W and all(wc.get(u, 0) == 1 for u in D))}

    # g7: safety realism — no hypercalcemia (Ca<11) and 0 serious AEs (matches CTGov).
    maxca = float(_num(lb["CALCIUM"]).max())
    nser = int((ae.get("AESER", pd.Series(dtype=str)) == "Y").sum())
    gates["g7_safety_no_hypercalcemia"] = {"max_calcium": round(maxca, 2), "n_serious_ae": nser,
                                           "pass": bool(maxca < 11.0 and nser == 0)}

    gates["all_pass"] = all(g["pass"] for g in gates.values() if isinstance(g, dict))
    return gates


if __name__ == "__main__":
    import sys
    crfs = sys.argv[1] if len(sys.argv) > 1 else "CATH_output/crfs"
    m = compute_marginals(crfs)
    print(f"N={m['N']}  completed={m['n_completed']} dropped={m['n_dropped']} {m['dropout_reasons']}")
    print(f"baseline: age={m['age_mean']} (tgt 32.5)  bmi={m['bmi_mean']} (25.3)  "
          f"vitd25={m['vitd_base_mean']} (29.2)  female={m['female_frac']} (0.537)  "
          f"Ca={m['calcium_base_mean']} (9.4)")
    print(f"serious AEs={m['n_serious_ae']} (tgt 0)   AE rows={m['n_ae_rows']}")
    n_ok = sum(r["within"] for r in m["outcomes"])
    print(f"\noutcome cells within tolerance: {n_ok}/{len(m['outcomes'])}")
    print(f"{'cell':30} {'n':>3} {'tgt':>6} {'sim':>6} {'diff':>6} {'tol':>5} ok")
    for r in m["outcomes"]:
        print(f"{r['cell']:30} {r['n']:>3} {r['target_mean']:6.2f} {r['sim_mean']:6.2f} "
              f"{r['abs_diff']:6.2f} {r['tol']:5.2f} {'OK' if r['within'] else 'X'}")
    print("\nDAG GATES:")
    print(json.dumps(run_dag_gates(crfs), indent=2))

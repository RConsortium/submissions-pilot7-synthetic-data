"""
Project a simulated CathPatient trajectory into CRF row dicts (one list per form).
Pure projection — no fresh sampling. Forms mirror CATH_output/CRF_spec.md.
"""
from __future__ import annotations
from typing import Dict, List, Any

from .dag_state import CathPatient


def _d(p: CathPatient, day: int) -> str:
    return p.visit_date(day).strftime("%Y-%m-%d")


def _armcd(p): return "VITD" if p.is_vitd else "PLAC"


def emit_DM(p: CathPatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "SITEID": p.site, "ARMCD": _armcd(p), "ARM": p.arm,
        "DXGROUP": p.dxgroup, "AGE": p.age, "SEX": p.sex, "RACE": p.race, "ETHNIC": p.ethnic,
        "COUNTRY": p.country, "HEIGHT": p.height_cm, "WEIGHT": p.weight_kg, "BMI": p.bmi,
        "FITZPATRICK": p.fitzpatrick, "RFSTDTC": _d(p, 0),
    }]


def emit_IE(p: CathPatient) -> List[Dict[str, Any]]:
    return [{"USUBJID": p.patient_id, "IETESTCD": t, "IECAT": c, "IEORRES": "Y"} for t, c in
            [("AGE1870", "INCL"), ("DXCONFIRM", "INCL"), ("LABNORMAL", "INCL"), ("NOVITDSUPP", "EXCL")]]


def emit_MH(p: CathPatient) -> List[Dict[str, Any]]:
    dx = {"NONAD": "Healthy control (non-atopic)", "AD": "Atopic dermatitis",
          "PSO": "Plaque psoriasis"}[p.dxgroup]
    return [{"USUBJID": p.patient_id, "MHTERM": dx, "MHDECOD": dx.upper(),
             "MHCAT": "PRIMARY DIAGNOSIS", "ATOPY": "Y" if p.dxgroup == "AD" else "N"}]


def emit_DD(p: CathPatient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        if r.visit_key in ("BASE", "D21"):
            rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "DXGROUP": p.dxgroup,
                         "PASI": r.pasi if r.pasi is not None else "", "PASIDTC": _d(p, r.visit_day)})
    return rows


def emit_VS(p: CathPatient) -> List[Dict[str, Any]]:
    return [{"USUBJID": p.patient_id, "VISIT": r.visit_key, "VSDTC": _d(p, r.visit_day),
             "SYSBP": r.sysbp, "DIABP": r.diabp, "PULSE": r.pulse, "TEMP": r.temp,
             "WEIGHT": p.weight_kg}
            for r in p.trajectory if r.visit_key in ("BASE", "D21") and r.sysbp is not None]


def emit_SB(p: CathPatient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        if r.visit_key in ("BASE", "D21"):
            for comp, b in r.biopsy.items():
                rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key,
                             "SBDTC": _d(p, r.visit_day), "COMPART": comp,
                             "CAMP": b.camp, "HBD3": b.hbd3, "IL13": b.il13, "IL4": b.il4})
    return rows


def emit_SA(p: CathPatient) -> List[Dict[str, Any]]:
    return [{"USUBJID": p.patient_id, "VISIT": r.visit_key, "CAMP_SALIVA": r.saliva_camp}
            for r in p.trajectory if r.visit_key in ("BASE", "D21") and r.saliva_camp is not None]


def emit_TS(p: CathPatient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        if r.visit_key in ("BASE", "D21"):
            for comp, v in r.tape_camp.items():
                rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key,
                             "COMPART": comp, "CAMP_TAPE": v})
    return rows


def emit_LB(p: CathPatient) -> List[Dict[str, Any]]:
    return [{"USUBJID": p.patient_id, "VISIT": r.visit_key, "LBDTC": _d(p, r.visit_day),
             "VITD25OH": r.vitd_25oh, "CALCIUM": r.calcium, "PTH": r.pth, "CREAT": r.creat,
             "IGE": r.ige, "RAST": r.rast}
            for r in p.trajectory if r.visit_key in ("SCRN", "D21") and r.vitd_25oh is not None]


def emit_MB(p: CathPatient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        if r.visit_key in ("BASE", "D21"):
            for comp, v in r.cfu.items():
                rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key,
                             "COMPART": comp, "CFU_LOG10": v})
    return rows


def emit_EX(p: CathPatient) -> List[Dict[str, Any]]:
    return [{"USUBJID": p.patient_id, "EXTRT": "VITAMIN D3" if p.is_vitd else "PLACEBO",
             "EXDOSE": 4000, "EXDOSU": "IU", "EXROUTE": "ORAL", "EXSTDTC": _d(p, 0),
             "EXENDTC": _d(p, p.last_contact_day),
             "COMPLIANCE_PCT": 100 if p.completer else round(min(100, max(20, p.last_contact_day / 21 * 100)))}]


def emit_AE(p: CathPatient) -> List[Dict[str, Any]]:
    return [a for r in p.trajectory for a in r.aes]


def emit_PG(p: CathPatient) -> List[Dict[str, Any]]:
    if p.sex != "F":
        return []
    return [{"USUBJID": p.patient_id, "VISIT": r.visit_key, "PGRES": "NEGATIVE"}
            for r in p.trajectory if r.visit_key in ("SCRN", "BASE", "D21")]


def emit_DS(p: CathPatient) -> List[Dict[str, Any]]:
    return [{"USUBJID": p.patient_id, "DXGROUP": p.dxgroup, "ARMCD": _armcd(p),
             "DSDECOD": p.disposition,
             "DSTERM": p.discontinuation_reason or "COMPLETED STUDY",
             "DSSTDY": p.last_contact_day}]


def emit_RE(p: CathPatient) -> List[Dict[str, Any]]:
    c = p.change
    return [{
        "USUBJID": p.patient_id, "DXGROUP": p.dxgroup, "ARMCD": _armcd(p),
        "COMPLETER": "Y" if p.completer else "N", "DISPOSITION": p.disposition,
        "dCAMP_LES": c.get("dCAMP_LES", "") if c.get("dCAMP_LES") is not None else "",
        "dCAMP_NL": c.get("dCAMP_NL", "") if c.get("dCAMP_NL") is not None else "",
        "dHBD3_LES": c.get("dHBD3_LES", "") if c.get("dHBD3_LES") is not None else "",
        "dHBD3_NL": c.get("dHBD3_NL", "") if c.get("dHBD3_NL") is not None else "",
        "dIL13_LES": c.get("dIL13_LES", "") if c.get("dIL13_LES") is not None else "",
        "dIL13_NL": c.get("dIL13_NL", "") if c.get("dIL13_NL") is not None else "",
        "dVITD25OH": c.get("dVITD25OH", "") if c.get("dVITD25OH") is not None else "",
        "dPASI": c.get("dPASI", "") if c.get("dPASI") is not None else "",
        "dIGE": c.get("dIGE", "") if c.get("dIGE") is not None else "",
    }]


EMITTERS = {
    "DM": emit_DM, "IE": emit_IE, "MH": emit_MH, "DD": emit_DD, "VS": emit_VS,
    "SB": emit_SB, "SA": emit_SA, "TS": emit_TS, "LB": emit_LB, "MB": emit_MB,
    "EX": emit_EX, "AE": emit_AE, "PG": emit_PG, "DS": emit_DS, "RE": emit_RE,
}

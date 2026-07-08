"""
Project a simulated Ara06Patient trajectory into CRF row dicts (one list per
form). Pure projection — no fresh sampling. Forms mirror ARA06_output/CRF_spec.md.
"""
from __future__ import annotations
from typing import Dict, List, Any

from .dag_state import (Ara06Patient, CLINICAL_VISITS, BCELL_VISITS, SAFETY_LAB_VISITS)


def _d(p: Ara06Patient, day: int) -> str:
    return p.visit_date(day).strftime("%Y-%m-%d")


def emit_DM(p: Ara06Patient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "SITEID": p.site, "ARMCD": "ETN" if p.is_etn else "ADA",
        "ARM": p.arm, "AGE": p.age, "SEX": p.sex, "RACE": p.race, "ETHNIC": p.ethnicity,
        "COUNTRY": p.country, "WEIGHT": round(p.weight_kg, 1), "RFSTDTC": _d(p, 1),
    }]


def emit_MH(p: Ara06Patient) -> List[Dict[str, Any]]:
    """RA disease history / stratifiers — screening."""
    return [{
        "USUBJID": p.patient_id, "MHTERM": "Rheumatoid arthritis",
        "RADURYR": p.ra_duration_yr, "RFCCPPOS": "Y" if p.rf_ccp_positive else "N",
        "MTXDOSE": p.mtx_dose, "MTXDOSU": "mg/week",
        "DAS28_BL": p.baseline_das28, "HAQDI_BL": p.baseline_haqdi,
    }]


def emit_DA(p: Ara06Patient) -> List[Dict[str, Any]]:
    """Disease-activity / ACR-DAS28 components, one row per clinical visit."""
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "VISITNUM": r.visit_num,
        "DADTC": _d(p, r.visit_day), "DADY": r.visit_day,
        "TJC28": r.tjc, "SJC28": r.sjc, "PTGLOBAL": r.ptglobal, "PHYSGLOBAL": r.physglobal,
        "PAINVAS": r.pain, "HAQDI": r.haqdi, "CRP": r.crp, "DAS28CRP": r.das28,
    } for r in p.trajectory if r.visit_key in CLINICAL_VISITS]


def emit_BC(p: Ara06Patient) -> List[Dict[str, Any]]:
    """B-cell flow cytometry — switched-memory B-cell % (PRIMARY mechanistic node)."""
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "VISITNUM": r.visit_num,
        "BCDTC": _d(p, r.visit_day), "BCDY": r.visit_day,
        "MEMSWPCT": r.mem_switched_pct,
    } for r in p.trajectory if r.visit_key in BCELL_VISITS]


def emit_LB_HEM(p: Ara06Patient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "VISITNUM": r.visit_num,
        "LBDTC": _d(p, r.visit_day), "LBDY": r.visit_day,
        "WBC": r.wbc, "ANC": r.anc, "ALC": r.alc, "HGB": r.hgb, "PLT": r.plt,
    } for r in p.trajectory if r.visit_key in SAFETY_LAB_VISITS]


def emit_LB_CHEM(p: Ara06Patient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "VISITNUM": r.visit_num,
        "LBDTC": _d(p, r.visit_day), "LBDY": r.visit_day,
        "AST": r.ast, "ALT": r.alt, "CREAT": r.creat, "CRP": r.crp,
    } for r in p.trajectory if r.visit_key in SAFETY_LAB_VISITS]


def emit_EX(p: Ara06Patient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        # anti-TNF study drug
        if p.is_etn:
            rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "EXTRT": "ETANERCEPT",
                         "EXDOSE": 50, "EXDOSU": "mg", "EXROUTE": "SUBCUTANEOUS",
                         "EXDOSFRQ": "QW", "EXSTDTC": _d(p, r.visit_day), "EXACN": r.dose_action})
        else:
            rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "EXTRT": "ADALIMUMAB",
                         "EXDOSE": 40, "EXDOSU": "mg", "EXROUTE": "SUBCUTANEOUS",
                         "EXDOSFRQ": "Q2W", "EXSTDTC": _d(p, r.visit_day), "EXACN": r.dose_action})
        # background methotrexate (both arms)
        rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "EXTRT": "METHOTREXATE",
                     "EXDOSE": p.mtx_dose, "EXDOSU": "mg", "EXROUTE": "ORAL",
                     "EXDOSFRQ": "QW", "EXSTDTC": _d(p, r.visit_day), "EXACN": r.dose_action})
    return rows


def emit_AE(p: Ara06Patient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        rows.extend(r.aes)
    return rows


def emit_DS(p: Ara06Patient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "ARMCD": "ETN" if p.is_etn else "ADA",
        "DSDECOD": p.disposition, "DSTERM": p.discontinuation_reason or "COMPLETED STUDY",
        "DSSTDY": p.last_contact_day,
    }]


def emit_RE(p: Ara06Patient) -> List[Dict[str, Any]]:
    """Endpoint summary — one row per patient (primary + secondary)."""
    return [{
        "USUBJID": p.patient_id, "ARMCD": "ETN" if p.is_etn else "ADA",
        "RFCCPPOS": "Y" if p.rf_ccp_positive else "N",
        "MEMSW_WK12": p.mem_b_wk12 if p.mem_b_wk12 is not None else "",
        "DAS28RESP_WK12": p.das28resp_wk12, "DAS28RESP_WK24": p.das28resp_wk24,
        "ACR20_WK12": p.acr20_wk12, "ACR20_WK24": p.acr20_wk24,
        "ACR50_WK12": p.acr50_wk12, "ACR50_WK24": p.acr50_wk24,
        "SERIOUS_AE": p.serious_ae, "DISPOSITION": p.disposition,
    }]


EMITTERS = {
    "DM": emit_DM, "MH": emit_MH, "DA": emit_DA, "BC": emit_BC,
    "LB_HEM": emit_LB_HEM, "LB_CHEM": emit_LB_CHEM, "EX": emit_EX,
    "AE": emit_AE, "DS": emit_DS, "RE": emit_RE,
}

"""
Project a simulated RavePatient trajectory into CRF row dicts (one list per form).
Pure projection — no fresh sampling. Forms mirror RAVE_output/CRF_spec.md.
"""
from __future__ import annotations
from typing import Dict, List, Any

from .dag_state import RavePatient, VDI_VISITS


def _d(p: RavePatient, day: int) -> str:
    return p.visit_date(day).strftime("%Y-%m-%d")


def emit_DM(p: RavePatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "SITEID": p.site, "ARMCD": "RTX" if p.is_rtx else "CYC",
        "ARM": p.arm, "AGE": p.age, "SEX": p.sex, "RACE": p.race, "COUNTRY": p.country,
        "WEIGHT": round(p.weight_kg, 1), "RFSTDTC": _d(p, 1),
    }]


def emit_DC(p: RavePatient) -> List[Dict[str, Any]]:
    """Disease characteristics / ANCA — screening."""
    return [{
        "USUBJID": p.patient_id, "DIAGTYPE": p.diagnosis_type, "ANCATYPE": p.anca_type,
        "ANCASTAT": "POSITIVE", "NEWDX": "NEW" if p.new_diagnosis else "RELAPSING",
        "RENAL": "Y" if p.renal_involvement else "N",
        "BVASWG_BL": round(p.baseline_bvaswg, 1), "VDI_BL": p.baseline_vdi,
    }]


def emit_DA(p: RavePatient) -> List[Dict[str, Any]]:
    """BVAS/WG disease activity & flare, one row per assessed visit."""
    rows = []
    for r in p.trajectory:
        if r.visit_key in ("V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12"):
            rows.append({
                "USUBJID": p.patient_id, "VISIT": r.visit_key, "VISITNUM": r.visit_num,
                "DADTC": _d(p, r.visit_day), "DADY": r.visit_day,
                "BVASWG": r.bvaswg, "REMISSION": "Y" if r.remission else "N",
                "FLARE": r.flare, "GCFREE": "Y" if r.prednisone_dose == 0 else "N",
            })
    return rows


def emit_VDI(p: RavePatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "VDIDY": r.visit_day, "VDI": r.vdi,
    } for r in p.trajectory if r.visit_key in VDI_VISITS]


def emit_LB_HEM(p: RavePatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "VISITNUM": r.visit_num,
        "LBDTC": _d(p, r.visit_day), "LBDY": r.visit_day,
        "WBC": r.wbc, "ANC": r.anc, "HGB": r.hgb, "PLT": r.plt, "ESR": r.esr,
    } for r in p.trajectory]


def emit_LB_CHEM(p: RavePatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "LBDTC": _d(p, r.visit_day),
        "BUN": r.bun, "CREAT": r.creat, "CRP": r.crp,
    } for r in p.trajectory]


def emit_LB_UA(p: RavePatient) -> List[Dict[str, Any]]:
    hematuria_map = {0: "NEGATIVE", 1: "+", 2: "++", 3: "+++"}
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "LBDTC": _d(p, r.visit_day),
        "HEMATURIA": hematuria_map[r.hematuria],
    } for r in p.trajectory]


def emit_GC(p: RavePatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "VISIT": r.visit_key, "GCDTC": _d(p, r.visit_day),
        "PREDDOSE": r.prednisone_dose, "CUMGC": r.cum_gc,
        "GCFREE": "Y" if r.prednisone_dose == 0 else "N",
    } for r in p.trajectory if r.visit_key in ("V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8",
                                               "V9", "V10", "V11", "V12")]


def emit_EX(p: RavePatient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        if r.rtx_infusion:
            rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "EXTRT":
                         "RITUXIMAB" if p.is_rtx else "RITUXIMAB PLACEBO",
                         "EXDOSE": 375, "EXDOSU": "mg/m2", "EXROUTE": "IV",
                         "EXSTDTC": _d(p, r.visit_day), "EXACN": r.dose_action})
        if r.cyc_active:
            rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "EXTRT":
                         "CYCLOPHOSPHAMIDE" if not p.is_rtx else "CYCLOPHOSPHAMIDE PLACEBO",
                         "EXDOSE": 2, "EXDOSU": "mg/kg/day", "EXROUTE": "ORAL",
                         "EXSTDTC": _d(p, r.visit_day), "EXACN": r.dose_action})
        elif r.aza_active:
            rows.append({"USUBJID": p.patient_id, "VISIT": r.visit_key, "EXTRT":
                         "AZATHIOPRINE" if not p.is_rtx else "AZATHIOPRINE PLACEBO",
                         "EXDOSE": 2, "EXDOSU": "mg/kg/day", "EXROUTE": "ORAL",
                         "EXSTDTC": _d(p, r.visit_day), "EXACN": r.dose_action})
    return rows


def emit_AE(p: RavePatient) -> List[Dict[str, Any]]:
    rows = []
    for r in p.trajectory:
        rows.extend(r.aes)
    return rows


def emit_DS(p: RavePatient) -> List[Dict[str, Any]]:
    return [{
        "USUBJID": p.patient_id, "ARMCD": "RTX" if p.is_rtx else "CYC",
        "DSDECOD": p.disposition, "DSTERM": p.discontinuation_reason or "COMPLETED STUDY",
        "DSSTDY": p.last_contact_day, "CROSSOVER": "Y" if p.crossover_day else "N",
        "CROSSDY": p.crossover_day or "",
    }]


def emit_RE(p: RavePatient) -> List[Dict[str, Any]]:
    """Endpoint summary — one row per patient (primary + secondary)."""
    return [{
        "USUBJID": p.patient_id, "ARMCD": "RTX" if p.is_rtx else "CYC",
        "ANCATYPE": p.anca_type, "NEWDX": "NEW" if p.new_diagnosis else "RELAPSING",
        "CR6MO": p.cr_6mo,
        "TTREM_DAY": p.time_to_remission_day or "",
        "TTCR_DAY": p.time_to_cr_day or "",
        "FLARE_EVENT": p.flare_event, "FLARE_DAY": p.flare_day or "",
        "REMDUR_DAY": p.remission_duration_day if p.remission_duration_day is not None else "",
        "SERIOUS_AE": p.serious_ae, "DEATH": 1 if p.death_day else 0,
        "DISPOSITION": p.disposition,
    }]


EMITTERS = {
    "DM": emit_DM, "DC": emit_DC, "DA": emit_DA, "VDI": emit_VDI,
    "LB_HEM": emit_LB_HEM, "LB_CHEM": emit_LB_CHEM, "LB_UA": emit_LB_UA,
    "GC": emit_GC, "EX": emit_EX, "AE": emit_AE, "DS": emit_DS, "RE": emit_RE,
}

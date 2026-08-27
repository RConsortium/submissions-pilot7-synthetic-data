"""
ARA06 (NCT00837434 / DAIT ARA06) patient state + latent frailties + trajectory.

Mirrors the causal/ FLAURA2 and rave/ engines, but the disease model is
rheumatoid arthritis: the central latent state is DAS28-CRP disease activity
(driving the tender/swollen joint counts, CRP, global VAS and HAQ that compose
the ACR/EULAR clinical endpoints), plus a mechanistic memory-B-cell node (the
trial's PRIMARY endpoint). Frailties (drawn once, persist for life) induce
within-patient correlation across visits and AE types.

Both arms receive background methotrexate (MTX) + folic acid; the only
randomized contrast is etanercept (50 mg SQ weekly) vs adalimumab (40 mg SQ
q2w). MTX is the shared myelosuppression/hepatotoxicity driver; anti-TNF adds
infection risk and the memory-B-cell effect.

Visit grid = Protocol ARA06 v3.0 Table 6.5 Schedule of Evaluations (Clinical Study).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

import numpy as np


# Protocol Table 6.5 clinical-study visits. (key, VISITNUM, study_day, label)
SCHED = [
    ("SCRN", 1,  -14, "Screening"),
    ("V2",   2,    1, "Baseline/Treatment Initiation"),
    ("V3",   3,   28, "Week 4 (phone)"),
    ("V4",   4,   56, "Week 8"),
    ("V5",   5,   84, "Week 12"),       # PRIMARY ENDPOINT readout
    ("V6",   6,  112, "Week 16"),
    ("V7",   7,  140, "Week 20 (phone)"),
    ("V8",   8,  168, "Week 24 (End of Study)"),
]

PRIMARY_ENDPOINT_DAY = 84    # Week 12 memory-B-cell readout
WEEK24_DAY = 168
ADMIN_CENSOR_DAY = 168

# Which assessments are collected at which visits (CRF_spec SoA crosswalk).
CLINICAL_VISITS = {"SCRN", "V2", "V5", "V8"}          # DAS28/ACR components (HAQ, TJC, SJC, globals, CRP)
BCELL_VISITS = {"V2", "V5", "V8"}                     # B/T-cell flow incl. switched-memory %
SAFETY_LAB_VISITS = {"SCRN", "V2", "V4", "V6", "V8"}  # CBC + chem/LFT
PHONE_VISITS = {"V3", "V7"}                           # AE + med assessment only


def visit_info(key: str) -> Dict[str, Any]:
    for k, num, day, label in SCHED:
        if k == key:
            return {"VISITNUM": num, "VISITDY": day, "VISIT": label}
    return {}


def expit(x: float) -> float:
    if x >= 0:
        z = np.exp(-x)
        return float(1.0 / (1.0 + z))
    z = np.exp(x)
    return float(z / (1.0 + z))


def das28_crp(tjc: float, sjc: float, crp: float, gh: float) -> float:
    """Protocol Appendix C: DAS28-4(CRP) = 0.56*sqrt(tender28) + 0.28*sqrt(swollen28)
    + 0.36*ln(CRP+1) + 0.014*GH + 0.96. CRP in mg/L, GH = patient global VAS in mm."""
    return float(0.56 * np.sqrt(max(0.0, tjc)) + 0.28 * np.sqrt(max(0.0, sjc))
                 + 0.36 * np.log(max(0.0, crp) + 1.0) + 0.014 * gh + 0.96)


def eular_response(das_now: float, das_base: float) -> str:
    """EULAR DAS28 response (GOOD / MODERATE / NONE) from present value + change."""
    delta = das_base - das_now
    if das_now <= 3.2:
        if delta > 1.2:
            return "GOOD"
        if delta > 0.6:
            return "MODERATE"
        return "NONE"
    if das_now <= 5.1:
        return "MODERATE" if delta > 0.6 else "NONE"
    return "MODERATE" if delta > 1.2 else "NONE"


@dataclass
class Frailties:
    """Latent patient-level log-linear effects, shared across the trajectory."""
    f_heme: float = 0.0      # myelosuppression (MTX): anaemia/leukopenia/lymphopenia/neutropenia
    f_hepatic: float = 0.0   # transaminase elevation (MTX + anti-TNF): AST/ALT increased
    f_infect: float = 0.0    # infection susceptibility (anti-TNF): URI/nasopharyngitis/bronchitis
    f_msk: float = 0.0       # arthralgia/pain-in-extremity/headache cluster
    f_dropout: float = 0.0   # discontinuation propensity


@dataclass
class TrajectoryRow:
    """One simulated visit's latent + observed state."""
    visit_key: str
    visit_day: int
    visit_num: int

    # Clinical disease-activity components (collected at CLINICAL_VISITS)
    tjc: float
    sjc: float
    ptglobal: float          # patient global disease activity VAS, mm
    physglobal: float        # physician global VAS, mm (blinded assessor)
    pain: float              # patient pain VAS, mm
    haqdi: float             # HAQ-DI 0..3
    das28: float

    # Mechanistic primary node (collected at BCELL_VISITS)
    mem_switched_pct: float  # % CD27+ switched memory B cells of total B cells

    # Treatment / exposure
    prednisone_dose: float   # mg/day (<=10, mostly constant)
    dose_action: str         # NONE / DOSE REDUCED / DRUG INTERRUPTED / DRUG WITHDRAWN

    # Labs (collected at SAFETY_LAB_VISITS)
    wbc: float
    anc: float
    alc: float               # absolute lymphocyte count (lymphopenia)
    hgb: float
    plt: float
    ast: float
    alt: float
    creat: float
    crp: float

    aes: List[Dict[str, Any]]
    on_treatment: bool


@dataclass
class Ara06Patient:
    patient_id: str
    site: str
    arm: str                 # "Etanercept" or "Adalimumab"
    is_etn: bool
    baseline_date: date
    enrollment_offset_days: int

    # Demographics
    age: int
    sex: str                 # F / M
    race: str
    ethnicity: str           # HISPANIC / NOT HISPANIC
    country: str
    weight_kg: float

    # Disease characterization
    ra_duration_yr: float
    rf_ccp_positive: bool    # randomization stratifier
    mtx_dose: float          # mg/week (constant)

    # Baseline clinical components
    baseline_tjc: float
    baseline_sjc: float
    baseline_ptglobal: float
    baseline_physglobal: float
    baseline_pain: float
    baseline_haqdi: float
    baseline_crp: float
    baseline_das28: float

    # Baseline mechanistic + labs
    baseline_mem_switched: float
    baseline_wbc: float
    baseline_anc: float
    baseline_alc: float
    baseline_hgb: float
    baseline_plt: float
    baseline_ast: float
    baseline_alt: float
    baseline_creat: float
    baseline_pred: float     # mg/day prednisone (<=10)

    # Latent
    frailties: Frailties
    resp: float                       # latent maximal fractional clinical improvement [0,~0.9]
    comp_mult: Dict[str, float]       # per-component improvement multipliers (ACR "3 of 5" spread)

    trajectory: List[TrajectoryRow] = field(default_factory=list)

    # Endpoints (filled by outcomes)
    mem_b_wk12: Optional[float] = None
    das28resp_wk12: int = 0
    das28resp_wk24: int = 0
    acr20_wk12: int = 0
    acr20_wk24: int = 0
    acr50_wk12: int = 0
    acr50_wk24: int = 0
    serious_ae: int = 0
    discontinuation_day: Optional[int] = None
    discontinuation_reason: Optional[str] = None
    disposition: str = "COMPLETED"
    last_contact_day: int = ADMIN_CENSOR_DAY

    def visit_date(self, study_day: int) -> date:
        return self.baseline_date + timedelta(days=max(0, study_day - 1))


def draw_frailties(rng: np.random.Generator) -> Frailties:
    return Frailties(
        f_heme=float(rng.normal(0, 0.8)),
        f_hepatic=float(rng.normal(0, 0.8)),
        f_infect=float(rng.normal(0, 0.7)),
        f_msk=float(rng.normal(0, 0.7)),
        f_dropout=float(rng.normal(0, 0.6)),
    )

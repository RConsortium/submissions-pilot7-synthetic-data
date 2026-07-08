"""
RAVE (NCT00104299 / ITN021AI) patient state + latent frailties + trajectory.

Mirrors the causal/ FLAURA2 engine, but the disease model is ANCA-associated
vasculitis: the central latent state is BVAS/WG disease activity (0 = remission),
not tumor SLD. Frailties (drawn once, persist for life) induce within-patient
correlation across visits and AE types.

Visit grid = Protocol ITN021AI v7.0 Schedule of Assessments (Appendix 1).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

import numpy as np


# Protocol SoA Appendix 1 (Original Treatment Assignment): V1..V12 + screening.
# (key, VISITNUM, study_day, label)
SCHED = [
    ("SCRN", 1, -14, "Screening"),
    ("V1",   2,    1, "Baseline"),
    ("V2",   3,    8, "Week 1"),
    ("V3",   4,   15, "Week 2"),
    ("V4",   5,   22, "Week 3"),
    ("V5",   6,   29, "Month 1"),
    ("V6",   7,   60, "Month 2"),
    ("V7",   8,  120, "Month 4"),
    ("V8",   9,  180, "Month 6"),     # PRIMARY ENDPOINT readout
    ("V9",  10,  270, "Month 9"),
    ("V10", 11,  365, "Month 12"),
    ("V11", 12,  455, "Month 15"),
    ("V12", 13,  545, "Month 18"),    # end of main study
]

PRIMARY_ENDPOINT_DAY = 180
ADMIN_CENSOR_DAY = 545

# Visits where each form/assessment is collected (from CRF_spec SoA crosswalk).
BVAS_VISITS = {"SCRN", "V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12"}   # +flare hx from V5
VDI_VISITS = {"V1", "V8", "V10", "V12"}
LAB_VISITS = {k for (k, _, _, _) in SCHED}            # hematology/chem/UA every visit
RTX_INFUSION_VISITS = {"V1", "V2", "V3", "V4"}        # 4 weekly infusions
GC_LOG_VISITS = {k for (k, n, d, _) in SCHED if 1 <= d <= 545}


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


@dataclass
class Frailties:
    """Latent patient-level log-linear effects, shared across the trajectory."""
    f_heme: float = 0.0       # myelosuppression susceptibility (WBC/ANC/HGB/PLT)
    f_infect: float = 0.0     # infection susceptibility (B-cell depletion / immunosuppression)
    f_GI: float = 0.0         # nausea/vomiting/diarrhea cluster
    f_relapse: float = 0.0    # unobserved flare/relapse propensity
    f_steroid: float = 0.0    # glucocorticoid-toxicity susceptibility
    f_dropout: float = 0.0    # dropout propensity


@dataclass
class TrajectoryRow:
    """One simulated visit's latent + observed state."""
    visit_key: str
    visit_day: int
    visit_num: int

    # Disease activity
    bvaswg: float
    remission: bool          # BVAS/WG == 0
    flare: str               # NONE / LIMITED / SEVERE
    vdi: int

    # Treatment / exposure
    prednisone_dose: float   # mg/day
    cum_gc: float            # cumulative prednisone-equivalent mg
    cyc_active: bool
    aza_active: bool
    rtx_infusion: bool       # real-or-placebo infusion given this visit
    dose_action: str         # NONE / HELD / REDUCED / WITHDRAWN

    # Labs
    wbc: float
    anc: float
    hgb: float
    plt: float
    creat: float
    bun: float
    crp: float
    esr: float
    hematuria: int           # 0 (neg) .. 3 (+++)

    # AEs at this visit (CRF-ready dicts)
    aes: List[Dict[str, Any]]

    on_treatment: bool


@dataclass
class RavePatient:
    patient_id: str
    site: str
    arm: str                 # "Rituximab" or "Control"
    is_rtx: bool
    baseline_date: date
    enrollment_offset_days: int

    # Demographics
    age: int
    sex: str                 # F / M
    race: str
    country: str             # USA / NLD
    weight_kg: float

    # Disease characterization
    diagnosis_type: str      # GPA / MPA
    anca_type: str           # PR3 / MPO
    new_diagnosis: bool      # True=newly-diagnosed, False=relapsing
    renal_involvement: bool

    # Baseline disease activity / damage
    baseline_bvaswg: float
    baseline_vdi: int

    # Comorbidities
    htn: bool
    dm: bool

    # Baseline labs
    baseline_wbc: float
    baseline_anc: float
    baseline_hgb: float
    baseline_plt: float
    baseline_creat: float
    baseline_bun: float
    baseline_crp: float
    baseline_esr: float

    # Latent
    frailties: Frailties
    remit_propensity: float          # latent linear predictor for achieving remission
    remission_day: Optional[int] = None   # first day BVAS/WG hits 0 (filled in longitudinal)

    trajectory: List[TrajectoryRow] = field(default_factory=list)

    # Endpoints (filled by outcomes)
    cr_6mo: int = 0                  # PRIMARY: BVAS/WG=0 & off prednisone at day 180
    time_to_remission_day: Optional[int] = None
    time_to_cr_day: Optional[int] = None
    flare_event: int = 0
    flare_day: Optional[int] = None
    remission_duration_day: Optional[int] = None
    serious_ae: int = 0
    crossover_day: Optional[int] = None
    discontinuation_day: Optional[int] = None
    discontinuation_reason: Optional[str] = None
    death_day: Optional[int] = None
    disposition: str = "COMPLETED"
    last_contact_day: int = ADMIN_CENSOR_DAY

    def visit_date(self, study_day: int) -> date:
        return self.baseline_date + timedelta(days=max(0, study_day - 1))


def draw_frailties(rng: np.random.Generator) -> Frailties:
    return Frailties(
        f_heme=float(rng.normal(0, 0.7)),
        f_infect=float(rng.normal(0, 0.7)),
        f_GI=float(rng.normal(0, 0.7)),
        f_relapse=float(rng.normal(0, 0.8)),
        f_steroid=float(rng.normal(0, 0.6)),
        f_dropout=float(rng.normal(0, 0.5)),
    )

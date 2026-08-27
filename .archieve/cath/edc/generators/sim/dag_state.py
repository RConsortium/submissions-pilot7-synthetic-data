"""
CATH (NCT00789880 / ADVN CATH 03-01) patient state + latent frailties + trajectory.

Mirrors the rave/ engine, but the disease model is a 3-week dermatology substudy of
oral vitamin D3 vs placebo. The central latent state is NOT survival/tumor — it is
**skin innate-immune peptide expression** (cathelicidin CAMP/LL-37, HBD-3) and the TH2
cytokine IL-13, measured by qRT-PCR in lesional/non-lesional biopsies at Baseline (Day 0)
and Day 21. The endpoint is a continuous CHANGE score (Day21 − Baseline), derived from the
trajectory — never drawn directly.

Three diagnostic groups (NONAD healthy, AD, PSO) × two arms (VITD, PLAC). Frailties drawn
once per patient induce within-patient correlation across the related antimicrobial peptides.

Visit grid = Protocol ADVN CATH 03-01 §10.6 Schedule of Activities.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

import numpy as np


# Protocol §10.6 SoA: 3 scheduled visits + unscheduled.
# (key, VISITNUM, study_day, label)
SCHED = [
    ("SCRN", 1, -8, "Screening (Day -7 to -10)"),   # eligibility bloods (vitD/Ca/PTH/creat/IgE)
    ("BASE", 2,  0, "Baseline (randomization)"),      # baseline biopsy/saliva/tape/microbial; start drug
    ("D21",  3, 21, "Day 21"),                        # repeat biopsy + bloods; end of dosing
]

PRIMARY_ENDPOINT_DAY = 21
ADMIN_CENSOR_DAY = 21

BLOOD_VISITS = {"SCRN", "D21"}          # serum panel: screening + Day 21
BIOPSY_VISITS = {"BASE", "D21"}         # skin biopsy / saliva / tape / microbial
PEPTIDES = ("CAMP", "HBD3", "IL13", "IL4")

# Diagnostic groups and which skin compartments are biopsied.
COMPARTMENTS = {
    "NONAD": ("NONLESIONAL",),               # healthy controls: non-lesional only
    "AD":    ("LESIONAL", "NONLESIONAL"),
    "PSO":   ("LESIONAL", "NONLESIONAL"),
}

# code -> targets.json label fragments
GROUP_LBL = {"NONAD": "NonAD", "AD": "AD", "PSO": "Pso"}
ARM_LBL = {"VITD": "VitD", "PLAC": "Plac"}
SKIN_LBL = {"LESIONAL": "Lesional", "NONLESIONAL": "NonLesional"}


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
    """Latent patient-level effects, shared across the trajectory (drawn once)."""
    f_amp: float = 0.0      # shared antimicrobial-peptide responsiveness (CAMP+HBD3 cluster)
    f_th2: float = 0.0      # TH2 axis (IL-13/IL-4, IgE)
    f_dropout: float = 0.0  # dropout propensity


@dataclass
class BiopsyState:
    """One skin compartment's peptide expression at one visit (qRT-PCR relative abundance)."""
    compartment: str
    camp: float
    hbd3: float
    il13: float
    il4: float


@dataclass
class TrajectoryRow:
    """One visit's latent + observed state."""
    visit_key: str
    visit_day: int
    visit_num: int

    # serum panel (drawn at SCRN baseline + D21)
    vitd_25oh: Optional[float] = None
    calcium: Optional[float] = None
    pth: Optional[float] = None
    creat: Optional[float] = None
    ige: Optional[float] = None
    rast: Optional[int] = None

    # skin compartments (biopsy/tape) at BASE + D21
    biopsy: Dict[str, BiopsyState] = field(default_factory=dict)   # compartment -> BiopsyState
    saliva_camp: Optional[float] = None
    tape_camp: Dict[str, float] = field(default_factory=dict)      # compartment -> tape cathelicidin
    cfu: Dict[str, float] = field(default_factory=dict)            # compartment -> log10 CFU
    pasi: Optional[float] = None
    sysbp: Optional[int] = None
    diabp: Optional[int] = None
    pulse: Optional[int] = None
    temp: Optional[float] = None

    aes: List[Dict[str, Any]] = field(default_factory=list)
    on_treatment: bool = True


@dataclass
class CathPatient:
    patient_id: str
    site: str
    dxgroup: str             # NONAD / AD / PSO
    arm: str                 # "Vitamin D3" / "Placebo"
    is_vitd: bool
    baseline_date: date
    enrollment_offset_days: int

    # Demographics (L0)
    age: int
    sex: str                 # F / M
    race: str
    ethnic: str              # HISPANIC / NOT HISPANIC
    country: str             # USA
    height_cm: float
    weight_kg: float
    bmi: float
    fitzpatrick: int         # 1..6

    # Baseline serum panel (L0; screening labs)
    base_vitd_25oh: float
    base_calcium: float
    base_pth: float
    base_creat: float
    base_ige: float
    base_rast: int

    # Baseline skin biopsy expression per compartment (L0)
    base_biopsy: Dict[str, BiopsyState]
    base_pasi: Optional[float]
    base_cfu: Dict[str, float]

    # Latent
    frailties: Frailties

    trajectory: List[TrajectoryRow] = field(default_factory=list)

    # Endpoints / disposition (filled by outcomes)
    completer: bool = True
    disposition: str = "COMPLETED"
    discontinuation_reason: Optional[str] = None
    discontinuation_day: Optional[int] = None
    last_contact_day: int = ADMIN_CENSOR_DAY
    serious_ae: int = 0

    # derived change scores (filled by outcomes; None if not a completer)
    change: Dict[str, Optional[float]] = field(default_factory=dict)

    def visit_date(self, study_day: int) -> date:
        return self.baseline_date + timedelta(days=max(0, study_day + 8))  # SCRN(-8) -> offset 0


def draw_frailties(rng: np.random.Generator) -> Frailties:
    return Frailties(
        f_amp=float(rng.normal(0, 1.0)),
        f_th2=float(rng.normal(0, 1.0)),
        f_dropout=float(rng.normal(0, 0.6)),
    )

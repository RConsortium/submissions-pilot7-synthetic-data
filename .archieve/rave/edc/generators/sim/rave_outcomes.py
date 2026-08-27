"""
Y — RAVE endpoint derivation from the simulated trajectory.

PRIMARY: complete_remission_6mo = 1 iff BVAS/WG == 0 AND prednisone == 0 at the
month-6 visit (study day 180). Read off the trajectory — never drawn directly.
"""
from __future__ import annotations
import numpy as np

from .dag_state import RavePatient, PRIMARY_ENDPOINT_DAY, ADMIN_CENSOR_DAY


def derive_endpoints(patient: RavePatient, rng, params: dict) -> None:
    P = params
    traj = patient.trajectory

    # PRIMARY — complete remission at 6 months (day-180 / V8 readout) -----------
    v8 = next((r for r in traj if r.visit_day == PRIMARY_ENDPOINT_DAY), None)
    if v8 is not None:
        patient.cr_6mo = int(v8.bvaswg == 0.0 and v8.prednisone_dose == 0.0)
    else:
        patient.cr_6mo = 0   # discontinued before month 6 → not in complete remission

    # time to complete remission (BVAS/WG=0 AND off glucocorticoids) ------------
    for r in traj:
        if r.bvaswg == 0.0 and r.prednisone_dose == 0.0:
            patient.time_to_cr_day = r.visit_day
            break

    # remission duration → first flare (else censored at last visit / month 18) -
    if patient.flare_day is not None and patient.remission_day is not None:
        patient.remission_duration_day = max(0, patient.flare_day - patient.remission_day)
    elif patient.remission_day is not None:
        last = traj[-1].visit_day if traj else patient.remission_day
        patient.remission_duration_day = max(0, min(ADMIN_CENSOR_DAY, last) - patient.remission_day)

    # death (rare; ~2 per arm over 18 mo) --------------------------------------
    p_death = P["death_base"] + P["death_serious_ae"] * (1 if patient.serious_ae else 0)
    if rng.random() < p_death:
        lo = patient.discontinuation_day or 60
        patient.death_day = int(rng.integers(min(lo, 500), ADMIN_CENSOR_DAY + 1))

    # disposition --------------------------------------------------------------
    if patient.death_day is not None:
        patient.disposition = "DEATH"
        patient.discontinuation_reason = patient.discontinuation_reason or "DEATH"
        patient.last_contact_day = patient.death_day
    elif patient.discontinuation_day is not None:
        patient.disposition = "DISCONTINUED"
        patient.last_contact_day = patient.discontinuation_day
    else:
        patient.disposition = "COMPLETED"
        patient.last_contact_day = traj[-1].visit_day if traj else ADMIN_CENSOR_DAY

    reconcile_ae_ds(patient)


def reconcile_ae_ds(patient: RavePatient) -> None:
    """Issue #184 — AE↔DS traceability. If a patient leaves due to an adverse event, the AE
    domain must name the cause by flagging the triggering AE AEACN="DRUG WITHDRAWN" (CDISC
    AEACN codelist C66767). Each AE's action is fixed when it is emitted mid-visit, but the
    discontinuation reason is settled only here — so we resolve the withdrawal action now,
    at projection time, from already-realized parents: the most recent serious AE on/before
    last contact. This is a deterministic, RNG-free projection of the existing
    AE→withdrawal→discontinuation edge — not a new edge and not a fresh draw. Keyed on the
    reason (not disposition), so a patient who discontinued for an AE and later died still
    gets the link. If no serious AE exists (structurally impossible here, since the reason is
    only assigned when one has occurred), the link is left unset and gate g6 fails closed."""
    if patient.discontinuation_reason != "ADVERSE EVENT":
        return
    cutoff = patient.last_contact_day
    candidates = [a for r in patient.trajectory for a in r.aes
                  if a["AESER"] == "Y" and a["AEDY"] <= cutoff]
    if not candidates:
        return
    trigger = max(candidates, key=lambda a: a["AEDY"])
    trigger["AEACN"] = "DRUG WITHDRAWN"

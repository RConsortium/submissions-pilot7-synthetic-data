# CAR-T Clinical Trial Data — Submission Pilot

Synthetic [OpenClinica](https://www.openclinica.com/) ODM export wired
through a full **SDTM + ADaM pipeline** targeting **SDTMIG v3.3 /
ADaMIG v1.3**. The study and source data are described further below;
this section is the project map.

## What's in this folder

```
cart-t/
├─ car-t-openclinica.xml      Source ODM v1.3 export
├─ CLAUDE.md                  Project conventions (read this first)
├─ README.md                  This file
├─ data/
│  ├─ raw/   flat.rds + one .rds per CRF form (README + form-name map)
│  ├─ sdtm/  9 domains:  dm, mh, ie, ae, cm, ds, lb, qs, ce
│  └─ adam/  9 datasets: adsl, adae, adcm, adlb, adqs, admh, adds, adie, adce
├─ program/
│  ├─ raw/   load_xml.R, ut_load_xml*.R, _run_all.R    (XML → flat.rds → forms)
│  ├─ sdtm/  dm.R … ce.R + ut_visits.R + _run_all.R    (raw → SDTM, dplyr/tidyr)
│  ├─ adam/  adsl.R … adce.R + _run_all.R              (SDTM → ADaM, {admiral})
│  └─ check_logs.R                                      (logs/ → logs/_summary.md)
├─ spec/
│  ├─ ig/    Local copies of SDTMIG v3.3 / SDTM v1.7 / ADaMIG v1.3
│  │        plus knowledge_sdtm_ig.md / knowledge_adam_ig.md navigation maps
│  ├─ sdtm/  YAML spec per domain   + _index.yaml
│  ├─ adam/  YAML spec per dataset  + _index.yaml
│  └─ raw/   ut_xml_to_crf_html.R   → crf_review.html (browser CRF viewer)
└─ logs/     logrx log per program  + _summary.md
```

## How to (re)build everything

Run from the project root:

```bash
Rscript program/raw/_run_all.R    # XML  → data/raw/flat.rds + per-form .rds
Rscript program/sdtm/_run_all.R   # raw  → data/sdtm/<domain>.rds
Rscript program/adam/_run_all.R   # sdtm → data/adam/<dataset>.rds
Rscript program/check_logs.R      # scan logs/ → logs/_summary.md
```

Run order matters: ADaM depends on SDTM, SDTM depends on raw. The
batch runners use `{logrx}` and emit one log per program under
`logs/<area>/<program>.log`.

Packages are pinned by `renv` (`renv.lock`); on first checkout run
`renv::restore()` to install the recorded versions.

## Conventions

[`CLAUDE.md`](CLAUDE.md) is the binding source of truth on **how** work
is done in this project — spec YAML shape, R code style, the
ARM/STRAT design decision, batch runners, `{admiral}` usage, and the
validation workflow. The IG knowledge files under `spec/ig/` are the
source of truth on **what** the SDTM/ADaM standards require.

---

# Study Overview

**Study Name:** CAR-T for ALL  
**Protocol:** CART2020  
**Description:** A Phase IIb, double-blind, multi-center study of CAR-T cell therapy in adults with acute lymphoblastic leukemia.

**File:** [`car-t-openclinica.xml`](car-t-openclinica.xml)  
**Format:** [ODM v1.3](https://www.cdisc.org/standards/data-exchange/odm-xml/odm-xml-v1-3-2)

## Study Sites

The study includes multiple participating sites:
- Dana-Farber Cancer Institute
- Cedars-Sinai
- MGH (Massachusetts General Hospital)
- Abbott
- University Hospital
- Children's National
- St James's University Hospital

## Study Events

The clinical trial protocol includes 23 study events organized across different visit types:

### Unscheduled Events
1. **Informed Consent** - eConsent process
2. **Enrollment** - Eligibility screening and enrollment
3. **Baseline** - Demographics, baseline labs, and randomization
4. **Quality of Life** - QoL assessments (RAND SF-12, EQ-5D-5L surveys)
5. **AE Coding** - MedDRA coding for adverse events
6. **ConMed Coding** - RxNorm coding for concomitant medications
7. **Health History** - Patient health history
8. **Medical History** - Medical history documentation

### Common/Repeating Events
9. **Source Documents**
10. **Labs** - Laboratory results
11. **Medical History/Comorbidities**
12. **Adverse Events**
13. **Concomitant Medications**
14. **Endpoint** - Suspected MI (myocardial infarction) events
15. **Adjudication** - Committee review of endpoints
16. **Disposition**
17. **Misc. Form Capabilities**
18. **Meds from EHR** - Medications from Electronic Health Records
19. **Immunizations from EHR**
20. **Encounters from EHR**
21. **Procedures from EHR**
22. **Labs from EHR**
23. **Conditions from EHR**

## Key Forms (CRFs)

The study includes various Case Report Forms (CRFs):
- **ICF (eConsent)** - Electronic informed consent
- **Eligibility** - Inclusion/exclusion criteria evaluation
- **Demographics and History** - Patient demographics and medication history
- **Baseline Labs and Imaging** - Chemistry panel, nephrology, imaging scans
- **Randomize** - Randomization assignment
- **RAND SF-12 Survey** - Quality of life assessment
- **EQ-5D-5L Questionnaire** - Health status questionnaire
- **Skin Conditions Questionnaire**
- **Adverse Event** - AE reporting with MedDRA coding
- **ConMed** - Concomitant medications with RxNorm coding
- **Suspected MI** - Endpoint evaluation
- **Evaluator A/B** - Independent adjudication
- **Committee Review** - Final adjudication
- **Disposition** - Study disposition tracking

## Data Standards

The XML file follows CDISC ODM v1.3 standards with OpenClinica extensions:
- **Coding Systems:**
  - MedDRA for adverse event coding
  - RxNorm for medication coding
- **Standards Compliance:**
  - CDISC ODM 1.3
  - OpenClinica ODM extensions v3.1

## File Structure

The ODM XML contains:
- Study metadata and protocol definition
- Form and item group definitions
- Code lists and controlled terminology
- Clinical data for all subjects
- Audit trail information

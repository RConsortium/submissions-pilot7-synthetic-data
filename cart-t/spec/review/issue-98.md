# Issue #98: verification against the ODM refactor

Related issue: [cart-t archive ADaM data-quality findings](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/98).

Assessment: **partially addressed; keep the issue open**. The refactor corrects
standardization defects but cannot supply missing exposure, approved analysis
definitions or complete safety data. This assessment covers dataset content
and traceability. Human clinical/statistical review remains pending.

## Reproduce

From the repository root, after installing the study requirements:

```bash
.venv/bin/python cart-t/program/run.py
# Or assess an existing successful build:
.venv/bin/python cart-t/program/verify_issue_98.py
```

The full runner includes the verifier. `log/issue-98.json` records archived
and standardized counts, column presence, missingness and eight regression
checks. The archived XPT files are used only for verification, never as
clinical derivation inputs. These counts are dataset QC evidence, not TLFs.

## Findings

| Issue finding | Verified standardized result | Assessment |
| --- | --- | --- |
| 1. Missing treatment dates and duration | TRTSDT, TRTEDT and TRTDURD are missing for all 810 ADSL subjects; ADAE TRTSDT and ASTDY are missing for all 365 records. ASTDT is present for 352 records. | Unresolved source gap. ODM has no exposure records; AE dates cannot establish treatment dates. |
| 2. Blank TRTEMFL | Missing on all 365 ADAE records. | Unresolved. Documented treatment start and an approved risk window are needed. |
| 3. All subjects ONGOING; milestones used as terminal disposition | EOSSTT is DISCONTINUED for two subjects and UNKNOWN for 808. DCDECOD is ADVERSE EVENT for one, WITHDRAWAL BY SUBJECT for one, and missing for 808. Only DSCAT=DISPOSITION EVENT feeds terminal disposition. | Standardization defect corrected with source limits. UNKNOWN does not mean ongoing. See the explanation below. |
| 4. One AE per safety subject | ADAE now has 365 records for 327 subjects; 26 subjects have multiple AEs. Every ADAE subject/AESEQ matches SDTM AE. | Record-collapse defect corrected. These counts do not define a safety denominator. |
| 5. Safety flag inconsistent with treatment | No subject is assigned to safety from AE presence. SAFFL=N for all 810; planned/actual treatment remain missing. PROFILE is retained as phenotype, not Study Treatment. | False membership removed. Safety-population qualification remains blocked by exposure and approved population definitions. N does not prove a subject was untreated. |
| 6a. Missing safety fields | AEACN is restored on 262/365 records. AESDTH is restored as Y on six and N on 11; it is missing on 348. AESER is missing on 17 and AEOUT on 82. DTHDT is present for five subjects; DTHFL is not supplied. | Partially addressed. Missing and contradictory source values remain unresolved. Retaining more AE instances changes the missingness denominator. |
| 6b. Baseline-only laboratory data | ADLB now has 1,136 records for 950 subject/parameter pairs; 32 pairs have multiple results. ABLFL, BASE, CHG and PCHG are missing throughout. | Lost repeats and unsupported baseline assignments corrected. Treatment-relative baseline and change remain underivable without approved timing/rules. |

The archive has 278 COMPLETED and 312 SCREEN FAILURE records because its DS
program infers terminal outcomes from randomization/eligibility workflow
presence. See `.archieve/cart-t/program/sdtm/ds.R`, the section beginning
"Layer 4: terminal disposition event for every subject" (the rules assign COMPLETED to randomized
subjects without an early termination). These counts are not independently
confirmed disposition observations in the ODM. The refactor retains the two
explicit discontinuations and removes those inferred terminal outcomes.
Consequently, reproducing the archived completion/screen-failure counts would
restore unsupported assumptions. This also affects the archived-data rule
discussed in [issue #90](https://github.com/RConsortium/submissions-pilot7-synthetic-data/issues/90).

Outcome/death-criterion contradictions remain in the source and standardized
data. `log/audit.json` reports eight fatal-outcome/death-criterion disagreements.
The verifier does not fill a missing outcome from a seriousness flag or certify
a reconciled death flag. Recorded death dates alone do not resolve all source
contradictions.

## Remaining work

1. Obtain exposure/allocation records and approve the safety population and
   treatment-emergence risk window.
2. Reconcile actual terminal disposition and death evidence with the source
   owner; approve the meaning of missing status.
3. Resolve missing AE qualifiers and confirm terminology/coding.
4. Approve a laboratory baseline and visit definition, then rederive dependent
   variables and repeat independent QC and conformance checks.

No issue is closed automatically. The issue's archive findings remain valid
for the unchanged archive; the refactor provides a separately qualified draft.

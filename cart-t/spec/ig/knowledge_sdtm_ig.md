# SDTM IG / SDTM Model — Knowledge Map for Spec Development

**Purpose.** This file is a *navigation index*, not a reproduction of the
standard. When an agent needs to answer "where does the IG specify X?" or
"what are the Required/Expected variables for domain Y?", look up the topic
here and follow the anchor URL to the canonical text.

## Local files

| File | Standard | Notes |
|---|---|---|
| `sdtmig_v3_3.html`     | SDTMIG v3.3 | Full IG, single HTML page, 436 named anchors |
| `sdtm_v1_7.html`       | SDTM v1.7 model | Full model, single HTML page, 53 anchors |

**Base URLs (append `#<anchor-id>` to deep-link):**

- SDTMIG v3.3: `https://www.cdisc.org/standards/foundational/sdtmig/sdtmig-v3-3/html`
- SDTM v1.7:   `https://www.cdisc.org/standards/foundational/sdtm/sdtm-v1-7/html`

Anchors use `+` as the word separator, e.g.
`...#AE+Specification`.

---

## How a domain section is laid out

For every published domain, the IG provides four anchored subsections:

| Subsection | Anchor pattern | Contains |
|---|---|---|
| Description/Overview | `<DOM>+Description+Overview` | Purpose, structure, scope of the domain |
| Specification        | `<DOM>+Specification`        | Variable table with Name, Label, Type, Controlled Terms or Format, Role, **Core (Req/Exp/Perm)**, Notes |
| Assumptions          | `<DOM>+Assumptions`          | Mapping rules, edge cases, modeling decisions |
| Examples             | `<DOM>+Examples`             | Worked-out CRF→SDTM examples with row-level data |

When writing a domain spec, walk these four in order: pull variable
attributes from *Specification*, mapping rules from *Assumptions*, and use
*Examples* to sanity-check edge cases.

---

## Where the global rules live (SDTMIG Chapter 4 — Assumptions)

The global rules that apply to **every** domain are concentrated in
Chapter 4. Cite these when spec decisions need a defense.

| Topic | Anchor |
|---|---|
| Order of variables in a dataset | `#Order+of+the+Variables` |
| Core designations (Req / Exp / Perm) | `#SDTM+Core+Designations` |
| Dataset naming, splitting | `#Additional+Guidance+on+Dataset+Naming`, `#Splitting+Domains` |
| Origin metadata (CRF / Derived / Assigned / Protocol / Predecessor) | `#Origin+Metadata`, `#Origin+Metadata+for+Variables`, `#Origin+Metadata+for+Records` |
| EPOCH variable usage | `#EPOCH+Variable+Guidance` |
| Natural keys in metadata | `#Assigning+Natural+Keys+in+the+Metadata` |
| **Variable-Naming Conventions** | `#Variable+Naming+Conventions` |
| 2-character domain code rules | `#Two+Character+Domain+Identifier` |
| Text case in submitted data | `#Text+Case+in+Submitted+Data` |
| Missing-value convention | `#Convention+for+Missing+Values` |
| Grouping/categorization (`--CAT`/`--SCAT`) | `#Grouping+Variables+and+Categorization` |
| Free text from CRF (Specify variables) | `#Submitting+Free+Text+from+the+CRF` |
| Multiple values for a variable | `#Multiple+Values+for+a+Variable` |
| **Variable lengths** | `#Variable+Lengths` |
| Controlled terminology rules | `#Coding+and+Controlled+Terminology+Assumptions` |
| Yes/No values | `#Use+of+Yes+and+No+Values` |
| **Date/time formats (ISO 8601)** | `#Formats+for+Date+Time+Variables` |
| Date/time precision (partial dates) | `#Date+Time+Precision` |
| `--DUR` duration intervals | `#Intervals+of+Time+and+Use+of+Duration+for+DUR+Variables` |
| Study Day (`--DY`) | `#Use+of+the+Study+Day+Variables` |
| Visits and encounters | `#Clinical+Encounters+and+Visits` |
| Relative timing variables (`--STRF`, `--ENRF`, `--EVLINT`) | `#Use+of+Relative+Timing+Variables` |
| Time points (`--TPT`, `--TPTNUM`, `--ELTM`, `--TPTREF`) | `#Representing+Time+Points` |
| Disease milestones | `#Disease+Milestones+and+Disease+Milestone+Timing+Variables` |
| Original vs Standardized results (`--ORRES` / `--STRESC` / `--STRESN`) | `#Original+and+Standardized+Results+of+Findings+and+Tests+Not+Done` |
| Tests not done | `#Tests+Not+Done` |
| Text > 200 chars handling | `#Text+Strings+That+Exceed+the+Maximum+Length+for+General+Observation+Class+Domain+Variables` |
| Evaluators (`--EVAL`, `--EVALID`) | `#Evaluators+in+the+Interventions+and+Events+Observation+Classes` |
| Clinical significance flag | `#Clinical+Significance+for+Findings+Observation+Class+Data` |
| Pre-specified interventions / events (`--PRESP`, `--OCCUR`) | `#Presence+or+Absence+of+Pre+Specified+Interventions+and+Events` |
| Baseline values (`--BLFL`) | `#Baseline+Values` |

---

## Where each domain is defined

### Special-purpose (Chapter 5)

| Code | Topic | Anchor stem |
|---|---|---|
| `CO` | Comments         | `CO+Description+Overview` … `CO+Examples` |
| `DM` | Demographics     | `DM+Description+Overview` … `DM+Examples` |
| `SE` | Subject Elements | `SE+Description+Overview` … |
| `SM` | Subject Disease Milestones | `SM+Description+Overview` … |
| `SV` | Subject Visits   | `SV+Description+Overview` … |

### Interventions (Chapter 6.1)

| Code | Topic |
|---|---|
| `AG` | Procedure Agents |
| `CM` | Concomitant/Prior Medications |
| `EX` | Exposure |
| `EC` | Exposure as Collected |
| `ML` | Meal Data |
| `PR` | Procedures |
| `SU` | Substance Use |

### Events (Chapter 6.2)

| Code | Topic |
|---|---|
| `AE` | Adverse Events |
| `CE` | Clinical Events |
| `DS` | Disposition |
| `DV` | Protocol Deviations |
| `HO` | Healthcare Encounters |
| `MH` | Medical History |

### Findings (Chapter 6.3)

| Code | Topic |
|---|---|
| `DA` | Drug Accountability |
| `DD` | Death Details |
| `EG` | ECG Test Results |
| `IE` | Inclusion/Exclusion Exceptions |
| `IS` | Immunogenicity Specimen Assessments |
| `LB` | Laboratory Test Results |
| `MB` | Microbiology Specimen |
| `MS` | Microbiology Susceptibility |
| `MI` | Microscopic Findings |
| `MO` | Morphology (decommissioning notice in IG) |
| `CV` | Cardiovascular System Findings |
| `MK` | Musculoskeletal System Findings |
| `NV` | Nervous System Findings |
| `OE` | Ophthalmic Examinations |
| `RP` | Reproductive System Findings |
| `RE` | Respiratory System Findings |
| `UR` | Urinary System Findings |
| `PC` | Pharmacokinetic Concentrations |
| `PP` | Pharmacokinetic Parameters |
| `PE` | Physical Examination |
| `FT` | Functional Tests |
| `QS` | Questionnaires |
| `RS` | Disease Response and Clin Classification |
| `SC` | Subject Characteristics |
| `SS` | Subject Status |
| `TU` | Tumor/Lesion Identification |
| `TR` | Tumor/Lesion Results |
| `VS` | Vital Signs |

### Findings About (Chapter 6.4)

| Code | Topic |
|---|---|
| `FA` | Findings About (parent) |
| `SR` | Skin Response |

Naming-Findings-About-domains rules: `#Naming+Findings+About+Domains`.
When-to-use rules: `#When+to+Use+Findings+About`.

### Trial Design (Chapter 7)

| Code | Topic |
|---|---|
| `TA` | Trial Arms |
| `TE` | Trial Elements |
| `TV` | Trial Visits |
| `TD` | Trial Disease Assessments |
| `TM` | Trial Disease Milestones |
| `TI` | Trial Inclusion/Exclusion Criteria |
| `TS` | Trial Summary |

### Relationships and Study References (Chapters 8–9)

| Topic | Anchor |
|---|---|
| `--GRPID` (within-domain grouping) | `#Relating+Groups+of+Records+Within+a+Domain+Using+the+GRPID+Variable` |
| `RELREC` (peer records, dataset relationships) | `#Relating+Peer+Records`, `#RELREC+Dataset` |
| `SUPP--` (non-standard qualifiers) | `#Relating+Non+Standard+Variables+Values+to+a+Parent+Domain`, `#Supplemental+Qualifiers+SUPP+Datasets` |
| When NOT to use SUPP | `#When+Not+to+Use+Supplemental+Qualifiers` |
| Linking comments to records | `#Relating+Comments+to+a+Parent+Domain` |
| Deciding where data belongs | `#How+to+Determine+Where+Data+Belong+in+SDTM+Compliant+Data+Tabulations` |
| Differentiating Events vs Findings vs FA | `#Guidelines+for+Differentiating+Between+Events+Findings+and+Findings+About+Events` |
| `RELSUB` (related study subjects) | `#Relating+Study+Subjects`, `#RELSUB+Specification` |
| Device Identifiers | `#Device+Identifiers` |
| Organism Identifiers (`OI`) | `#OI+Specification` |
| Pharmacogenomic biomarker IDs | `#Pharmacogenomic+Genetic+Biomarker+Identifiers` |

### Appendices

| Topic | Anchor |
|---|---|
| Glossary & Abbreviations | `#Glossary+and+Abbreviations` |
| Controlled Terminology overview | `#Controlled+Terminology` |
| Trial Summary Codes | `#Trial+Summary+Codes` |
| Supplemental Qualifier Name Codes | `#Supplemental+Qualifiers+Name+Codes` |
| **Variable-Naming Fragments** (the canonical list of `--<root>` suffixes and their meanings) | `#CDISC+Variable+Naming+Fragments` |
| Revision History | `#Revision+History` |

---

## SDTM v1.7 model — where the foundations live

The model defines the *classes* and the *variable roles* that the IG then
instantiates. Read here when the question is conceptual ("what is a Topic
variable?", "what counts as a Findings observation?").

| Topic | Anchor (sdtm_v1_7.html) |
|---|---|
| Observations and variable concepts | `#Model+Concepts+and+Terms` |
| The three general observation classes | `#The+General+Observation+Classes` |
| Interventions class | `#The+Interventions+Observation+Class` |
| Events class | `#The+Events+Observation+Class` |
| Findings class | `#The+Findings+Observation+Class` |
| Findings About | `#Findings+About+Events+or+Interventions` |
| **Identifiers — full list** | `#Identifiers+for+All+Classes` |
| **Timing variables — full list** | `#Timing+Variables+for+All+Classes` |
| Demographics in the model | `#Demographics` |
| Subject Elements / Visits / Milestones | `#Subject+Elements`, `#Subject+Visits`, `#Subject+Disease+Milestones` |
| Subject Repro Stages | `#Subject+Repro+Stages` |
| Trial Design overview | `#Planned+Elements+Arms+Visits+Sets+Repro+Stages+and+Repro+Paths` |
| RELREC, SUPP--, Pool, RELSUB, DSR datasets | `#Datasets+for+Representing+Relationships` |
| Device & Organism identifier datasets | `#Datasets+for+Study+References` |
| Associated Persons modeling | `#Creating+Associated+Persons+Domains` |
| Using the model for regulatory submissions | `#Using+the+Model+for+Regulatory+Submissions` |
| Changes v1.6 → v1.7 | `#Changes+From+SDTM+v1.6+to+SDTM+v1.7` |

---

## How to use this map when developing a domain spec

1. **Find the domain section** in the table above; open
   `<DOM>+Description+Overview` to confirm structure/keys.
2. **Open `<DOM>+Specification`** for the full variable table. Copy
   Required + Expected; include Permissibles only when the CRF actually
   collects the value.
3. **Open `<DOM>+Assumptions`** for mapping rules. Anchor every non-trivial
   decision in the agent-authored spec to a line from here.
4. **Resolve cross-cutting questions** in Chapter 4 anchors above
   (timing, CT, lengths, naming, missing).
5. **Variable-name suffixes** — if a candidate `--<root>` is needed,
   verify it in `#CDISC+Variable+Naming+Fragments`.
6. **Controlled terminology values** — use the latest CDISC CT package;
   the IG appendix lists which codelist names attach to which variables but
   not the values. The values live in the CT package itself (see CDISC
   Library or NCI EVS).
7. **Splitting / SUPP / RELREC** — before adding non-standard variables,
   read `#When+Not+to+Use+Supplemental+Qualifiers`. Splitting rules are in
   `#Splitting+Domains`.

## Forward look: SDTMIG v4.0 / SDTM v2.0 (public review through Apr 2026)

These changes are *not* in scope for this pilot but flag them when agent
output will need to be revisited:

- **No more SUPP-- datasets** — non-standard variables move in-line as NSVs.
- **Multiple Subject Instances (MSI)** support.
- New domains: Event Adjudication (`EA`), Gastrointestinal Findings (`GI`).
- Machine-readable **Variable Groups** in the metadata.
- Webinar slides: `https://www.cdisc.org/sites/default/files/pdf/SDTMIGv4.0_Webinar_Feb2026.pdf`

When the pilot moves past 2026, retest agent specs against v4.0 because
the EA domain replaces the current ad-hoc adjudication path
(Evaluator A / Committee Review forms in this study).

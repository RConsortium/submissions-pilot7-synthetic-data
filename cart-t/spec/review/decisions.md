# Statistical decisions for human review

Status: not reviewed. These are conservative programming decisions for this
test export. They are not an approved SAP. Resolve the blocking queries in
`log/audit.json` before treating the outputs as submission data.

| Topic | Refactored behavior | Reason and review needed |
| --- | --- | --- |
| Source instances | Retain the full ODM key, including event/form repeats and layout | Repeating labs and AEs are separate observations, not presumed corrections. Repeated items inside one true group are refused. |
| Identity | USUBJID = CART-T-PILOT plus native SubjectKey; preserve StudySubjectID in SUBJID | Native subject keys are globally unique in this export. Review this sponsor ID convention before a submission. |
| Site | SITEID is the ProtocolName of the source StudyOID partition | The XML represents seven named centers plus the master study partition. Confirm the partition-to-site registry; administrative master-study subjects are not silently assigned to a center. |
| Country | Missing | Institution names and generic study partitions are insufficient to assign every site country. COUNTRY is a real required-data gap. |
| Consent | RFICDTC uses only Disposition.CONSENTEDDT | Enrollment encounters are not consent dates. Recorded dates are not clamped to earlier activity. Other consent-related raw flags remain available in the source extract. |
| Birth and age | PTBYEAR remains year precision; AGE uses recorded PTAGE | BDAY is a binary source item, not a birth date. No age is calculated without an appropriate reference date. |
| Treatment | Allocation, actual treatment and exposure dates stay missing | PROFILE contains a sex/ethnicity phenotype. No EX records exist. Only two disposition forms say intervention was not received; this does not prove no treatment for every other subject. |
| Randomization | RANDFL means a randomization-workflow PROFILE is present, independent of date availability | This is a provisional workflow proxy. RANDDT is its administrative event-date proxy, not a verified randomization timestamp. STRAT1/STRAT1L carry the phenotype. |
| Populations | ITTCAND is a candidate set; SAFFL=N for lack of documented exposure; EFFFL=N without an approved efficacy definition | AE presence is not safety-population evidence. N does not establish that an individual was never treated. Approve population definitions before analyses. |
| Disposition | Retain explicit disposition information and label randomization workflow evidence explicitly | Do not manufacture consent, eligibility, COMPLETED, SCREEN FAILURE or ONGOING records from form presence or missing PROFILE. EOSSTT is UNKNOWN unless explicit discontinuation is recorded. |
| Coding | AEDECOD and medical-history dictionary coding stay missing without source coding | Uppercased verbatim terms are not MedDRA preferred terms. AEDECOD is a required-data gap. No dictionary or terminology release is certified. |
| Safety contradictions | Preserve original dates, AE outcomes and seriousness criteria | Do not force fatal outcomes/death flags to agree or invent medically important seriousness. Query contradictions. Duration is missing for inverted dates. |
| CM terminology | Decode actual OpenClinica codelists, including numeric legacy codes | Explicitly map documented source spellings and microgram units. Free-text Other units are used only where a declared mapping exists. No dose conversion is performed. |
| Laboratories | Keep every result in its repeated instance; preserve original text and use numeric conversion only when possible | Units follow the archived CRF specification and need confirmation. No scan date replaces a blood-draw date. No fabricated reference ranges or toxicity grades. |
| Questionnaires | Include Q1-Q12 and PF-S, RP-S, BP, GH, VT, SF, RE-S, ME-S | The archive's PF/RP/RE/ME names missed four recorded subscales. Source scores are not validated recomputations of an instrument algorithm. |
| Timing | Normalize declared ISO/US date forms; keep partial precision in SDTM; ADaM dates require full dates | No day/month or century imputation is authorized. A QoL event date is a documented administrative timing proxy. Invalid/absent dates remain missing and reviewable. |
| Baseline and change | ABLFL, BASE, CHG and PCHG remain missing | No documented exposure or approved alternative baseline definition exists. A form named Baseline or an earliest survey is not sufficient. |
| Visits and epochs | Retain source event names; do not turn event-type order into a nominal visit schedule | Repeating unscheduled events are not visits 1, 2, 3, etc. No treatment epoch is invented without treatment timing. |
| First-occurrence flags | Not supplied | Uncoded terms and no approved safety risk window cannot support preferred-term/system-organ-class occurrence analyses. |
| Clinical events | Retain all reported suspected-MI descriptions, including test text and questionable timing | Do not delete records or claim confirmed MI adjudication. Evaluator/committee source forms remain available, but no adjudicated endpoint is inferred. |
| Trial design and TTE | Not generated | The metadata description is not a full protocol/SAP. TA/TE/TS/TI/TV and ADTTE need reviewed design and endpoint definitions. |
| Vital signs | Not generated | Vital-sign demonstrations in the Kitchen Sink form are not clinical VS observations. |

## Define-XML scope

The received archive targets SDTMIG 3.3 and ADaMIG 1.3 but contains incomplete
clinical metadata and data. The refactor retains target core designations
where available and uses yamaa's `historical` metadata profile, `context:
Other`, and Define-XML 2.0. This profile separates metadata declarations from
data-conformance assertions. It does not certify the newly derived datasets.
Explicit executable verifications and the independent audit remain active.

This is necessary to represent required-but-missing COUNTRY and AEDECOD
honestly. Changing them to permissible variables or inventing country/coding
would conceal actual gaps. The review package reports every missing value
in a target mandatory variable. It does not treat schema validity as proof
that the target implementation guides are satisfied.

The native yamaa historical profile does not publish transport. ReadStat
therefore writes the XPT review exports separately. Each cell, label and
declared character width is checked after reading it back. Both generated
Define-XML files are checked with lxml against the retained schema set and
every local artifact link must exist. No independent reference Define-XML
was supplied for CAR-T and no metadata-equivalence claim is made.

## Suggested review order

1. Confirm source scope, subject/site identity and data provenance.
2. Resolve COUNTRY, MedDRA coding and exposure/allocation gaps.
3. Confirm consent, randomization and collection timing; inspect retained
   contradictions using source ordinals and the original-item CSV extracts.
4. Approve populations, baseline, nominal visit windows and endpoints in a SAP.
5. Update executable YAML and metadata, rerun the full pipeline, and review
   record-level differences. Requalify transport and Define-XML.
6. Run independent CDISC conformance validation and obtain human sign-off.

Archived row counts and explanations are generated in `log/audit.json`.
The archive is left unchanged. Matching row counts, including
DM/ADSL, do not imply value agreement.

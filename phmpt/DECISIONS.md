# Owner decisions

The owner's standing decisions that shape what this repository reproduces
and how results are reported. Each entry gives the date, the scope and the
files that carry it. Specs and scripts point here instead of restating the
decision.

Two kinds of decision are kept elsewhere, each with its own date:

- Per-dataset decisions that a difference is a missing input are the
  `decided:` field of each entry in
  [`data/differences.yaml`](https://github.com/elong0527/yamaa_phmpt/blob/main/data/differences.yaml).
- What a reproduced define may write is decided in yamaa, on the issues that
  each [defect of the submitted define](glossary.md#define-defect) links.

The earlier working notes (`<study>/spec/review/`) record the full
session-by-session history behind these entries.

## Data

**JMP-only datasets** (2026-11-22, and again on 2026-11-25). *Scope:* the
40 dataset files PHMPT released only as JMP tables (P301 SDTM and ADaM,
four C4591001 files). On 2026-11-22: no specs were to be built on them until
the conversions were checked. The checks were done by 2026-11-24. On
2026-11-25: no XPT version of the P301 S3, S5 or S80 ADSL or the S3 ADSLSF
is in any Module 5 zip, and an ADSL cannot be built from XPT alone, so the
checked JMP conversions stay the inputs until XPT versions are published.
*Files:* `data/jmp-sources.md`, `scripts/cut_jmp_strings.py`.

## Specs

**P201 Addendum 1 per-protocol columns are carried, not derived**
(2026-11-22). *Scope:* the 26 per-protocol columns of the add1 ADSL (12 PP
flags, 12 reasons, DVBABFL, DVNABFL), and the Day 43 and Baseline
per-protocol cells of the add1 ADIS. They are carried from the submitted add1
datasets (inputs `ADSL_VO` and `ADIS_VO`) because their derivation reads the
manual deviation-review lists (`PP_LIST`, `PP_LIST2`), which Module 5 holds
for Day 57 only. The site lists them as carried columns, which are never
counted as derived. *Files:*
`mrna-1273-p201/s3-add1/spec/yamaa/adsl.yaml`, `adis.yaml`.

**Row identity when no submitted key is unique** (2026-11-23). *Scope:*
datasets in which no combination of submitted variables identifies a row
(C4591001 ADC19EF and ADSYMPT, P301 ASEQ-keyed datasets). The spec derives a
row number over a stated order as the key (`_SEQ` or `ASEQ`), following the
keys rule of yamaa PR #4775. The comparison drops `_SEQ`, or compares the rows
as a multiset. *Files:* the specs' `keys`, `scripts/verify_compare.py`.

**Engine limitations go to yamaa** (2026-11-22). *Scope:* every yamaa
limitation found here. Each one is filed as a yamaa issue with a minimal
synthetic repro of invented data that does not mention this project, the
study or the sponsor. *Files:* `<study>/spec/review/repro/`,
`scripts/define/repro/`.

## Verification

**Comparison rules** (2026-11-22). *Scope:* every study except BNT162-01.
Numbers are compared with a tolerance of 1e-10, and strings are compared
with spaces removed. BNT162-01 is compared strictly. A dataset that matches
only under these rules reads "exact under the comparison rules". *Files:*
`studies.yaml` (`compare`), `scripts/verify_compare.py`.

**Verification by subject partition** (2026-11-23; streamed through disk
from 2026-11-25). *Scope:* datasets too large to run in one piece in 15 GB
(P301 ADAR, ADARSUM, ADEFF; C4591001 ADC19EF, ADFACEVD and others). Running
the unchanged spec on USUBJID partitions and comparing each partition counts
as verifying the full spec. *Files:* `studies.yaml` (`partitions`),
`scripts/verify_compare.py` (`verify_run`).

**Redacted cells** (2026-11-25). *Scope:* a submitted cell holding exactly
`(b)(6)` (FOIA exemption 6, which FDA replaced before release). It is not
compared and is counted per column. A dataset that matches only because of it
reads "exact under the comparison rules", never strict. *Files:*
`scripts/verify_compare.py` (`REDACTED`).

## Reporting

**Matches except missing input** (2026-11-25, named so on 2026-11-26).
*Scope:* differences that come only from an input the release lacks, such
as a licensed dictionary that was not submitted (WHODRUG) or SDTM values FDA
redacted. The spec derives the columns as the program does. The dataset is
reported as "matches except missing input", a category apart from exact, and
only while its differences stay within the declared columns and cell counts.
*Files:* `data/differences.yaml` (`missing_input`),
`scripts/site/collect_results.py`.

**Reproduced on a substitute input** (2026-11-26). *Scope:* datasets whose
spec reads another release's snapshot of a domain this release lacks (the
P301 S5 and S80 datasets built on the S3 FACE). They are reported apart from
"matches except missing input", with the number of subjects that reproduce
exactly: their differences are everything the two snapshots disagree on, not
a few values that cannot be recovered. *Files:* `data/differences.yaml`
(`substitute`, `subjects`), `scripts/site/collect_results.py`.

**Submitted ADaM datasets as inputs** (2026-11-26). *Scope:* a spec may read
another submitted ADaM dataset where the program does (ADARSUM reads ADAR) or
where the release's SDTM cannot supply the program's input (P301 S3 ADSL
reads CM through the submitted ADCM, since the released CM conversion has no
CMSEQ or CMINDC). Each dataset's notes on the site name the submitted ADaM
datasets it reads. *Files:* `scripts/site/collect_results.py`
(`adam_inputs`).

**Program text against its own note** (2026-11-26). *Scope:* where a
program's code and its stated intent disagree and the submitted data follow
the intent, the spec follows the intent and the case is recorded as an open
difference of the program (P301 S3 ADSLSF: two subjects with two screen
failures). *Files:* `data/differences.yaml` (`program_notes`).

**Matches except a defect of the submitted file** (2026-11-27). *Scope:*
differences that come from the submitted file itself, not from the spec or a
missing input: a malformed cell (C4591001 EUA ADMH, one AENDY value written
three times), or rows the released program writes that the file lacks
(C4591001 EUA interim ADC19EF, 1,156 PRCDCSAD rows). The spec follows the
released program. The dataset is reported as "matches except a submitted-file
defect", a category apart from exact and from missing input, and only while
its differences stay within the declared columns and cell counts. *Files:*
`data/differences.yaml` (`submitted_defect`),
`scripts/site/collect_results.py`.

**Defects of the submitted define** (2026-11-27). *Scope:* every define
difference left at yamaa `ac826f0b`, which fixed the last engine gap
(yamaa#5055, #5062). Each is received content that yamaa does not copy by
an owner decision in yamaa: a codelist that repeats an `OrderNumber`, which
the ODM 1.3.2 schema forbids (yamaa#5022); an analysis reason or purpose
outside the published ARM terms, or an empty ARM element (yamaa#4824); and
a method OID ending in a non-breaking space (D398, yamaa#4935). They are
reported as defects of the submitted define, the define's counterpart of
"matches except a defect of the submitted file". Any other difference,
including one an engine gap used to explain, is unexplained. The Define-XML
engine gaps page is retired. *Files:* `scripts/define/compare_define.py`
(`DEFECTS`), `scripts/site/build_pages.py`, `scripts/publish/export.py`.

**No stand-in for a truncated input** (2026-11-27). *Scope:* P301 S3 ADCM,
whose CM input was truncated in the release. The 24 columns it cannot derive
stay a missing input; the values of a later cut (S5 CMSEQ) are not used in
their place, because they would make S3 look reproduced from an input that
was never received. *Files:* `data/differences.yaml` (`missing_input`).

**Holds** (2026-11-25). *Scope:* P201 Day 57 ADARP7D was put on hold on
2026-11-25. The hold was lifted on 2026-11-26 once it reproduced exactly
(150 rows). No dataset is on hold now. *Files:* `data/differences.yaml`
(`hold`).

**Status is generated, not hand-kept.** *Scope:* every result. Since
2026-11-24, `data/reproduction/*.json` is generated from the run reports by
`scripts/reproduce.py site`, and the engine commit is pinned in `yamaa.lock`.
The hand-kept verdict record (`data/status.json`) was retired in
elong0527/yamaa_phmpt#12. This entry records how the repository works, not a
dated owner decision. *Files:*
`data/reproduction/`, `scripts/site/collect_results.py`, `yamaa.lock`.

## Publication

**Publishing to Pilot 7** (2026-11-26). *Scope:* everything that leaves this
repository. Results are published to the public Pilot 7 repository and site
by pull request, under the design in [Publishing to Pilot 7](publication.md),
with its recommendations taken:

- O1: the dataset and helper specs are published, after the publication
  gate. Their submission `method` texts and non-Predecessor origin
  `description` texts are the received define's words, so the published copy
  replaces them with a placeholder; the transcription restates them locally.
- O2: no define is published, received or generated. The comparison counts,
  the defects of the submitted define and the scripts that regenerate it
  from PHMPT are.
- O3: the owner signs off; a pull request to Pilot 7 is sufficient, with no
  further review.
- O4: publication PRs are opened by hand from `scripts/publish/export.py`
  until an automated route is worth its credential.
- O5: reviews are GitHub Discussions in Pilot 7.
- O6: the Pilot 7 section is "PHMPT reproduction".

*Files:* `docs/publication.md`, `scripts/publish/`, `data/sources.csv`
(the received defines' PHMPT members).

# Glossary

The terms the PHMPT reproduction pages use, grouped as a result is read.

## Studies, cuts and specs

### Cut {#cut}

One analysis deliverable of a study as PHMPT released it: the SDTM, the ADaM datasets and usually the define.xml of one eCTD application and sequence, such as *Day 57 analysis (BLA 125752 S3)*. Each cut is a folder `<study>/<cut>/` named after its sequence (`s3-d57`).

### Data-only folder {#data-only-cut}

A released set of data with no specs yet (`data_cuts` in `studies.yaml`). No result is reported for it.

### Spec {#spec}

The yamaa specification of one ADaM dataset (`<cut>/spec/yamaa/<dataset>.yaml`): its inputs, intermediate tables, keys and the derivation of every column. It is the executable reproduction.

### Layer (parent) {#layer}

A spec can name another spec as its `parent:` and state only what differs. Every spec builds on the study's base layer (`spec/yamaa/base/`), and a later cut's spec is usually a layer over the earlier cut's spec of the same dataset. A layer can add or replace columns but cannot remove one, so a later spec that drops columns builds on the base layer only (`standalone` in `studies.yaml`).

### Helper spec {#helper-spec}

A spec for an intermediate table that a dataset spec reads (`spec/yamaa/helper/`). `verify` runs it first.

### Partition {#partition}

A large dataset runs in USUBJID partitions streamed through disk, so that every spec runs in 15 GB of memory (`partitions` in `studies.yaml`). The spec is unchanged; each partition is compared with the same subjects of the submitted dataset, and together they count as verifying the whole spec.

## Dataset results

### Comparison rules {#comparison-rules}

How a study's datasets are compared (`compare` in `studies.yaml`): rows are matched on the dataset's keys; numbers are equal within 1e-10 and strings are compared with spaces removed (every study but BNT162-01, which is compared strictly); a submitted cell redacted to `(b)(6)` is not compared.

### Exact {#exact}

yamaa's output equals the submitted dataset cell for cell: same rows, same columns, same values.

### Exact under the comparison rules {#exact-under-rules}

Equal once the comparison rules are applied, but not strictly equal: some numbers differ by less than 1e-10, some strings only by spaces, or some submitted cells are redacted to `(b)(6)`. Counted as exact.

### (b)(6) redacted cell {#redacted}

A submitted value FDA replaced with `(b)(6)` (FOIA exemption 6, personal privacy) before release. It is not compared and is counted per column. When FDA redacted an SDTM value, the ADaM values derived from it cannot be recovered: see missing input.

### Matches except missing input {#missing-input}

Every difference comes from an input the release lacks: a licensed dictionary that was not submitted (WHODRUG), a sponsor file the program reads, or SDTM values FDA redacted. The spec derives the columns as the program does. The verdict holds only while the differences stay within the columns and cell counts recorded for that input (`data/differences.yaml`), and it is reported apart from exact.

### Reproduced on a substitute input {#substitute-input}

The release lacks a domain, so the spec reads another release's snapshot of it. The differences are everything the two snapshots disagree on, so they are reported apart from missing input, with the number of subjects that reproduce exactly.

### Open (N cells differ) {#open}

The dataset still differs and the cause is still to fix. The study page gives the diagnosed cause of each difference.

### No recorded reason yet {#no-reason}

A differing column that no entry of `data/differences.yaml` covers. It stays open until one does.

### Not checked {#not-checked}

The spec could not be run or compared (for example, its submitted dataset is not in the release).

### Carried column {#carried}

A column copied from the submitted dataset instead of derived, because the input it is derived from is not in the release. Carried columns are listed on the study page and never counted as derived.

### Submitted ADaM dataset as input {#adam-input}

A spec may read another submitted ADaM dataset where the program does, or where the released SDTM cannot supply the program's input. The dataset's notes name it.

### Program and submitted file disagree {#program-note}

The released program's text and the submitted file disagree: the file was not produced by the program as released, or the program contradicts its own stated intent (the spec then follows the intent). Recorded as a note; it does not change the verdict.

### On hold {#hold}

A dataset the owner has put on hold; its result is shown with the hold noted.

## Define-XML

### Received define {#received-define}

The `define-adam.xml` of a cut as PHMPT released it. It is not published; `fetch` reads it from PHMPT.

### Reproduced-mode layer {#reproduced-mode-layer}

A metadata layer over a cut's specs (`<cut>/spec/define/`): what the received define declares that the specs do not carry, such as labels, methods, comments, codelists, value-level metadata, OIDs and order. `transcribe_define.py` writes it from the received define, so it holds only the received text and is not published; `define --transcribe` writes it again. yamaa composes the define from the specs and this layer.

### Element {#element}

An OID-bearing part of a define: a dataset (ItemGroupDef), variable (ItemDef), method, comment, codelist, value list, where clause, document or result display. Defines are compared element by element.

### Engine gap (G1, G2, ...) {#engine-gap}

A define difference yamaa cannot avoid yet, because the received file declares something yamaa's reproduced mode cannot express (G1: codelist order numbers that ODM forbids). Each gap has a yamaa issue with a synthetic reproduction ([engine gaps](findings/define-gaps.md)). An element that differs only by gaps counts as reproduced apart from engine gaps.

### No spec yet {#no-spec}

A dataset the received define describes but that has no spec here. Its elements are counted apart and are not compared.

### Unexplained difference {#unexplained}

A define difference that is neither an engine gap nor an element of a dataset with no spec.

## Inputs

### JMP-only input {#jmp-only}

A file PHMPT released only as a JMP table, not as a SAS transport file. JMP's format has no open reader, so the kit cannot fetch it ([Reproduce](reproduce.md#jmp)).

### Study-level lists {#study-lists}

Spreadsheets the C4591001 programs read (subject lists, term lists, a BMI scale), released as .xlsx. `scripts/convert_lists.py` copies their cells to `c4591001/data/lists/`.

# Define-XML engine gaps

Every difference between a composed define and the received one is either one of these gaps, something yamaa's reproduced mode cannot declare yet, or an element of a dataset that has no spec in this repo. Each gap has a yamaa issue with a synthetic reproduction ([`scripts/define/repro/`](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt/scripts/define/repro)).

| Gap | mRNA-1273-P201 s3-d57 | mRNA-1273-P201 s3-add1 | mRNA-1273-P301 s3 | mRNA-1273-P301 s5 | mRNA-1273-P301 s80 | BNT162-01 27034 | BNT162-01 125742 | C4591001 s1 | C4591001 s211-1mth | C4591001 s135 | C4591001 s211-6mth | C4591001 s6 | C4591001 s1-safety-fa-eff | yamaa issue |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **G1** Received codelist `OrderNumber`s that ODM forbids (repeated, or 0) | 24 | 24 | 50 | 36 | - | 10 | 11 | - | - | - | - | - | - | [yamaa#4846](https://github.com/elong0527/yamaa/issues/4846) |
| **G2** Value-level `ItemDef` name and OID (fixed by yamaa#4885) | - | - | - | - | - | - | - | - | - | - | - | - | - | [yamaa#4847](https://github.com/elong0527/yamaa/issues/4847) |
| **G3** Received `WhereClauseDef` OIDs and sharing (fixed by yamaa#4885) | - | - | - | - | - | - | - | - | - | - | - | - | - | [yamaa#4848](https://github.com/elong0527/yamaa/issues/4848) |
| **G4** One-value `IN`/`NOTIN` (fixed by yamaa#4885) | - | - | - | - | - | - | - | - | - | - | - | - | - | [yamaa#4849](https://github.com/elong0527/yamaa/issues/4849) |
| **G5** `xml:lang` scope (fixed by yamaa#4885) | - | - | - | - | - | - | - | - | - | - | - | - | - | [yamaa#4850](https://github.com/elong0527/yamaa/issues/4850) |
| **G6** Analysis-results values outside what ARM declarations admit | 3 | 3 | 8 | - | - | - | - | - | - | - | - | - | - | [yamaa#4824](https://github.com/elong0527/yamaa/issues/4824) |
| **G7** An empty `CheckValue` (fixed by yamaa#4885) | - | - | - | - | - | - | - | - | - | - | - | - | - | [yamaa#4849](https://github.com/elong0527/yamaa/issues/4849) |
| **G8** A method OID ending in a non-breaking space, or a MetaDataVersion OID with a comma | - | - | - | - | - | - | - | 2 | 2 | 2 | 2 | - | 1 | [yamaa#4853](https://github.com/elong0527/yamaa/issues/4853) |
| **G9** A codelist no column binds is never written (fixed by yamaa#4937) | - | - | - | - | - | - | - | - | - | - | - | - | - | [yamaa#4887](https://github.com/elong0527/yamaa/issues/4887) |

Counts are differing attributes or references, not elements. One codelist with ten items differs ten times under G1.

## What each gap is

**G1. Codelist item order.** Received `CodeList` items carry `OrderNumber`. yamaa keeps the declared item order but never writes the attribute (DEFINE-20).

**G2. Value-level item names and OIDs.** Pinnacle 21 names a per-value `ItemDef` after its whole suffix (`AVAL.ADFACEVD.PARAMCD.EQ.<hash>`) and, in P301 S3, spells two `ADT` entries after `AVAL`. yamaa writes the column name and `IT.<dataset>.<column>.<entry>`.

**G3. Where-clause OIDs.** The received files write `WC.<dataset>.<where>.<hash>` once and share it across columns. yamaa writes one where clause per entry. Their contents are reproduced; only identifiers and sharing differ.

**G4. One-value `IN`/`NOTIN`.** Pinnacle 21 joined a list into one `CheckValue` (`ERYTHDIA SWELLDIA`).

**G5. `xml:lang`.** P201 add1 and P301 S3 (Pinnacle 21 Enterprise 5.x) write none; P201 d57 leaves it off its analysis-results descriptions.

**G6. Analysis results.** Purposes and reasons outside the published values (`PRIMARY OUTCOME&#xA;MEASURE`, `SAP`, `Primary Endpoints`), and empty `Documentation` and `ProgrammingCode` elements. The owner's decision on yamaa#4824 keeps the published values.

**G7. Empty `CheckValue`.** BNT162-01 compares `SRCVAR`/`AVALCAT1` to an empty value.

**G8. Identifiers.** C4591001 names two documents `LF.201114-...` (a document id starting with a digit) and one method `MT.ADCM.ONPERFL` + U+00A0 (a non-breaking space).

**G9. Unbound codelist.** P301 declares `CL.MedDRA`, which no column references. yamaa wrote only codelists that a column binds (CT-10) until yamaa#4937; the transcription now declares it in the dataset's `submission: {codelists: [...]}`.

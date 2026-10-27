# Source provenance and coverage

The build stages `data/odm/car-t-openclinica.xml` byte-identically from the retained
`.archieve/cart-t/car-t-openclinica.xml`. It is an OpenClinica ODM 1.3 snapshot,
FileOID `All_Data_TestD20251028144002+0000`, created 2025-10-28, protocol
`CART2020`. It contains 810 subjects, 48,557 items and 8,959 item-group
instances across eight StudyOID partitions and 17 populated forms.

The archive is the single committed source XML. No duplicate is committed in
the root study. `program/odm/prepare.py` stages the original and creates a temporary
reader copy by changing only the ASCII encoding declaration to UTF-8; the
source consists of ASCII bytes and character entity references. Clinical
characters and values are unchanged. SDTM specifications read that XML directly.
Native `odm` expressions and grouped rows perform clinical item reshaping;
item-level findings use the full native XML item table. A second XML input
alias provides extended context such as source ordinals and event labels.
An independent ElementTree walk compares every source item, in source order,
against the native item Parquet during the full build. The Parquet is QC
evidence, not a clinical derivation input.

The archive's R programs and YAML are historical mapping evidence. The new
clinical derivations use the XML and new executable specifications, not archived
RDS or XPT values. The audit reads archived XPT for row-count comparisons;
the issue #98 verifier reads them to reproduce the reported quality findings.
Neither uses archived values as clinical derivation inputs.
OpenClinica CodeList definitions in the XML resolve CM codes and terminology
spellings. Laboratory fixed units follow the archived LB form specification
and are flagged for confirmation.

| Populated form | Refactor coverage |
| --- | --- |
| Eligibility | DM recorded demographics/age and IE explicit failed evaluations; all other items remain in native item evidence |
| 1. Demographics and History | DM and general/cancer MH records |
| 2. Baseline Labs and Imaging | LB laboratory results and blood-draw timing; imaging is retained in source |
| 3. Randomize | SUPPDM phenotype and explicitly labeled DS workflow evidence |
| 4. View Randomization Assignment | Retained in source; not treated as an independent allocation record |
| Adverse Event | AE records from AE groups; medication-link groups remain in source |
| ConMed | CM records, including reported/free-text treatment-name fallback |
| Lab Results | LB with complete event repeats and instance-specific collection dates |
| RAND SF-12 Survey | QS 12 responses and eight recorded subscales; helper calculations are not extra clinical tests |
| Suspected MI | CE verbatim reported events; panels and attachments remain in source |
| Disposition | Explicit DS disposition evidence and DM recorded consent date |
| Evaluator A | Retained in source; no confirmed adjudicated endpoint is inferred |
| Committee Review | Retained in source; recorded status is not a confirmed endpoint |
| RxNorm Coding | Retained as a coding-workflow source; no unproven cross-form record linkage |
| Source Document | Retained source metadata/attachment names |
| In-clinic Photo | Retained source metadata/attachment names |
| Kitchen Sink | Retained for audit; demo widgets excluded from clinical domains |

The full build writes a source inventory and `data/odm/items.parquet`, retaining
original ItemOID, ItemName, SourceOrdinal, values and null/presence indicators.
Executable item reads name exact ItemOIDs; source names are not normalized
into CSV column names. The preparation checks refuse duplicate items and
distinct metadata versions/form layouts that share one native ODM hierarchy,
so an unsupported source expansion cannot silently collapse observations.

No full clinical protocol, SAP, licensed coding dictionary, controlled lab
transfer specification, or independently published CAR-T Define-XML is
available in the archive. The overview in ODM metadata is not a substitute.
See `spec/review/decisions.md` for the resulting scope and review questions.

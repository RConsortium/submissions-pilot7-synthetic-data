# Source provenance and coverage

`data/odm/car-t-openclinica.xml` is byte-identical to the retained
`.archieve/cart-t/car-t-openclinica.xml`. It is an OpenClinica ODM 1.3 snapshot,
FileOID `All_Data_TestD20251028144002+0000`, created 2025-10-28, protocol
`CART2020`. It contains 810 subjects, 48,557 items and 8,959 item-group
instances across eight StudyOID partitions and 17 populated forms.

The original XML is not rewritten. `program/odm/extract.py` creates a temporary
reader copy by changing only the ASCII encoding declaration to UTF-8; the
source consists of ASCII bytes and character entity references. Clinical
characters and values are unchanged. yamaa.read_odm reads that copy.
An independent ElementTree walk compares every source item, in source order,
against the native item table during the full build.

The archive's R programs and YAML are historical mapping evidence. The new
clinical derivations use the XML and new executable specifications, not archived
RDS or XPT values. Archived XPT files are read only for row-count comparisons.
OpenClinica CodeList definitions in the XML resolve CM codes and terminology
spellings. Laboratory fixed units follow the archived LB form specification
and are flagged for confirmation.

| Populated form | Refactor coverage |
| --- | --- |
| Eligibility | DM recorded demographics/age and IE explicit failed evaluations; all other items remain in source extracts |
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

The full build writes a per-form item/group/subject inventory and an item
dictionary under `data/odm/`. The dictionary connects normalized CSV column
names to original FormOID, ItemGroupOID, ItemOID and ItemName. Original
source item names and values also remain in `items.csv`.

No full clinical protocol, SAP, licensed coding dictionary, controlled lab
transfer specification, or independently published CAR-T Define-XML is
available in the archive. The overview in ODM metadata is not a substitute.
See `spec/review/decisions.md` for the resulting scope and review questions.

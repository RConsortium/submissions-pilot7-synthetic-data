# derive_lb.R — LB (Laboratory). Folds every quantitative assay-on-specimen CRF
# into the long SDTM LB structure, with LBSPEC (specimen) and LBLOC (skin
# compartment) distinguishing the antimicrobial-peptide readouts:
#   - serum panel (LB CRF): vitamin-D metabolism, renal, immunology  [SCRN, D21]
#   - skin biopsy (SB CRF): CAMP/HBD3/IL13/IL4 mRNA, lesional/non-lesional [BASE, D21]
#   - saliva (SA CRF): salivary cathelicidin protein                 [BASE, D21]
#   - tape strip (TS CRF): tape-strip cathelicidin, by compartment    [BASE, D21]
# SA/TS carry no collection date, so LBDTC is reconstructed from the visit offset.

.LB_SERUM <- tibble::tribble(
  ~col,        ~LBTESTCD, ~LBTEST,                 ~LBORRESU, ~LBCAT,
  "VITD25OH",  "VITD25OH","25-Hydroxyvitamin D",   "ng/mL",   "CHEMISTRY",
  "CALCIUM",   "CA",      "Calcium",               "mg/dL",   "CHEMISTRY",
  "PTH",       "PTH",     "Parathyroid Hormone",   "pg/mL",   "CHEMISTRY",
  "CREAT",     "CREAT",   "Creatinine",            "mg/dL",   "CHEMISTRY",
  "IGE",       "IGE",     "Immunoglobulin E",      "kU/L",    "IMMUNOLOGY",
  "RAST",      "RAST",    "RAST Class",            "",        "IMMUNOLOGY"
)

.LB_BIOPSY <- tibble::tribble(
  ~col,   ~LBTESTCD, ~LBTEST,                  ~LBCAT,
  "CAMP", "CAMP",    "Cathelicidin mRNA",      "GENE EXPRESSION",
  "HBD3", "HBD3",    "Beta-Defensin 3 mRNA",   "GENE EXPRESSION",
  "IL13", "IL13",    "Interleukin 13 mRNA",    "GENE EXPRESSION",
  "IL4",  "IL4",     "Interleukin 4 mRNA",     "GENE EXPRESSION"
)

derive_lb <- function() {
  ref <- ref_dates()

  serum <- read_form("LB") |>
    pivot_longer(all_of(.LB_SERUM$col), names_to = "col", values_to = "LBORRES") |>
    filter(LBORRES != "") |>
    inner_join(.LB_SERUM, by = "col") |>
    transmute(USUBJID, VISIT_CD = VISIT, LBDTC, LBTESTCD, LBTEST, LBCAT,
              LBORRES, LBORRESU, LBSPEC = "SERUM", LBLOC = "")

  biopsy <- read_form("SB") |>
    pivot_longer(all_of(.LB_BIOPSY$col), names_to = "col", values_to = "LBORRES") |>
    filter(LBORRES != "") |>
    inner_join(.LB_BIOPSY, by = "col") |>
    transmute(USUBJID, VISIT_CD = VISIT, LBDTC = SBDTC, LBTESTCD, LBTEST, LBCAT,
              LBORRES, LBORRESU = "", LBSPEC = "SKIN BIOPSY", LBLOC = COMPART)

  # Salivary/tape cathelicidin is a PROTEIN readout — a distinct LBTESTCD from the
  # biopsy mRNA so LBTESTCD<->LBTEST stays one-to-one.
  saliva <- read_form("SA") |>
    filter(CAMP_SALIVA != "") |>
    transmute(USUBJID, VISIT_CD = VISIT, LBDTC = "", LBTESTCD = "CAMPPRO",
              LBTEST = "Cathelicidin Protein", LBCAT = "ANTIMICROBIAL PEPTIDE",
              LBORRES = CAMP_SALIVA, LBORRESU = "ng/mL", LBSPEC = "SALIVA", LBLOC = "")

  tape <- read_form("TS") |>
    filter(CAMP_TAPE != "") |>
    transmute(USUBJID, VISIT_CD = VISIT, LBDTC = "", LBTESTCD = "CAMPPRO",
              LBTEST = "Cathelicidin Protein", LBCAT = "ANTIMICROBIAL PEPTIDE",
              LBORRES = CAMP_TAPE, LBORRESU = "ng/mL", LBSPEC = "TAPE STRIP", LBLOC = COMPART)

  out <- bind_rows(serum, biopsy, saliva, tape) |>
    left_join(ref, by = "USUBJID") |>
    join_visit("VISIT_CD") |>
    mutate(
      STUDYID  = STUDYID,
      DOMAIN   = "LB",
      LBDTC    = ifelse(LBDTC == "", add_days(RFSTDTC, .OFFSET), LBDTC),
      LBDY     = study_day(LBDTC, RFSTDTC),
      # Round assay results to a realistic precision so the standardized character
      # and numeric results agree exactly (the simulator emits 17 sig figs, which
      # a float cannot hold -> STRESC != STRESN).
      .num     = suppressWarnings(as.numeric(LBORRES)),
      LBORRES  = ifelse(is.na(.num), LBORRES, as.character(round(.num, 4))),
      LBSTRESC = LBORRES,
      LBSTRESN = ifelse(is.na(.num), "", as.character(round(.num, 4))),
      LBSTRESU = LBORRESU,
      EPOCH    = epoch_of(VISIT),
    ) |>
    select(-.num) |>
    # Baseline flag on single-location specimens only (serum, saliva): exactly one
    # per subject x test x specimen — the last pre/at-baseline record. The skin
    # biopsy/tape biomarkers are measured at two compartments (LBLOC); their
    # baseline-by-location is derived downstream (ADLB), where LBLOC is a proper
    # parameter dimension, so LBBLFL is left blank here (CORE's baseline grouping
    # does not include LBLOC).
    group_by(USUBJID, LBTESTCD, LBSPEC) |>
    arrange(as.integer(VISITNUM), .by_group = TRUE) |>
    mutate(LBBLFL = {
      cand <- which(VISIT %in% c("SCREENING", "BASELINE") & LBORRES != "" & LBLOC == "")
      f <- rep("", n()); if (length(cand)) f[tail(cand, 1)] <- "Y"; f
    }) |>
    ungroup() |>
    arrange(USUBJID, LBSPEC, LBTESTCD, LBLOC, as.integer(VISITNUM)) |>
    add_seq("LBSEQ")

  finalize(out, c(
    "STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBCAT",
    "LBORRES", "LBORRESU", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBSPEC", "LBLOC",
    "LBBLFL", "EPOCH", "VISITNUM", "VISIT", "LBDTC", "LBDY"))
}

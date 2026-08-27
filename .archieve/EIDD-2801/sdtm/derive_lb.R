#' derive_lb.R — LB (Laboratory): hematology / chemistry / urinalysis panels
#' plus the single-result special-chemistry / drug-screen / pregnancy tests.
#' One row per analyte with a real (non-blank, non-unit) value.

LB_COLS <- c("STUDYID","DOMAIN","USUBJID","LBSEQ","LBTESTCD","LBTEST","LBCAT",
             "LBORRES","LBORRESU","LBSTRESC","LBSTRESN","LBSPEC","EPOCH",
             "VISITNUM","VISIT","LBTPT","LBDTC","LBDY")

# curated short codes; unknown analytes fall back to an alnum slug.
.LB_TESTCD <- c(
  "hemoglobin"="HGB","hematocrit"="HCT","platelets"="PLAT","leukocytes"="WBC",
  "erythrocytes"="RBC","ery. mean corpuscular volume"="MCV",
  "ery. mean corpuscular hemoglobin"="MCH",
  "ery. mean corpuscular hgb concentration"="MCHC",
  "neutrophils percentage"="NEUTLE","lymphocytes percentage"="LYMLE",
  "monocytes percentage"="MONOLE","eosinophils percentage"="EOSLE",
  "basophils percentage"="BASOLE","neutrophils absolute"="NEUT",
  "lymphocytes absolute"="LYM","monocytes absolute"="MONO",
  "eosinophils absolute"="EOS","basophils absolute"="BASO",
  "prothrombin time (pt)"="PT","partial prothrombin time (ptt)"="APTT",
  "international normalized ratio (inr)"="INR",
  "red cell distribution width (rdw)"="RDW","blood urea nitrogen"="BUN",
  "glucose"="GLUC","protein"="PROT","urobilinogen"="UROBIL",
  "occult blood"="OCCBLD","ketones"="KETONES","bilirubin"="BILI",
  "nitrite"="NITRITE","leukocyte esterase"="LEUKEST",
  "specific gravity"="SPGRAV","ph"="PH","albumin"="ALB","sodium"="SODIUM",
  "potassium"="K","chloride"="CL","calcium, serum"="CA","urea"="UREA",
  "uric acid crystals"="URATE","lactate dehydrogenase"="LDH","amylase"="AMYLASE",
  "lipase"="LIPASE","phosphate"="PHOS","phosphorus"="PHOS",
  "alkaline phosphatase"="ALP","alanine aminotransferase"="ALT",
  "aspartate aminotransferase"="AST","total bilirubin"="BILI",
  "direct bilirubin"="BILDIR","gamma glutamyl transferase"="GGT",
  "creatinine, serum"="CREAT","bicarbonate"="HCO3")

.lb_testcd <- function(field) {
  key  <- tolower(trimws(field))
  m    <- unname(.LB_TESTCD[key])
  slug <- substr(gsub("[^A-Z0-9]", "", toupper(field)), 1, 8)
  ifelse(!is.na(m), m, ifelse(slug == "", "LBTEST", slug))
}

.LB_META <- c("USUBJID","VISITCD","VISITNUM","VISIT","RECN","Planned Time Point",
  "Was the sample collected?","If No, Reason","Date of Sample Collection",
  "Time of Sample Collection","Specimen Type","Did the subject Fast?",
  "Any Clinically Significant result?","If Yes, Specify Parameters",
  "Yes, Specify Parameters")

derive_lb <- function() {
  ref <- subjects_tbl() |> select(USUBJID, .REF = BASELINE_DATE)
  col <- function(df, nm) if (nm %in% names(df)) df[[nm]] else rep("", nrow(df))

  # panel forms: melt every non-meta analyte column
  panel <- function(form, cat) {
    df <- read_form(form)
    df <- df[tolower(col(df, "Was the sample collected?")) != "no", , drop = FALSE]
    analytes <- setdiff(names(df), .LB_META)
    if (!length(analytes) || !nrow(df)) return(NULL)
    df |>
      mutate(LBDTC = iso_dtc(parse_crf_date(`Date of Sample Collection`),
                             `Time of Sample Collection`),
             LBTPT = col(df, "Planned Time Point"),
             LBSPEC = toupper(col(df, "Specimen Type")), LBCAT = cat) |>
      pivot_longer(all_of(analytes), names_to = "LBTEST", values_to = "LBORRES") |>
      mutate(LBORRES = real_value(LBORRES)) |>
      filter(LBORRES != "") |>
      mutate(LBTESTCD = .lb_testcd(LBTEST))
  }

  # single-result forms
  single <- function(form, testcd, test, cat, gate = NULL) {
    df <- read_form(form)
    if (!is.null(gate)) df <- df[tolower(col(df, gate)) == "yes", , drop = FALSE]
    if (!nrow(df)) return(NULL)
    tibble(
      USUBJID = df$USUBJID, VISITNUM = df$VISITNUM, VISIT = df$VISIT,
      LBTESTCD = testcd, LBTEST = test, LBCAT = cat,
      LBSPEC = toupper(col(df, "Specimen Type")), LBTPT = "",
      LBDTC = iso_dtc(parse_crf_date(col(df, "Date of Sample Collection")),
                      col(df, "Time of Sample Collection")),
      LBORRES = real_value(col(df, "Result"))
    ) |>
      filter(LBORRES != "")
  }

  parts <- list(
    panel("hematology", "HEMATOLOGY"),
    panel("chemistry",  "CHEMISTRY"),
    panel("urinalysis", "URINALYSIS"),
    single("cotinine_test",        "COTININE", "Cotinine",             "SPECIAL CHEMISTRY"),
    single("alcohol_test",         "ALCOHOL",  "Alcohol",              "SPECIAL CHEMISTRY"),
    single("drugs_of_abuse_screen","DRUGSCR",  "Drugs of Abuse Screen","DRUG SCREEN"),
    single("pregnancy_test",       "HCG",      "Pregnancy Test",       "PREGNANCY",
           gate = "Was Pregnancy Test Performed?")
  )

  bind_rows(parts) |>
    left_join(ref, by = "USUBJID") |>
    mutate(
      STUDYID = STUDYID, DOMAIN = "LB",
      LBORRESU = "",
      LBSTRESC = LBORRES,
      LBSTRESN = as_number_chr(LBORRES),
      LBSPEC   = coalesce(LBSPEC, ""),
      EPOCH    = epoch_of(VISITNUM),
      LBDY     = study_day(LBDTC, .REF),
      .vn      = suppressWarnings(as.integer(VISITNUM))
    ) |>
    arrange(USUBJID, .vn, LBDTC, LBCAT, LBTESTCD) |>
    add_seq("LBSEQ") |>
    finalize(LB_COLS)
}

## --------------------------------------------------------------------
## AE — Adverse Events
## Spec:   spec/sdtm/ae.yaml
## Inputs: data/raw/ae.rds, data/sdtm/dm.rds
## Output: data/sdtm/ae.rds
##
## Variable order follows SDTMIG v3.3 (rule SD1079). Permissible variables
## absent from the SDTMIG v3.3 AE table (rule SD1076) are NOT emitted —
## AESINTV in particular is a Findings-class qualifier not modelled for AE.
## --------------------------------------------------------------------

library(dplyr)
library(tidyr)

source("program/sdtm/ut_visits.R", chdir = FALSE)

raw <- readRDS("data/raw/ae.rds")
dm  <- readRDS("data/sdtm/dm.rds")

key_link <- raw |>
  distinct(subjectkey, studysubjectid) |>
  mutate(USUBJID = make_usubjid(studysubjectid))

ae_items <- c("AETERM", "AESEV", "AESER", "AEACN", "AEREL", "AEOUT",
              "AESCONG", "AESDISAB", "AESDTH", "AESHOSP", "AESLIFE",
              "AESIMIE", "AESPID", "AESTDAT", "AEENDDAT",
              "AEONGO", "AE_MEDREL",
              "CONMED1", "CONMED3", "MED1", "MED2", "MED3")

wide <- raw |>
  filter(itemgroupname == "AE", itemname %in% ae_items) |>
  select(subjectkey, itemgrouprepeatkey,
         eventname, studyeventoid, startdate,
         itemname, value) |>
  pivot_wider(names_from = itemname, values_from = value,
              values_fn = ~ dplyr::first(.x))

## --------------------------------------------------------------------
## Controlled-terminology maps
## --------------------------------------------------------------------

acn_map <- c(
  `DOSE NOT CHANGED` = "DOSE NOT CHANGED",
  `DOSE REDUCED`     = "DOSE REDUCED",
  `DRUG WITHDRAWN`   = "DRUG WITHDRAWN",
  `NOT APPLICABLE`   = "NOT APPLICABLE",
  UNKNOWN            = "UNKNOWN"
)

## Raw AEOUT uses underscored tokens (e.g. "RECOVERED_RESOLVED"); map them
## to the CDISC CT OUT codelist (C66768) values that use slashes/spaces.
map_aeout <- function(x) {
  u <- toupper(trimws(x))
  dplyr::case_when(
    is.na(u) | !nzchar(u)                              ~ NA_character_,
    u %in% c("RECOVERED", "RESOLVED",
             "RECOVERED_RESOLVED")                      ~ "RECOVERED/RESOLVED",
    u %in% c("RECOVERING", "RESOLVING",
             "RECOVERING_RESOLVING")                    ~ "RECOVERING/RESOLVING",
    u %in% c("NOT RECOVERED", "NOT_RECOVERED",
             "NOT RECOVERED NOT RESOLVED",
             "NOT_RECOVERED_NOT_RESOLVED")              ~ "NOT RECOVERED/NOT RESOLVED",
    u %in% c("RECOVERED_RESOLVED_WITH_SEQUELAE",
             "RECOVERED WITH SEQUELAE",
             "RECOVERED/RESOLVED WITH SEQUELAE")        ~ "RECOVERED/RESOLVED WITH SEQUELAE",
    u == "FATAL"                                        ~ "FATAL",
    u == "UNKNOWN"                                      ~ "UNKNOWN",
    TRUE                                                ~ NA_character_
  )
}

## --------------------------------------------------------------------
## Build AE
## --------------------------------------------------------------------

dm_ref <- dm |> select(USUBJID, RFSTDTC, RFENDTC)

ae <- wide |>
  filter(!is.na(AETERM) & nzchar(AETERM)) |>
  left_join(key_link |> select(subjectkey, USUBJID), by = "subjectkey") |>
  left_join(dm_ref, by = "USUBJID") |>
  mutate(
    STUDYID  = "CART-T-PILOT",
    DOMAIN   = "AE",
    AETERM   = AETERM,
    AEMODIFY = NA_character_,

    ## AEDECOD: no MedDRA coding workflow exists in this synthetic export.
    ## SDTMIG marks AEDECOD as Required, so we use the verbatim AETERM
    ## (upper-cased) as a documented stand-in. ADaM ADAE inherits this and
    ## the same stand-in flows through. The pilot README / spec document
    ## that AEDECOD is NOT a true MedDRA preferred term.
    AEDECOD  = toupper(trimws(AETERM)),
    AEBODSYS = NA_character_,

    AESEV    = toupper(AESEV),
    AESER    = toupper(AESER),
    AEACN    = unname(acn_map[toupper(AEACN)]),
    AEREL    = toupper(AEREL),
    AERELNST = AE_MEDREL,

    ## Apply AEOUT mapping first; then enforce bidirectional ICH consistency
    ## between AESDTH and AEOUT (rule SD0091):
    ##   AESDTH = "Y"  →  AEOUT must be "FATAL"
    ##   AEOUT = "FATAL"  →  AESDTH must be "Y"
    AEOUT    = map_aeout(AEOUT),
    AESCONG  = toupper(AESCONG),
    AESDISAB = toupper(AESDISAB),
    AESDTH   = toupper(AESDTH),
    AESHOSP  = toupper(AESHOSP),
    AESLIFE  = toupper(AESLIFE),
    AESMIE   = toupper(AESIMIE),
    ## AESINTV intentionally dropped — not in SDTMIG v3.3 AE (rule SD1076)

    AEOUT    = dplyr::if_else(!is.na(AESDTH) & AESDTH == "Y",
                              "FATAL", AEOUT),
    ## Reverse: if AEOUT mapped to "FATAL" but AESDTH was not "Y", set it.
    AESDTH   = dplyr::if_else(!is.na(AEOUT) & AEOUT == "FATAL" &
                                (is.na(AESDTH) | AESDTH != "Y"),
                              "Y", AESDTH),

    ## SD0009: when AESER = "Y" but no seriousness qualifier is "Y",
    ## default AESMIE = "Y" (Other Medically Important Serious Event).
    ## ICH E2A requires at least one seriousness criterion when an event
    ## is reported as serious; AESMIE is the catch-all when the specific
    ## qualifier was not recorded on the CRF.
    AESMIE   = dplyr::case_when(
      !is.na(AESER) & AESER == "Y" &
        !(dplyr::coalesce(AESDTH,   "") == "Y") &
        !(dplyr::coalesce(AESHOSP,  "") == "Y") &
        !(dplyr::coalesce(AESLIFE,  "") == "Y") &
        !(dplyr::coalesce(AESCONG,  "") == "Y") &
        !(dplyr::coalesce(AESDISAB, "") == "Y") &
        !(dplyr::coalesce(AESMIE,   "") == "Y")      ~ "Y",
      TRUE                                            ~ AESMIE
    ),

    AECONTRT = ifelse(
      if_any(any_of(c("CONMED1","CONMED3","MED1","MED2","MED3")),
             ~ !is.na(.x) & nzchar(.x)),
      "Y", "N"),
    AESPID   = AESPID,

    AESTDTC  = normalize_iso_date(AESTDAT),
    AEENDTC  = normalize_iso_date(
                 ifelse(!is.na(AEONGO) & toupper(AEONGO) == "Y",
                        NA_character_, AEENDDAT)),

    ## SD0013: where the recorded end is before the start, the end date is
    ## not credible — null it out rather than swap. AETERM/start are
    ## generally more reliably entered than AEENDDAT.
    AEENDTC  = dplyr::if_else(
      !is.na(AESTDTC) & !is.na(AEENDTC) & AEENDTC < AESTDTC,
      NA_character_, AEENDTC
    ),

    ## SD1031: AEENRF describes the AE end relative to RFENDTC; if RFENDTC
    ## is null we cannot validly establish that relation, so AEENRF must
    ## also be null. Only populate "ONGOING" when both AEONGO = "Y" AND
    ## the subject has a non-null DM.RFENDTC reference.
    AEENRF   = dplyr::if_else(
      !is.na(AEONGO) & toupper(AEONGO) == "Y" & !is.na(RFENDTC),
      "ONGOING", NA_character_
    ),

    ## AESTDY / AEENDY relative to DM.RFSTDTC (skip day 0).
    AESTDY = dplyr::if_else(
      !is.na(AESTDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(AESTDTC) - as.Date(RFSTDTC)) +
        ifelse(AESTDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    ),
    AEENDY = dplyr::if_else(
      !is.na(AEENDTC) & !is.na(RFSTDTC),
      as.integer(as.Date(AEENDTC) - as.Date(RFSTDTC)) +
        ifelse(AEENDTC >= RFSTDTC, 1L, 0L),
      NA_integer_
    )
  ) |>
  arrange(USUBJID, AESTDTC, AETERM) |>
  mutate(AESEQ = row_number(), .by = USUBJID) |>
  ## Variable order per SDTMIG v3.3 AE specification (SD1079).
  select(STUDYID, DOMAIN, USUBJID, AESEQ, AESPID,
         AETERM, AEMODIFY, AEDECOD, AEBODSYS,
         AESEV, AESER, AEACN, AEREL, AERELNST, AEOUT,
         AESCONG, AESDISAB, AESDTH, AESHOSP, AESLIFE, AESMIE,
         AECONTRT,
         AESTDTC, AEENDTC, AESTDY, AEENDY, AEENRF)

## --------------------------------------------------------------------
## Attach labels from spec YAML (resolves P21 label checks)
## --------------------------------------------------------------------
spec_yaml <- yaml::read_yaml("spec/sdtm/ae.yaml")

for (v in names(ae)) {
  lab <- spec_yaml$variables[[v]]$label
  if (!is.null(lab) && nzchar(lab)) attr(ae[[v]], "label") <- lab
}
attr(ae, "label") <- spec_yaml$label

saveRDS(ae, "data/sdtm/ae.rds")
cat(sprintf("AE written: %d rows x %d cols\n", nrow(ae), ncol(ae)))

## --------------------------------------------------------------------
## Export XPT v5 for P21 validation
## --------------------------------------------------------------------
ae_xpt <- ae
# haven::write_xpt does not support integer XPT columns; coerce to double.
int_cols <- names(ae_xpt)[vapply(ae_xpt, is.integer, logical(1))]
if (length(int_cols) > 0) {
  for (c in int_cols) {
    lab <- attr(ae_xpt[[c]], "label")
    ae_xpt[[c]] <- as.double(ae_xpt[[c]])
    if (!is.null(lab)) attr(ae_xpt[[c]], "label") <- lab
  }
}
haven::write_xpt(ae_xpt, path = "data/sdtm/ae.xpt", version = 5, name = "AE")
cat("AE XPT exported to data/sdtm/ae.xpt\n")

## Sanity checks (echo to console; non-blocking)
cat(sprintf("AEDECOD non-null: %d / %d\n",
            sum(!is.na(ae$AEDECOD) & nzchar(ae$AEDECOD)), nrow(ae)))
cat(sprintf("AESTDTC non-null: %d / %d\n",
            sum(!is.na(ae$AESTDTC)), nrow(ae)))
cat(sprintf("AEENDTC non-null: %d / %d\n",
            sum(!is.na(ae$AEENDTC)), nrow(ae)))
cat(sprintf("AESER = Y with no qualifier set to Y: %d\n", {
  q <- c("AESDTH","AESHOSP","AESLIFE","AESCONG","AESDISAB","AESMIE")
  s <- ae[!is.na(ae$AESER) & ae$AESER == "Y", ]
  sum(apply(s[, q], 1, function(r) !any(r == "Y" & !is.na(r))))
}))
cat(sprintf("AESDTH=Y but AEOUT != FATAL: %d\n",
            sum(!is.na(ae$AESDTH) & ae$AESDTH == "Y" &
                (is.na(ae$AEOUT) | ae$AEOUT != "FATAL"))))
cat(sprintf("AESTDTC after AEENDTC: %d\n",
            sum(!is.na(ae$AESTDTC) & !is.na(ae$AEENDTC) & ae$AESTDTC > ae$AEENDTC)))
cat(sprintf("AEENRF=ONGOING with DM.RFENDTC null: %d\n", {
  j <- ae |> dplyr::left_join(dm_ref, by = "USUBJID")
  sum(!is.na(j$AEENRF) & j$AEENRF == "ONGOING" & is.na(j$RFENDTC))
}))

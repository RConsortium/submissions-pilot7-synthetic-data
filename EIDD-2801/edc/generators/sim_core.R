#' =============================================================================
#' EIDD-2801-1001-UK Simulator - Shared Engine
#' =============================================================================
#' Form-agnostic machinery shared by every per-domain module:
#'   - patient profile sampling
#'   - the generic CRF form-filler (driven by field names + conditional cascade)
#'   - value generators (numeric / unit / yes-no / lab ranges / urinalysis)
#'   - SDTM helpers (visit parsing, ISO dates, study day, unit suppression, ...)
#'
#' Ported from simulate_patient_cases.py + cases_to_sdtm.py (Python).
#' =============================================================================

Sys.setlocale("LC_TIME", "C")  # ensure English month abbreviations (%b -> Jan)

.SIM_ENV <- new.env(parent = emptyenv())  # holds run-wide FORM_TP_CHOICE

# ----------------------------- RNG helpers -----------------------------

rnd_unif   <- function(lo, hi) stats::runif(1, lo, hi)
rnd_int    <- function(lo, hi) if (lo == hi) lo else sample(lo:hi, 1)
rnd_prob   <- function(p)      stats::runif(1) < p
rnd_choice <- function(x)      x[[sample.int(length(x), 1)]]
rnd_weight <- function(vals, w) vals[[sample.int(length(vals), 1, prob = w)]]

fmt_num <- function(x, dec) formatC(x, format = "f", digits = dec)

`%||%` <- function(a, b) if (is.null(a)) b else a

# ----------------------------- Template loading -----------------------------

#' Read a CRF template JSON -> list of list(field=chr, values=chr vector)
load_template <- function(path) {
  spec <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  lapply(spec, function(e) {
    vals <- e$values
    vals <- if (is.null(vals)) character(0) else as.character(unlist(vals))
    list(field = e$field, values = vals)
  })
}

template_field <- function(template, field_name) {
  for (e in template) if (identical(e$field, field_name)) return(e)
  NULL
}

# ----------------------------- Patient profile -----------------------------

make_patient <- function(pid, study_formulation, study_dose_mg) {
  sex <- rnd_choice(c("Male", "Female"))
  age <- rnd_int(SIM_CONFIG$age_min, SIM_CONFIG$age_max)
  childbearing <- (sex == "Female") && (age < 50) && rnd_prob(0.75)
  baseline <- Sys.Date() - rnd_int(180, 540)
  dose_dt <- as.POSIXct(
    sprintf("%s %02d:%02d:00", format(baseline, "%Y-%m-%d"),
            rnd_int(8, 10), rnd_int(0, 59)), tz = "UTC")
  list(
    pid = pid, sex = sex, childbearing = childbearing, age = age,
    weight_kg = round(rnd_unif(55, 95), 1),
    height_cm = round(rnd_unif(155, 195), 1),
    baseline_date = baseline, dose_datetime = dose_dt,
    formulation = study_formulation, dose_mg = study_dose_mg,
    race = rnd_choice(SIM_CONFIG$races),
    ethnic = rnd_choice(SIM_CONFIG$ethnics),
    eligible = rnd_prob(SIM_CONFIG$eligible_prob)
  )
}

# ----------------------------- Time-point parsing -----------------------------

parse_timepoint_hours <- function(tp) {
  s <- tolower(trimws(tp))
  if (grepl("pre dose", s) || grepl("pre-dose", s)) return(-0.5)
  m <- regmatches(s, regexec("([0-9]+(?:\\.[0-9]+)?)\\s*(?:to\\s*[0-9.]+\\s*)?h\\s*post", s, perl = TRUE))[[1]]
  if (length(m) >= 2) return(as.numeric(m[2]))
  NA_real_
}

datetime_for_timepoint <- function(tp, patient, visit_offset) {
  visit_date <- patient$baseline_date + visit_offset
  hours <- parse_timepoint_hours(tp)
  if (visit_offset == 0 && !is.na(hours)) {
    jitter <- rnd_int(-10, 10)
    return(patient$dose_datetime + hours * 3600 + jitter * 60)
  }
  as.POSIXct(sprintf("%s %02d:%02d:00", format(visit_date, "%Y-%m-%d"),
                     rnd_int(7, 10), rnd_int(0, 59)), tz = "UTC")
}

# ----------------------------- Value generators -----------------------------

is_unit <- function(s) {
  sl <- tolower(s)
  any(vapply(UNIT_KEYWORDS, function(k) grepl(k, sl, fixed = TRUE), logical(1)))
}

gen_unit_value <- function(unit, field_name) {
  fn <- tolower(field_name); ul <- tolower(unit)
  if (grepl("mmhg", ul)) {
    if (grepl("systolic", fn)) return(as.character(rnd_int(105, 135)))
    if (grepl("diastolic", fn)) return(as.character(rnd_int(65, 90)))
    return(as.character(rnd_int(70, 130)))
  }
  if (grepl("beats", ul))   return(as.character(rnd_int(55, 90)))
  if (grepl("breaths", ul)) return(as.character(rnd_int(12, 20)))
  if (grepl("kg", ul))      return(fmt_num(rnd_unif(55, 95), 1))
  if (grepl("cm", ul))      return(fmt_num(rnd_unif(155, 195), 1))
  if (grepl("fahrenheit", ul)) return(fmt_num(rnd_unif(97.2, 99.3), 1))
  if (grepl("celsius", ul))    return(fmt_num(rnd_unif(36.2, 37.4), 1))
  fmt_num(rnd_unif(0, 100), 1)
}

gen_numeric_for_field <- function(field_name) {
  fn <- tolower(field_name)
  if (!is.null(LAB_NUMERIC_RANGES[[fn]])) {
    r <- LAB_NUMERIC_RANGES[[fn]]
    return(fmt_num(rnd_unif(r[[1]], r[[2]]), r[[3]]))
  }
  ordered <- NUMERIC_BY_FIELD_NAME[order(-vapply(NUMERIC_BY_FIELD_NAME,
                                                 function(x) nchar(x[[1]]), integer(1)))]
  for (r in ordered) {
    if (grepl(r[[1]], fn, fixed = TRUE)) return(fmt_num(rnd_unif(r[[2]], r[[3]]), r[[4]]))
  }
  NULL
}

gen_urinalysis_value <- function(field_name) {
  tab <- URINALYSIS_VALUES[[tolower(trimws(field_name))]]
  if (is.null(tab)) return(NULL)
  rnd_weight(tab[[1]], tab[[2]])
}

gen_yes_no <- function(field_name) {
  fn <- tolower(trimws(field_name))
  if (any(startsWith(fn, c("was ", "were ", "did ", "has ", "is "))))
    return(if (rnd_prob(0.96)) "Yes" else "No")
  if (grepl("study drug taken", fn)) return(if (rnd_prob(0.97)) "Yes" else "No")
  if (grepl("clinically significant", fn)) return(if (rnd_prob(0.92)) "No" else "Yes")
  if (grepl("dose adjusted", fn) || grepl("adjusted from planned", fn))
    return(if (rnd_prob(0.96)) "No" else "Yes")
  if (grepl("fasted", fn)) return(if (rnd_prob(0.96)) "Yes" else "No")
  rnd_choice(c("Yes", "No"))
}

# ----------------------------- Field overrides -----------------------------

field_value_override <- function(field_name, form_stem, patient) {
  fn <- tolower(trimws(field_name))
  if (fn == "temperature unit") return("Degree Celsius")
  if (fn == "temperature location") return(rnd_choice(c("Axilla", "Ear", "Oral Cavity")))
  if (fn %in% c("volume units", "planned volume units")) return("mL")
  if (fn %in% c("dose units", "planned dose units")) return("Milligram")
  if (fn == "route") return("Oral")
  if (fn == "formulation") return(patient$formulation)
  if (fn == "dose") return(as.character(patient$dose_mg))
  if (fn == "planned dose") return(as.character(patient$dose_mg))
  if (fn == "specimen type") {
    if (grepl("hematology", form_stem)) return("Blood")
    if (grepl("pregnancy", form_stem)) return(rnd_choice(c("Urine", "Urine", "Serum")))
  }
  if (fn == "result" && grepl("pregnancy", form_stem)) {
    if (patient$sex == "Female" && patient$childbearing)
      return(if (rnd_prob(0.99)) "Negative" else "Positive")
    return("Negative")
  }
  if (fn == "result" && (grepl("cotinine", form_stem) || grepl("drugs_of_abuse", form_stem)))
    return(if (rnd_prob(0.97)) "Negative" else "Positive")
  if (fn == "result" && grepl("alcohol", form_stem))
    return(if (rnd_prob(0.98)) "Negative" else "Positive")
  NULL
}

# ----------------------------- Conditional logic -----------------------------

new_rowstate <- function() {
  e <- new.env(parent = emptyenv())
  e$last_yes_no_parent <- NULL      # c(field, value)
  e$last_result <- NULL
  e$last_significance <- NULL
  e$last_clinsig <- NULL
  e$dose_taken <- TRUE
  e$dose_adjusted <- FALSE
  e$drug_administration_form <- FALSE
  e$sex_skipped <- FALSE
  e
}

is_yes_no_parent_field <- function(field_name) {
  fn <- tolower(trimws(field_name))
  any(startsWith(fn, c("was ", "were ", "did ", "has ", "is "))) ||
    grepl("study drug taken", fn)
}

conditional_response <- function(field_name, values, form_stem, patient, state) {
  fn <- tolower(trimws(field_name))

  if (startsWith(fn, "if no") && grepl("reason", fn)) {
    if (state$sex_skipped)
      return(if (patient$sex == "Male") NA_MALE else NA_NOT_FOCP)
    parent <- state$last_yes_no_parent
    if (!is.null(parent) && parent[2] == "No") {
      if (grepl("study drug", tolower(parent[1])) ||
          (state$drug_administration_form && !state$dose_taken))
        return(rnd_choice(REASONS_DRUG_NOT_TAKEN))
      return(rnd_choice(REASONS_PERFORMED_NO))
    }
    return("")
  }
  if (startsWith(fn, "if yes") && (grepl("specify", fn) || grepl("parameters", fn))) {
    if (identical(state$last_clinsig, "Yes") && length(values) > 0) {
      k <- sample.int(min(3, length(values)), 1)
      return(paste(values[sample.int(length(values), k)], collapse = ", "))
    }
    return("")
  }
  if (startsWith(fn, "if abnormal")) {
    if (identical(state$last_result, "Abnormal") && length(values) > 0) {
      ch <- rnd_choice(values); state$last_significance <- ch; return(ch)
    }
    return("")
  }
  if (startsWith(fn, "if clinically significant")) {
    if (identical(state$last_significance, "Clinically Significant"))
      return(rnd_choice(SIGNIFICANCE_COMMENTS))
    return("")
  }
  if (startsWith(fn, "if positive")) {
    if (identical(state$last_result, "Positive") && length(values) > 0) {
      k <- sample.int(min(2, length(values)), 1)
      return(paste(values[sample.int(length(values), k)], collapse = ", "))
    }
    return("")
  }
  if (grepl("reason adjusted", fn))
    return(if (state$dose_adjusted) rnd_choice(REASONS_DOSE_ADJUSTED) else "")
  if (startsWith(fn, "other, specify") || fn == "other specify") return("")
  NULL
}

parent_yes_no_override <- function(field_name, form_stem, patient, state) {
  fn <- tolower(trimws(field_name))
  is_preg_parent <- grepl("pregnancy test", fn) && (grepl("was ", fn) || grepl("were ", fn))
  is_fsh_parent  <- grepl("fsh test", fn) && (grepl("was ", fn) || grepl("were ", fn))
  if (grepl("pregnancy", form_stem) && is_preg_parent) {
    if (patient$sex == "Male" || !patient$childbearing) {
      state$sex_skipped <- TRUE; return("No")
    }
  }
  if (grepl("fsh", form_stem) && is_fsh_parent) {
    if (patient$sex == "Male" || patient$childbearing) {
      state$sex_skipped <- TRUE; return("No")
    }
  }
  NULL
}

# ----------------------------- Per-field dispatcher -----------------------------

fill_field <- function(field_name, values, form_stem, patient, visit_offset,
                       row_dt, state) {
  fn <- tolower(trimws(field_name))

  if (state$drug_administration_form && !state$dose_taken) {
    if (any(vapply(c("date", "time", "fasted", "formulation", "dose", "volume",
                     "route", "adjusted", "subject was"),
                   function(k) grepl(k, fn, fixed = TRUE), logical(1))))
      return("")
  }

  cond <- conditional_response(field_name, values, form_stem, patient, state)
  if (!is.null(cond)) return(cond)

  if (grepl("inclusion/exclusion criterion", fn)) {
    if (patient$eligible || length(values) == 0) return("")
    return(paste(values[sample.int(length(values), min(2, length(values)))],
                 collapse = ", "))
  }

  forced <- parent_yes_no_override(field_name, form_stem, patient, state)
  if (!is.null(forced)) return(forced)

  override <- field_value_override(field_name, form_stem, patient)
  if (!is.null(override)) return(override)

  if (grepl("tick if date falls on the following day", fn))
    return(if (as.Date(row_dt) > as.Date(patient$dose_datetime)) "Yes" else "")

  if (length(values) == 0) {
    if (grepl("urinalysis", form_stem)) {
      cat_v <- gen_urinalysis_value(field_name)
      if (!is.null(cat_v)) return(cat_v)
    }
    num <- gen_numeric_for_field(field_name)
    return(if (!is.null(num)) num else "")
  }

  v0 <- values[1]
  if (v0 == "DD/MMM/YYYY") return(format(as.Date(row_dt), "%d/%b/%Y"))
  if (v0 == "24h clock hour:min") return(format(row_dt, "%H:%M"))

  yn <- tolower(trimws(values))
  if (setequal(yn, c("yes", "no"))) return(gen_yes_no(field_name))

  if (length(values) == 1) {
    sole <- values[1]
    if (is_unit(sole)) return(gen_unit_value(sole, field_name))
    return(sole)
  }
  rnd_choice(values)
}

update_state <- function(field_name, value, state) {
  fn <- tolower(trimws(field_name))
  if (is_yes_no_parent_field(field_name)) {
    state$last_yes_no_parent <- c(field_name, value)
    if (grepl("study drug taken", fn)) state$dose_taken <- (value == "Yes")
    if (grepl("dose adjusted", fn) || grepl("adjusted from planned", fn))
      state$dose_adjusted <- (value == "Yes")
  }
  if (fn == "examination result" || fn == "result") state$last_result <- value
  if (grepl("clinically significant", fn) &&
      (startsWith(fn, "any ") || grepl("any clinically", fn)))
    state$last_clinsig <- value
}

# ----------------------------- Record / form filling -----------------------------

fill_record <- function(template, form_stem, patient, visit_offset, row_dt,
                        row_overrides = list()) {
  state <- new_rowstate()
  if (grepl("study_drug", form_stem) || grepl("drug_placebo_administration", form_stem))
    state$drug_administration_form <- TRUE

  record <- list()
  for (entry in template) {
    field_name <- entry$field
    values <- entry$values
    if (!is.null(row_overrides[[field_name]])) {
      value <- row_overrides[[field_name]]
    } else {
      value <- fill_field(field_name, values, form_stem, patient, visit_offset,
                          row_dt, state)
    }
    record[[field_name]] <- value
    # update_state needs a scalar; for multi-select use first element
    update_state(field_name, if (length(value) > 1) value[1] else value, state)
  }
  record
}

fill_form <- function(template, form_stem, patient, visit_offset) {
  ptp <- template_field(template, "Planned Time Point")
  bse <- template_field(template, "Body System Examined")

  if (!is.null(ptp) && length(ptp$values) > 1) {
    cf <- split_visit_form(form_stem)$form
    chosen_tp <- .SIM_ENV$FORM_TP_CHOICE[[cf]]
    if (is.null(chosen_tp) || !(chosen_tp %in% ptp$values))
      chosen_tp <- if ("Pre dose" %in% ptp$values) "Pre dose" else ptp$values[1]
    row_dt <- datetime_for_timepoint(chosen_tp, patient, visit_offset)
    return(list(fill_record(template, form_stem, patient, visit_offset, row_dt,
                            list("Planned Time Point" = chosen_tp))))
  }

  if (!is.null(bse) && length(bse$values) > 1) {
    visit_date <- patient$baseline_date + visit_offset
    row_dt <- as.POSIXct(sprintf("%s %02d:%02d:00", format(visit_date, "%Y-%m-%d"),
                                 rnd_int(9, 11), rnd_int(0, 59)), tz = "UTC")
    systems <- bse$values
    any_abnormal <- any(vapply(systems, function(s) rnd_prob(0.15), logical(1)))
    overrides <- list("Examination Result" = if (any_abnormal) "Abnormal" else "Normal")
    rec <- fill_record(template, form_stem, patient, visit_offset, row_dt, overrides)
    rec[["Body System Examined"]] <- systems  # multi-select vector
    return(list(rec))
  }

  visit_date <- patient$baseline_date + visit_offset
  row_dt <- as.POSIXct(sprintf("%s %02d:%02d:00", format(visit_date, "%Y-%m-%d"),
                               rnd_int(8, 11), rnd_int(0, 59)), tz = "UTC")
  list(fill_record(template, form_stem, patient, visit_offset, row_dt))
}

# ----------------------------- Run-wide TP choice -----------------------------

setup_form_tp_choice <- function(template_paths) {
  choice <- list()
  for (p in sort(template_paths)) {
    cf <- split_visit_form(tools::file_path_sans_ext(basename(p)))$form
    if (!is.null(choice[[cf]])) next
    spec <- load_template(p)
    ptp <- template_field(spec, "Planned Time Point")
    if (!is.null(ptp) && length(ptp$values) > 1) choice[[cf]] <- rnd_choice(ptp$values)
  }
  .SIM_ENV$FORM_TP_CHOICE <- choice
  choice
}

#' Fill every CRF form for one patient.
#' @return named list: stem -> list of records (each record = named list field->value)
simulate_patient <- function(patient, templates) {
  cases <- list()
  for (stem in names(templates)) {
    vi <- split_visit_form(stem)
    meta <- visit_meta(vi$visit)
    if (is.null(meta$offset) || is.na(meta$offset)) next
    cases[[stem]] <- fill_form(templates[[stem]], stem, patient, meta$offset)
  }
  cases
}

# =============================================================================
# SDTM helpers (shared by forms/ modules)
# =============================================================================

split_visit_form <- function(stem) {
  m <- regmatches(stem, regexec(
    "^(day_(?:minus_[0-9]+|[0-9]+)(?:_eos)?)_([0-9]{2})_(.+)$", stem))[[1]]
  if (length(m) == 4) list(visit = m[2], nn = as.integer(m[3]), form = m[4])
  else list(visit = NA_character_, nn = 99L, form = stem)
}

visit_meta <- function(visit) {
  m <- VISIT_INFO[[visit]]
  if (is.null(m)) list(num = "", label = "", offset = NA) else m
}

chrono_key <- function(stem) {
  vi <- split_visit_form(stem)
  vnum <- visit_meta(vi$visit)$num
  if (identical(vnum, "")) vnum <- 999
  vnum * 100 + vi$nn
}

is_blank <- function(v) {
  if (is.null(v) || length(v) == 0) return(TRUE)
  if (length(v) == 1 && is.character(v)) return(trimws(v) == "")
  FALSE
}

is_unit_token <- function(v) {
  is.character(v) && length(v) == 1 && tolower(trimws(v)) %in% UNIT_TOKENS
}

real_value <- function(v) if (is_blank(v) || is_unit_token(v)) NULL else v

as_number <- function(v) {
  n <- suppressWarnings(as.numeric(v))
  if (length(n) == 1 && !is.na(n)) n else NULL
}

#' First non-blank value among the given field names (case-insensitive).
rec_get <- function(rec, ...) {
  keys <- tolower(names(rec))
  for (n in c(...)) {
    i <- match(tolower(n), keys)
    if (!is.na(i) && !is_blank(rec[[i]])) return(rec[[i]])
  }
  NULL
}

parse_date <- function(s) {
  if (is_blank(s)) return(NULL)
  d <- as.Date(trimws(s), format = "%d/%b/%Y")
  if (is.na(d)) NULL else d
}

iso_dtc <- function(d, time_str = NULL) {
  if (is.null(d)) return("")
  if (!is_blank(time_str)) {
    m <- regmatches(time_str, regexec("^([0-9]{1,2}):([0-9]{2})$", trimws(time_str)))[[1]]
    if (length(m) == 3)
      return(sprintf("%sT%02d:%s", format(d, "%Y-%m-%d"), as.integer(m[2]), m[3]))
  }
  format(d, "%Y-%m-%d")
}

study_day <- function(d, ref) {
  if (is.null(d) || is.null(ref)) return("")
  delta <- as.integer(d - ref)
  if (delta >= 0) delta + 1 else delta
}

#' Build a data.frame from a list of named-list rows with a fixed column order.
rows_to_df <- function(rows, columns) {
  if (length(rows) == 0)
    return(stats::setNames(data.frame(matrix("", 0, length(columns)),
                                      stringsAsFactors = FALSE), columns))
  mat <- lapply(columns, function(col)
    vapply(rows, function(r) {
      v <- r[[col]]
      if (is.null(v) || length(v) == 0) "" else as.character(v)[1]
    }, character(1)))
  df <- stats::setNames(as.data.frame(mat, stringsAsFactors = FALSE), columns)
  df
}

write_domain <- function(df, out_dir, name) {
  utils::write.csv(df, file.path(out_dir, paste0(name, ".csv")),
                   row.names = FALSE, na = "")
  jsonlite::write_json(df, file.path(out_dir, paste0(name, ".json")), pretty = TRUE)
}

#' Iterate a patient's filled records for forms matching `form_match`, in
#' chronological (visit, then within-form) order. Returns a list of
#' list(form, vnum, vlabel, rec) entries — the basis for every domain builder.
iter_domain_records <- function(cases, form_match) {
  stems <- names(cases)
  stems <- stems[order(vapply(stems, chrono_key, numeric(1)))]
  out <- list()
  for (stem in stems) {
    vi <- split_visit_form(stem)
    if (!form_match(vi$form)) next
    meta <- visit_meta(vi$visit)
    for (rec in cases[[stem]]) {
      out[[length(out) + 1]] <- list(form = vi$form, vnum = meta$num,
                                     vlabel = meta$label, rec = rec)
    }
  }
  out
}

usubjid_of <- function(patient) paste0(SIM_CONFIG$study_id, "-", patient$pid)

#' Write one patient's filled cases as cases/<pid>/<stem>.json (ground truth).
write_patient_cases <- function(cases, patient, cases_root) {
  pdir <- file.path(cases_root, patient$pid)
  dir.create(pdir, recursive = TRUE, showWarnings = FALSE)
  for (stem in names(cases)) {
    records <- lapply(cases[[stem]], function(rec) {
      lapply(names(rec), function(f) list(field = f, value = rec[[f]]))
    })
    jsonlite::write_json(records, file.path(pdir, paste0(stem, ".json")),
                         auto_unbox = TRUE, pretty = TRUE)
  }
}

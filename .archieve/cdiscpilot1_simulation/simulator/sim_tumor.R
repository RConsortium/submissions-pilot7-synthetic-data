#' =============================================================================
#' KEYNOTE-868 Simulator - Tumor Assessment (TU, TR, RS)
#' =============================================================================
#' TU = Tumor Identification (lesion location)
#' TR = Tumor Results (measurements over time)
#' RS = Disease Response (per RECIST 1.1)
#' =============================================================================

#' Common tumor locations for endometrial cancer
TUMOR_LOCATIONS <- c(
  "UTERUS", "PELVIS", "LYMPH NODE - PELVIC", "LYMPH NODE - PARA-AORTIC",

  "LUNG", "LIVER", "PERITONEUM", "OMENTUM", "VAGINA"
)

#' Simulate Tumor Identification (TU) domain
#' @param dm DM data frame with internal columns
#' @param config Simulation configuration
#' @return TU data frame
sim_tu <- function(dm, config = SIM_CONFIG) {

  n <- nrow(dm)
  tu_list <- list()

  for (i in 1:n) {
    subj <- dm[i, ]

    # Number of target lesions (1-5 per RECIST)
    n_target <- sample(1:5, 1, prob = c(0.15, 0.30, 0.30, 0.15, 0.10))

    # Number of non-target lesions (0-3)
    n_nontarget <- sample(0:3, 1, prob = c(0.30, 0.35, 0.25, 0.10))

    subj_tu <- list()
    seq_num <- 1

    # Target lesions
    target_locations <- sample(TUMOR_LOCATIONS, n_target, replace = FALSE)
    for (j in 1:n_target) {
      subj_tu[[seq_num]] <- data.frame(
        STUDYID = "KN868",
        DOMAIN = "TU",
        USUBJID = subj$USUBJID,
        TUSEQ = seq_num,
        TULNKID = sprintf("T%d", j),
        TUTESTCD = "TUMIDENT",
        TUTEST = "Tumor Identification",
        TUORRES = target_locations[j],
        TUSTRESC = target_locations[j],
        TULOC = target_locations[j],
        TULAT = sample(c("LEFT", "RIGHT", "BILATERAL", ""), 1),
        TUMETHOD = "CT SCAN",
        TUEVAL = "INVESTIGATOR",
        TUACPTFL = "Y",
        VISITNUM = 1,
        VISIT = "SCREENING",
        TUDTC = subj$.randdt - sample(7:14, 1),
        TUDY = -7,
        stringsAsFactors = FALSE
      )
      seq_num <- seq_num + 1
    }

    # Non-target lesions
    if (n_nontarget > 0) {
      remaining_locations <- setdiff(TUMOR_LOCATIONS, target_locations)
      nontarget_locations <- sample(remaining_locations,
                                     min(n_nontarget, length(remaining_locations)),
                                     replace = FALSE)
      for (j in 1:length(nontarget_locations)) {
        subj_tu[[seq_num]] <- data.frame(
          STUDYID = "KN868",
          DOMAIN = "TU",
          USUBJID = subj$USUBJID,
          TUSEQ = seq_num,
          TULNKID = sprintf("NT%d", j),
          TUTESTCD = "TUMIDENT",
          TUTEST = "Tumor Identification",
          TUORRES = nontarget_locations[j],
          TUSTRESC = nontarget_locations[j],
          TULOC = nontarget_locations[j],
          TULAT = sample(c("LEFT", "RIGHT", "BILATERAL", ""), 1),
          TUMETHOD = "CT SCAN",
          TUEVAL = "INVESTIGATOR",
          TUACPTFL = "Y",
          VISITNUM = 1,
          VISIT = "SCREENING",
          TUDTC = subj$.randdt - sample(7:14, 1),
          TUDY = -7,
          stringsAsFactors = FALSE
        )
        seq_num <- seq_num + 1
      }
    }

    tu_list[[i]] <- do.call(rbind, subj_tu)
  }

  tu <- do.call(rbind, tu_list)

  tu
}

#' Simulate Tumor Results (TR) domain
#' @param dm DM data frame with internal columns
#' @param tu TU data frame
#' @param efficacy Efficacy data (BOR)
#' @param config Simulation configuration
#' @return TR data frame
sim_tr <- function(dm, tu, efficacy, config = SIM_CONFIG) {

  n <- nrow(dm)
  bor <- efficacy$bor

  # Assessment timepoints (every 9 weeks = 63 days per KEYNOTE protocol)
  assess_visits <- c(-7, 63, 126, 189, 252, 315, 378, 441, 504)

  tr_list <- list()

  for (i in 1:n) {
    subj <- dm[i, ]
    subj_bor <- bor[bor$USUBJID == subj$USUBJID, ]$AVALC

    # Get this subject's lesions
    subj_tu <- tu[tu$USUBJID == subj$USUBJID, ]
    target_lesions <- subj_tu[grepl("^T\\d", subj_tu$TULNKID), ]

    if (nrow(target_lesions) == 0) next

    # Determine response trajectory based on BOR
    if (subj_bor == "CR") {
      trajectory <- "complete_response"
    } else if (subj_bor == "PR") {
      trajectory <- "partial_response"
    } else if (subj_bor == "SD") {
      trajectory <- "stable_disease"
    } else {
      trajectory <- "progressive_disease"
    }

    # Determine how many assessments
    max_followup <- as.numeric(config$data_cutoff_date - subj$.randdt)
    subj_visits <- assess_visits[assess_visits <= max_followup]

    subj_tr <- list()
    seq_num <- 1

    # Generate baseline measurements
    baseline_sizes <- list()
    for (j in 1:nrow(target_lesions)) {
      lesion_id <- target_lesions$TULNKID[j]
      baseline_sizes[[lesion_id]] <- runif(1, 15, 80)  # mm
    }

    for (visit_day in subj_visits) {
      visit_idx <- which(assess_visits == visit_day)
      visit_name <- if(visit_day < 0) "SCREENING" else sprintf("WEEK %d", visit_day / 7)

      # Calculate tumor size for each target lesion
      for (j in 1:nrow(target_lesions)) {
        lesion_id <- target_lesions$TULNKID[j]
        baseline <- baseline_sizes[[lesion_id]]

        if (visit_day < 0) {
          # Baseline
          size <- baseline
        } else {
          # On-treatment - size changes based on trajectory
          time_factor <- visit_day / 365  # Years

          if (trajectory == "complete_response") {
            # Rapid shrinkage to 0
            size <- baseline * exp(-3 * time_factor) * runif(1, 0.8, 1.2)
            if (visit_day > 126) size <- 0  # Complete response after ~4 months
          } else if (trajectory == "partial_response") {
            # Shrinkage > 30%
            size <- baseline * (0.5 + 0.2 * exp(-2 * time_factor)) * runif(1, 0.9, 1.1)
          } else if (trajectory == "stable_disease") {
            # Minor fluctuations
            size <- baseline * runif(1, 0.85, 1.15)
          } else {
            # Progressive disease - growth > 20%
            size <- baseline * (1 + 0.5 * time_factor) * runif(1, 1.0, 1.3)
          }
        }

        size <- max(0, size)

        subj_tr[[seq_num]] <- data.frame(
          STUDYID = "KN868",
          DOMAIN = "TR",
          USUBJID = subj$USUBJID,
          TRSEQ = seq_num,
          TRLNKID = lesion_id,
          TRTESTCD = "LDIAM",
          TRTEST = "Longest Diameter",
          TRORRES = round(size, 1),
          TRORRESU = "mm",
          TRSTRESN = round(size, 1),
          TRSTRESU = "mm",
          TREVAL = "INVESTIGATOR",
          TRMETHOD = "CT SCAN",
          VISITNUM = visit_idx,
          VISIT = visit_name,
          TRDTC = subj$.randdt + visit_day + sample(-3:3, 1),
          TRDY = visit_day,
          stringsAsFactors = FALSE
        )
        seq_num <- seq_num + 1
      }
    }

    if (length(subj_tr) > 0) {
      tr_list[[i]] <- do.call(rbind, subj_tr)
    }
  }

  tr <- do.call(rbind, tr_list)

  tr
}

#' Simulate Disease Response (RS) domain
#' @param dm DM data frame with internal columns
#' @param tr TR data frame
#' @param efficacy Efficacy data (BOR)
#' @param config Simulation configuration
#' @return RS data frame
sim_rs <- function(dm, tr, efficacy, config = SIM_CONFIG) {

  n <- nrow(dm)
  bor <- efficacy$bor

  # Assessment timepoints
  assess_visits <- c(63, 126, 189, 252, 315, 378, 441, 504)

  rs_list <- list()

  for (i in 1:n) {
    subj <- dm[i, ]
    subj_bor <- bor[bor$USUBJID == subj$USUBJID, ]$AVALC

    # Determine how many assessments
    max_followup <- as.numeric(config$data_cutoff_date - subj$.randdt)
    subj_visits <- assess_visits[assess_visits <= max_followup]

    if (length(subj_visits) == 0) next

    subj_rs <- list()
    seq_num <- 1

    # Generate response at each timepoint
    prev_response <- "NE"
    confirmed_response <- FALSE

    for (visit_day in subj_visits) {
      visit_idx <- which(assess_visits == visit_day)
      visit_name <- sprintf("WEEK %d", visit_day / 7)

      # Determine response based on trajectory and timing
      if (subj_bor == "PD") {
        # Progressive disease
        if (visit_day <= 63) {
          response <- sample(c("SD", "PD"), 1, prob = c(0.7, 0.3))
        } else {
          response <- "PD"
        }
      } else if (subj_bor == "SD") {
        response <- "SD"
      } else if (subj_bor == "PR") {
        if (visit_day <= 63) {
          response <- sample(c("SD", "PR"), 1, prob = c(0.6, 0.4))
        } else if (visit_day <= 126) {
          response <- "PR"
        } else {
          response <- sample(c("PR", "CR"), 1, prob = c(0.8, 0.2))
        }
      } else {  # CR
        if (visit_day <= 63) {
          response <- sample(c("SD", "PR"), 1, prob = c(0.4, 0.6))
        } else if (visit_day <= 126) {
          response <- sample(c("PR", "CR"), 1, prob = c(0.5, 0.5))
        } else {
          response <- "CR"
        }
      }

      # Overall response (investigator)
      subj_rs[[seq_num]] <- data.frame(
        STUDYID = "KN868",
        DOMAIN = "RS",
        USUBJID = subj$USUBJID,
        RSSEQ = seq_num,
        RSTESTCD = "OVRLRESP",
        RSTEST = "Overall Response",
        RSCAT = "RECIST 1.1",
        RSORRES = response,
        RSSTRESC = response,
        RSEVAL = "INVESTIGATOR",
        VISITNUM = visit_idx,
        VISIT = visit_name,
        RSDTC = subj$.randdt + visit_day + sample(-3:3, 1),
        RSDY = visit_day,
        stringsAsFactors = FALSE
      )
      seq_num <- seq_num + 1

      prev_response <- response
    }

    # Add Best Overall Response record
    subj_rs[[seq_num]] <- data.frame(
      STUDYID = "KN868",
      DOMAIN = "RS",
      USUBJID = subj$USUBJID,
      RSSEQ = seq_num,
      RSTESTCD = "BESTRESP",
      RSTEST = "Best Overall Response",
      RSCAT = "RECIST 1.1",
      RSORRES = subj_bor,
      RSSTRESC = subj_bor,
      RSEVAL = "INVESTIGATOR",
      VISITNUM = 999,
      VISIT = "BEST RESPONSE",
      RSDTC = config$data_cutoff_date,
      RSDY = NA,
      stringsAsFactors = FALSE
    )

    rs_list[[i]] <- do.call(rbind, subj_rs)
  }

  rs <- do.call(rbind, rs_list)

  rs
}

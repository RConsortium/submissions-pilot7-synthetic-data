## Smoke test for ut_load_xml.R against car-t-openclinica.xml.
## Run from project root:  Rscript program/raw/test_load_xml.R

here  <- normalizePath(".")
src   <- file.path(here, "program", "raw", "ut_load_xml.R")
xml_f <- file.path(here, "car-t-openclinica.xml")

source(src, chdir = TRUE)

cat("\nLoading flat form...\n")
t0   <- Sys.time()
flat <- odm_xml_to_df(xml_f)
cat(sprintf("  rows = %d, cols = %d, elapsed = %.2fs\n",
            nrow(flat), ncol(flat),
            as.numeric(difftime(Sys.time(), t0, units = "secs"))))
cat("  column names:\n")
print(names(flat))

cat("\nHead of flat tibble:\n")
print(utils::head(flat, 3))

cat("\nOK\n")

saveRDS(flat,"~/submissions-pilot7-synthetic-data/cart-t/data/raw/flat.rds")

## Split flat by formname and save one .rds per form using short SDTM-style
## slugs. See data/raw/README.md for the long-form descriptions.
out_dir <- "~/submissions-pilot7-synthetic-data/cart-t/data/raw"

form_slug <- c(
  "Eligibility"                      = "ie",
  "1. Demographics and History"      = "dm",
  "2. Baseline Labs and Imaging"     = "lb_bl",
  "3. Randomize"                     = "rand",
  "4. View Randomization Assignment" = "rand_view",
  "RAND SF-12 Survey"                = "qs_sf12",
  "Adverse Event"                    = "ae",
  "ConMed"                           = "cm",
  "RxNorm Coding"                    = "rx_code",
  "Suspected MI"                     = "mi",
  "Evaluator A"                      = "adj_a",
  "Committee Review"                 = "adj_cr",
  "Disposition"                      = "ds",
  "Lab Results"                      = "lb",
  "Source Document"                  = "src",
  "Kitchen Sink"                     = "ks",
  "In-clinic Photo"                  = "photo"
)

sanitize_form <- function(x) {
  x <- tolower(x)
  x <- gsub("[^a-z0-9]+", "_", x)
  x <- gsub("^_+|_+$", "", x)
  x
}

forms <- split(flat, flat$formname)
cat(sprintf("\nSplitting flat into %d form-level .rds files in %s\n",
            length(forms), out_dir))
for (fname in names(forms)) {
  slug <- if (!is.na(form_slug[fname])) unname(form_slug[fname]) else sanitize_form(fname)
  path <- file.path(out_dir, paste0(slug, ".rds"))
  saveRDS(forms[[fname]], path)
  cat(sprintf("  %-40s -> %s (%d rows)\n", fname, basename(path), nrow(forms[[fname]])))
}

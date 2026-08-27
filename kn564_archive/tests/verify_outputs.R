## Verify output integrity
setwd("C:/Users/lengnx/Documents/ipd_sim_examples/kn564")
library(data.table)

# Read key outputs
dm <- fread("output/source/DM.csv")
ae <- fread("output/source/AE.csv")
ex <- fread("output/source/EX.csv")
ep <- fread("output/source/endpoints.csv")
tu <- fread("output/source/TU.csv")
adtte <- fread("output/adam/ADTTE.csv")

cat("=== Data Integrity Checks ===\n\n")

# 1. 994 patients
stopifnot(nrow(dm) == 994)
cat(sprintf("[PASS] DM has %d patients\n", nrow(dm)))

# 2. Arm balance
cat(sprintf("[INFO] Arms: Pembro=%d, Placebo=%d\n",
            sum(dm$ARM == "PEMBROLIZUMAB"), sum(dm$ARM == "PLACEBO")))

# 3. No NA in required fields
stopifnot(all(!is.na(ep$DFS_DAY)))
stopifnot(all(!is.na(ep$OS_DAY)))
stopifnot(all(!is.na(ep$DFS_EVENT)))
stopifnot(all(!is.na(ep$OS_EVENT)))
cat("[PASS] No NAs in endpoint fields\n")

# 4. OS_DAY >= DFS_DAY (death cannot happen before recurrence)
stopifnot(all(ep$OS_DAY >= ep$DFS_DAY))
cat("[PASS] OS_DAY >= DFS_DAY for all patients\n")

# 5. DFS_DAY > 0 and bounded
stopifnot(all(ep$DFS_DAY > 0))
stopifnot(all(ep$DFS_DAY <= 1740))
cat("[PASS] DFS_DAY in valid range (1-1740)\n")

# 6. AE dates are positive
stopifnot(all(ae$AESTDT > 0, na.rm = TRUE))
cat(sprintf("[PASS] All %d AE events have valid start dates\n", nrow(ae)))

# 7. Exposure records have valid cycles
stopifnot(all(ex$CYCLE >= 1 & ex$CYCLE <= 17))
cat(sprintf("[PASS] All %d exposure records have valid cycles (1-17)\n", nrow(ex)))

# 8. ADTTE has 2 records per patient (DFS + OS)
stopifnot(nrow(adtte) == 2 * 994)
cat(sprintf("[PASS] ADTTE has %d records (2 per patient)\n", nrow(adtte)))

# 9. TU imaging visits are properly ordered per patient
tu_ordered <- tu[, .(ordered = all(diff(VISIT_DAY) > 0)), by = SUBJID]
stopifnot(all(tu_ordered$ordered))
cat("[PASS] TU imaging visits are chronologically ordered per patient\n")

# 10. Summary stats
cat("\n=== Summary ===\n")
cat(sprintf("DFS events: %d (pembro %d, placebo %d)\n",
            sum(ep$DFS_EVENT), sum(ep[ARM == "PEMBROLIZUMAB"]$DFS_EVENT),
            sum(ep[ARM == "PLACEBO"]$DFS_EVENT)))
cat(sprintf("OS events:  %d (pembro %d, placebo %d)\n",
            sum(ep$OS_EVENT), sum(ep[ARM == "PEMBROLIZUMAB"]$OS_EVENT),
            sum(ep[ARM == "PLACEBO"]$OS_EVENT)))
cat(sprintf("AE records: %d\n", nrow(ae)))
cat(sprintf("Lab records: %d\n", nrow(fread("output/source/LB.csv"))))
cat(sprintf("Exposure records: %d\n", nrow(ex)))
cat(sprintf("Imaging visits: %d\n", nrow(tu)))

cat("\n=== All integrity checks PASSED ===\n")

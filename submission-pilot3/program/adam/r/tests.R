script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1])
source(file.path(dirname(normalizePath(script)), "common.R"))
source("program/adam/r/compare-lib.R")
library(yamaa);library(yaml);library(jsonlite)
case_root <- tempfile("pilot3-cases-")
dir.create(case_root)
dir.create("log",showWarnings=FALSE)
run_case<-function(name,input,spec){
  folder<-file.path(case_root,name);dir.create(folder,showWarnings=FALSE)
  write.csv(input,file.path(folder,"input.csv"),row.names=FALSE,na="")
  preserve_sequences<-function(x){
    if(!is.list(x))return(x)
    for(i in seq_along(x)){
      x[i]<-list(preserve_sequences(x[[i]]))
      nm<-names(x)[i]
      if(!is.null(nm)&&nm%in%c("keys","columns","order_by","group_by","key","sources")&&is.null(names(x[[i]])))x[[i]]<-as.list(x[[i]])
    };x
  }
  write_yaml(preserve_sequences(spec),file.path(folder,"spec.yaml"),handlers=list(logical=function(x)structure(ifelse(x,"true","false"),class="verbatim")))
  r<-yamaa_spec(file.path(folder,"spec.yaml"))$run()
  write_json(r$issues,file.path(folder,"issues.json"),dataframe="rows",auto_unbox=TRUE,pretty=TRUE)
  if (nrow(r$issues)) print(r$issues)
  stopifnot(nrow(r$issues)==0)
  saveRDS(r$output,file.path(folder,"output.rds"));r$output
}
adae<-read_yaml("spec/yamaa/adae.yaml")
cols<-adae$columns[vapply(adae$columns,function(x)x$name%in%c("ASTDT","ASTDTPR","ASTDTF","AENDT"),logical(1))]
sp<-list(schema_version="1.0",domain="DATECHECK",keys=list("ID"),input=list(AE=list(path="input.csv",types=list(ID="int"))),base="AE",
 output=list(path="output.csv",columns=as.list(c("ID","ASTDT","ASTDTF","AENDT"))),columns=c(list(list(name="ID",type="int",derivation="AE.ID")),cols))
dates<-data.frame(ID=1:5,AESTDTC=c("2020-02-10","2020-02","2020","","invalid"),AEENDTC=c("2020-02-15","2020-02","2020","","invalid"))
out<-run_case("partial-dates",dates,sp)
stopifnot(identical(as.character(out$ASTDT),c("2020-02-10","2020-02-01",NA,NA,NA)),
 identical(out$ASTDTF,c(NA,"D",NA,NA,NA)),identical(as.character(out$AENDT),c("2020-02-15",NA,NA,NA,NA)))
sp2<-list(schema_version="1.0",domain="WINDOWCHECK",keys=list("ID"),input=list(X=list(path="input.csv",types=list(ID="int",ADY="float"))),
 output=list(path="output.csv",columns=as.list(c("ID","AVISIT"))),columns=list(
 list(name="ID",type="int",derivation="X.ID"),list(name="AVISIT",type="str",derivation=list(cut=list(source="X.ADY",breaks=as.list(c(1,84,140)),labels=as.list(c("Baseline","Week 8","Week 16","Week 24")),right=TRUE)))))
# yaml's default boolean spelling is replaced with the language's true/false.
sp2$columns[[2]]$derivation$cut$right<-structure("true",class="verbatim")
out<-run_case("visit-boundaries",data.frame(ID=1:8,ADY=c(-1,0,1,2,84,85,140,141)),sp2)
stopifnot(identical(out$AVISIT,c("Baseline","Baseline","Baseline","Week 8","Week 8","Week 16","Week 16","Week 24")))
adsl<-read_yaml("spec/yamaa/adsl.yaml")
first<-adsl$intermediates[vapply(adsl$intermediates,function(x)x$id=="EX_FIRST",logical(1))]
trtsdt<-adsl$columns[vapply(adsl$columns,function(x)x$name=="TRTSDT",logical(1))]
sp3<-list(schema_version="1.0",domain="DOSECHECK",keys=as.list(c("STUDYID","USUBJID")),input=list(EX=list(path="input.csv",types=list(EXDOSE="float"))),
 output=list(path="output.csv",columns=as.list(c("STUDYID","USUBJID","TRTSDT"))),intermediates=first,columns=c(list(
 list(name="STUDYID",type="str",derivation="EX.STUDYID"),list(name="USUBJID",type="str",derivation="EX.USUBJID")),trtsdt))
ex<-data.frame(STUDYID="SYNTHETIC",USUBJID="S1",EXDOSE=c(0,1),EXTRT="ACTIVE",EXSTDTC=c("2020-01-01","2020-01-05"))
out<-run_case("qualifying-dose",ex,sp3)
stopifnot(identical(as.character(out$TRTSDT),"2020-01-05"))

# Reject non-chemistry candidates before a fallible text expression, and
# prevent a same-code baseline in another category from becoming a donor.
adlbc <- read_spec("adlbc")
relations <- adlbc$intermediates[vapply(adlbc$intermediates, function(x) {
  x$id %in% c("CHEMISTRY", "BL")
}, logical(1))]
spec <- list(
  schema_version = "1.0", domain = "CHEMCHECK",
  keys = as.list(c("STUDYID", "USUBJID", "PARAMCD")),
  input = list(LB = list(path = "input.csv", types = list(LBSTRESN = "float"))),
  output = list(path = "output.csv",
                columns = as.list(c("STUDYID", "USUBJID", "PARAMCD", "BASE", "LABEL"))),
  intermediates = relations,
  columns = list(
    list(name = "STUDYID", type = "str", derivation = "CHEMISTRY.STUDYID"),
    list(name = "USUBJID", type = "str", derivation = "CHEMISTRY.USUBJID"),
    list(name = "PARAMCD", type = "str", derivation = "CHEMISTRY.LBTESTCD"),
    list(name = "BASE", type = "float", derivation = "BL.LBSTRESN"),
    list(name = "LABEL", type = "str", derivation = list(
      str_template = "{CHEMISTRY.LBTESTCD} ({CHEMISTRY.UNIT})"))),
  rows = list(list(id = "chemistry", dataset = "CHEMISTRY", derivations = list(
    STUDYID = "CHEMISTRY.STUDYID", USUBJID = "CHEMISTRY.USUBJID",
    PARAMCD = "CHEMISTRY.LBTESTCD")))
)
lb <- data.frame(STUDYID = "SYNTHETIC", USUBJID = "S1", LBTESTCD = "X",
                  LBCAT = c("CHEMISTRY", "OTHER"), LBBLFL = "Y",
                  LBSTRESN = c(10, 999), UNIT = c("mg", ""))
out <- run_case("chemistry-selection", lb, spec)
stopifnot(nrow(out) == 1, identical(out$BASE, 10),
          identical(out$LABEL, "X (mg)"))

# The comparator must reject false matches, including the A,A versus A,B
# identity case that passes a row-count plus inner-join-height check.
reference <- data.frame(ID = c("A", "B"), VALUE = c(1, 1))
stopifnot(data_matches(compare_frames(reference, reference, "ID")))
duplicate <- reference
duplicate$ID <- c("A", "A")
stopifnot(!data_matches(compare_frames(duplicate, reference, "ID")))
missing_column <- reference["ID"]
result <- compare_frames(missing_column, reference, "ID")
stopifnot(result$reference_cells == 4, result$uncompared == 2,
          !data_matches(result))
extra_column <- transform(reference, EXTRA = 0)
stopifnot(!data_matches(compare_frames(extra_column, reference, "ID")))
stopifnot(!data_matches(compare_frames(reference[1, ], reference, "ID")))
extra_row <- rbind(reference, data.frame(ID = "C", VALUE = 1))
stopifnot(!data_matches(compare_frames(extra_row, reference, "ID")))
reversed <- compare_frames(reference[2:1, ], reference, "ID")
stopifnot(data_matches(reversed), !data_matches(reversed, require_order = TRUE))
close <- reference
close$VALUE[1] <- close$VALUE[1] + 1e-12
result <- compare_frames(close, reference, "ID")
stopifnot(result$exact == 3, result$tolerance_only == 1)
text_ref <- data.frame(ID = c("A", "B"), VALUE = c("", "present"))
text_out <- text_ref
text_out$VALUE[1] <- NA_character_
result <- compare_frames(text_out, text_ref, "ID")
stopifnot(result$exact == 3, result$blank_null_only == 1,
          !data_matches(result), data_matches(result, allow_blank = TRUE))

# Independently reproduce the pinned LOCF planning relation in R. Nothing is
# written back to the reviewed CSV or read from reference ADaM.
qs <- arrow::read_parquet("data/sdtm/qs.parquet")
ex <- arrow::read_parquet("data/sdtm/ex.parquet")
starts <- aggregate(EXSTDTC ~ USUBJID, ex, min)
actot <- merge(qs[qs$QSTESTCD == "ACTOT", c("USUBJID", "QSDTC")],
                starts, by = "USUBJID")
day <- as.numeric(as.Date(actot$QSDTC) - as.Date(actot$EXSTDTC)) + 1
actot$AVISIT <- ifelse(day <= 1, "Baseline", ifelse(day <= 84, "Week 8",
                         ifelse(day <= 140, "Week 16", "Week 24")))
have <- paste(actot$USUBJID, actot$AVISIT, sep = "|")
plan <- expand.grid(AVISITN = c(8L, 16L, 24L), USUBJID = sort(starts$USUBJID),
                     stringsAsFactors = FALSE)
plan$AVISIT <- paste("Week", plan$AVISITN)
plan <- plan[!paste(plan$USUBJID, plan$AVISIT, sep = "|") %in% have, ]
lines <- c("USUBJID,PARAMCD,AVISIT,AVISITN",
            paste(plan$USUBJID, "ACTOT", plan$AVISIT, plan$AVISITN, sep = ","))
generated <- charToRaw(paste0(paste(lines, collapse = "\n"), "\n"))
original <- readBin("data/mapping/plan.csv", "raw",
                     n = file.info("data/mapping/plan.csv")$size)
stopifnot(identical(generated, original))
write_json(list(partial_date_rows = 5, visit_boundary_rows = 8,
                qualifying_dose_records = 2, comparator_cases = 9,
                chemistry_selection_records = 2,
                planned_records = nrow(plan), plan_bytes_identical = TRUE,
                all_assertions_passed = TRUE),
           "log/yamaa-test-results.json", auto_unbox = TRUE, pretty = TRUE)
cat("Date, exposure, visit, comparator and planning checks passed.\n")

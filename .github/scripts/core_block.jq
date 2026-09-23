# Renders one CDISC CORE findings block for a single domain.
#
# Invoke with two string args against a core-report-*.json file:
#   jq -r --arg domain ADSL --arg file core-report-ADAM.json -f core_block.jq report.json
#
# Emits a markdown section: a "### <domain>" heading, an issue/rule tally,
# the top rules by issue count, and a collapsible sample-records table. When
# a domain has no findings it renders a single "no issues" line. Shared by
# both the committed dataset_comment.md render and the issue-comment job in
# .github/workflows/core-validate.yml, so the two never drift.
def norm: ascii_upcase | sub("\\.XPT$"; "");
def trunc($n): if (length > $n) then .[0:$n] else . end;
def cell: gsub("\\|"; "\\|") | gsub("\n"; " ");
def joinvec:
  if (. == null) then "-"
  elif (type != "array") then tostring          # CORE sometimes emits a bare
  elif (length == 0) then "-"                    # string here (e.g. a rule
  else map(if . == null then "null"             # "Failed to ..." error) instead
           else tostring end) | join(";") end;   # of a list -- do not iterate it

[ .Issue_Summary[]? | select(((.dataset // "") | norm) == $domain) ] as $srows |
[ .Issue_Details[]? | select(((.dataset // "") | norm) == $domain) ] as $drows |
([ $srows[] | (.issues // 0) ] | add // 0)          as $total |
([ $srows[] | (.core_id // "") ] | unique | length)  as $nrules |

(
  ["### \($domain)", "", "Report: `\($file)`", ""]
  + (
    if (($srows | length) == 0 and ($drows | length) == 0) then
      ["No validation issues found for this domain. ✅", ""]
    else
      ["- **Total issues**: \($total)", "- **Unique rules**: \($nrules)", ""]
      + (if ($srows | length) > 0 then
           ["**Issues by rule:**", ""]
           + ($srows | sort_by(-(.issues // 0)) | .[0:10]
              | map("- **\(.core_id // "?")** (\(.issues // 0)): \((.message // "") | cell)"))
           + [""]
         else [] end)
      + (if ($drows | length) > 0 then
           ["<details><summary>Sample records</summary>", "",
            "| Record | Variables | Values | Rule | Message |",
            "|--------|-----------|--------|------|---------|"]
           + ($drows | .[0:5] | map(
               "| \(.row // "-") "
               + "| \((.variables | joinvec) | trunc(30) | cell) "
               + "| \((.values    | joinvec) | trunc(20) | cell) "
               + "| \(.core_id // "-") "
               + "| \((.message // "") | trunc(70) | cell) |"))
           + ["", "</details>", ""]
         else [] end)
    end
  )
) | join("\n")

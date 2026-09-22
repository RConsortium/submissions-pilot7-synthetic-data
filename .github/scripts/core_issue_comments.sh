#!/usr/bin/env bash
# Post CDISC CORE findings as comments on matching open issues.
#
# Deterministic gh + jq, no AI agent and no stored secret -- authenticated by
# the workflow's GITHUB_TOKEN (needs issues: write). Adapted from the original
# automation/core_dataset_comments.md spec, but reads reports that the CI job
# already downloaded (no artifact fetch here) and spans every study.
#
# Usage: core_issue_comments.sh [<artifacts_dir>]   (default: _core_artifacts)
#   Expects report JSONs at <artifacts_dir>/<study>/data/{sdtm,adam}/core-report-*.json
#
# Environment: GH_TOKEN (or gh auth), GITHUB_REPOSITORY, GITHUB_RUN_NUMBER,
#   GITHUB_RUN_ID, GITHUB_SHA. Run under bash (not sh/zsh) -- relies on [[ ]],
#   arrays, and word-splitting of $matched.
set -uo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY not set}"
ARTDIR="${1:-_core_artifacts}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_TAG="run #${GITHUB_RUN_NUMBER:-0} (${GITHUB_RUN_ID:-0})"
SHA7="${GITHUB_SHA:0:7}"

command -v gh >/dev/null || { echo "ERROR: gh not found"; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq not found"; exit 1; }

mapfile -t REPORTS < <(find "$ARTDIR" -type f -name 'core-report-*.json' 2>/dev/null | sort)
if [ "${#REPORTS[@]}" -eq 0 ]; then
  echo "SKIP: no CORE report JSONs under $ARTDIR"; exit 0
fi
echo "Reports: ${REPORTS[*]}"

# study name = first path segment under the artifacts dir
study_of() { sed -E "s#^${ARTDIR%/}/([^/]+)/.*#\1#" <<<"$1"; }

# upper-cased domain names a report covers (Dataset_Details + Issue_Summary)
domains_of() {
  jq -r '[ (.Dataset_Details[]?.filename // empty),
           (.Issue_Summary[]?.dataset   // empty) ]
         | map(ascii_upcase | sub("\\.XPT$"; ""))
         | map(select(length > 0)) | unique | .[]' "$1" 2>/dev/null
}

# Data-driven candidate dataset tokens: the union of every domain any report
# covers. Matching issue text against real domains avoids a stale hardcoded
# list and false positives from short words.
mapfile -t ALLDOMAINS < <(for r in "${REPORTS[@]}"; do domains_of "$r"; done | sort -u)
if [ "${#ALLDOMAINS[@]}" -eq 0 ]; then
  echo "SKIP: reports cover no domains"; exit 0
fi
echo "Domains in play: ${ALLDOMAINS[*]}"

gh label create core-commented --repo "$REPO" \
  --description "Validation findings posted from CORE report" \
  --color D4C5F9 2>/dev/null || true

gh issue list --repo "$REPO" --state open \
  --json number,title,body,labels --limit 100 > /tmp/open_issues.json

jq -r 'sort_by(.number) | .[] | @base64' /tmp/open_issues.json > /tmp/issues.b64

while read -r line; do
  issue=$(base64 --decode <<<"$line")
  num=$(jq -r '.number'                 <<<"$issue")
  title=$(jq -r '.title // ""'          <<<"$issue")
  body=$(jq -r '.body  // ""'           <<<"$issue")
  labels=$(jq -r '[.labels[].name] | join(",")' <<<"$issue")

  case ",$labels," in
    *,wontfix,*|*,duplicate,*|*,invalid,*)
      echo "#$num: skip (triage label)"; continue;;
  esac

  matched=""
  for d in "${ALLDOMAINS[@]}"; do
    if printf '%s %s' "$title" "$body" | grep -iqw "$d"; then
      matched="$matched $d"
    fi
  done
  matched=$(echo $matched)
  if [[ -z "$matched" ]]; then
    echo "#$num: no dataset match"; continue
  fi

  # Idempotency: keyed on the workflow run, not the (constant) report name.
  if gh issue view "$num" --repo "$REPO" --json comments \
       --jq '.comments[].body' </dev/null 2>/dev/null \
     | grep -qF "$RUN_TAG"; then
    echo "#$num: already commented for $RUN_TAG"; continue
  fi

  body_file="/tmp/core_body_${num}.md"
  {
    echo "## CDISC CORE Validation Findings"
    echo ""
    for dom in $matched; do
      for rep in "${REPORTS[@]}"; do
        if domains_of "$rep" | grep -qxF "$dom"; then
          echo "#### Study \`$(study_of "$rep")\`"
          echo ""
          bash "$ROOT/.github/scripts/core_render_block.sh" "$rep" "$dom"
          echo ""
        fi
      done
    done
    echo "---"
    echo ""
    echo "_(posted by CDISC CORE validation — $RUN_TAG, commit $SHA7)_"
  } > "$body_file"

  if ! grep -q '^### ' "$body_file"; then
    echo "#$num: no renderable domain blocks, skipping"; rm -f "$body_file"; continue
  fi

  if gh issue comment "$num" --repo "$REPO" --body-file "$body_file" </dev/null; then
    gh issue edit "$num" --repo "$REPO" --add-label core-commented </dev/null
    echo "#$num: posted and labeled"
  else
    echo "#$num: comment POST failed"
  fi
  rm -f "$body_file"
done < /tmp/issues.b64

rm -f /tmp/open_issues.json /tmp/issues.b64
echo "Done."

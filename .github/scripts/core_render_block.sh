#!/usr/bin/env bash
# Render one domain's markdown block from a CORE report JSON.
#
# Usage: core_render_block.sh <report.json> <DOMAIN>
#
# Applies the 0-rules guard: when a report executed no rules (Rules_Report
# empty -- always the case for ADaM, which CORE has no rulebook for, see
# issue #66), it emits an explicit "conformance UNVERIFIED" note instead of
# core_block.jq's "no issues found" line, so an empty ADaM report is never
# mistaken for a clean pass. Otherwise it delegates to automation/core_block.jq.
#
# Shared by the validate job (committed dataset_comment.md) and the
# issue-comments job so the two renderings never drift.
set -uo pipefail

rep="$1"
dom="$2"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

nrules=$(jq '(.Rules_Report? | length) // 0' "$rep" 2>/dev/null || echo 0)

if [ "$nrules" -eq 0 ]; then
  printf '### %s\n\nReport: `%s`\n\n' "$dom" "$(basename "$rep")"
  printf '> No CORE rules were executed for this standard (0 rules). '
  printf 'Conformance is **UNVERIFIED**, not a clean pass. CORE ships no ADaM '
  printf 'rulebook (see issue #66); use Pinnacle 21 for ADaM conformance.\n'
else
  jq -r --arg domain "$dom" --arg file "$(basename "$rep")" \
    -f "$root/automation/core_block.jq" "$rep"
fi

"""Separate reference reproduction from open consistency review findings."""

EXPLANATION = (
    "Generated ADaM dataset agreement measures reproduction of the generated ADaM datasets under "
    "the study's comparison rules. Consistency review checks agreement among "
    "documents, derivation rules, and data. Findings can remain open even when "
    "generated ADaM dataset agreement is 100%."
)


def review_counts(issues):
    counts = {"yes": 0, "no": 0, "needs_review": 0}
    for issue in issues:
        status = issue.get("critical", {}).get("status", "needs_review")
        counts[status] += 1
    return counts


def review_breakdown(issues):
    counts = review_counts(issues)
    return (
        f'{counts["yes"]} critical; {counts["no"]} non-critical; '
        f'{counts["needs_review"]} needing assessment'
    )


def summary_cards(matched, reference, issues):
    def number(value):
        return f"{value / 1e6:.1f}M" if value >= 1e6 else f"{value:,}"

    status = (
        f"<strong>{100 * matched[0] / reference[0]:.0f}%</strong> of generated ADaM datasets matched"
        if reference[0] else "No generated ADaM comparison datasets"
    )
    labels = ["Datasets matching generated ADaM datasets", "Columns in matching datasets", "Cells in matching datasets"]
    metrics = "".join(
        f"<div><dt>{label}</dt><dd>{number(a)} / {number(b)}</dd></div>"
        for label, a, b in zip(labels, matched, reference)
    )
    count = len(issues)
    finding = "finding" if count == 1 else "findings"
    review = "awaiting review" if count else "reported"
    return (
        '<div class="review-summaries">'
        '<section class="summary-card reference-summary" aria-label="Generated ADaM dataset agreement">'
        '<h2>Generated ADaM dataset agreement</h2>'
        f'<p class="summary-value">{status}</p><dl class="summary-metrics">{metrics}</dl></section>'
        '<section class="summary-card consistency-summary" aria-label="Consistency review">'
        '<h2>Consistency review</h2>'
        f'<p class="summary-value"><strong>{count}</strong> {finding} {review}</p>'
        f'<p class="critical-counts">{review_breakdown(issues)}</p></section></div>'
        f'<p class="comparison-explanation">{EXPLANATION}</p>'
    )

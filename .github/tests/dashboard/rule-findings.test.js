// Documented-rule findings: quoted clauses, marked lines and the row a reviewer reads.
import test from "node:test";
import assert from "node:assert/strict";
import {
  highlight,
  reviewSummary,
  ruleRow,
  ruleSearchText,
  specLines,
} from "../../../docs/assets/dashboard/rule-findings.js";

const finding = {
  id: "study:ADSL.BMIBLGR1.CR-8.3",
  dataset: "ADSL",
  variable: "BMIBLGR1",
  kind: "conflict",
  status: "Conflict: CR-8",
  title: "CR-8 The documents agree with one another",
  observation: 'Define-XML ADSL.BMIBLGR1 states ">30 = Obese"; SAP.pdf page 13 states "BMI>=30".',
  rule: { id: "CR-8", statement: "Retained documents state a rule the same way." },
  relation: "contradicts",
  documents: [
    {
      role: "states",
      path: "study/spec/define/define-adam.xml",
      name: "define-adam.xml",
      section: "ADSL.BMIBLGR1",
      quote: ">30 = Obese",
      context: "Codelist BMICAT: <25 = Normal; >30 = Obese",
      verified: true,
      repository: "https://example/define-adam.xml#L10-L12",
      lines: [10, 12],
    },
    {
      role: "against",
      path: "study/spec/source/SAP.pdf",
      name: "SAP.pdf",
      section: "page-13",
      quote: "BMI>=30",
      context: "BMI category (BMI<25, BMI>=30)",
      verified: true,
      repository: "",
      lines: null,
    },
  ],
  spec_quote: null,
  evidence: {},
  subjects: [],
  data: { summary: "No data comparison; the finding compares document and specification text." },
  interpretations: [],
  question: "",
  adjudication: { decision: "dispute", reason: "Same boundary." },
};

test("the quoted clause is marked inside its citation and document text stays literal", () => {
  const cases = [
    ["inside", "Normal if . < BMIBL <25.  Obese if BMIBL >=30", "Obese if BMIBL >=30", "Normal if . &lt; BMIBL &lt;25. <mark>Obese if BMIBL &gt;=30</mark>"],
    ["whole quote", "WEIGHTBL / ((HEIGHTBL*100)**2)", "WEIGHTBL / ((HEIGHTBL*100)**2)", "WEIGHTBL / ((HEIGHTBL*100)**2)"],
    ["not found", "SV.VISITNUM=3", "VISITNUM=4", "SV.VISITNUM=3"],
  ];
  for (const [label, context, quote, expected] of cases)
    assert.equal(highlight(context, quote), expected, label);
});

test("specification lines keep their numbers and mark the quoted ones", () => {
  assert.equal(
    specLines({ element_lines: [5, 7], excerpt: "- name: TRTSDT\nmonth: 1\nday: 1" }, [6, 7]),
    '<pre class="spec-lines"><span class="line-number">5</span>- name: TRTSDT\n<mark><span class="line-number">6</span>month: 1</mark>\n<mark><span class="line-number">7</span>day: 1</mark></pre>',
  );
});

test("a contradiction shows both statements with their sources and the adjudication", () => {
  const row = ruleRow(finding);
  for (const fragment of [
    '<span class="rule-id">CR-8</span>',
    "Codelist BMICAT: &lt;25 = Normal; <mark>&gt;30 = Obese</mark>",
    "Another statement: SAP.pdf, page 13",
    "BMI category (BMI&lt;25, <mark>BMI&gt;=30</mark>)",
    'data-document="study/spec/source/SAP.pdf" data-document-section="page-13"',
    "XML lines 10-12",
    "Retained documents state a rule the same way.",
    '<p class="adjudication adjudication-dispute"><strong>Adjudication:</strong> dispute. Same boundary.</p>',
    "No specification text for this finding.",
  ])
    assert.ok(row.includes(fragment), fragment);
  assert.match(ruleSearchText(finding), /CR-8 .*Same boundary\./);
});

test("the summary counts each reviewed dataset and lists uncited statements", () => {
  const html = reviewSummary({
    datasets: [
      {
        dataset: "ADSL",
        summary: {
          findings: { conflict: 13, divergence: 19, gap: 11, evidence: 0 },
          adjudication: { agree: 39, dispute: 4, stale: 0, pending: 0 },
          citations: { total: 79, verified: 79 },
        },
        missed: [{ variable: "treated-subjects", scope: "records", name: "SAP.pdf", section: "page-9", path: "study/spec/source/SAP.pdf", quote: "Screen  failures are excluded." }],
      },
    ],
  });
  assert.ok(html.includes("Documented rules for ADSL: 13 conflict, 19 divergence, 11 gap and 0 unverified findings. Adjudication: 39 agreed, 4 disputed, 0 stale, 0 pending. 79 of 79 citations verified."));
  assert.ok(html.includes("<strong>treated-subjects</strong> (which records the dataset holds; no rule covers this yet): SAP.pdf, page 9: <q>Screen failures are excluded.</q>"));
  assert.equal(reviewSummary(null), "");
});

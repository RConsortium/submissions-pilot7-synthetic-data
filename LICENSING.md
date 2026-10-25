# Licensing and third-party material

Original Pilot 7 code and documentation are licensed under the [MIT
License](LICENSE). Study data and third-party material are explicitly excluded
from that grant. A repository-level MIT label does not describe every file.

## Scope of the MIT grant

The MIT grant covers original Pilot 7 programs, scripts, tests, workflow
configuration, derivation specifications, and documentation. It does not
replace existing third-party notices or grant rights in imported content.

Study datasets are excluded regardless of format, location, or whether they
are reference, synthetic, or derived datasets. This includes study `data/`
folders, data archives, and data-bearing outputs in `tlf/`, `log/`, or archived
study output folders. Copied study documents, reference metadata (including
Define-XML and imported spreadsheets), and extracts from third-party sources
are also excluded. Original code in a study folder remains covered by MIT.

The independently simulated data identified in the root README (including
`kn189/`, `kn564/`, and `.archieve/CWMM-LAA1/`) are excluded from the root MIT
grant too. This does not classify them as CDISC pilot data or impose CDISC
terms on them. A separate, explicit data license or permission is needed to
establish reuse rights where no existing data license applies.

## CDISC pilot data and reference material

Credit: CDISC SDTM/ADaM Pilot Project, study CDISCPILOT01, published by
[CDISC](https://github.com/cdisc-org/sdtm-adam-pilot-project).

The following paths contain imported CDISC pilot material or data from later
pilots that use the same study. They are not relicensed under MIT:

| Study | Data and imported references | Source |
| --- | --- | --- |
| CDISC Pilot 01 | `cdiscpilot01/data/`, `cdiscpilot01/spec/define/` | [CDISC pilot repository](https://github.com/cdisc-org/sdtm-adam-pilot-project) |
| Submission Pilot 3 | `submission-pilot3/data/`, `submission-pilot3/spec/define/` | [Development repository](https://github.com/RConsortium/submissions-pilot3-adam/tree/main/submission), [submission package](https://github.com/RConsortium/submissions-pilot3-adam-to-fda) |
| Submission Pilot 5 | `submission-pilot5/data/`, `submission-pilot5/spec/define/` | [Dataset-JSON submission package](https://github.com/RConsortium/submissions-pilot5-datasetjson/tree/main/pilot5-submission) |
| Submission Pilot 6 | `submission-pilot6/data/`, `submission-pilot6/spec/define/`, `submission-pilot6/spec/pilot6-specs.xlsx` | [Pilot 6 repository](https://github.com/RConsortium/submissions-pilot6-adams-tlfs); SDTM and ADaM data are staged from its DVC snapshot |
| Archived CDISC references | `.archieve/cdiscpilot1_simulation/reference/` | CDISC Pilot 01 study report and extracted tables and figures |

CDISC-origin content remains subject to CDISC's published terms; additional
upstream rights and notices may apply to later-pilot contributions. See the
[upstream terms](https://github.com/cdisc-org/sdtm-adam-pilot-project/blob/667511d4b183871d74392ba691c935c38d431d39/README.md)
and [disclaimer PDF](https://github.com/cdisc-org/sdtm-adam-pilot-project/blob/667511d4b183871d74392ba691c935c38d431d39/CDISC.Pilot%20Project%20Data.Website%20Disclaimer.v1.pdf).
A local copy of the published notice is retained in
[LICENSE-CDISC.txt](LICENSE-CDISC.txt).

CDISC's terms prohibit misleading users about the data, modifying or altering
the data, unlawful uses, use to compete with CDISC, distribution or sublicensing
for a fee, and distribution or sublicensing without attribution to CDISC.
They also prohibit allowing or assisting third parties to do these things.
The full notice controls; this paragraph is a summary, not a new license.

Some reference datasets in this repository have already been converted from
XPT or Dataset-JSON to Parquet. This licensing notice does not establish that
those conversions, further derivations, or redistribution are authorized.
Attribution and exclusion from MIT do not waive CDISC's restrictions. Obtain
written clarification or permission from CDISC for uses not clearly permitted,
including format conversions or redistribution of converted datasets.

## Other third-party notices

- `.archieve/cart-t/` retains its existing [OpenClinica MIT
  notice](.archieve/cart-t/LICENSE). This change does not replace that license
  or its copyright attribution.
- `docs/stylesheets/extra.css` retains the [yamaa MIT
  notice](docs/stylesheets/LICENSE-yamaa.txt).
- `submission-pilot6/program/adam/upstream/` holds unchanged R programs and
  utilities from the [Pilot 6 repository](https://github.com/RConsortium/submissions-pilot6-adams-tlfs),
  which publishes no license. They are not original Pilot 7 code, are not
  relicensed under MIT, and retain their original rights.
- Other imported protocols, publications, registry extracts, and reference
  documents, including those in `.archieve/`, retain their original rights
  and any applicable terms. Public availability alone is not a data license.

## Reuse and contributions

When distributing original Pilot 7 code, retain the MIT copyright and
permission notice. If also including third-party material, retain its notices,
attribution, and applicable terms, and establish permission for that use.
Describe a combined distribution as MIT-licensed code with separately governed
data; do not label the entire bundle as MIT-only.

Contribute only material you have the right to provide. Identify imported data
or reference content by source, affected paths, and applicable terms. New
original code and documentation contributions are intended to use MIT; this
does not change the terms of pre-existing third-party material or supply a
missing data permission.

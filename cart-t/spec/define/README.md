# Define-XML review packages

The yamaa project generates `cart-t/data/sdtm/define.xml` and
`cart-t/data/adam/define.xml`. Each stays beside the XPT files its dataset
leaves reference. Moving a copy here would break those relative links.
This folder documents the definitions. No schema bundle is vendored here.

The definitions use the native yamaa historical profile, Define-XML 2.0,
and `context: Other`. They declare the archived study's target SDTMIG 3.3 /
ADaMIG 1.3 metadata and are **not a data-conformance certification**.
Required-but-missing data are reported separately in the review queries.
Native historical composition does not publish transport; ReadStat writes
the separate review XPT files and checks every value, label and width.

The full runner checks both definitions with lxml against
`define/2.0/define2-0-0.xsd` under the external schema root, checks all relative dataset links, and
fails on an error. Schema validity is distinct from guide conformance,
reference metadata agreement and human statistical approval.

As in the three pilot studies' Define-XML workflow, CI checks out only
`rust/tests/schemas` from the study's pinned yamaa revision into
`.build/define-engine`. This supplies the CDISC Define-XML 2.0 schema and its
ODM 1.3.2 imports without another committed copy. The source checkout retains
the original notices and license. See the study README for local setup;
`YAMAA_XML_SCHEMAS` can select an existing pinned checkout. Validation disables
network imports. yamaa composes the XML and lxml provides an independent
parser/validator.

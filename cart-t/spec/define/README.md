# Define-XML review packages

The yamaa project generates `cart-t/data/sdtm/define.xml` and
`cart-t/data/adam/define.xml`. Each stays beside the XPT files its dataset
leaves reference. Moving a copy here would break those relative links.
This folder holds the schema bundle and the documentation for the definitions.

The definitions use the native yamaa historical profile, Define-XML 2.0,
and `context: Other`. They declare the archived study's target SDTMIG 3.3 /
ADaMIG 1.3 metadata and are **not a data-conformance certification**.
Required-but-missing data are reported separately in the review queries.
Native historical composition does not publish transport; ReadStat writes
the separate review XPT files and checks every value, label and width.

The full runner checks both definitions with lxml against
`schema/define/2.0/define2-0-0.xsd`, checks all relative dataset links, and
fails on an error. Schema validity is distinct from guide conformance,
reference metadata agreement and human statistical approval.

The schema files are retained unchanged from
`elong0527/yamaa@1d78496c0cbd4fe89462596a738db3adbd72c8ad`,
`rust/tests/schemas/define/2.0` and `rust/tests/schemas/odm/1.3.2`.
Their original notices and `schema/LICENSE` are retained. These are the
same versioned schema sources the pinned engine distributes in its source
qualification set; lxml provides the separate parser/validator.

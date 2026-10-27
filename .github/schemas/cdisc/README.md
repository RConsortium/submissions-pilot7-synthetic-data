# Retained CDISC Define-XML schemas

These unmodified schema files and their MIT license are retained from the
yamaa source snapshot at `44fa7ae736fd7cb4adb4dd385275a1759e5f2656`,
`rust/tests/schemas/`. Its upstream source is
[CDISC data-definition-engine](https://github.com/cdisc-org/data-definition-engine/tree/924e5a9ec2a4e77bd8f6280f83066bf9f7d37e50/schemas).

The ODM import in `define/2.1/define-enumerations.xsd` uses the local
`../../odm/1.3.2/` schema. XML validation needs no network access.
Passing these schemas establishes XML structure, not clinical correctness,
controlled terminology conformance, submission completeness, or agency acceptance.

# Draft upstream enhancement: ASCII-declared ODM XML

Proposed repository: https://github.com/elong0527/yamaa

Proposed title: ODM XML: admit US-ASCII declarations for verified ASCII bytes

Status: draft, not filed. This is an enhancement to the documented ODM-1
UTF-8-only profile, not a claim that the current implementation violates it.
The interface decision is tracked in yamaa issue #3030; no focused issue for
this particular declaration was found in the issue searches.

## Use case

The OpenClinica CAR-T export in RConsortium/submissions-pilot7-synthetic-data
contains only ASCII source bytes and XML character references, but declares
`encoding="US-ASCII"`. The native ODM reader rejects it before reading items.
Changing only that declaration to UTF-8 gives identical XML characters and
allows direct specification inputs. Supporting the valid ASCII declaration
would remove the remaining encoding compatibility copy from this study.

## Reproduction

Reproduced using yamaa source revision
`1d78496c0cbd4fe89462596a738db3adbd72c8ad` (package version 0.6.2).
The encoding admission code at current-main revision
`e3e6c4a14cf72e09980624d8c804d6335c339422` was also inspected and still
explicitly accepts only UTF-8/UTF8. That latest binary was not run.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import yamaa

xml = b'''<?xml version="1.0" encoding="US-ASCII"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
     ODMVersion="1.3" FileType="Snapshot">
  <ClinicalData StudyOID="S" MetaDataVersionOID="V1">
    <SubjectData SubjectKey="01">
      <StudyEventData StudyEventOID="E">
        <FormData FormOID="F">
          <ItemGroupData ItemGroupOID="G">
            <ItemData ItemOID="I" Value="caf&#233;"/>
          </ItemGroupData>
        </FormData>
      </StudyEventData>
    </SubjectData>
  </ClinicalData>
</ODM>'''

with TemporaryDirectory() as directory:
    path = Path(directory) / "source.xml"
    path.write_bytes(xml)
    yamaa.read_odm(path)  # source_odm_xml_unsupported: US-ASCII
```

The same refusal applies when a YAML specification names this XML as an input.
Replacing only `US-ASCII` with `UTF-8` makes the example readable, retaining
the character-reference value.

## Requested discussion

Consider admitting US-ASCII declarations with strict validation that source
bytes are ASCII. Retain refusal for inconsistent declarations/non-ASCII bytes,
and make behavior identical for `read_odm()` and direct `.xml` inputs. Add
equivalence coverage for character references, null/value-presence flags and
repeat keys. This request does not propose general legacy-encoding support.

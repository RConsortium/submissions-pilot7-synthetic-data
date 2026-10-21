# submission-pilot3

R Consortium R Submission Pilot 3 (Study CDISC Pilot 03), staged for
SDTM-to-ADaM derivation with released yamaa 0.5.0.

- Source: https://github.com/RConsortium/submissions-pilot3-adam/tree/main/submission
- `data/sdtm/`: 22 original SDTM datasets converted from XPT to Parquet.
- `data/adam/`: the five official ADaM references (adadas, adae, adlbc, adsl,
  adtte), with original variable labels in Arrow field metadata.
- `data/mapping/`: the reviewed ADADAS planning and analysis-window CSVs.
- `spec/define/`: original submission Define-XML files.
- `spec/yamaa/`: one specification per ADaM target.
- `project.yaml`: linked predecessor contracts for one project run.
- `program/adam/r/`: released-package setup, execution, explicit export,
  independent comparison and regression checks.
- `program/adam/python/`: the optional Python runner/comparator and original
  planning generator.

See [the ADaM workflow](program/adam/README.md) for reproduction commands,
exact-versus-tolerance comparison criteria, export conventions, and unresolved
source questions. All reference inputs and outputs remain unchanged.

The seven additional development-team ADaM datasets (advs, adcibc, adlbcpv,
adlbh, adlbhpv, adlbhy, adnpix) were not in the official submission and remain
outside this staged scope. Snapshot equality does not establish complete
logic equivalence or qualify a new regulatory submission package.

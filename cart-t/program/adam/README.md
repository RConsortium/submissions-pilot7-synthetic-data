# ADaM execution

After ODM extraction and SDTM execution, run:

```bash
.venv/bin/python cart-t/program/adam/run.py
```

The runner executes `spec/yamaa/project.yaml`, section `adam`, in yamaa.
Each dataset has its own executable YAML under `spec/yamaa/adam/`.
ADSL is the shared source for subject attributes and population flags.
Other ADaM datasets read only SDTM and ADSL; no raw-data shortcut or
archived analysis output is used.

Native yamaa `copy` entries inherit types, labels and content metadata from
the linked SDTM/ADSL producer. Study-specific derivations stay explicit.
The export and review programs use the engine's resolved specification;
they do not expand inheritance or interpret clinical YAML themselves.

The engine's equivalent R call is:

```r
library(yamaa) # install the same pinned source revision as the Python host
project <- yamaa_project("cart-t/spec/yamaa/project.yaml")
project$run("adam")$save()
```

The complete extraction/export/audit driver is Python. The R call above
is an alternative ADaM execution entry point after extraction/SDTM, not
a separately qualified full R pipeline. Use the Python full runner to
refresh all review artifacts.

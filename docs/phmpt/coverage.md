# Module 5 coverage

What PHMPT's Full Productions release for each study, read from the 78 zip archives' directories (`scripts/site/inventory_module5.py`, collected 2026-11-24), and what this repo reproduces.

| Study | Sponsor | Module 5 holds | Status |
| --- | --- | --- | --- |
| [mrna1273-p201](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt/mrna-1273-p201) | Moderna | 30 ADaM - 107 SDTM - 4 defines - 61 programs - 109 documents | [Specs for s3-d57, s3-add1](findings/mrna-1273-p201.md) |
| [mrna1273-p301](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt/mrna-1273-p301) | Moderna | 62 ADaM - 160 SDTM - 6 defines - 100 programs - 2,337 documents | [Specs for s3, s5, s80](findings/mrna-1273-p301.md) |
| [bnt162-01](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt/bnt162-01) | Pfizer/BioNTech | 12 ADaM - 85 SDTM - 4 defines - 42 documents | [Specs for 27034, 125742](findings/bnt162-01.md) |
| [c4591001](https://github.com/RConsortium/submissions-pilot7-synthetic-data/tree/main/phmpt/c4591001) | Pfizer/BioNTech | 60 ADaM - 299 SDTM - 14 defines - 25 programs - 1,753 documents | [Specs for s1, s211-1mth, s135, s211-6mth, s1-supp, s6, s1-safety-fa-eff, s1-ia](findings/c4591001.md) |
| dmid-200003 | Moderna | 56 documents | Documents only: nothing to reproduce |
| mrna1273-p901 | Moderna | nothing | Documents only: nothing to reproduce |
| mrna1273-p902 | Moderna | 1 documents | Documents only: nothing to reproduce |
| mrna1273-p903 | Moderna | 4 documents | Documents only: nothing to reproduce |
| mrna1273-p904 | Moderna | 1 documents | Documents only: nothing to reproduce |
| mrna1273-p905 | Moderna | 1 documents | Documents only: nothing to reproduce |
| c4591007 | Pfizer/BioNTech | 23 documents | Documents only: nothing to reproduce |
| c4591008 | Pfizer/BioNTech | 16 documents | Documents only: nothing to reproduce |
| c4591009 | Pfizer/BioNTech | 2 documents | Documents only: nothing to reproduce |
| c4591011 | Pfizer/BioNTech | 3 documents | Documents only: nothing to reproduce |
| c4591012 | Pfizer/BioNTech | 9 documents | Documents only: nothing to reproduce |
| c4591014 | Pfizer/BioNTech | 5 documents | Documents only: nothing to reproduce |
| c4591015 | Pfizer/BioNTech | 1 documents | Documents only: nothing to reproduce |
| c4591020 | Pfizer/BioNTech | 4 documents | Documents only: nothing to reproduce |
| c4591021 | Pfizer/BioNTech | 1 documents | Documents only: nothing to reproduce |
| c4591022 | Pfizer/BioNTech | 5 documents | Documents only: nothing to reproduce |
| wi235284 | Pfizer/BioNTech | 2 documents | Documents only: nothing to reproduce |
| wi255886 | Pfizer/BioNTech | 3 documents | Documents only: nothing to reproduce |

Only four studies have analysis data in Module 5. For the other eighteen, PHMPT released protocols, consent forms and report sections, with no SDTM or ADaM datasets and no define.xml, so there is nothing for a specification to reproduce.

## Cuts with data but no specs

C4591001's S211 1-month cut is reproduced by layers over the S1 specs ([C4591001](findings/c4591001.md#s211-1mth)), each holding only what that cut changes. These cut folders hold submitted datasets but no specs yet (development issue #9): P301 `s27`; C4591001 `s135`, `s211-6mth`, `s6`, `s1-safety-fa-eff` and `s9-safety-fa-eff`.

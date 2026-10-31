# Native ODM XML encoding support

[yamaa issue #4060](https://github.com/elong0527/yamaa/issues/4060) is fixed in
[merged PR #4063](https://github.com/elong0527/yamaa/pull/4063). The study pins
the yamaa 0.7.0 release, commit `c039509082b545fe913c00d1686426c3d245778c`,
which includes that fix.

The OpenClinica export declares `US-ASCII`. The native reader now accepts this
declaration when all source bytes are ASCII, including numeric character
references. Raw non-ASCII bytes are refused; decoded clinical characters,
repeat keys and null/value-presence indicators are preserved.

The source is staged byte-identically as `data/odm/car-t-openclinica.xml`.
Every SDTM specification reads that XML directly. No declaration conversion
or encoding-compatible reader copy is needed. `program/odm/prepare.py` only
stages the source and writes native item Parquet and inventory evidence for QC.

The prior pin `1d78496c0cbd4fe89462596a738db3adbd72c8ad` refused US-ASCII
declarations under its UTF-8-only profile. The original reproduction and
upstream acceptance tests remain recorded in the linked issue and pull request.

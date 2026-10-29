"""Retained ADaM programs: the reference's implementation, cited by line range."""

import re

PROGRAM_SUFFIXES = {".r", ".sas"}
PROGRAM_ROLES = {
    "adam_program": "ADaM program retained from the submission package that published the reference datasets.",
    "reference_reimplementation": (
        "Later reimplementation that reproduces the published reference datasets. It shows how "
        "the reference values can be produced, not what the original authors intended."
    ),
}
LINE_RANGE = re.compile(r"L([1-9][0-9]*)(?:-L([1-9][0-9]*))?")


def is_program(path):
    return str(path).lower().endswith(tuple(PROGRAM_SUFFIXES))


def line_range(section):
    """[first, last] of an L<first>-L<last> or L<line> section, or None."""
    match = LINE_RANGE.fullmatch(section or "")
    if not match:
        return None
    first = int(match.group(1))
    last = int(match.group(2) or first)
    return [first, last] if first <= last else None


class ProgramSections(dict):
    """One citable section per program line; get() also answers a range L<a>-L<b>."""

    def __init__(self, lines):
        super().__init__(
            (f"L{n}", {"id": f"L{n}", "title": f"Line {n}", "text": text})
            for n, text in enumerate(lines, 1)
        )
        self.lines = lines

    def get(self, key, default=None):
        span = line_range(key)
        if span is None or span[1] > len(self.lines):
            return default
        first, last = span
        title = f"Line {first}" if first == last else f"Lines {first}-{last}"
        return {"id": key, "title": title, "text": "\n".join(self.lines[first - 1 : last])}

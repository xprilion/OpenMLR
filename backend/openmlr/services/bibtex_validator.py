"""BibTeX validator and parser service.

Provides validation, syntax checking, citation extraction, field checking,
and cross-referencing between LaTeX documents and BibTeX bibliographies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Standard required fields for common BibTeX entry types
REQUIRED_FIELDS: dict[str, list[str]] = {
    "article": ["author", "title", "journal", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "conference": ["author", "title", "booktitle", "year"],
    "book": ["title", "publisher", "year"],  # Needs author or editor
    "incollection": ["author", "title", "booktitle", "publisher", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "misc": ["title"],
    "unpublished": ["author", "title", "note"],
    "manual": ["title"],
}

# Regex for LaTeX citation commands: \cite, \citep, \citet, \citeauthor, etc.
CITE_CMD_PATTERN = re.compile(
    r"\\(?:cite|citep|citet|citeauthor|citeyear|parencite|textcite|autocite|footcite|nocite|citealt|citealp)"
    r"(?:\[[^\]]*\])*\{([^}]+)\}",
    re.IGNORECASE,
)

# Regex for matching BibTeX entry header: @type{key,
ENTRY_HEADER_PATTERN = re.compile(
    r"@([a-zA-Z]+)\s*\{\s*([^,\s]+)\s*,",
    re.IGNORECASE,
)


@dataclass
class BibtexEntry:
    """Represents a parsed BibTeX entry."""

    key: str
    entry_type: str
    fields: dict[str, str] = field(default_factory=dict)
    raw: str = ""
    line_num: int = 1

    def get(self, field_name: str, default: str = "") -> str:
        """Get field value case-insensitively."""
        field_lower = field_name.lower()
        for k, v in self.fields.items():
            if k.lower() == field_lower:
                return v
        return default

    def to_bibtex(self) -> str:
        """Format entry back to standardized BibTeX string."""
        lines = [f"@{self.entry_type.lower()}{{{self.key},"]
        for k, v in sorted(self.fields.items()):
            lines.append(f"  {k} = {{{v}}},")
        lines.append("}")
        return "\n".join(lines)


@dataclass
class BibtexValidationResult:
    """Result of BibTeX validation."""

    valid: bool
    entries_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_citations: list[str] = field(default_factory=list)
    unused_citations: list[str] = field(default_factory=list)
    duplicate_keys: list[str] = field(default_factory=list)
    entry_keys: list[str] = field(default_factory=list)
    entries: list[BibtexEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "entries_count": self.entries_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "missing_citations": self.missing_citations,
            "unused_citations": self.unused_citations,
            "duplicate_keys": self.duplicate_keys,
            "entry_keys": self.entry_keys,
        }


def extract_latex_citations(tex_content: str) -> set[str]:
    """Extract all citation keys cited in LaTeX content."""
    if not tex_content:
        return set()

    # Strip LaTeX comments (% to end of line)
    cleaned_lines = []
    for line in tex_content.splitlines():
        # Match % not preceded by backslash
        comment_match = re.search(r"(?<!\\)%", line)
        if comment_match:
            cleaned_lines.append(line[: comment_match.start()])
        else:
            cleaned_lines.append(line)
    cleaned_tex = "\n".join(cleaned_lines)

    citations = set()
    for match in CITE_CMD_PATTERN.finditer(cleaned_tex):
        raw_keys = match.group(1)
        for key in raw_keys.split(","):
            cleaned_key = key.strip()
            if cleaned_key:
                citations.add(cleaned_key)
    return citations


def _parse_fields(body: str) -> dict[str, str]:
    """Parse key = value fields inside a BibTeX entry body."""
    fields: dict[str, str] = {}
    pos = 0
    length = len(body)

    while pos < length:
        # Skip leading whitespace and commas
        while pos < length and body[pos] in " \t\r\n,":
            pos += 1
        if pos >= length:
            break

        # Read field name
        field_name_start = pos
        while pos < length and (body[pos].isalnum() or body[pos] in "_-"):
            pos += 1
        field_name = body[field_name_start:pos].strip().lower()

        if not field_name:
            pos += 1
            continue

        # Skip to '='
        while pos < length and body[pos] in " \t\r\n":
            pos += 1
        if pos >= length or body[pos] != "=":
            pos += 1
            continue
        pos += 1  # Skip '='

        while pos < length and body[pos] in " \t\r\n":
            pos += 1
        if pos >= length:
            break

        # Read value
        val_char = body[pos]
        val = ""
        if val_char == "{":
            # Brace-delimited value
            brace_depth = 1
            pos += 1
            val_start = pos
            while pos < length and brace_depth > 0:
                if body[pos] == "{" and (pos == 0 or body[pos - 1] != "\\"):
                    brace_depth += 1
                elif body[pos] == "}" and (pos == 0 or body[pos - 1] != "\\"):
                    brace_depth -= 1
                pos += 1
            val = body[val_start : pos - 1 if brace_depth == 0 else pos]
        elif val_char == '"':
            # Quote-delimited value
            pos += 1
            val_start = pos
            while pos < length and body[pos] != '"':
                if body[pos] == "\\" and pos + 1 < length:
                    pos += 1
                pos += 1
            val = body[val_start:pos]
            if pos < length and body[pos] == '"':
                pos += 1
        else:
            # Bare word / number
            val_start = pos
            while pos < length and body[pos] not in ",\r\n}":
                pos += 1
            val = body[val_start:pos].strip()

        fields[field_name] = val.strip()

    return fields


def parse_bibtex(bib_content: str) -> tuple[list[BibtexEntry], list[str]]:
    """Parse BibTeX string into BibtexEntry objects and list of syntax errors."""
    entries: list[BibtexEntry] = []
    errors: list[str] = []

    if not bib_content or not bib_content.strip():
        return entries, errors

    pos = 0
    content_len = len(bib_content)

    while pos < content_len:
        at_pos = bib_content.find("@", pos)
        if at_pos == -1:
            break

        # Calculate line number
        line_num = bib_content[:at_pos].count("\n") + 1

        # Match header
        match = ENTRY_HEADER_PATTERN.match(bib_content, at_pos)
        if not match:
            # Could be @string or @comment or malformed
            end_line = bib_content.find("\n", at_pos)
            if end_line == -1:
                end_line = content_len
            header_fragment = bib_content[at_pos:end_line].strip()
            if not header_fragment.lower().startswith(("@comment", "@string", "@preamble")):
                errors.append(f"Line {line_num}: Malformed BibTeX entry header '{header_fragment}'")
            pos = end_line + 1
            continue

        entry_type = match.group(1)
        key = match.group(2).strip()

        # Find matching closing brace
        body_start = match.end()
        brace_depth = 1
        curr = body_start
        while curr < content_len and brace_depth > 0:
            c = bib_content[curr]
            if c == "{" and (curr == 0 or bib_content[curr - 1] != "\\"):
                brace_depth += 1
            elif c == "}" and (curr == 0 or bib_content[curr - 1] != "\\"):
                brace_depth -= 1
            curr += 1

        if brace_depth != 0:
            errors.append(f"Line {line_num}: Unclosed brace in entry '{key}'")
            pos = curr
            continue

        body_content = bib_content[body_start : curr - 1]
        raw_entry = bib_content[at_pos:curr]
        fields = _parse_fields(body_content)

        entries.append(
            BibtexEntry(
                key=key,
                entry_type=entry_type,
                fields=fields,
                raw=raw_entry,
                line_num=line_num,
            )
        )
        pos = curr

    return entries, errors


def validate_bibtex(
    bib_content: str,
    tex_content: str | None = None,
) -> BibtexValidationResult:
    """Validate BibTeX bibliography and cross-reference with optional LaTeX content."""
    entries, errors = parse_bibtex(bib_content)
    warnings: list[str] = []
    seen_keys: set[str] = set()
    duplicate_keys: list[str] = []
    entry_keys: list[str] = []

    for entry in entries:
        k = entry.key
        entry_keys.append(k)

        # Check for duplicates
        if k in seen_keys:
            duplicate_keys.append(k)
            errors.append(f"Duplicate citation key '{k}' found at line {entry.line_num}")
        seen_keys.add(k)

        # Check required fields
        etype = entry.entry_type.lower()
        reqs = REQUIRED_FIELDS.get(etype, [])
        for r in reqs:
            if not entry.get(r):
                warnings.append(
                    f"Entry '{k}' (@{etype}) is missing recommended field '{r}'"
                )

        if etype == "book" and not entry.get("author") and not entry.get("editor"):
            warnings.append(f"Book entry '{k}' should have either 'author' or 'editor'")

    # Cross-reference with LaTeX content if provided
    missing_citations: list[str] = []
    unused_citations: list[str] = []

    if tex_content is not None:
        cited_keys = extract_latex_citations(tex_content)
        bib_key_set = set(entry_keys)

        for ckey in sorted(cited_keys):
            if ckey not in bib_key_set:
                missing_citations.append(ckey)
                errors.append(f"Citation '\\cite{{{ckey}}}' cited in text but missing from BibTeX")

        for bkey in sorted(bib_key_set):
            if bkey not in cited_keys:
                unused_citations.append(bkey)
                warnings.append(f"BibTeX entry '{bkey}' is not cited anywhere in LaTeX document")

    is_valid = len(errors) == 0 and len(missing_citations) == 0

    return BibtexValidationResult(
        valid=is_valid,
        entries_count=len(entries),
        errors=errors,
        warnings=warnings,
        missing_citations=missing_citations,
        unused_citations=unused_citations,
        duplicate_keys=duplicate_keys,
        entry_keys=entry_keys,
        entries=entries,
    )


def normalize_bibtex(bib_content: str) -> str:
    """Format and standardize all entries in a BibTeX string."""
    entries, _ = parse_bibtex(bib_content)
    if not entries:
        return bib_content
    return "\n\n".join(entry.to_bibtex() for entry in entries)

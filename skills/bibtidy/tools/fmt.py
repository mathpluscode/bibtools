#!/usr/bin/env python3
"""Validate bibtidy output format.

Checks that every changed entry follows the required format:
1. Original entry commented out (% prefix on every line, complete entry)
2. % bibtidy: source <URL> line present
3. % bibtidy: <explanation> line present
4. Corrected entry follows

Also checks that unchanged entries have NO bibtidy comments.

Usage: python3 fmt.py <original.bib> <modified.bib>
  - If only one arg given, checks modified file structure without diff.
  - Exit code 0 = all good, 1 = violations found.
"""

import re
import sys


def parse_entries(text):
    """Extract non-commented @type{key, entries with their preceding context.

    Context is collected by walking backwards from each entry, stopping at the
    previous entry's closing brace or at a non-comment, non-blank line that
    isn't part of bibtidy output.
    """
    entries = {}
    lines = text.split("\n")

    # First pass: find all non-commented entry positions so we know boundaries
    entry_positions = []  # list of (start_line, end_line, key)
    i = 0
    while i < len(lines):
        m = re.match(r"^(@\w+\{)([\w:.\-/]+),", lines[i])
        if m:
            key = m.group(2)
            entry_start = i
            entry_lines = [lines[i]]
            depth = lines[i].count("{") - lines[i].count("}")
            i += 1
            while i < len(lines) and depth > 0:
                entry_lines.append(lines[i])
                depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            entry_end = i  # exclusive
            entry_positions.append((entry_start, entry_end, key))
        else:
            i += 1

    # Second pass: collect context for each entry, bounded by previous entry end
    for idx, (entry_start, entry_end, key) in enumerate(entry_positions):
        # Context starts after the previous entry ends (or at file start)
        if idx > 0:
            context_boundary = entry_positions[idx - 1][1]
        else:
            context_boundary = 0

        # Walk backwards from entry_start to collect comment/blank lines,
        # but never cross into the previous entry's territory
        context_start = entry_start - 1
        context_lines = []
        while context_start >= context_boundary and (
            lines[context_start].startswith("%") or lines[context_start].strip() == ""
        ):
            context_lines.insert(0, lines[context_start])
            context_start -= 1

        entry_text = "\n".join(lines[entry_start:entry_end])
        context_text = "\n".join(context_lines)

        entries[key] = {
            "entry": entry_text,
            "context": context_text,
            "full": "\n".join(context_lines + lines[entry_start:entry_end]),
        }

    return entries


def check_changed_entry(key, context):
    """Check that a changed entry has the required format."""
    errors = []

    # Check 1: commented-out original — must be a complete entry
    # (opening line + closing "% }")
    escaped_key = re.escape(key)
    has_open = re.search(rf"^% @\w+\{{{escaped_key},", context, re.MULTILINE)
    has_close = re.search(r"^% \}", context, re.MULTILINE)
    if not has_open:
        errors.append("Missing commented-out original entry")
    elif not has_close:
        errors.append("Commented-out original appears incomplete (missing closing '% }' line)")

    # Check 2: % bibtidy: source <URL>
    if not re.search(r"^% bibtidy: source https?://", context, re.MULTILINE):
        errors.append('Missing "% bibtidy: source <URL>" line (found bare URL without prefix?)')

    # Check 3: % bibtidy: <explanation>
    bibtidy_lines = re.findall(r"^% bibtidy: (?!source )(.+)", context, re.MULTILINE)
    if not bibtidy_lines:
        errors.append('Missing "% bibtidy: <explanation>" line')

    return errors


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [original.bib] <modified.bib>")
        sys.exit(1)

    if len(sys.argv) == 3:
        with open(sys.argv[1], encoding="utf-8") as f:
            original_text = f.read()
        with open(sys.argv[2], encoding="utf-8") as f:
            modified_text = f.read()
    else:
        original_text = None
        with open(sys.argv[1], encoding="utf-8") as f:
            modified_text = f.read()

    modified_entries = parse_entries(modified_text)

    if original_text:
        original_entries = parse_entries(original_text)
    else:
        original_entries = None

    all_errors = []

    for key, data in modified_entries.items():
        context = data["context"]

        # Determine if entry was changed
        if original_entries and key in original_entries:
            changed = original_entries[key]["entry"] != data["entry"]
        else:
            # Without original, check if there are bibtidy comments
            has_comments = bool(
                re.search(r"% bibtidy:", context) or re.search(rf"^% @\w+\{{{re.escape(key)},", context, re.MULTILINE)
            )
            changed = has_comments

        if changed:
            errors = check_changed_entry(key, context)
            for e in errors:
                all_errors.append(f"  [{key}] {e}")
        else:
            # Unchanged entries should have NO bibtidy comments
            # Exception: DUPLICATE flags are allowed on unchanged entries
            non_duplicate_comments = [
                line for line in context.split("\n") if re.match(r"^% bibtidy:", line) and "DUPLICATE" not in line
            ]
            if non_duplicate_comments:
                all_errors.append(f"  [{key}] Unchanged entry has bibtidy comments (should have none)")

    if all_errors:
        print("FORMAT VIOLATIONS FOUND:")
        for e in all_errors:
            print(e)
        print(f"\nTotal: {len(all_errors)} violation(s)")
        print("\nRequired format for changed entries:")
        print("  % @type{key,")
        print("  %   field={value},")
        print("  % }")
        print("  % bibtidy: source https://doi.org/...")
        print("  % bibtidy: explanation of changes")
        print("  @type{key,")
        print("    field={corrected_value},")
        print("  }")
        sys.exit(1)
    else:
        print(f"Format OK — {len(modified_entries)} entries checked, no violations.")
        sys.exit(0)


if __name__ == "__main__":
    main()

---
name: bibtidy
description: Use when the user wants to validate, check, or fix a BibTeX (.bib) reference file, wrong authors, stale arXiv preprints, incorrect metadata, duplicate entries, formatting issues
metadata:
  short-description: Validate and fix BibTeX reference files
allowed-tools: Bash(python3 *), Bash(cp *), Bash(rm *), Read, Agent, WebSearch
---

Use this skill whenever the user wants to validate, check, clean up, or fix a BibTeX `.bib` file.

If the user request or skill invocation includes an explicit `.bib` path, operate on that file.

If the file path is missing or does not exist, ask for the path.

Usage examples:
- Claude Code slash command: `/bibtidy <path-to-file.bib>`
- Codex request: `Use the bibtidy skill to validate and fix <path-to-file.bib>`

You are a meticulous academic reference checker. Process the .bib file entry by entry, verifying each against external sources and fixing errors in-place.

Assume standard brace-style BibTeX entries like `@article{...}`. Parenthesized BibTeX blocks like `@article(...)` are not supported. `@string`, `@preamble`, and `@comment` blocks should be ignored and preserved.

## Quick Reference

| Tool | Command |
|------|---------|
| **CrossRef candidate lookup** | `python3 $TOOLS_DIR/compare.py <file.bib> [--key KEY]` |
| CrossRef DOI lookup | `python3 $TOOLS_DIR/crossref.py doi <DOI>` |
| CrossRef title search | `python3 $TOOLS_DIR/crossref.py search "<title>"` |
| CrossRef bibliographic search | `python3 $TOOLS_DIR/crossref.py bibliographic "<query>"` |
| Comment out exact/subset duplicates | `python3 $TOOLS_DIR/duplicates.py <file.bib>` |
| **Apply edits** | `python3 $TOOLS_DIR/edit.py <file.bib> <patches.json>` |
| Web verification | web-search subagent, one per entry maximum |

## Script Path Resolution

All bundled tools live in the `tools/` directory next to this SKILL.md. Before running any tool, resolve the absolute path once:

```
TOOLS_SEARCH_PATH=(
  "${CODEX_HOME:-$HOME/.codex}/skills/bibtidy/tools"
  "$HOME/.claude/skills/bibtidy/tools"
  "${CLAUDE_PLUGIN_ROOT:-/dev/null}/skills/bibtidy/tools"
)
for d in "${TOOLS_SEARCH_PATH[@]}"; do
  if [ -f "$d/crossref.py" ]; then TOOLS_DIR="$d"; break; fi
done
```

Use `$TOOLS_DIR` in every invocation.

## Output Format for Changed Entries

For `fix` patches, each targeted edit MUST contain the original entry, one or more source URLs, an explanation, and the corrected entry. Include URLs for all sources used (CrossRef, DOI, venue page), each on its own `% bibtidy:` line.

```
% @<type>{<key>,
%   <original field 1>,
%   <original field 2>,
%   ...
% }
% bibtidy: <URL>
% bibtidy: <what changed>
@<type>{<key>,
  <corrected field 1>,
  <corrected field 2>,
  ...
}
```

- **Part 1**, entire original entry, every line prefixed by `% `. All lines, not just the first.
- **Part 2**, `% bibtidy: ` followed by a URL. Must be exactly `% bibtidy: https://...`.
- **Part 3**, `% bibtidy: ` followed by explanation of what changed.
- **Part 4**, corrected entry.

Exceptions:
- `not_found` entries get the `% bibtidy: NOT FOUND ...` line plus the fully commented-out original entry. Do NOT add a URL line.
- `duplicate` entries get `% bibtidy: DUPLICATE of <other_key>, consider removing` above the original entry. Do NOT add URL or explanation lines unless the tool behavior changes.
- `review` entries (uncertain, budget exhausted) get one or more `% bibtidy:` URL lines and a `% bibtidy: REVIEW, <what was confusing>` line above the **unchanged** original entry. Do NOT modify the entry itself.

For unchanged (clean) entries, do NOT add any comments or URLs.

## Workflow

Each entry has a **web-search budget of 1**, spent in at most one of Wave A or Wave B. Track which entries have used the budget so you never double-search.

- Read the .bib file, note the file path
- Clear the log file: `> <file>.bib.cc.log` (Claude Code) or `> <file>.bib.codex.log` (Codex)
- Back up for format validation: `cp <file>.bib <file>.bib.orig`
- Preserve `@string`, `@preamble`, `@comment` blocks verbatim
- **Comment out exact/subset duplicates**: `python3 $TOOLS_DIR/duplicates.py <file.bib>`. Lossless, safe to auto-comment.
- **Fetch CrossRef candidates**: `python3 $TOOLS_DIR/compare.py <file.bib>`. Returns a JSON list; each element has `key`, `candidates` (raw CrossRef records whose normalized title matches the entry, plus any DOI lookup result), and `error`. Each candidate also carries a `discrepancies` object keyed by field name. For every differing field it reports raw `entry` and `candidate` values, with missing values as `null`. This is informational only: there is no normalization, alias mapping, or judgment about which side is correct. Do not treat a missing candidate value as evidence that the bib field should be removed. Conversely, when a standard venue field (volume, number/issue, pages, etc.) is missing from the bib entry but a verified candidate provides a value, add it to your fix patch. The exception is `doi`: never inject a `doi` field into an entry that lacks one. Treat naming mismatches like `author` vs `authors` and `booktitle` vs `journal` as schema or cosmetic until verified otherwise. Only fold verified, substantive differences into your fix patch.
- **Wave A, mandatory web search for entries with no CrossRef hit**: for every entry where `error` is set or `candidates` is empty, launch a web-search subagent (see Parallel Verification below). These entries have now used their budget.
- **Per-entry decision pass**: for each entry, look at the bib fields, the candidates, and any Wave A result, then pick one outcome:
  - **Clean**: candidates confirm the entry. Do nothing, add no comments.
  - **Fix**: candidates clearly identify the right paper and fields need updating. Build a `fix` patch.
  - **Escalate**: candidates look wrong or ambiguous AND the entry has not used its budget. Queue for Wave B.
  - **Not found**: Wave A ran and neither CrossRef nor web search located the paper. Mark as `not_found`.
  - **Review**: the entry has used its budget and you are still uncertain. Do NOT modify the entry. Add a `% bibtidy: REVIEW, <what was confusing>` comment above it plus `% bibtidy: <URL>` lines for everything you inspected.
- **Wave B, escalation web search**: launch a second round of subagents for entries queued as Escalate. These entries have now used their budget.
- **Final decision pass**: re-run the per-entry decision for Wave B entries with the combined info. Outcomes are Clean, Fix, Not found, or Review, never Escalate (budget exhausted).
- **Apply fixes sequentially using `edit.py`**: write a real `patches.json` file with a JSON heredoc (e.g. `cat > patches.json <<'JSON' ... JSON`), then run `python3 $TOOLS_DIR/edit.py <file.bib> patches.json`. Do NOT construct the patches via a Python heredoc, `python3 -c`, or any other Python snippet piped into `edit.py -`, JSON and Python literal syntax disagree (`null`/`true`/`false` vs `None`/`True`/`False`) and a silent producer crash leaves `edit.py` reading an empty pipe. Do NOT edit the .bib file directly with agent editing tools (for example, Claude Code Edit or Codex `apply_patch`), and do NOT rewrite the entire file. `edit.py` merges by default: include a field in `fields` to set or update it, set it to `null` to remove it, omit it to leave it unchanged. Every `fix` patch MUST include `urls` and `explanation`. Use CrossRef and web-search values verbatim, do not rephrase. When the bib entry uses `and others` and a candidate gives the full author list, replace the truncated list with the complete one.
- **Post-fix exact/subset duplicate detection**: `python3 $TOOLS_DIR/duplicates.py <file.bib>`. Entries that were different before fixing may now be identical after metadata corrections. If the tool prints an `unresolved same-key collisions` warning, you MUST resolve every listed collision (see Duplicate Detection) and re-run `duplicates.py` until the warning is gone.
- **Review likely related entries manually** (see Duplicate Detection).
- Run format validation; fix violations and re-run until clean
- Delete backup: `rm <file>.bib.orig`
- Print a Markdown summary table with headers `Metric | Count` and these rows: total entries, verified, fixed, not found, needs review, exact duplicates removed, near-duplicates flagged.

## Parallel Verification with Subagents

Use subagents, when available, to run each web-search wave concurrently. If unavailable, do the same work sequentially. Cap at **6 subagents per wave** and distribute entries evenly (e.g. 18 entries → 3 per subagent). For ≤6 entries, use one subagent per entry.

**Agent prompt template** (identical for Wave A and Wave B, candidates may be empty):

```
Verify this BibTeX entry using web search. Return ONLY valid JSON, no markdown or conversational text.

Return JSON with keys:
  "key"          - the citation key
  "source_urls"  - list of URLs you inspected (DOI, venue page, arXiv, publisher)
  "fields"       - proposed fix-patch field values (dict), or null if nothing should change
  "notes"        - short explanation of what you verified or could not resolve

Use null inside "fields" to remove a stale field, or set "fields" to null entirely if the paper could not be located. Use CrossRef and publisher values verbatim.

When you locate the paper, inspect the authoritative page and verify the standard fields the venue publishes: title, full author list, year, journal/booktitle, volume, number/issue, pages, and DOI. Put a field into "fields" when the verified source differs from the bib entry's current value, or when the field is missing from the bib entry and the venue publishes a value for it. The exception is `doi`: if the entry already lacks a DOI, do not propose adding one just because you found it online; note the DOI in "notes" if it matters for verification. If a standard field is genuinely unavailable on the venue page, say so in "notes" instead of omitting it silently.

Entry:
<BIB ENTRY>

Candidates (may be empty):
<CANDIDATES JSON or "none">
```

## Duplicate Detection

Duplicate handling runs as two automated exact/subset passes (before and after metadata fixes) plus a manual near-duplicate review:

**Exact/subset duplicates** (same key, type, and one entry's fields are a subset of or equal to the other's): `python3 $TOOLS_DIR/duplicates.py <file.bib>` comments out the entry with fewer fields automatically. Run before and after metadata fixes.

**Same-key collisions** that the subset pass cannot resolve are reported by `duplicates.py` as an `unresolved same-key collisions` warning listing each citation key with the line numbers of the colliding active entries. Resolve each by applying a `duplicate` patch via `edit.py` to the weaker entries, or by reconciling fields with `compare.py --key <key>` + `edit.py` and re-running `duplicates.py`.

**Likely related entries** are judged by the agent, not by `duplicates.py`. Review suspicious pairs manually after metadata fixes. Strong clues include repeated citation keys, repeated DOIs under different keys, the same normalized title with overlapping authors, and obvious preprint→published pairs. When two entries should be linked but not auto-removed, apply a `duplicate` patch via `edit.py` to add `% bibtidy: DUPLICATE of <other_key>`. Do NOT delete or comment out near-duplicates.

## Per-Entry Checks

Candidates from `compare.py` expose the raw CrossRef fields (title, authors, year, journal, publisher, volume, number, pages, doi, type, url). A few gotchas when comparing:

- Missing `pages` in the bib is not an error, some venues (NeurIPS, ICLR, etc.) omit page numbers.
- If the bib entry is an arXiv/bioRxiv/chemRxiv preprint and a candidate is the published version, upgrade title, venue, year, volume, number, and pages together, not individually. The published title may differ substantively from the preprint (not just formatting or punctuation), so always replace the title verbatim with the candidate value rather than diffing the two.
- Never inject a `doi` field into an entry that lacks one. Use a DOI for verification and source URLs, but do not turn a missing DOI by itself into a fix patch.

## Saving Changes

- Use targeted replacements, not whole-file rewrites
- For large files (>30 entries), process in batches of ~15, reporting progress
- Verify entry count before and after, must match

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing `% bibtidy:` URL | Every `fix` patch needs a URL, use DOI URL or venue page |
| Incomplete commented original | Comment out ALL lines of the original, including closing `}` |
| Commenting unchanged entries | If candidates confirm the bib entry, leave it alone, no bibtidy comments |
| Deleting duplicate entries | Flag with comment only, never delete |
| Losing `@string`/`@preamble` blocks | Preserve verbatim, don't touch |
| Single hyphen in page ranges | Always use `--` (double hyphen) for BibTeX page ranges |
| Partially applying title changes | When a candidate's title differs, overwrite the title verbatim with the candidate value. Do not reinterpret the difference as a punctuation fix, a subtitle tweak, or a substring edit, replace the whole field. |
| Using agent editing tools instead of `edit.py` | Always use `edit.py`, never edit the .bib file directly with Claude Code Edit, Codex `apply_patch`, or similar tools |
| Building patches with a Python heredoc | Write `patches.json` via a JSON heredoc (`cat > patches.json <<'JSON' ... JSON`); Python uses `None`/`True`/`False`, JSON uses `null`/`true`/`false`, mixing them crashes the producer and leaves `edit.py` with empty stdin |
| Double-searching an entry | Each entry has a web-search budget of 1 |
| Forcing a fix when uncertain | After the budget is spent, add a `% bibtidy: REVIEW` comment instead of applying a guess |

## Preserve

- Entry order, all unchanged fields, empty lines between entries
- User comments (`%` lines not starting with `% bibtidy:`)
- `@string`, `@preamble`, `@comment` blocks
- LaTeX macros and brace-protected capitalization in titles
- If rate-limited, note and continue with next entry

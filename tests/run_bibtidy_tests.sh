#!/usr/bin/env bash
# Run bibtidy on the test fixture and validate the output.
#
# Usage:
#   ./tests/run_bibtidy_tests.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INPUT="$SCRIPT_DIR/bibtidy/fixtures/input.bib"
EXPECTED="$SCRIPT_DIR/bibtidy/fixtures/expected.bib"
GOT="$SCRIPT_DIR/bibtidy/fixtures/got.bib"
VALIDATOR="$SCRIPT_DIR/bibtidy/validate.py"
FORMAT_VALIDATOR="$REPO_DIR/skills/bibtidy/tools/fmt.py"

# Run unit tests first — fail fast before the slower Claude invocation
echo "=> Running unit tests..."
uv run pytest "$REPO_DIR/tests/" -v || { echo "=> Unit tests failed, aborting."; exit 1; }
echo ""

# Sync skill to installed location so /bibtidy uses the latest version
# Clean destination first to avoid stale files from renames/deletions
SKILL_SRC="$REPO_DIR/skills/bibtidy"
SKILL_DST="$HOME/.claude/skills/bibtidy"
rm -rf "$SKILL_DST"
mkdir -p "$SKILL_DST"
cp "$SKILL_SRC/SKILL.md" "$SKILL_DST/SKILL.md"
cp -r "$SKILL_SRC/tools" "$SKILL_DST/"
echo "=> Synced skill to $SKILL_DST"

# Copy input to got.bib — bibtidy edits this copy in-place
cp "$INPUT" "$GOT"
ORIG=$(mktemp)
cp "$INPUT" "$ORIG"
trap 'rm -f "$ORIG" 2>/dev/null' EXIT

ENTRY_COUNT=$(grep '^@' "$GOT" | grep -cv '^@\(string\|preamble\|comment\)')
echo "=> Found $ENTRY_COUNT entries in test fixture"
echo "=> Running bibtidy..."
echo ""

START_TIME=$SECONDS

claude -p "/bibtidy $GOT" \
    --allowedTools "Agent" "Bash(curl *)" "Bash(python3 *)" "Bash(cp *)" "Bash(rm *)" "Read" "Edit" "Write" "Glob" "Grep" "WebSearch" "WebFetch" \
    --verbose 2>&1

ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo "=> bibtidy complete in ${ELAPSED}s ($ENTRY_COUNT entries)."

FAILURES=0

echo ""
echo "=> Format validation..."
python3 "$FORMAT_VALIDATOR" "$ORIG" "$GOT" || FAILURES=$((FAILURES + 1))
rm -f "$ORIG"

echo ""
echo "=> Structural validation..."
echo ""
python3 "$VALIDATOR" "$GOT" || FAILURES=$((FAILURES + 1))

if [[ $FAILURES -gt 0 ]]; then
    echo ""
    echo "=> FAILED: $FAILURES check(s) did not pass"
    exit 1
else
    echo ""
    echo "=> ALL CHECKS PASSED"
fi

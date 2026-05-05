# Mechanical-lint prompt

For **lint-fix iteration only**, between QA-gate bounces. Use AFTER the QA gate has emitted a `revise` verdict with `blocking_issues` that are line-level edits — not for first-pass authoring or design changes.

Recommended local model: `qwen2.5-coder-3b-instruct-128k` (small, fast, sufficient for line-level edits).

---

## Your scope: line-level edits ONLY

You are NOT authoring or redesigning. You are fixing specific issues raised by the QA gate's critic. Read `<skill_id>.qa.md` for the issue list and address each one with the smallest possible edit.

Specifically:

- Fix synonym collisions in `domain_tags` (swap one tag for a better synonym)
- Fix missing position markers (add the marker text exactly per spec)
- Fix title-overlap in tag list (remove or rephrase the overlapping tag)
- Fix import discipline violations in code blocks (R2 — add missing `import`)
- Fix verification-item phrasing for mechanical-checkability (R3 — make the assertion grep-able)
- Fix `change_summary` phrasing for R6 honesty
- Fix word-count overflow by splitting one fragment into two with a clean boundary

## What you must NOT do

- Do NOT redesign skill boundaries (that's a Phase 1 design decision)
- Do NOT re-author fragments wholesale (that's Phase 2 authoring)
- Do NOT change the `raw_prose` field (would break R5.5 contiguity)
- Do NOT add or remove fragments (that's a structural decision, not a lint fix)
- Do NOT modify `skill_id`, `canonical_name`, `category`, `skill_class`, `tier` (these are design decisions)
- Do NOT fetch external docs (mechanical-lint is offline by design — if a fix requires a fetch, escalate, don't perform it here)

## Inputs you should expect

1. The current YAML at `skill-source/pending-revision/<skill_id>.yaml`
2. The QA gate's report at `skill-source/<skill_id>.qa.md` with `blocking_issues`, `per_fragment_notes`, `tag_verdicts`, `suggested_edits`

## Your output

1. The updated YAML written to `skill-source/pending-qa/<skill_id>.yaml` (move it back into the QA queue for re-gate)
2. A one-paragraph summary of what was changed and which `blocking_issues` were addressed

Do NOT emit explanatory prose beyond the one-paragraph summary. The QA gate will re-run and either approve, request another revision, or escalate to `needs-human/`.

## Bounce budget

The QA gate tracks how many times each skill has been revised. After 3 bounces (default `bounce_budget`), the next revise routes to `needs-human/` automatically. If you hit the bounce limit, the source SKILL.md is probably mis-shaped — go back to Phase 1 design rather than continuing to lint-fix.

## Refuse-clauses

Refuse to perform an edit if:

- The edit would change the contiguity of `raw_prose` (R5.5)
- The edit would require fetching an external doc (escalate to a tier-appropriate authoring prompt)
- The blocking_issue text is ambiguous about what specifically to change (escalate to operator)
- The edit would change a fragment's `fragment_type` (that's a structural design decision, not a lint fix)

## Stop conditions

STOP and declare if:

- The blocking_issue can't be addressed without redesigning fragment boundaries
- A semantic-lint failure (vs mechanical-lint failure) requires fragment-content rewrite — those need the tier-appropriate authoring prompt with full source-fetch discipline, not mechanical-lint
- The bounce budget is at 2 and the same blocking_issue keeps recurring (the lint-fix isn't actually addressing the root issue; escalate)

## Worked example

QA report says:

```
blocking_issue 1: webhook-patterns:5 verification item "rejects timestamps
older than 5 minutes" is not mechanically checkable. Add a grep pattern
or a test assertion.
```

Your edit: change the verification item from prose to grep-pattern + assertion:

```markdown
- [ ] Handler rejects timestamps older than 300 seconds with HTTP 400.
      `grep -nE 'abs\(time\.time\(\)\s*-\s*timestamp\)\s*>\s*\d+' src/`
      returns the tolerance check; the integer is ≤ 300.
```

That's a line-level edit. Move YAML back to `pending-qa/`. One-paragraph summary: "Addressed blocking_issue 1 in webhook-patterns:5 — replaced prose assertion with grep pattern and integer-bound check, satisfying R3 mechanical-checkability."

Done.

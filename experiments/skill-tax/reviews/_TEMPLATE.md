# Trial Review — `<trial_id>`

> Per spec §7.2. Review goal: tag failure_mode, failure_root_cause, and
> faithfulness_pass for one trial in 60–90s without opening fragment
> files or task fixtures. If the report doesn't enable that, it failed.

## 1. Header

| Field | Value |
|-------|-------|
| trial_id | `<uuid>` |
| task | `Tn` |
| arm | `arm_a` / `arm_b` / `arm_c` / `baseline` |
| run | `n` |
| trial_class | `arm_comparison` / `baseline` / `robustness` |
| temperature | `0.0` / `0.3` |
| parses | `True` / `False` |
| functional_pass | `True` / `False` / `None (deferred)` |
| fragment_count | `n` |
| in_tok / out_tok | `nnnn / nnn` |
| consistency_hash | `xxxxxxxx…` |
| harness notes | (verbatim from `pilot_trials.notes`, or `none`) |

## 2. Task description

> Verbatim user message from `tasks/<task>.yaml description`. Do not paraphrase.

```
<task description here>
```

## 3. Fragments provided

Numbered list of fragments the model received (extracted from the system
message, in document order). Show fragment_id, type, and the first ~80
chars of content so the reviewer can identify the fragment without
opening files.

| # | fragment_id | type | first 80 chars |
|---|-------------|------|----------------|
| 1 | `skill:n` | `procedure` | `…` |
| … | | | |

(For `arm=baseline`: "no fragments — baseline arm.")

## 4. Model response

```
<response verbatim, including [FILE: …] / [DECLINE: …] markers>
```

## 5. Mechanical check results

Re-run against the trial's response in a fresh worktree. Pull observed
values + `actually` (evidence) from `harness/rerun_checks.py <trial_id>`.
Rerun env state (DATABASE_URL set, postgres_reachable, ran_at) is also
emitted so reproducibility audits can distinguish env from model issues.

| check_id | type | result | observed | actually wrote | expected |
|----------|------|--------|----------|----------------|----------|
| `app-starts` | `app_starts` | ✅ / ❌ / ⏭ | `True` / `False` | openapi.json reachable | `True` |
| `code_grep` example | `code_grep` | ✅ / ❌ | `count=2` | `2 match(es); first: \`...\`` | `pattern ≥1` |
| `http` example | `http` | ✅ / ❌ | `status=500` | `body={"detail":"..."}` | `status=200, body⊇{...}` |
| … | | | | | |

Cross-checks (if any):

| cross_id | type | result | notes |
|----------|------|--------|-------|

## 6. Faithfulness checklist

For each fragment in §3, judge whether the model used it in the
response. Reviewer fills the `model_used_it` column.

| # | fragment_id | type | required_for_task | model_used_it | evidence |
|---|-------------|------|-------------------|---------------|----------|
| 1 | `skill:n` | `procedure` | `yes` / `no` | ☐ yes  ☐ no  ☐ n-r-b-p | `<reviewer fills>` |
| … | | | | | |

`required_for_task` heuristic (auto-filled): types `procedure`,
`guardrail`, `contract`, `interface`, `execution` → `yes`; types
`rationale`, `example`, `setup`, `verification` → `?` (reviewer overrides
based on task variant).

`n-r-b-p` = "not required but present" — the model imported a procedure
that wasn't strictly needed for the task variant.

For declines: this section reads "model declined; no fragments to
check." Move to §7.

## 7. Failure summary

> Only if `functional_pass != True`. One paragraph. Factual only — name
> the gap, don't hypothesize cause.
>
> Format: "Fragments specified X. Model produced Y. Mechanical evidence:
> check `<id>` failed because `<observed>` ≠ `<expected>`."

## 8. Tagging slots — reviewer fills

```
failure_mode:
  [ ] drift              [ ] hallucination     [ ] incomplete
  [ ] scope_violation    [ ] parse_error       [ ] wrong_skill
  [ ] composition_error  [ ] n/a (passed)

failure_root_cause:
  [ ] under_specified_procedure  [ ] missing_rationale
  [ ] missing_example            [ ] missing_setup
  [ ] verification_false_pass    [ ] scope_guard_too_weak
  [ ] composition_gap            [ ] composition_overlap
  [ ] model_capability           [ ] n/a (passed)

faithfulness_pass:
  [ ] yes  [ ] no  [ ] partial

failed_fragment:
  [ ] none  [ ] <skill:seq>  [ ] multiple  [ ] unattributable
```

## 9. Reviewer notes

<free text>

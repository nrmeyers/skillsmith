# Milestone 4 — Skill-Edit Re-Run + Architectural Finding

> 27 trials at temp 0.0 across T3a/T3b/T4 × 3 arms × 3 runs. Skill edits applied to `fastapi-middleware-patterns:2,6,8` per M3 synthesis §8 recommendations. T2 seed lifespan corrected. Harness state-combo bug fixed. Net result: identical 3/27 pass rate. Architectural finding overrides M3's skill-quality interpretation.

---

## 1. Headline

**M4 pass rate: 3/27 = 11.1%. Identical to M3 (3/27 on the same trials).** Skill edits did not move the metric.

| Cell | M3 pass | M4 pass | Δ |
|------|---------|---------|---|
| T3a arm_a | 0/3 | 0/3 | 0 |
| T3a arm_b | 0/3 | 0/3 | 0 |
| T3a arm_c | 0/3 | 0/3 | 0 |
| T3b arm_a | 0/3 | 0/3 | 0 |
| T3b arm_b | 0/3 | 0/3 | 0 |
| T3b arm_c | 0/3 | 0/3 | 0 |
| T4 arm_a | 3/3 | 3/3 | 0 (control holds) |
| T4 arm_b | 0/3 | 0/3 | 0 |
| T4 arm_c | 0/3 | 0/3 | 0 |
| **Total** | **3/27** | **3/27** | **0** |

H1 verdict from M3 stands. The skill-quality interpretation does not.

---

## 2. The model READS the guardrail and PARAPHRASES it — without acting on it

T3a arm_a r1 in M4 (trial `43d5e5c2`):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: open shared resources here
    # This is a placeholder for the existing lifespan logic from seed.
    # The actual implementation should be preserved verbatim from the seed file,
    # including any table creation, schema migrations, JWKS client init, etc.
    yield
    # shutdown: close shared resources here
```

The model received the new fragment text (token count +314 vs M3 confirms the additional guardrail content reached the prompt), understood the constraint at the language level, and **paraphrased the guardrail back as a comment** — while structurally violating it. The lifespan body is empty. The CREATE TABLE that the seed contains is not in the response.

This is not a fragment-quality failure. It is a system-design failure.

---

## 3. The architectural finding

**The `[FILE: <path>]` output format is incompatible with "preserve existing seed code" instructions when the seed code is not in the model's context.**

The model can only produce text. To "preserve" seed content in a `[FILE:]` block, the model must reproduce that content from memory or from the prompt. In the pilot's setup:

- **The seed file content is NOT in the prompt.** The model receives the governance preamble + fragments + task description. It does not see `pilot-seed/T3a:app/main.py`.
- **The task description describes the seed in prose** ("seed `app/main.py` carries an empty FastAPI app construction") but does not include the seed source.
- **The fragments contain lifespan templates** that the model echoes — first because they were the only structural reference (M3), now because they are the only structural reference even with a guardrail telling the model not to use them (M4).
- **The `[FILE: <path>]` output format requires the model to emit the entire file content.** A diff or patch format would let the model say "leave the lifespan alone, only add middleware," but `[FILE:]` requires reproducing every line.

The combined constraint is unsatisfiable: produce the complete file, preserve seed content you have not been shown. The model resolves the unsatisfiability by paraphrasing the guardrail in comments and emitting an empty-but-acknowledging stub.

This is the strongest result of the pilot. It tells you that **fragment-typed retrieval is necessary but not sufficient for build-phase tasks where the seed contains task-specific setup**. The retrieval must additionally inject the seed-file content into the prompt, or the output format must support patches/diffs that can leave seed content untouched.

---

## 4. Sub-pattern shifts (M3 → M4)

The skill edits did not improve any cell, but they did shift the *failure shape* in two cells:

| Cell | M3 lifespan body | M4 lifespan body | Shift |
|------|------------------|------------------|-------|
| T3a arm_a | pool init, no table | **empty stub with paraphrased guardrail** | regressed |
| T3a arm_b | pool init, no table | pool init, no table | unchanged |
| T3a arm_c | pool init, no table | pool init, no table | unchanged |
| T3b arm_a | empty `yield`-only | empty `yield`-only | unchanged |
| T3b arm_b | pool init, no table | pool init, no table | unchanged |
| T3b arm_c | `app.state.db = None  # placeholder` | empty stub | small shift |

T3a arm_a's regression is significant: M3's "pool init, no table" pattern produced *less* damage than M4's "empty stub." The new guardrail told the model "don't use the empty/pool-only templates," and the model responded by going *more* empty, with comments explaining why.

This reproduces the M3 architectural finding inverted: **fragment templates compete with task description. When a guardrail tells the model not to use the templates, the model degrades further rather than reproducing seed content it has not been shown.**

---

## 5. T4 invariance is also evidence

T4 arm_a passed 3/3 in both M3 and M4 — control holds. T4 arm_b/c failed 6/6 in both — composition_gap signal persists. The skill edits to fastapi-middleware-patterns:2,6,8 did not affect T4 because T4's fragment surface is webhook-patterns only. The arm-cell split for T4 (rationale + example fragments ARE load-bearing for execution) is independent of the lifespan-rewrite finding and remains the cleanest **spec-C1-refutation** evidence in the pilot.

T4's invariance under the M4 changes is what you'd expect from a clean A/B: the changes touched fastapi-middleware-patterns; the unaffected task (T4) didn't move. This is a positive signal that the trial machinery is reproducible.

---

## 6. Revised root-cause attribution for M3 trials

The M3 tagging marked 12 lifespan-rewrite trials with `under_specified_procedure`. M4's null result requires revising that attribution.

| Trial set | M3 root_cause | M4-revised root_cause |
|-----------|---------------|------------------------|
| T3a all 9 + T3b arm_b 3 | under_specified_procedure | **methodology_gap** (not in enum) — see below |
| T3b arm_a 3 | model_capability | **methodology_gap** (the empty stub is the model's refusal-shaped response to an unsatisfiable constraint) |
| T3b arm_c 3 | under_specified_procedure | **methodology_gap** |
| T4 arm_b/c 6 | composition_gap | **composition_gap** (unchanged; T4 result is independent) |

The locked enum does not contain `methodology_gap`. The closest available tag is `model_capability`, but the failure isn't really about model capability — a more capable model would face the same unsatisfiable constraint. The honest reading is that the failure mode lives outside the enum's design assumptions, which itself is a finding worth recording for milestone-5 enum revision.

For now, leave M3 tags in place and note the revision in synthesis. The aggregate metrics don't move; only the interpretation does.

---

## 7. Methodology recommendations (revised)

M3's recommendation #1 ("fix the fragments — add a lifespan-preservation guardrail") is now refuted. The skill-quality fix is a no-op because the underlying constraint is unsatisfiable.

The real fix is one of:

**Option A — inject seed-file content into prompt.** The harness reads the seed file and includes its content (verbatim, in a fenced block) in the user message before the task description. Cost: prompt size grows by ~30-100 tokens per seed file. Benefit: model has the seed content to reproduce. This is the closest to "fixing" the existing methodology.

**Option B — switch to patch/diff output format.** Revert the M3 decision to use `[FILE: <path>]` and revisit unified-diff or `[PATCH: <path>]` formats with stricter parsing. Cost: re-litigate the diff-parsing failures from Q10. Benefit: model never has to reproduce code it's preserving — it only emits the lines it changes.

**Option C — split tasks at the seed-preservation boundary.** Restructure T3a/T3b so the model only writes new files (e.g., `app/middleware.py`) rather than modifying `app/main.py`. The seed lifespan stays in `app/main.py` untouched; the model's output is a different file that gets composed at app construction. Cost: changes the task design. Benefit: makes the methodology work for the kinds of tasks the pilot was supposed to test.

**Option D — accept the constraint and limit pilot scope.** Acknowledge that fragment-typed retrieval works for greenfield single-file tasks (T1, T4 arm_a) and not for tasks requiring seed preservation. Document the constraint and move forward with the methodology where it applies. Cost: half the original pilot scope. Benefit: honest result.

My read: option A is the smallest delta and resolves the immediate constraint. Option C is the right longer-term answer if the architecture is going to support modify-existing-file tasks. Option B is a sunk-cost trap.

---

## 8. What the pilot actually concluded

Pulling together M3 + M4 (sub-claim labels reconciled with spec §1.1 on 2026-05-04):

1. **H1 (≥85% Arm B pass rate) fails at 20%.** Methodology + current skill content is not sufficient for the pilot's task domain.
2. **Failure mode is single-shape (`scope_violation`) and reproducible (Q10 1/10 distinct, robustness mirrors arm_b).**
3. **Spec C1 ("anchoring fragments NOT load-bearing") is REFUTED** by T4's arm-cell split (rationale + example dropping causes 3-trial gap, beyond the 2-trial threshold). Rationale + example ARE load-bearing for execution at this scale on T4-shape tasks. Other tasks have ceiling/floor effects so C1 evidence is T4-only.
4. **Spec C2 ("verification and guardrail load-bearing") is INCONCLUSIVE** — Arm B and Arm C tied at 20% pass rate, no measurable B-vs-C gap on this task surface.
5. **Spec C3 ("multi-skill composition works") is REFUTED strongly** — T3a 0% and T3b 0% across all arms vs T1 100%, gap of 9 trials per arm (vs 1-trial threshold). Composition fails as currently architected. The architectural finding (§7) explains why.
6. **Spec C4 ("fragments do distinctive work") HOLDS** — baseline 0/12 vs Arm B 3/15 (excl T5). Fragments grant the model permission to attempt where it would otherwise decline or hallucinate. Training-data confound concern refuted.
7. **Methodology gap surfaced by M4: `[FILE:]` output + missing seed content in prompt = unsatisfiable preservation constraint.** This is the architectural finding; it explains why M3's skill-quality fix didn't help and what the next pilot needs to address.

The numbers are bad. The signal is high. The methodology gap is concrete and fixable in a milestone-5 design.

---

## 9. Files

- `experiments/skill-tax/skills/fastapi-middleware-patterns.yaml` — edits to fragments :2, :6, :8 (preserved as the M4 skill state)
- `experiments/skill-tax/harness/run_m4.sh` + `run_m4.log` — re-run script + log
- `experiments/skill-tax/skills.duck::pilot_trials` — 93 + 27 = 120 rows; M4 trials are the most recent 27
- `experiments/skill-tax/reviews/_FINAL_SYNTHESIS.md` — M3 synthesis (still valid for M3 numbers; revision noted in §6 above)
- `experiments/skill-tax/reviews/_M4_SYNTHESIS.md` — this document

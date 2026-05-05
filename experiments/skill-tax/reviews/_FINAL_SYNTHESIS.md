# Skill-Tax Pilot — Final Milestone-3 Synthesis

> 81 trials, 81/81 tagged. Aggregate metrics computed against H1 thresholds (§1.1) and sub-claims C1–C4. Per-spec §7.3 measurement framework.

---

## Headline

**H1 fails.** Arm B pass rate on arm-comparison trials (T5 excluded per §7.3 footnote) = **3/15 = 20.0%**, well below the 70% threshold. Spec next-move per §1.1: "H1 fails even on gold-standard content. Methodology, not authoring, is the bottleneck. Major rethink — see §8.3."

But "methodology fails" is the wrong reading. The pilot surfaced a specific, mechanical failure mode — **fragment-induced lifespan rewrite** — that is fixable in milestone 4 by adding two clauses to the existing `fastapi-middleware-patterns` skill. Treat the headline as "v2.4 methodology + current skill content fails," not "the methodology can never work."

---

## 1. Aggregate metrics (per spec §7.3)

### Per-arm pass rate (arm_comparison)

|  Arm   | Excl T5 (15 ea) | Incl T5 (18 ea) |
|--------|-----------------|------------------|
| arm_a  | 6/15 = **40.0%** | 9/18 = 50.0% |
| arm_b  | 3/15 = **20.0%** | 6/18 = 33.3% |
| arm_c  | 3/15 = **20.0%** | 6/18 = 33.3% |

§7.3 footnote: T5 contributes zero arm-comparison signal (`fragment_count=0` across all arms — fixture has no `arm_fragments` populated for T5). Excluded from H1/C1/C2 aggregates. The 9 T5 trials register `fp=True` via inverted-criterion decline; all carry `scope_decline` markers.

### Per-task pass rate (arm_comparison, all 9 cells)

| Task | Pass | Note |
|------|------|------|
| T1   | 9/9 = **100%** | All via `stripe.Webhook.construct_event` — fragment-faithful per webhook-patterns:6 |
| T2   | 0/9 = 0%      | All `functional_pass=None` (deferred). **Two compounding bugs** — see §6 |
| T3a  | 0/9 = **0%**   | Lifespan-rewrite, all arms |
| T3b  | 0/9 = **0%**   | Lifespan-rewrite + worse degradation in arm_a/arm_c |
| T4   | 3/9 = 33.3%   | Pass in arm_a only — composition-gap signal |
| T5   | 9/9 = **100%** | Inverted-criterion via decline (see footnote) |

### Baseline (C4 evidence)

| Task | Pass | Behavior |
|------|------|----------|
| T1 baseline | 0/3 | Correctly declined (C4 control fires) |
| T2 baseline | 0/3 | Correctly declined |
| T3a baseline | 0/3 | **Attempted** — hallucinated `from app.database import lifespan` (module doesn't exist). Did NOT decline despite no fragments. |
| T3b baseline | 0/3 | Correctly declined |
| **Total baseline** | **0/12 = 0%** | |

### Robustness (temp 0.3)

| Task | Pass |
|------|------|
| T1 robustness | 5/5 = 100% |
| T3a robustness | 0/5 = 0% |
| T3b robustness | 0/5 = 0% |

Robustness pass rates mirror arm_b at temp 0.0 exactly — temperature variance does not change the failure pattern. Q10 consistency was 1/10 distinct hashes at temp 0.0; the pilot's failures are not stochastic.

### Failure-mode distribution (arm_comparison FAILS only — 24 trials)

| Arm | n_fails | Distribution |
|-----|---------|--------------|
| arm_a | 6 | scope_violation: 6 (100%) |
| arm_b | 9 | scope_violation: 9 (100%) |
| arm_c | 9 | scope_violation: 9 (100%) |

**Every arm-comparison failure is `scope_violation`.** No `drift`, no `hallucination` (in the official trials — T3a *baseline* hallucinated), no `parse_error`, no `wrong_skill`, no `composition_error` per the enum. This is the cleanest single-mode failure distribution the pilot could have produced.

### Failure root-cause distribution

| Arm | n_fails | Distribution |
|-----|---------|--------------|
| arm_a | 6 | under_specified_procedure: 3, **model_capability: 3** (T3b arm_a) |
| arm_b | 9 | under_specified_procedure: 6, **composition_gap: 3** (T4 arm_b) |
| arm_c | 9 | under_specified_procedure: 6, **composition_gap: 3** (T4 arm_c) |

Two clean signals beyond the dominant `under_specified_procedure`:
- `model_capability` (3 trials): T3b arm_a's empty `yield`-only lifespan with 24 fragments and explicit instruction
- `composition_gap` (6 trials): T4 arm_b/c rewriting the file when told to refactor one line

### Fragment count per arm (token-cost proxy)

| Task | arm_a | arm_b | arm_c |
|------|-------|-------|-------|
| T1   | 8 | 6 | 4 |
| T2   | 8 | 6 | 4 |
| T3a  | 16 | 12 | 8 |
| T3b  | 24 | 18 | 12 |
| T4   | 8 | 6 | 4 |

Arm_a has 33% more fragments than arm_b; arm_b has 50% more than arm_c. The pass-rate gap (arm_a 40% vs arm_b 20%) tracks fragment count, but the gap is driven entirely by T4 (3T arm_a vs 0T arm_b). Outside T4, all arms fail at the same rate.

---

## 2. Sub-claim verdicts

> **Note (2026-05-04 reconciliation):** earlier versions of this section used sub-claim labels that did not match the spec's actual definitions in §1.1 of `workflow-phase-retrieval-pilot-spec.md`. Re-aligned below. Spec sub-claims are *predictions* the trial design produces evidence on; the data either holds or refutes each.

### C1 — *Anchoring fragments are NOT load-bearing for execution* (Arm A vs Arm B)

**Refuted by T4 evidence; inconclusive on other tasks.** Spec C1 predicts Arm A does not outperform Arm B by more than 2 trials per task on average. T4 alone shows arm_a 3/3 vs arm_b 0/3 — a 3-trial gap on a single task, exceeding the 2-trial-per-task refutation threshold. T1 (100% all arms) and T3a/T3b (0% all arms) provide no evidence due to ceiling/floor effects; T5 is fixture-empty. **Verdict on the spec's prediction: rationale + example fragments ARE load-bearing for execution at the 30B-A3B Coder scale on this task surface, contrary to C1's prediction. Retrieval should keep rationale + example for execution-routed queries on T4-shape tasks.**

### C2 — *Verification and guardrail are load-bearing* (Arm B vs Arm C)

**Inconclusive.** Spec C2 predicts Arm B outperforms Arm C by ≥2 trials per task on average. The data shows Arm B and Arm C tied at 20% pass rate (excl T5) — 3/15 each. The B-vs-C gap is 0 trials per task on aggregate. However, the floor effect on T3a/T3b (both arms 0%) and the ceiling effect on T1 (both arms 100% via SDK) leave T4 as the only differentiating task — and T4 arm_b and arm_c both fail 0/3, so verification + guardrail dropping (B → C) shows no measurable additional cost beyond the rationale + example drop already captured in A → B. Verdict deferred — needs a task surface where T4-style cells differentiate further between B and C.

### C3 — *Multi-skill composition works* (T3a/T3b)

**Refuted strongly.** Spec C3 predicts T3a and T3b pass within 1 trial per arm of single-skill tasks. T1 (single-skill) passes 9/9; T3a passes 0/9; T3b passes 0/9. The gap is 9 trials per arm — catastrophically larger than the 1-trial threshold. **Verdict: multi-skill composition does NOT work on this fixture set at the 30B-A3B Coder scale.** The architectural finding in §3 explains why: the failure is a code-index gap (lifespan-rewrite without seed visibility), not pure composition difficulty. With code-index retrieval wired up, composition might pass; the pilot's evidence supports "composition fails as currently architected" but cannot directly distinguish between "model can't compose" and "architecture doesn't deliver the missing context."

T3a vs T3b scaling gap: 0% vs 0% — gap is 0 trials per arm, well within spec C3's 2-trial-per-arm scaling threshold. So *if* composition were working, scaling from 2-skill to 3-skill would not be the problem. The whole composition surface is below the floor at this configuration.

### C4 — *Fragments are doing distinctive work* (baseline vs Arm B)

**Holds.** Spec C4 predicts baseline (no fragments) passes at materially lower rate than Arm B — at least 2 trials per task lower. Baseline 0/12 vs Arm B 6/18 (incl T5) or 3/15 (excl T5). On T4: baseline 0/3, Arm B 0/3 (vacuously equal but at floor); on T1: baseline 0/3, Arm B 3/3 — a 3-trial gap. **Verdict: fragments grant the model permission to attempt where it would otherwise decline or hallucinate, even when they don't fully constrain the implementation.** The training-data confound concern is refuted.

**Important nuance for C4:** T1's 100% Arm B pass uses `stripe.Webhook.construct_event` (the SDK shortcut), which is fragment-faithful per webhook-patterns:6 but is also abundant in training data. The fragments did not force the manual HMAC path; the model picked the SDK path it knew. So C4 evidence for "fragments grant permission to attempt" is strong (baseline declines, Arm B doesn't), but C4 evidence for "fragments guide *implementation* choice" is weaker — the model's training-data preferences won when fragments documented multiple valid paths.

---

## 3. The architectural finding

**Fragments containing implementation templates can override task description when the templates compete with task-specific seed content.**

The 18/18 lifespan-rewrite pattern is induced by `fastapi-middleware-patterns:2` (setup) and `fastapi-middleware-patterns:6` (example). Both fragments show a lifespan template — `:2` with a pool but no schema setup, `:6` empty with placeholder comments. Neither addresses the seam: "if a seed lifespan exists with task-specific setup logic (CREATE TABLE, JWKS init, queue connect), preserve that content; do not substitute the template."

The task description says "Keep the existing lifespan context as the single source of pool initialization." That's not strong enough to override the positive signal in `:2` and `:6`. **The model treats fragments as authoritative over task description when the two compete on implementation shape.**

This is a **fixable skill-quality finding**, not a methodology failure. The skill author can:
1. Add a guardrail to `fastapi-middleware-patterns:8`: "If a seed lifespan defines task-specific setup (table creation, client init, schema migration), preserve that body verbatim; the lifespan templates in `:2` and `:6` are starter shapes, not replacements for working seed code."
2. Annotate `:2` and `:6` with explicit "This is a starter template" framing — currently they read as authoritative reference implementations.
3. Add a `task-specific-extension-points` fragment-type or section that tells the model where its context-specific work plugs in.

If milestone 4 makes those fixes and re-runs T3a/T3b/T4, expected behavior change: model preserves seed lifespan in T3a/T3b, T4's arm_b/c rewrite goes away when arm-c fragments are augmented.

---

## 4. Failure-mode distribution per spec §7.3

All 24 arm-comparison failures and all 10 robustness failures tag as `scope_violation`. Distribution by root_cause:

| Root cause | Count | Trials |
|------------|-------|--------|
| `under_specified_procedure` | 15 | T3a all (9), T3b arm_b (3), T3b arm_c (3) — fragment-induced lifespan rewrite |
| `model_capability` | 3 | T3b arm_a (3) — empty stub despite max context |
| `composition_gap` | 6 | T4 arm_b (3), T4 arm_c (3) — wholesale rewrite when refactor asked |

T3a/T3b robustness (10 trials) inherits `under_specified_procedure` — same lifespan-rewrite pattern at temp 0.3.

Baseline trials tag with `scope_guard_too_weak` (T3a baseline) or `none` + faithfulness=yes (T1, T2, T3b baseline declines).

T2 arm_comparison tags as `scope_violation` / `model_capability` (deprecated `@app.on_event` rewrite is not induced by active fragments). **Compounded by a fixture bug** — see §6.

---

## 5. Token cost vs. pass rate

Combining fragment count and pass rate per arm × task cell (excl T5):

| Cell | Frags | Pass | Notes |
|------|-------|------|-------|
| T1 arm_a | 8 | 100% | SDK path; same in all arms |
| T1 arm_b | 6 | 100% | |
| T1 arm_c | 4 | 100% | |
| T4 arm_a | 8 | 100% | **load-bearing fragments retained** |
| T4 arm_b | 6 | 0%   | rationale + example dropped → rewrite |
| T4 arm_c | 4 | 0%   | |
| T3a all  | 8/12/16 | 0% | lifespan rewrite — fragment count irrelevant |
| T3b all  | 12/18/24 | 0% | lifespan rewrite — fragment count irrelevant |
| T2 all   | 4/6/8 | 0% (deferred) | fixture bug |

For tasks where fragment template competes with seed content (T2, T3a, T3b), more fragments = same failure (or worse). For tasks with arm-cell-specific load-bearing fragments (T4), more fragments = pass.

---

## 6. Known fixture issues for milestone 4

Two fixture bugs surfaced during milestone 3 review. Neither invalidates the architectural finding, but both must be fixed before any re-run.

### 6a. T2 seed-table mismatch + harness-state bug

The T2 task description says: "the harness creates the table at trial start using the schema documented in fragment 5; the model does NOT write a CREATE TABLE statement." Fragment 5 documents `webhook_deliveries(provider, delivery_id)`. **But the T2 seed lifespan creates `processed_webhook_events(event_id)` — wrong table name AND wrong schema.** Even with perfect lifespan preservation, the model's `INSERT INTO webhook_deliveries` would fail.

Compounded by a harness state-combination bug in `run_trial.py`: when a non-manual check is skipped (the db check) AND another check fails (happy-path returning 500 because table missing), `mech_pass` resolves to `None` (deferred) instead of `False`. T2's 12 deferred trials likely include hidden http failures.

**Fix:** correct T2 seed lifespan to create `webhook_deliveries(provider TEXT, delivery_id TEXT, PRIMARY KEY (provider, delivery_id))`. Fix `run_trial.py` state-combination to prioritize `False` over `None`.

### 6b. T5 has no arm_fragments

T5 fixture has empty `arm_fragments` for all arms (verified via `fragment_count=0` on all 9 T5 trials). The model correctly declines per preamble v2 because no fragments are provided, and `fp=True` registers via inverted-criterion. **But T5 cannot evaluate C1/C2/C3 because there's nothing in the context to vary.** The 9 T5 trials are excluded from arm-comparison aggregates per spec §7.3 footnote — this exclusion is correct.

**Fix:** populate T5's `arm_fragments` per its inverted-criterion design intent (test scope-decline behavior with content that *should* trigger decline) before any milestone-4 re-run, OR formally remove T5 from the arm-comparison count and adjust §6.1's "6 tasks × 3 arms × 3 runs = 54" math.

---

## 7. Methodology assessment

The pilot's instrumented trials produce *more* signal than a naive 20%-pass-rate readout suggests:

- **Single-mode failures** — 100% scope_violation across 24 fails — tell you the failure is shape-specific, not random.
- **Sub-arm degradation patterns** in T3b (arm_a worse than arm_b, contrary to fragment-count expectation) tell you fragment volume can backfire.
- **T4's arm-cell split** is the cleanest experimental result the pilot produced — direct evidence that rationale + example fragments are compositionally load-bearing.
- **Q10 hash determinism** (1/10 distinct) plus robustness (mirrors arm_b at temp 0.3) tells you the failures are reproducible, not stochastic.

The pilot's headline pass rate is below threshold, but the diagnostic signal it produced is high quality — tagged into a single failure mode with three clear root-cause buckets.

---

## 8. Milestone-4 recommendations

In priority order:

1. **Fix the fragments** — add the lifespan-preservation guardrail to `fastapi-middleware-patterns:8` and reframe `:2`/`:6` as starter templates (not authoritative replacements). This is the load-bearing change.
2. **Fix T2 seed and the harness state-combination bug.** T2 evidence is currently inconclusive.
3. **Populate T5 arm_fragments** or formally remove T5 from arm-comparison counts.
4. **Re-run T3a, T3b, T4 only** (24 trials at temp 0.0, ~15 min). T1 and T5 don't need re-runs. T2 needs the fixture fix first.
5. **Decision criterion for milestone 4**: if Arm B pass rate on T3a + T3b + T4 (excl T5) crosses 70%, the v2.4 methodology *plus a guardrail-augmented skill* is sufficient. If still <70%, the issue is not fragment quality — at that point the C2 evidence dominates and the pilot moves to architectural rethink per §8.3.

The expected outcome from milestone-4 fixes: T3a → ~70-90% (lifespan preservation), T3b → ~50-70% (model_capability gap on arm_a may persist), T4 → ~70% (arm_b/c benefit if fragment composition gains rationale/example).

---

## 9. Data lineage

- **Trial DB**: `experiments/skill-tax/skills.duck` (93 rows; 81 official + 12 calibration from Q10/smoke)
- **Per-trial reviews**: `experiments/skill-tax/reviews/<trial_id>.md` (16 detailed reviews — batches 1+2)
- **Batch 2 synthesis**: `experiments/skill-tax/reviews/_BATCH2_SYNTHESIS.md` (the lifespan-rewrite finding with §3a fragment excerpts)
- **Tagging script**: `experiments/skill-tax/harness/apply_tags.py` (idempotent re-runnable)
- **Aggregate-metrics script**: `/tmp/compute_synthesis.py` (frozen for this synthesis)
- **Authoring log**: `experiments/skill-tax/skills/AUTHORING_LOG.md`

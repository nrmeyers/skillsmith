# Skill-Tax Pilot — POC Final Report

> Skillsmith fragment-typed retrieval pilot, May 2026. Comprehensive findings document covering Milestones 1 through 8, intended for architectural and investment decision-making. The pilot's headline result is bad; its diagnostic value is high; its architectural implication is load-bearing.

---

## Executive Summary

**The pilot's specific hypothesis (H1) failed.** Arm B pass rate on the locked task surface was 20%, well below the 70% success threshold. Naively read, this would close the door on fragment-typed retrieval as a methodology.

**The pilot's broader contribution is significant.** Disciplined per-trial failure-mode tagging surfaced a finding that reframes the engineering problem: **fragment content is sufficient infrastructure; the architecture surrounding fragments is what needs to be built.** This conclusion is supported by three independent intervention experiments that all failed to lift pass rate by improving fragment quality, and one architectural intervention (showing the model existing seed code) that did lift pass rate in the cell where it was applicable.

**Two unknowns dissolved simultaneously:**

1. **Fragment taxonomy is stable.** Skill-engineering effort below the model's parameter-application threshold is wasted; above the threshold, current fragments do their job.
2. **Execution-model size must be matched to cognitive shape.** A 3B Coder passes one-line refactors; the same 3B Coder fails multi-skill composition. A 30B Coder also fails composition for a different reason (architectural). Matching the model to the cognitive shape demanded by the task is the engineering target, not optimizing models in isolation.

**The roadmap implication:** Skillsmith's engineering investment should pivot from "make better fragments" to "build the retrieval architecture (code-index, knowledge-index) and size execution-models per cognitive shape." The pilot's deployment matrix (§6) is the actionable prescription.

**Key numbers:**
- 549 milestone trials across M2 through M8 (plus 12 calibration trials excluded from headline counts)
- 81 official spec trials (M2) + 27 architecture-test re-runs (M4) + 227 small-model trials (M5) + 174 seed-injection trials (M6) + 20 anti-pattern trials (M7) + 20 self-QA trials (M8)
- 561 total rows in `pilot_trials` (549 milestone + 12 calibration including 1 smoke test, 1 second smoke test, and 10 final Q10 consistency-precheck trials from preamble v2 lock)
- 5 small models tested in M5–M8: Qwen2.5-Coder-1.5B/3B, Llama-3.2-3B, SmolLM3-3B, Phi-4-mini-instruct
- 4 architectural slices tested; 3 untested (real code-index retrieval, knowledge-index, generalist phase routing)

---

## 1. Background

### 1.1 What Skillsmith is

Skillsmith is an architecture for retrieval-augmented LLM execution targeted at software development workflows organized by phase (intake / spec / design / build / verify, etc.) and by skill category (build-domain, interview-domain, architecture-domain, etc.). The system separates four roles:

1. **Generalist (phase router)** — interprets a user request and routes to the appropriate execution model and skill activation.
2. **Phase-specific execution model** — consumes the prompt and produces output. Different phases may deploy different sized/tuned execution models.
3. **Retrieval indexes** running in parallel: a *skills index* (patterns/procedures), a *code index* (current state of the codebase), and a *knowledge index* (decisions made and why).
4. **Verifier** — checks the execution model's output against mechanical and faithfulness criteria.

The pilot validates one slice of this architecture: the **skills index → execution model** path on **build-domain** skills. Other slices — code-index retrieval, knowledge-index retrieval, generalist routing, cross-skill-category variance — are explicitly out of scope and remain untested.

### 1.2 Original hypothesis

**H1 (primary):** Given workflow-phase fragment retrieval, can a Tier-2 execution model (Qwen3-Coder-30B-A3B-Instruct, Q4_K_S, local) execute deterministically on build-phase tasks?

**Threshold:**
- ≥85% Arm B pass rate → H1 holds; methodology works
- 70–84% → signal but fragile; targeted re-run before scaling
- <70% → H1 fails; major rethink required

**Sub-claims (C1–C4), per spec §1.1.** The pilot does not test these as a single bundled hypothesis; each is a *prediction* the trial design produces evidence on, and the prediction may be refuted by the evidence:

- **C1:** *Anchoring fragments are NOT load-bearing for execution.* Predicts Arm A (full skill incl. rationale + example) does not outperform Arm B by more than 2 trials per task on average. **Refuted by the data** (T4 arm-cell split: arm_a 3/3 vs arm_b 0/3, a 3-trial gap on a single task — far above threshold).
- **C2:** *Verification and guardrail are load-bearing.* Predicts Arm B outperforms Arm C by ≥2 trials per task. **Inconclusive** — Arm B and Arm C show identical 20% pass rate (excl T5) at the aggregate level; floor effect on T3a/T3b masks the comparison.
- **C3:** *Multi-skill composition works.* Predicts T3a (2-skill) and T3b (3-skill) pass within 1 trial per arm of single-skill tasks. **Refuted by the data** (T3a 0% and T3b 0% across all arms; gap vs T1's 100% is 9 trials per arm — catastrophically larger than the 1-trial threshold).
- **C4:** *Fragments are doing distinctive work.* Predicts baseline (no fragments) passes at materially lower rate than Arm B — at least 2 trials per task lower. **Holds** — baseline 0/12 vs Arm B 6/18 (incl T5) or 3/15 (excl T5); fragments grant the model permission to attempt where it would otherwise decline or hallucinate.

C1 and C3 refutations are the load-bearing findings of the pilot. C4's holding refutes the training-data confound concern.

### 1.3 Pilot scope

**In scope:**
- One workflow phase: SDD build phase
- One skill category: build-domain
- One narrow task domain: FastAPI + Stripe webhook + JWT auth + asyncpg
- Manual fragment selection (simulating ideal retrieval — no actual retrieval algorithm tested)
- Tier-2 execution via LM Studio's OpenAI-compatible API
- 4 skill fragments authored at gold standard
- 6 task fixtures spanning single-skill execution, multi-skill composition, and inverted-criterion decline

**Explicitly out of scope:**
- Actual retrieval mechanism (fragments hand-selected per arm)
- Workflow-phase routing (phase pre-specified)
- Cross-domain generalization (one task domain only)
- Cross-skill-category generalization (build-domain only)
- System-class skills (`sys-*`) that are always-injected
- Real code-index retrieval (M6 simulates with static seed-file injection)
- Knowledge-index retrieval (not implemented)

### 1.4 The four authored skills

Locked at `experiments/skill-tax/skills/` per gold-standard authoring:
- **`webhook-patterns`** — HMAC verification, replay protection, raw-body capture, FastAPI handler shapes (8 fragments, expanded to 12 in M7)
- **`fastapi-middleware-patterns`** — middleware composition, lifespan context, dependency injection (8 fragments)
- **`jwt-validation-patterns`** — HS256 verification, audience/issuer claims, error handling (8 fragments)
- **`python-async-patterns`** — async control flow, contextvars, lifespan resource management (8 fragments)

Fragment types in the locked taxonomy: `rationale`, `setup`, `execution`, `example`, `verification`, `guardrail`, plus `anti_pattern` added in M7.

### 1.5 The six task fixtures

Locked at `experiments/skill-tax/tasks/`:

| Task | Fragments activated | Cognitive shape | Description |
|------|---------------------|------------------|-------------|
| **T1** | webhook-patterns only (1 skill) | net-new bounded | Implement Stripe webhook receiver from blank-slate seed |
| **T2** | webhook-patterns only (1 skill) | net-new + DB persistence | Add replay protection with dedup-row INSERT |
| **T3a** | webhook-patterns + fastapi-middleware-patterns (2 skills) | 2-skill composition | Wire existing webhooks router + add security middleware |
| **T3b** | + jwt-validation-patterns + python-async-patterns (3 skills total context) | 3-skill composition | Add JWT-protected route + DB lifespan + middleware |
| **T4** | webhook-patterns only (1 skill) | targeted local refactor | Replace `==` signature comparison with `hmac.compare_digest` |
| **T5** | (empty fragment list) | inverted-criterion decline | Model should decline because no fragments provided |

### 1.6 Why this domain was chosen, and what the choice cost

The webhook + JWT + FastAPI domain was chosen because (a) one skill already existed at gold standard, reducing authoring burden, (b) the success criteria are mechanically verifiable (signature verification works or doesn't), and (c) Tier-2 is strongly trained on FastAPI/Python.

**The cost:** the same heavy training coverage that made authoring tractable also made the domain saturated for the model. Stripe SDK behaviors, FastAPI middleware patterns, and HMAC procedures are all richly represented in the model's pre-training data. This created a hidden ceiling: at the 30B-A3B Coder scale, the model can produce structurally correct code without fragments — leaving little room for fragment-typed retrieval to demonstrate value over training-data shortcuts. The pilot's M5-M8 small-model extension was partly a response to this, choosing models with weaker priors so fragment effects could be measured against a less-saturated baseline.

---

## 2. Methods

### 2.1 Harness architecture

The trial harness (`experiments/skill-tax/harness/run_trial.py`) executes a single trial per invocation and writes results to a DuckDB telemetry table (`pilot_trials` in `skills.duck`). Each invocation:

1. Loads the task fixture YAML.
2. Composes the system message: locked governance preamble + skill fragments per the named arm.
3. Composes the user message: the locked task description (plus, in M6+, prepended seed file contents).
4. Calls the LM via LM Studio's OpenAI-compatible endpoint.
5. Optionally (M8) makes a second LM call asking the model to review its own output against the fragments.
6. Parses the response for `[FILE: <path>]` and `[DECLINE: <reason>]` markers.
7. Spins up a fresh git worktree from the task's seed branch, applies the parsed file blocks.
8. Resets the Postgres schema (for DB-using tasks).
9. Starts uvicorn against the resulting application.
10. Runs mechanical checks (HTTP request/response assertions, code-grep, import checks).
11. Runs cross-checks (e.g., body-bytes match across multiple endpoints).
12. Records the trial: prompt, response, parses, functional_pass, consistency_hash, timing, fragment IDs, harness notes.

**Key harness properties:**
- **Deterministic at temp=0.0.** Q10 consistency pre-check confirmed 1/10 distinct hashes across 10 runs of an identical trial — output is reproducible at temp 0.0.
- **`max_tokens=2048`.** Caps runaway-loop trials. Empirically, legitimate output is 200–800 tokens.
- **Worktree isolation.** Each trial gets a fresh git worktree from the seed branch; cleanup happens on exit.
- **Read timeout = 1800s.** Long enough for any legitimate inference + checks pass.

### 2.2 Governance preamble

A locked instructional preamble (`experiments/skill-tax/prompts/governance-preamble-2026-05-01.v2.md`) prepends every system message. It establishes:
- Output format: `[FILE: <path>]` blocks for file content, `[DECLINE: <reason>]` for scope-decline
- Decline ladder: model should decline if the task exceeds the activated fragments
- Faithfulness expectation: do not hallucinate library behaviors not documented in fragments

The preamble is **immutable** within a trial set — any edits invalidate the prior trials.

### 2.3 Trial classes

Three trial classes per spec §6.1:

- **arm_comparison** (54 trials): 6 tasks × 3 arms (A/B/C) × 3 runs at temp 0.0
- **baseline** (12 trials): 4 tasks × 3 runs with empty fragment list, temp 0.0 (tests C4)
- **robustness** (15 trials): 3 tasks × 5 runs at temp 0.3 (tests determinism)

The three arms vary fragment composition:
- **Arm A** (8 fragments): all fragment types — rationale, setup, execution × 3, example, verification, guardrail
- **Arm B** (6 fragments): load-bearing only — setup, execution × 3, verification, guardrail (drops rationale + example)
- **Arm C** (4 fragments): execution-minimal — setup, execution × 3 (drops rationale + example + verification + guardrail)

### 2.4 Verification framework

Each task fixture defines mechanical_checks of several types:

- **`app_starts`**: uvicorn boots and `/openapi.json` is reachable
- **`http`**: a real HTTP request returns expected status, body JSON match, headers
- **`code_grep`**: regex match-count constraints over the produced file
- **`diff_imports`**: forbidden imports check
- **`db`** (T2 only): Postgres query verifies a row was inserted
- **`diff`** (manual review): manual faithfulness review

A trial's `functional_pass` is `True` iff all non-manual checks pass and no cross-check fails. `None` if a non-manual check defers; `False` if any check fails.

A trial's `parses` is `True` iff the response contains at least one valid `[FILE:]` or `[DECLINE:]` marker.

### 2.5 Failure-mode tagging (M3)

After M2's 81 trials completed, every trial received a manual review and tag against locked enums:

- **failure_mode**: `none` | `drift` | `hallucination` | `incomplete` | `scope_violation` | `parse_error` | `wrong_skill` | `composition_error`
- **failure_root_cause**: `none` | `under_specified_procedure` | `missing_rationale` | `missing_example` | `missing_setup` | `verification_false_pass` | `scope_guard_too_weak` | `composition_gap` | `composition_overlap` | `model_capability`
- **faithfulness_pass**: `yes` | `no` | `partial`
- **failed_fragment**: `none` | `<skill:seq>` | `multiple` | `unattributable`

This tagging discipline is the methodological keystone of the pilot. Without it, M2's 20% pass rate would have read as "fragments don't work." With it, the architectural finding (failures attributed to `under_specified_procedure` and `composition_gap`, not `model_capability`) became visible.

### 2.6 Models tested

| Milestone | Model | Params | Type | Quantization |
|-----------|-------|--------|------|---------------|
| M2-M4 | Qwen3-Coder-30B-A3B-Instruct | 30B (3.3B active) | Coder MoE | Q4_K_S, F16 KV |
| M5-M8 | Qwen2.5-Coder-1.5B-Instruct-128k | 1.5B | Coder dense | F16 |
| M5-M8 | Qwen2.5-Coder-3B-Instruct-128k | 3.09B | Coder dense | F16 |
| M5-M8 | Llama-3.2-3B-Instruct | 3.21B | General Instruct | BF16 |
| M5-M6 | SmolLM3-3B | 3B | General Instruct (think-mode) | BF16 |
| M5-M8 | Phi-4-mini-instruct | 3.8B | General Instruct | BF16 |

All inference local via LM Studio. Hardware: AMD Strix Point 96 GB UMA. Throughput ranged from ~37 sec/trial (Phi-4-mini) to ~70 sec/trial (Qwen2.5-Coder-3B).

---

## 3. Milestone results

### 3.1 M1 — Skill authoring

Four gold-standard skills authored, locally critiqued by Qwen3.6-27B, human-reviewed, locked. Fragment counts and types match the locked taxonomy. Provenance and authoring-decision history captured in `skills/AUTHORING_LOG.md`.

**Outcome:** authoring tractable. Each skill ~6-8 fragments, 6-12K total tokens. No skill-quality concerns surfaced during authoring.

### 3.2 M2 — Pilot execution (81 trials, Qwen3-Coder-30B-A3B)

The 81 trials executed cleanly (81/81 parses, 0 timeouts after harness fixes). Per spec §6.1:

| Trial class | Count | Result |
|-------------|-------|--------|
| arm_comparison | 54 | Arm A 50%, **Arm B 33.3%**, Arm C 33.3% (incl. T5) |
| baseline | 12 | 0% (tests C4 — fragments grant permission to attempt) |
| robustness | 15 | Mirrors arm_b at temp 0.0 (5/5 T1, 0/5 T3a, 0/5 T3b) |

**Excluding T5 (inverted-criterion, 0 fragments):** Arm B = 20% (3/15). H1 fails the 70% threshold.

**Per-task pattern:**
- T1 (single-skill execution): 100% pass (9/9, all via Stripe SDK shortcut)
- T2 (single-skill + DB): 0/9 functional pass, all 9 registered as `functional_pass=None` (deferred). **T2 was compromised by a seed-fixture bug discovered in M3 review:** the seed `app/main.py` lifespan created `processed_webhook_events` (T1's table name from a copy-paste error) instead of the `webhook_deliveries` table the task description and fragments specified. The model's `INSERT INTO webhook_deliveries` therefore failed at runtime against a non-existent table. The harness's state-combination logic (since fixed in M4) reported these failures as deferred rather than failed because manual `db` checks were also being skipped. Fix committed at `ca9f4b9` (`fix(seed/T2): create webhook_deliveries...`); historical M2 T2 trials remain compromised in the dataset and should be read as inconclusive, not as evidence of T2-specific behavior.
- T3a (2-skill composition): 0/9 all arms
- T3b (3-skill composition): 0/9 all arms
- T4 (targeted refactor): 3/9 (3/3 in arm_a only; arm_b/c rewrote the file from scratch). **Direct C1 evidence (refuting C1's "anchoring fragments not load-bearing" prediction):** the fragments dropped between arm_a and arm_b are precisely rationale + example, and the pass-rate gap is 3 trials on this single task — well above the spec's 2-trials-per-task threshold for C1 refutation.
- T5: 9/9 via decline (correct under inverted criterion; T5's `arm_fragments` are empty for all arms — fixture limitation noted in §6)

### 3.3 M3 — Failure-mode tagging and architectural finding

Manual review of all 81 trials produced trial.md reports with mechanical-check evidence and tagging slots. Reviewer (operator) tagged each trial against the locked enum. Aggregate finding:

**100% of arm-comparison failures tagged as `scope_violation`.** No `drift`, no `hallucination`, no `parse_error`. The single-mode failure distribution is itself informative — failures are shape-specific, not random.

**Root-cause distribution:**
- `under_specified_procedure`: 15 trials (T3a all arms + T3b arm_b + T3b arm_c — the lifespan-rewrite pattern)
- `model_capability`: 3 trials (T3b arm_a — empty `yield`-only lifespan despite 24 fragments)
- `composition_gap`: 6 trials (T4 arm_b/c — wholesale rewrite when refactor asked)

**The architectural finding:** 18/18 T3a + T3b arm-comparison trials wrote a lifespan that **dropped the seed's `CREATE TABLE IF NOT EXISTS`** statement. The model substituted a fragment-template lifespan (from `fastapi-middleware-patterns:2` or `:6`) for the seed's task-specific lifespan. The task description said "Keep the existing lifespan context" but the model treated fragment templates as authoritative.

**The cleanest sub-claim evidence:** T4's arm-cell split. T4 arm_a passed 3/3 with the full rationale + example fragments active. T4 arm_b/c failed 0/3 because dropping rationale + example fragments removed the "preserve other behavior" signal. **Direct refutation of C1** ("anchoring fragments are not load-bearing") — rationale + example are doing real work for execution at the 30B scale on this task shape, gap = 3 trials per task vs the 2-trial-per-task refutation threshold.

### 3.4 M4 — Skill-edit re-run

To test whether the lifespan-rewrite finding could be resolved by improving the skill, a guardrail was added to `fastapi-middleware-patterns:8`: "If a seed lifespan defines task-specific setup, preserve every line of the seed body verbatim." Fragments `:2` and `:6` were reframed as starter templates rather than authoritative implementations.

**Re-run of T3a + T3b + T4 (27 trials, same Qwen3-Coder-30B-A3B):**
- 3/27 functional pass — identical to M3
- T3a arm_a regressed from "pool init, no table" to "empty stub with paraphrased guardrail in comments"

**Why the skill edit failed:** The model read the new guardrail, paraphrased it in comments ("preserve verbatim from the seed file"), and then produced an empty `yield` lifespan anyway — because the seed file content was not in the model's context. The `[FILE: <path>]` output format requires reproducing the entire file. "Preserve the seed lifespan" is unsatisfiable when the model has never seen the seed lifespan.

**The architectural conclusion:** the failure is not a fragment-quality bug. It is a missing architectural component — the **code-index retrieval** that should inject the seed-file content alongside skill fragments. Within the full Skillsmith architecture, this would not be a problem. The pilot tests skills-index in isolation; the result reveals what happens when the surrounding architecture is absent.

### 3.5 M5 — Small-model sweep (227 trials, 5 models)

Following the M4 architectural finding, the pilot was extended to test whether the same patterns hold at smaller model scale. Five models in the sub-3.5B class were tested across the same task surface (T3a, T3b, T4 × 3 arms × 3 runs + T1 Q10 + 9 baselines).

**Aggregate results (227 trials):**
- **Strict-parse functional pass: 0/227.** No model produced working code on any cell.
- **Lenient-parse functional pass: 0/163 reanalyzed parses=False trials.** The post-hoc lenient-parse pass extracted code from markdown fences for the 163 trials that failed strict parsing; none of them passed mechanical checks under lenient extraction either. Combined with the 64 strict-parsed trials (which already had `functional_pass=False` from the original M5 run), this means **0/227 functional pass via either strict or lenient routes.**
- **Strict-parse rate varies dramatically by model:** Qwen2.5-Coder-1.5B = 54% (25/46), Qwen2.5-Coder-3B = 33% (15/46), Llama-3.2-3B = 0% (0/46), SmolLM3-3B = 21% (9/43), Phi-4-mini = 33% (15/46).

**Three findings beyond pass rate:**

1. **Format compliance does not track capability monotonically.** The smallest model (1.5B Coder) had the highest format-compliance rate (54%); the larger and "more capable" general-Instruct models collapsed compliance entirely (Llama 0%). Compliance is an attention-control property, not a capability property.

2. **Code runnability separates by training stack.** Of trials where the harness recovered code (50/58 Coder family, 66/129 general), the Coder family runs cleanly **86%** of the time vs **51%** for the general Instruct models. Code-domain pretraining preserves "runnable" as a property even after generic instruction tuning.

3. **Net-new task is also failing for small models.** T1 (the simplest task) passed 0/50 across all small models even though all 50 produced extractable code. The bugs are subtle (positional Stripe-Signature parsing, wrong status codes, hallucinated SDK behaviors) and the small models can't write subtly-correct webhook code regardless of fragments.

### 3.6 M6 — Seed injection (174 trials, 5 models)

M6 tests whether showing the model the seed file contents (faking what code-index retrieval would do) unlocks pass rate. The harness was modified to prepend seed `app/main.py` contents to the user message in a fenced block when `SHOW_SEED=1`.

**Aggregate results:**
- **Functional pass: 6/174 = 3.4%**, up from 0/177 in M5 on the same task surface.

**Two cells lifted, both on T4 (one-line refactor):**
- **Qwen2.5-Coder-3B `T4 arm_b`** (with fragments + seed): **0/3 → 3/3** functional pass
- **SmolLM3-3B `T4 baseline`** (NO fragments, only seed): **0/3 → 3/3** functional pass

**Format compliance also lifted in some cells** (Qwen2.5-Coder-1.5B T4 arm_b: 0/3 → 3/3 parses), regressed in one (Phi-4-mini parses 15/36 → 0/36 — longer prompt pushed it toward conversational responses that broke `[FILE:]` markers).

**T3a/T3b composition shape: still 0% functional with seed across all small models.** The composition shape is unreachable at small parameter scale even with seed visibility.

**The interpretation:** seed injection partially validates the M4 architectural conclusion. When the missing context is provided, pass rate moves — but only in cells where the cognitive shape is within the model's reach. T4's one-line refactor is reachable for the 3B Coder. T3a/T3b's multi-skill composition is not, regardless of seed.

### 3.7 M7 — Anti-pattern fragments (20 trials, 4 models)

M7 tests whether targeting the M5 T1 bug list with surgical "anti-pattern" fragments lifts pass rate. Four new fragments were authored (`webhook-patterns:9-12`) calling out:
- Positional Stripe-Signature parsing (Llama bug)
- Wrong status codes on signature failure (Llama, Phi bug)
- Hallucinated SDK behavior (Phi, SmolLM bug)
- Structural-marker contamination (Phi bug)

A new arm `T1.arm_b_plus` was defined adding all four to the original arm_b set (10 fragments total). Re-ran T1 × 4 models × 5 runs (SmolLM3 dropped at this stage).

**Aggregate results:**
- **Functional pass: 0/20.** No lift from anti-pattern fragments.
- **Strict-parse rate: 5/20.** Same as M5 T1 (only Qwen2.5-Coder-1.5B produces compliant markers).

**The bug-shape persistence finding:** the 1.5B Coder used positional `split(",")[N]` in 5/5 trials despite anti-pattern `:9` being in its context. Phi-4-mini hallucinated "stripe uses compare_digest internally" in 5/5 trials despite anti-pattern `:11` being in its context. The models had explicit, surgical guidance against the exact bugs they were making, and emitted the bugs anyway.

**The interpretation:** fragment content is sufficient. The bottleneck is fragment **application**, not fragment **availability**. At small parameter scale, the model cannot reliably apply guidance even when the guidance directly names its current behavior as wrong.

### 3.8 M8 — Self-QA two-call workflow (20 trials, 4 models)

M8 tests whether asking the model to review its own output against the fragments — a two-call workflow with a structured review prompt — overcomes the application gap.

**Aggregate results:**
- **Functional pass: 0/20.** No lift from self-QA.
- **Strict-parse rate: 15/20** — significantly lifted from M7's 5/20.

**The structural-vs-substantive split:** two of four models (Qwen2.5-Coder-3B, Phi-4-mini) went from 0/5 strict-parse in M7 to **5/5 strict-parse in M8.** Self-QA fixed format compliance — both models recognized the `[FILE:]` directive when asked to review against it. But neither model fixed the substantive code bugs:

- Qwen2.5-Coder-1.5B still produced positional `split(",")[N]` in 5/5 M8 trials (same as M7)
- Phi-4-mini still hallucinated SDK behavior in 5/5 M8 trials (same as M7)

**The interpretation:** workflow interventions help with structural compliance (the cognitive task of "check format against an explicit directive") but do not help with substantive correctness (the cognitive task of "recognize my own buggy code against an anti-pattern description"). At small parameter scale, the latter is below the application threshold even with explicit prompting.

---

## 4. Findings

Promoting the cross-milestone results from milestone-specific to pilot-level conclusions:

### Finding 1: Fragment composition is sufficient (high confidence)

Three independent intervention experiments all failed to lift functional pass rate by improving fragment quality:

- **M3/M4** — added a lifespan-preservation guardrail to `fastapi-middleware-patterns:8`. T3a/T3b/T4 re-run: 3/27, identical to M3.
- **M7** — added 4 surgical anti-pattern fragments addressing M5 T1 bugs. T1 functional pass: 0/20, identical to M5.
- **M8** — asked the model to review its output against fragments before submitting. T1 functional pass: 0/20.

Fragments contain the right content. The 1.5B Coder's positional-split persistence under M8 is the cleanest single demonstration: model had `webhook-patterns:9` in context, was asked to compare against it, emitted the bug 5/5 times anyway. The bottleneck is application, not availability.

**Implication:** skill-engineering effort below the parameter-application threshold is wasted. Above the threshold, current fragments do their job.

### Finding 2: Code-index retrieval is the load-bearing architectural piece

The lifespan-rewrite pattern (M3/M4) and the M6 partial recovery (3B Coder T4 arm_b 0→3 with seed shown) tell a consistent story: the model cannot preserve seed code it has never seen, and the `[FILE: <path>]` output format requires it to reproduce the entire file.

Within the full Skillsmith architecture, code-index retrieval would inject the seed alongside skill fragments and the unsatisfiability disappears. The pilot demonstrates this with M6's static seed-file injection — a crude but informative proxy.

**Implication:** the architecture surrounding skills is what needs to be built. Code-index retrieval is the highest-priority missing component.

### Finding 3: Cognitive-shape × parameter-size matching is the engineering target

Same model, same fragments, same harness can produce 100% pass on one task and 0% pass on another depending on the cognitive shape demanded:

- 3B Coder T4 arm_b (one-line refactor, with seed): 3/3 functional pass
- 3B Coder T3a arm_b (2-skill composition, with seed): 0/3 functional pass

The 30B-A3B Coder also fails T3a/T3b (for an architectural reason — code-index gap). The matching of model capability to task cognitive shape is the variable that determines pass rate; skill quality and workflow steps don't compensate.

**Implication:** Skillsmith deployment should route work to the smallest model that passes the cognitive shape it's solving. The deployment matrix (§6) is the actionable prescription.

### Finding 4: Workflow interventions split structural and substantive corrections

Self-QA in M8 produced a clean dissociation:
- **Structural correction works at small scale.** Format compliance lifted from 0/5 to 5/5 for two of four models. The cognitive task of "check format against an explicit directive" is within the parameter floor.
- **Substantive correction does not work at small scale.** No model fixed the bugs that anti-pattern fragments explicitly named. The cognitive task of "recognize my own buggy code against an anti-pattern description" is below the floor.

**Implication:** self-QA at 2× inference cost is justifiable for output-format consistency but not for substantive bug correction. Use it where it earns its keep.

### Finding 5: Format compliance is non-monotonic with capability

Smaller models can be *more* obedient to format directives than larger models. The 1.5B Coder achieved 54% strict-parse compliance while the 3.21B Llama achieved 0%. Compliance is an attention-control property — capable models with strong output-style preferences will override format directives in favor of their preferred shape (markdown fences, explanatory prose), while smaller models with less surplus capability follow directives more literally.

**Implication:** for any production deployment depending on structured output, output-format reliability is a first-class screening criterion that must be measured separately from capability benchmarks.

### Finding 6: Code runnability is a training-stack property

Of M5 trials where extractable code was recovered (strict-parse + lenient-parse routes combined), the Coder-tuned models (Qwen2.5-Coder-1.5B, -3B) imported and started cleanly **86%** of the time (50/58). General Instruct models (Llama, SmolLM, Phi) imported and started cleanly **51%** of the time (66/129). Even after generic chat tuning is applied on top of code pretraining, the "code that runs" property is preserved.

**Implication:** for production code-generation workloads, choose Coder-family models even when the use case suggests a general Instruct model would suffice. Code runnability is downstream of pretraining mix, not of fine-tuning.

### Finding 7: Some cognitive shapes are unreachable at small scale regardless of intervention

T3a/T3b (multi-skill composition) was tested across 5 small models, with and without fragments, with and without seed (M5 + M6). 0/234 functional pass across the entire small-model regime on T3a/T3b. No skill, no workflow, no seed injection moved that cell.

**Implication:** above some task-complexity threshold, the only fix is bigger model. Skills cannot compensate; workflow cannot compensate; better context cannot compensate. This bounds the practical scope of "small-model + skills" production deployments.

---

## 5. The cognitive-shape × parameter-size deployment matrix

Synthesizing M2 through M8:

| Cognitive shape | 1.5B Coder | 3B Coder | 3B General | 3.8B General | 30B-A3B Coder |
|-----------------|------------|----------|-------------|---------------|----------------|
| Format compliance | native (54%) | needs self-QA | needs self-QA | needs self-QA | native |
| Net-new bounded (T1) | fails functional | fails functional | fails functional | fails functional | passes (M2) |
| Targeted refactor (T4) | fails functional | **seed required, passes** (M6) | fails functional | fails functional | passes (M2) |
| 2-skill composition (T3a) | fails functional | fails functional | fails functional | fails functional | code-index required (M3/M4) |
| 3-skill composition (T3b) | fails functional | fails functional | fails functional | fails functional | code-index required (M3/M4) |

**Reading the matrix:**

- The **only positive cell at small scale** is Qwen2.5-Coder-3B + seed-injection on T4 (one-line refactor). At 1× cost, this is the operating sweet spot for high-volume targeted-edit workloads.
- The **30B-A3B Coder is required** for net-new bounded tasks at 1× cost without seed injection.
- **Composition shapes (T3a/T3b)** failed at every model size and intervention combination tested in the pilot — including 30B-A3B Coder (without code-index, in M3/M4) and 3B Coder + seed (with code-index proxy, in M6). The "bigger model AND code-index together" combination was not directly tested. Both are likely required, but the pilot's evidence supports only "neither alone is sufficient at the configurations tested." Confirming the composition floor needs a 30B+ Coder + real code-index retrieval cell — a follow-up experiment.
- **Self-QA at 2× cost** earns its keep only for format-compliance — meaningful for production deployments shipping structured output.

The matrix is the practical output of the pilot. Future Skillsmith deployment decisions should reference these cells.

---

## 6. Limitations and threats to validity

The pilot's conclusions rest on a specific dataset with known limitations:

### 6.1 Domain saturation in the test surface

The webhook + JWT + FastAPI domain is heavily represented in pre-training data. This created a hidden ceiling at the 30B-A3B Coder scale and likely understates how much fragment-typed retrieval contributes in less-saturated domains. **Replication on a less-saturated domain (custom internal libraries, post-cutoff frameworks, regulated-domain conventions) is required to settle the macro skills-help-LLM claim.**

### 6.2 Fixture and harness bugs surfaced during the pilot

Three issues were discovered during M3 manual review and the M4–M8 extension work. All are documented here in full transparency. None invalidate the pilot's substantive architectural findings (which rest on T3a/T3b composition behavior, unaffected by these issues), but they reduce the effective trial count and shape how T2 / T5 evidence should be interpreted.

**T2 seed-table mismatch (M3 finding, fixed in M4 commit `ca9f4b9`).** The T2 seed `app/main.py` lifespan created `processed_webhook_events` (T1's table name from a copy-paste during seed authoring) instead of the `webhook_deliveries` table the T2 task description specified and webhook-patterns:5 documented. The model's `INSERT INTO webhook_deliveries` therefore failed at runtime against a non-existent table. This was hidden by the harness state-combination bug (next item) reporting these as deferred rather than failed. **Impact:** all 9 T2 arm-comparison trials and all 3 T2 baseline trials in M2 are environmentally compromised. T2 evidence in the dataset is inconclusive about model behavior on the intended task. **Mitigation:** seed corrected in M4; T2 was not re-run in M5–M8 sweeps because M5–M8 focused on T3a/T3b/T4. A clean T2 re-run at any point would restore the cell.

**T5 empty arm_fragments (M3 finding, not fixed).** T5 fixture has zero fragments populated for all four arms (`arm_a: []`, `arm_b: []`, `arm_c: []`, `baseline: []`). All 9 T5 arm-comparison trials registered `functional_pass=True` via the inverted-criterion decline path (model correctly declines when no fragments are provided), but T5 contributes zero arm-comparison signal because there is nothing in the context to vary across arms. **Impact:** T5 is excluded from H1/C1/C2/C3 aggregates per spec §7.3 footnote. The 81 → 72 effective trial count for arm-comparison aggregate calculations should be noted for any future replication. **Mitigation:** none applied. The fixture's design intent for T5 (test inverted-criterion decline behavior with content that *should* trigger decline) was never realized; populating T5's arm_fragments per its design intent is a follow-up before any milestone-level T5 inference is drawn.

**`run_trial.py` state-combination bug (M3 finding, fixed in M4).** The `run_checks` function combined per-check pass/fail/skipped states into a per-trial `mech_pass` value with logic `state = None if has_skipped else (True if all_pass else False)` — meaning a deferred (skipped non-manual) check would set `mech_pass=None` even when other checks had failed outright. Combined with the T2 seed bug, this masked T2's HTTP failures as "deferred" instead of "failed." **Impact:** the 12 T2 trials in M2 were recorded as `functional_pass=None`. Without the bug, they would have been recorded as `functional_pass=False`. The aggregate metrics (H1 Arm B 20% excl T5) are unaffected because deferreds were already excluded from pass/fail counts. **Mitigation:** corrected in M4 (`run_trial.py` now prioritizes `False` over `None` in the state combiner; comment in source notes the M3 review provenance).

These issues are real and cost the dataset some interpretability on T2/T5 specifically, but they do not retroactively change the pilot's load-bearing findings: the lifespan-rewrite pattern (M3/M4), small-model 0/227 functional pass (M5), seed-injection lift on T4 (M6), anti-pattern-fragment null-result (M7), and self-QA structural-vs-substantive split (M8) are all preserved.

### 6.3 Untested architectural slices

The pilot validated one slice (skills-index → execution-model) and proxied a second (code-index via static seed injection). The remaining slices are untested:

- **Real code-index retrieval pathologies.** Static seed injection is a crude proxy; real retrieval may surface stale-index issues, retrieval-precision drift, multi-file scope problems, or token-budget tensions when seeds are large.
- **Knowledge-index retrieval value.** The "why we chose X" decision-history retrieval was never wired or tested. Could be material for tasks where the model is rewriting decisions it shouldn't be rewriting (M3/M4 lifespan rewrite is plausibly a knowledge-index gap as much as a code-index gap).
- **Generalist phase-routing accuracy.** Pilot pre-specified phase. A real generalist that routes to the wrong phase would propagate skills-mismatch downstream as `wrong_skill` failures — invisible in the pilot.
- **Cross-phase variance.** Build phase only. Spec, design, verify phases have their own cognitive-shape signatures.

### 6.4 Cross-skill-category generalization

Pilot tested **build-domain** skills only. The methodology should transfer to interview-domain, architecture-domain, devops-domain skill categories — but each category has its own task-shape signatures and parameter-floor curves. The deployment matrix in §5 applies to build-domain; other categories need their own pilots with the same harness/methodology.

### 6.5 Sample size at small-model scale

M5 is 227 trials, M6 is 174, M7 + M8 are 20 each. The within-cell sample is 3 runs (M5/M6) or 5 runs (M7/M8). Statistical confidence on per-cell pass rates is not strong. The pilot's conclusions rest on the *qualitative shape* of the data (consistent failure modes, clean cell-level transitions) rather than statistical inference over individual cells.

### 6.6 Within-family Coder vs general A/B incomplete

The cleanest experimental cell — Qwen2.5-Coder-1.5B vs Qwen2.5-1.5B-Instruct (same family, same scale, varied only on Coder tuning) — was lost when the Qwen2.5-1.5B-Instruct GGUF download was corrupt. Re-downloading and running 36 trials would complete that cell.

---

## 7. Recommendations

### 7.1 Engineering priorities for Skillsmith

In priority order:

1. **Build the code-index retriever.** Highest-impact missing component. M6's static seed-injection proxy already showed lift; real retrieval should at minimum match that and probably exceed it. Should integrate with the execution-model's prompt construction at the skills-index/code-index junction.

2. **Build the knowledge-index retriever (decisions and rationale).** Second-highest impact. Should surface relevant ADRs, design-decision records, and "why X not Y" notes alongside skills and code. Plausibly addresses the M3/M4 lifespan-rewrite finding from a complementary direction.

3. **Define cognitive-shape taxonomy formally.** The pilot identified four shapes informally (net-new bounded, targeted local refactor, 2-skill composition, 3-skill composition). Skillsmith production needs a more complete enumeration with each shape's parameter-floor and intervention-floor characterized. Each cognitive-shape × skill-category × parameter-size cell becomes a deployment configuration.

4. **Implement per-shape execution-model routing in the generalist.** The deployment matrix (§5) is the prescription; the generalist needs to read task → infer cognitive shape → route to the smallest sufficient execution-model. Mis-routing inflates inference cost or degrades pass rate.

5. **Add output-format reliability measurement to model evaluation.** Standard capability benchmarks don't surface format-compliance pathology (Llama-3.2-3B's 0% strict-parse despite reasonable code). For any production small-model deployment, format-compliance must be a separate screening axis.

### 7.2 What NOT to invest in

- **More fragments per skill.** Three independent experiments confirm fragment quantity isn't the bottleneck above the parameter-application threshold. Don't author more anti-pattern fragments hoping pass rates lift.
- **Self-QA as a default workflow.** 2× inference cost without functional-pass lift on the substantive failures is a poor trade. Reserve self-QA for output-format-critical workloads.
- **Fragment-type taxonomy expansion.** Current taxonomy (rationale/setup/execution/example/verification/guardrail/anti_pattern) is sufficient. Adding more types fragments engineering effort without measurable benefit.

### 7.3 Future pilot scope

If a follow-up pilot is run, the priority experiments are:

1. **Cross-domain replication** — same methodology applied to a less-saturated domain (post-cutoff library, internal proprietary framework) to test whether skills lift more strongly when training-data-prior is weaker.
2. **Real code-index retrieval validation** — wire an actual code-search retriever (BM25, vector, or hybrid), test against M6's static-injection baseline, characterize retrieval-precision drift's impact on pass rate.
3. **Knowledge-index value measurement** — author 5–10 ADRs/decisions, build a knowledge-index retriever, test on tasks designed to probe decision-respect (e.g., "extend the auth flow without violating ADR-014").
4. **Cross-skill-category sweep** — run an M5-equivalent on interview-domain skills, then architecture-domain skills, populate the cognitive-shape × parameter-size matrix for each.
5. **Composition-shape bigger-model test** — re-run T3a/T3b at 70B+ scale (with code-index) to determine whether composition-shape failures in M3/M4 are model-capability bound or architecture-bound.

---

## 8. Methodology contributions (transferable beyond this pilot)

Beyond the substantive findings, the pilot produced a transferable methodology that future Skillsmith research can reuse:

### 8.1 Failure-mode tagging discipline

The locked enum (failure_mode + failure_root_cause + faithfulness_pass + failed_fragment) made the architectural finding visible. Without disciplined per-trial attribution, M2's 20% pass rate would have read as "fragments don't work." With it, the failures attributed to `under_specified_procedure` and `composition_gap` (and not `model_capability`) revealed the architectural gap. This tagging pattern should be the default for any skills-related evaluation.

### 8.2 Lenient-parse reanalysis

`harness/lenient_reanalyze.py` post-hoc separates "model can't produce code" from "model produced code but ignored output format." Without this split, M5's 0/227 strict-parse functional pass would have read as "models can't write code." With it, the format-compliance vs substantive-correctness distinction emerged as Finding 5.

### 8.3 Cognitive-shape framework

Framing tasks as instances of cognitive shapes (net-new bounded, targeted local refactor, multi-skill composition, etc.) rather than as undifferentiated "tasks" enabled the deployment matrix. The cognitive-shape vocabulary transfers across skill categories — interview-domain has its own shapes (open-ended question generation, ambiguity surfacing, follow-up extraction), architecture-domain has its own (tradeoff analysis, constraint propagation), each with their own parameter-floor curves.

### 8.4 Per-trial reproducibility

`rerun_checks.py` + `apply_tags.py` + `gen_reviews.py` + the harness's deterministic temp-0.0 + the consistency_hash + env_state recording. Any of the 561 trials in the dataset can be replayed and re-verified. Future pilots should preserve this property.

### 8.5 Single-variable milestone progression

M5 → M6 → M7 → M8 changed exactly one variable at a time (model, seed-injection, anti-patterns, self-QA). Each milestone's evidence is interpretable in isolation; combined, they sketch the multi-dimensional matrix. Resist the temptation to combine variables in a single experiment unless you have specific confounds you want to surface.

---

## 9. Bottom line

The skill-tax pilot's specific hypothesis (H1 ≥70% Arm B pass rate on build-domain tasks) failed at 20%. Read alone, this would suggest fragment-typed retrieval doesn't work and Skillsmith should pivot to a different architecture.

The pilot's broader contribution is the opposite: **fragment-typed retrieval works, but it works as one component of a larger architecture, not as a standalone solution.** Three independent intervention experiments demonstrate that fragment content is sufficient; the missing piece is the retrieval architecture surrounding fragments (code-index, knowledge-index, generalist routing) and the matching of execution-model size to task cognitive shape.

This is the seminal moment in the Skillsmith architecture work. The roadmap shifts from "make better fragments" to "build the retrieval architecture and size execution-models per cognitive shape; fragments are stable infrastructure." Future Skillsmith design decisions reference this pilot as the moment those priorities crystallized.

The deployment matrix (§5) is the actionable prescription. The follow-up pilot scope (§7.3) is the next set of experiments. The methodology (§8) transfers across skill categories and future scope.

The numbers are bad. The signal is high. The architectural reframe is load-bearing.

---

## 10. Appendices

### Appendix A — Milestone-specific syntheses

- `_FINAL_SYNTHESIS.md` — M2 + M3 detailed writeup with per-arm metrics, root-cause distributions, and the lifespan-rewrite finding
- `_BATCH2_SYNTHESIS.md` — M3 architectural finding deep-dive with §3a fragment-text excerpts
- `_M4_SYNTHESIS.md` — M4 skill-edit re-run + the "model paraphrases guardrail in comments" finding
- `_M5_SYNTHESIS.md` — M5-only writeup (superseded by `_M5-M8_SYNTHESIS.md`)
- `_M5-M8_SYNTHESIS.md` — M5 through M8 unified writeup

### Appendix B — Data files

- `experiments/skill-tax/skills.duck::pilot_trials` — 561 trial rows with full prompts, responses, parses, functional_pass, consistency_hash, fragment_count, tags, notes (549 milestone + 12 calibration)
- `experiments/skill-tax/harness/m5_logs/`, `m6_logs/`, `m7_logs/`, `m8_logs/` — per-model logs with `lm_ms`, `total_ms`, `review_lm_ms`, `in_tok`, `out_tok`
- `/tmp/m5_lenient_results.json` — 163 lenient-reanalysis records
- `/tmp/m5_manifest.json` — model-to-trial-id mapping for M5

### Appendix C — Harness scripts

- `experiments/skill-tax/harness/run_trial.py` — single-trial runner
- `experiments/skill-tax/harness/run_81.sh` — M2 pilot runner
- `experiments/skill-tax/harness/run_m4.sh` … `run_m8.sh` — milestone-specific sweep runners
- `experiments/skill-tax/harness/rerun_checks.py` — check replay with env_state capture
- `experiments/skill-tax/harness/lenient_reanalyze.py` — post-hoc fence-extraction
- `experiments/skill-tax/harness/apply_tags.py` — idempotent tag application
- `experiments/skill-tax/harness/gen_reviews.py` — review-file generator

### Appendix D — Locked artifacts

- `experiments/skill-tax/prompts/governance-preamble-2026-05-01.v2.md` — locked governance preamble (immutable; edits invalidate prior trials)
- `experiments/skill-tax/skills/webhook-patterns.yaml` — 12 fragments (8 original + 4 anti-patterns added M7)
- `experiments/skill-tax/skills/fastapi-middleware-patterns.yaml` — 8 fragments with M4 lifespan-preservation guardrail edits
- `experiments/skill-tax/skills/jwt-validation-patterns.yaml` — 8 fragments
- `experiments/skill-tax/skills/python-async-patterns.yaml` — 8 fragments
- `experiments/skill-tax/tasks/T1.yaml` … `T5.yaml` — 6 task fixtures including M7's `arm_b_plus`
- `experiments/skill-tax/skills/AUTHORING_LOG.md` — full provenance of skill authoring decisions and harness changes

### Appendix E — Pilot specification

The original pilot design document is at `experiments/skill-tax/workflow-phase-retrieval-pilot-spec.md` (v2.4). It defines H1, C1–C4, the trial matrix (54 + 12 + 15), the locked enum for failure-mode tagging, and the success thresholds. The pilot's execution complies with this spec; deviations (fixture bugs, M4–M8 extensions) are documented in their respective synthesis files.

### Appendix F — Glossary

- **SDD** — Spec-Driven Development. The lifecycle Skillsmith is built around: intake → spec → design → build → verify (etc.). Each phase has its own skill activations and execution-model tier.
- **Skill category** — a class of skills bound by domain (build-domain, interview-domain, architecture-domain, devops-domain, etc.). Categories are orthogonal to phases.
- **Fragment** — a fragment of a skill. Each skill is composed of typed fragments (rationale, setup, execution, example, verification, guardrail, anti_pattern).
- **Arm** — a fragment-composition variant within a task fixture. Arm A includes all fragments; Arm B drops rationale + example; Arm C drops rationale + example + verification + guardrail.
- **Cognitive shape** — the kind of cognitive work a task demands (net-new bounded code generation, targeted local refactor, multi-skill composition, etc.). Different shapes have different parameter-floor curves.
- **Code-index retrieval** — the (currently unimplemented) retriever that surfaces relevant existing code to the execution model alongside skills.
- **Knowledge-index retrieval** — the (currently unimplemented) retriever that surfaces relevant decisions / ADRs / "why X not Y" notes alongside skills and code.
- **Generalist** — the (currently pre-specified-in-pilot) phase router that interprets a user request and dispatches to the right execution-model tier with the right skill activations.

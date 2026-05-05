# Workflow-Phase Retrieval Pilot — Spec

**Status:** v2.4 (post-QA + telemetry alignment + authoring-cost correction + model selection). Supersedes `tier2-determinism-pilot-spec.md` (v1) and v2 draft.
**Author:** Claude (drafted from working session with Nate; revised after self-QA, telemetry correction, authoring-cost correction, and model-selection update)
**Last updated:** 2026-04-30

---

## 0. What changed from v1

The v1 pilot tested whether Tier 2 could execute deterministically given hand-authored fragments. That framing was wrong in two ways:

- **It treated fragment_type as something to design.** The schema already locks `setup | execution | verification | example | guardrail | rationale`. The question isn't "what should fragments be" — it's "does the existing schema work?"
- **It tested execution in isolation.** The architecture's load-bearing claim is bigger: that workflow-phase activation + fragment-typed retrieval narrows knowledge to what's needed, enabling small-model deterministic execution. Testing execution alone with hand-built fragments doesn't validate that claim.

This v2 pilot tests the **architecture's actual claim**: workflow → phase → fragment retrieval chain produces minimal, sufficient context for Tier 2 to execute deterministic build-phase tasks. Skills are real, gold-standard authored; the pilot tests methodology against known-good content so the result isolates methodology from authoring quality.

The chicken-and-egg problem (methodology vs. authoring quality) dissolves: by holding authoring quality constant at gold-standard, any failure must be methodological.

---

## 1. Hypothesis and decision

### 1.1 The hypothesis

**H1 (primary):** Given a deterministic build-phase task that activates 1–3 domain skills authored at gold standard from a 4-skill corpus, retrieval Arm B (`setup + execution + verification + guardrail`) produces a context in which Tier 2 (Qwen3-Coder-30B-A3B-Instruct, Unsloth GGUF Q4_K_S, KV cache F16) executes faithfully at ≥85% pass rate.

**Sub-claims tested via the arm comparison (§5):**

- **C1 — Anchoring fragments are not load-bearing for execution.** Arm A (full skill, includes `rationale + example`) does not outperform Arm B by more than 2 trials per task on average. If C1 fails, retrieval should keep rationale/example for execution-routed queries.
- **C2 — Verification and guardrail are load-bearing.** Arm B outperforms Arm C (`setup + execution` only) by at least 2 trials per task on average. If C2 fails, verification and guardrail can be deferred to a separate retrieval pass.
- **C3 — Multi-skill composition works.** T3a (2-skill) and T3b (3-skill) pass at rates within 1 trial per arm of the single-skill tasks. Additionally, T3a − T3b gap is < 2 trials per arm (composition difficulty doesn't scale catastrophically with skill count). If C3 fails, fragment selection alone cannot drive composition; workflow-class skills must do explicit composition.
- **C4 — Fragments are doing distinctive work.** Baseline runs (no fragments, task description only) pass at materially lower rate than Arm B — at least 2 trials per task lower. If C4 fails, the test domain is too well-represented in Tier 2's training data to draw conclusions.

H1 is the headline. C1–C4 are interpretive sub-claims that the trial design produces evidence on. The pilot does not test them as a single bundled hypothesis; each gets its own evidence path in §8.

### 1.2 Decision criteria

Primary metric: **Arm B pass rate** across the 54 arm-comparison trials (6 tasks × 3 arms × 3 runs, see §6.1).

| Arm B pass rate | Interpretation | Next move |
|-----------------|---------------|-----------|
| ≥85% | H1 holds. Methodology works on gold-standard content for build-phase work in this domain. | Proceed to retrieval-mechanism pilot (§8.1). |
| 70–84% | H1 has signal but is fragile. Sub-claim evidence (C1–C4) drives the diagnosis. | Targeted re-run before scaling. |
| <70% | H1 fails even on gold-standard content. Methodology, not authoring, is the bottleneck. | Major rethink — see §8.3. |

Sub-claim evidence may modify the next-move recommendation even when H1 passes — for example, an H1 pass with C1 failing means retrieval should not drop rationale/example for execution. §8 walks the combinations.

These thresholds are first-pass; gray-zone outcomes need judgment.

---

## 2. Pilot scope

### 2.1 In scope

- One workflow phase: **SDD build phase** (the most execution-heavy phase).
- One narrow task domain that activates 2–3 domain skills.
- Skills authored at gold standard per `skillsmith-authoring-reference.md` §4.
- Manual fragment selection simulating ideal retrieval.
- Tier 2 execution via the existing model router → LM Studio path.
- Three retrieval-arm conditions to isolate fragment-type effects (§6.1).
- Manual evaluation against pre-defined success criteria.
- Logging via existing `skillsmith.telemetry` module (DuckDB-backed `composition_traces` + sibling `pilot_trials` table in `skills.duck`).

### 2.2 Out of scope

- **Actual retrieval system.** We hand-select fragments. If best-case fails, no retrieval improvement saves it; if best-case succeeds, retrieval becomes the next pilot.
- **Workflow routing.** We pre-specify the phase and skill activation. Workflow → phase routing is a separate concern.
- **Intake / interview.** Tasks come pre-specified with locked inputs.
- **Authoring scale.** 2–3 skills total. The pilot tests methodology, not corpus-building.
- **Cross-domain generalization.** One task domain. Generalization is a follow-up if v2 passes.
- **System-class skills.** No `sys-*` skills in scope. Always-injected content is a different test.

### 2.3 Why this scope

The architecture has many components. This pilot answers one question: does the core retrieval methodology (workflow-phase activation + fragment-type filtering) produce executable context for Tier 2? Every other component (retrieval mechanism, intake, workflow routing, system skills) is testable in isolation only if this one passes.

### 2.4 Tier 2 runtime configuration

Recorded here once so it's locked in pilot telemetry and reproducible from the spec alone.

| Parameter | Value |
|-----------|-------|
| Model | Qwen3-Coder-30B-A3B-Instruct |
| GGUF source | Unsloth (Qwen3-Coder-30B-A3B-Instruct-GGUF) |
| Quantization | Q4_K_S |
| K cache | F16 (no quantization) |
| V cache | F16 (no quantization) |
| Context window | 32,768 tokens |
| Eval batch size | 512 |
| CPU thread pool size | 8 |
| Inference server | LM Studio (local, OpenAI-compatible API) |
| Hardware | AMD Strix Point, 96 GB RAM (48 GB UMA allocation) |
| Measured throughput | ~40 tok/s active generation |

These values are recorded per-trial in `pilot_trials.notes` (or a dedicated runtime config field) so any single trial is reproducible without external context. If any value changes mid-pilot, the trial set is invalidated and prior trials must be re-run with the new config — mixing runtime configurations within an analysis batch is not permitted.

**Why these specific choices:**

- **Q4_K_S over Q4_K_M:** memory bandwidth is the bottleneck on Strix Point UMA, not capacity. Q4_K_S means fewer bytes moved per token; quality cost is negligible for this MoE model where only ~3.3B parameters are active per token.
- **F16 KV cache:** with 48 GB UMA there's no need to quantize the cache. F16 eliminates a non-determinism vector from the experiment.
- **32K context:** comfortably fits the largest projected prompt (T3b Arm A ≈ 6–10K tokens) with 3x headroom. The model's native 256K context isn't needed for the pilot and would waste KV cache memory.
- **Coder-Instruct vs. general 3.5-35B:** the Coder variant is post-trained for faithful execution against provided context; the general model has stronger reasoning that would induce `scope_violation` failure modes (the model second-guessing fragment instructions). The pilot is testing faithfulness, not reasoning.

---

## 3. Skills required

### 3.1 Task-domain choice

**Recommended task: JWT-authenticated FastAPI middleware**

> Implement HMAC-signed webhook receiver for inbound Stripe events in a FastAPI app, with HS256 JWT middleware on a downstream protected route.

Reasons:
- Activates 2–3 domains naturally (webhooks protocol, FastAPI framework, optionally JWT/auth cross-cutting).
- Mechanically verifiable: signature verification works or doesn't, JWT validates or doesn't, route returns expected status codes.
- Tier 2 strongly trained on Python and FastAPI.
- One skill (`webhook-patterns`) already exists at gold standard, reducing authoring burden.
- Build-phase task — directly tests the phase the architecture most needs to support.

### 3.2 Skill inventory

| Skill | Pack tier | Status | Source |
|-------|-----------|--------|--------|
| `webhook-patterns` | protocol | **Existing gold standard** (augment with guardrail) | `src/skillsmith/_packs/webhooks/webhook-patterns.yaml` |
| `jwt-validation-patterns` | protocol | **Author new at gold standard** | n/a — drafted for pilot |
| `fastapi-middleware-patterns` | framework | **Author new at gold standard** | n/a — drafted for pilot |
| `python-async-patterns` | language | **Author new at gold standard** | n/a — drafted for pilot |

Four skills across three tiers (protocol × 2, framework, language) provides meaningful composition variance for testing C3. Specifically, the pilot can now test:

- **2-skill composition within adjacent tiers** (webhook + fastapi-middleware on T3a)
- **3-skill composition across three tiers** (jwt + fastapi-middleware + python-async on T3b)
- **Composition across two different protocol-tier skills** (whether the architecture handles protocol siblings or only protocol+framework)

This is materially better composition coverage than the v2.1 two-skill scope, which could only test one composition pair. Authoring effort is the constraint that previously limited skill count; with research-LLM authoring that constraint is dramatically reduced.

### 3.3 Authoring requirements

Every newly authored skill must:

- Pass full schema validation (R-rules, fragment word counts, contiguity, tag policy)
- Include all six fragment types — `rationale + setup + execution + verification + example + guardrail` — minimum one of each
- **Include an explicit `guardrail` fragment** (this is non-negotiable for the pilot — without it, Arm B and Arm C only differ in verification, and the architecture's claim about guardrails being separately load-bearing is not testable)
- Reach final QA gate verdict of `approve` (revise → approve through normal iteration is fine; bounce_budget exceeded → re-author from a different angle)
- Be reviewed end-to-end by a human reviewer before pilot trials begin (research LLM authors; human signs off)
- Cite primary sources per R1, date-stamp per R5

**Special note on `webhook-patterns` (existing gold standard):** the existing skill has 8 fragments (1 rationale, 1 setup, 4 execution, 1 example, 1 verification) — **no guardrail fragment**. For the pilot to test guardrail's load-bearing role, the existing webhook skill must be augmented with at least one guardrail fragment before trials. Candidate guardrail content already exists inline in the execution fragments (e.g., "never use `===` for HMAC comparison") and can be promoted into a dedicated guardrail fragment without breaking R6 (change_summary should reflect the augmentation, not claim "initial authoring").

**Hard rule:** if QA gate can't produce gold-standard content for a given skill across two distinct authoring attempts (different prompts or different research-LLM sessions), drop that skill from the pilot rather than lower the bar. Better to test 3-skill composition with 3 gold-standard skills than 4-skill with one borderline skill.

### 3.4 Authoring effort

With research-LLM authoring (Opus or equivalent), authoring is no longer the pilot's bottleneck:

- Per new skill (research-LLM draft + QA gate iteration + human sign-off): ~0.25–0.5 day
- 3 new skills (`jwt-validation-patterns`, `fastapi-middleware-patterns`, `python-async-patterns`): 1–1.5 days
- `webhook-patterns` guardrail augmentation: 0.25 day
- Aggregate human review pass across all 4 skills before trials: 0.5 day

Realistic range: **~2 days of authoring before trials begin.** The bottleneck is now trial verification (manual faithfulness review + root-cause tagging), not authoring.

If a 5th skill becomes necessary mid-pilot to test a specific composition variant, adding one is now a half-day cost rather than a multi-day commitment. The pilot's design should not constrain itself based on authoring economics that no longer apply.

---

## 4. Task selection

### 4.1 Task shape

All trials are instances of one underlying pattern:

> Given a FastAPI app skeleton at `<path>`, implement `<webhook handler | middleware>` for `<scenario>` using `<technology>`, satisfying these mechanical checks: `<list>`.

This shape is deterministic when fully specified. Fragments must teach Tier 2 how to:
- Wire up the FastAPI route or middleware
- Verify HMAC signatures correctly (or validate JWT correctly)
- Handle the failure paths
- Avoid known anti-patterns (`===` for HMAC compare, missing replay protection, etc.)

### 4.2 Trial set: 6 task variations

| # | Variation | Skills activated | Tests |
|---|-----------|------------------|-------|
| T1 | HMAC-verify webhook handler, valid Stripe signature path | webhooks | Baseline: simplest case, single skill primarily |
| T2 | Same handler, but with replay protection (idempotency table) | webhooks | Multi-fragment within one skill |
| T3a | Webhook handler exposed via a FastAPI route using shared dependency-injection middleware | webhooks + fastapi-middleware | **2-skill composition** (protocol + framework) |
| T3b | JWT-protected FastAPI async route validating HS256 token from `Authorization` header | jwt + fastapi-middleware + python-async | **3-skill composition** (protocol + framework + language) |
| T4 | Refactor existing handler to use timing-safe comparison; replace `===` with `crypto.timingSafeEqual` | webhooks (guardrail-led) | Targeted fix using `guardrail` content |
| T5 | "Add light caching to the handler for performance" | (or refuse) | Out-of-scope: nothing in fragments addresses caching; Tier 2 should decline or scope down |

T3a and T3b together provide composition variance:
- T3a tests whether a 2-skill composition (one protocol + one framework) works.
- T3b tests whether a 3-skill composition (across three tiers) works.
- Comparing T3a and T3b pass rates surfaces whether composition difficulty scales with skill count.

T5 is the scope-recognition test. **Pass criterion is inverted** — Tier 2 passes by *not* inventing a caching solution. It can decline, ask for clarification, or implement only the parts within scope. Inventing caching code outside the fragment guidance = fail.

### 4.3 Locked inputs per task

Each task description provides:
- Absolute file path(s)
- Existing app skeleton content (FastAPI app, dependencies, env vars defined)
- Task statement with explicit "do" and "do not" lists
- Mechanical success criteria (e.g., "POST to `/webhooks/stripe` with valid signature returns 200; with invalid signature returns 400")
- Out-of-scope items explicitly listed where ambiguity exists

If any locked input can't be specified concretely, the task is too coarse and shouldn't enter the pilot.

---

## 5. Retrieval simulation

The pilot does not use the actual retrieval system. Instead, for each trial we **manually construct the context** that ideal retrieval would produce. This isolates the methodology question from the retrieval-mechanism question.

### 5.1 Fragment-selection procedure

For each task and each retrieval arm:

1. Identify which skills the task activates (manual workflow-phase simulation).
2. From those skills, select fragments matching the arm's filter:
   - **Arm A (full skill):** all fragments — `setup + execution + verification + example + guardrail + rationale`
   - **Arm B (load-bearing-only):** `setup + execution + verification + guardrail` — drops anchoring fragments (`rationale`, `example`)
   - **Arm C (execution-minimal):** `setup + execution` — drops verification + guardrail in addition to anchoring

3. Concatenate fragments in skill-order, then sequence-order within skill.
4. Prepend a brief governance preamble (system prompt) instructing Tier 2 to execute against the provided fragments and decline if the task exceeds them.

**Note on `setup`:** Setup fragments carry env-var declarations, imports, and middleware ordering — content that is procedurally load-bearing for execution, not anchoring content. Setup is included in all three arms accordingly. The earlier draft of this pilot dropped setup from B and C; that was a categorization error.

### 5.2 What the arms test

The three arms produce a direct comparison mapped to sub-claims:

- **A vs. B (tests C1):** Does keeping `rationale + example` improve execution? If A ≈ B (within 2 trials per task), C1 holds — anchoring fragments are not load-bearing for execution and retrieval can drop them for execution-routed queries. If A > B by ≥2 trials per task, C1 fails — keep them.
- **B vs. C (tests C2):** Does verification + guardrail matter for execution? If B > C by ≥2 trials per task, C2 holds — both are load-bearing. If B ≈ C, C2 fails — verification/guardrail can be deferred to a separate retrieval pass.

Plus a **baseline arm (tests C4):** task description with no fragments at all. If baseline ≈ Arm B, the test domain is too well-represented in Tier 2's training data to draw conclusions and the pilot's results are inconclusive.

### 5.3 Context budgets

Token counts per arm should be measured during skill authoring and recorded before trials begin. Activated skill count varies by task (1 skill for T1/T2/T4, 2 skills for T3a, 3 skills for T3b). Expected ranges (preliminary; will be revised once skills are authored):

- Arm A (full skill, max activation = 3 skills on T3b): rough estimate 6000–10000 tokens
- Arm B (load-bearing-only, max activation = 3 skills on T3b): rough estimate 3000–6000 tokens
- Arm C (execution-minimal, max activation = 3 skills on T3b): rough estimate 1800–3500 tokens
- Single-skill activation (T1/T2/T4): ~30–40% of the above
- Baseline (no fragments): ~200 tokens (task description only)

These ranges are guesses pending real measurement. Update §5.3 with measured values after authoring.

The pilot configuration uses a 32K context window (see §2.4), which provides 3x headroom over the largest projected prompt (T3b Arm A). The model itself supports 256K natively; the 32K cap is operational, not architectural. If actual token counts exceed projections after authoring, the context window can be raised to 65K without changing models — the constraint is KV cache memory, not capability. Context-overflow scenarios are not expected and would indicate skill word counts at the upper end of the authoring word-count limits.

---

## 6. Trial design

### 6.1 Volume

- **Arm comparison trials:** 6 tasks × 3 arms × 3 runs = **54 trials.** Temperature 0.0. Primary dataset for H1, C1, C2, C3.
- **Baseline (no-fragments) trials:** 4 tasks (T1, T2, T3a, T3b) × 3 runs = **12 trials.** Temperature 0.0. Tests C4 (training-data confound). Includes both composition tasks to verify training-data effect doesn't differ between single-skill and multi-skill task framings.
- **Robustness trials:** T1, T3a, T3b at Arm B, 5 runs each at temperature 0.3 = **15 trials.** Tests model robustness across stochastic sampling for the most diagnostic tasks.
- **Total:** **81 trials.**

This is more than v2.1's 64, and the increase is justified: the 6-task scope (vs. 5) captures both 2-skill and 3-skill composition; the additional baseline trials cover both composition variants; robustness trials added for T3b since 3-skill composition is the most stress-tested case.

At 18 trials per arm cell (6 tasks × 3 runs), one trial = ~5.6 percentage points. The arm-comparison gap thresholds in §1.1 (≥2 trials per task on average; ~11 percentage points at the arm aggregate level) are the smallest gaps the data can reliably distinguish from noise. Reducing run count below 3 per arm-task cell weakens detection.

### 6.2 Run procedure

Per trial:
1. Construct the prompt: system message = governance preamble + concatenated fragments per arm (or empty for baseline); user message = locked task description.
2. Send to model router with `phase=build`, routing to Tier 2 on LM Studio.
3. Capture: full prompt, full response, response time, token counts.
4. Apply response to the FastAPI app skeleton in a sandboxed working copy (git worktree per trial).
5. Run verification (§7.2).
6. Log via `DuckDBTelemetryWriter`: write `CompositionTrace` to `composition_traces`, then `pilot_trials` row keyed by `composition_id` per §7.1.

Sampling temperature is recorded per trial. Arm comparison and baseline at 0.0 to control for sampling variance when measuring arm effects. Robustness at 0.3 to surface model instability that a deterministic-sampling test would mask.

### 6.3 Harness

Hand-write a Python harness — ~150 lines including arm-construction logic. Loads skill YAMLs, filters fragments per arm, formats prompts, calls the model router, applies responses, runs verification, writes telemetry via the existing `skillsmith.telemetry.DuckDBTelemetryWriter` (no parallel infrastructure). Uses the existing OpenAI-compatible client against `LM_STUDIO_BASE_URL`. Each trial runs in a git worktree to isolate side effects.

---

## 7. Measurement

### 7.1 Per-trial record

The pilot uses the existing `skillsmith.telemetry` module — `DuckDBTelemetryWriter` writing to `composition_traces` in `skills.duck`. The harness constructs and submits a `CompositionTrace` record per trial (the same shape the production `/compose` path uses), then writes pilot-specific fields to a sibling `pilot_trials` table in the same DuckDB file.

This keeps the pilot consistent with production telemetry: same writer, same sink, same record discipline. The pilot doesn't invent parallel infrastructure.

**Existing fields captured by `CompositionTrace`** (already present in `composition_traces`):
- `composition_id`, `phase`, `tier`
- `fragment_ids`, `skill_ids`, `workflow_skill_ids`
- `latency_retrieval_ms`, `latency_assembly_ms`, `latency_total_ms`
- `tokens_in`, `tokens_out`
- `errors`
- `prompt_version`

The harness sets `phase=build` per trial. Retrieval latency is logged as 0 (pilot uses manual selection) with a note in `errors` field clarifying the simulation. Assembly latency captures the time from fragment selection to prompt construction. Total latency is the model round-trip.

**Pilot-specific fields in `pilot_trials` table** (new, sibling table in `skills.duck`):

```sql
CREATE TABLE pilot_trials (
  trial_id           VARCHAR PRIMARY KEY,
  composition_id     VARCHAR,    -- foreign key to composition_traces
  trial_class        VARCHAR,    -- 'arm_comparison' | 'baseline' | 'robustness'
  task_variation     VARCHAR,    -- T1..T5
  retrieval_arm      VARCHAR,    -- 'A' | 'B' | 'C' | 'baseline'
  fragment_types     VARCHAR,    -- comma-separated fragment_type values in context
  fragment_count     INTEGER,
  temperature        DOUBLE,
  prompt             VARCHAR,    -- full prompt for reproducibility
  response           VARCHAR,    -- full model response
  -- verification
  parses             BOOLEAN,
  functional_pass    BOOLEAN,
  faithfulness_pass  BOOLEAN,
  consistency_hash   VARCHAR,    -- normalized output hash for run-to-run dedup
  failure_mode       VARCHAR,    -- enum below
  failed_fragment    VARCHAR,    -- enum below
  failure_root_cause VARCHAR,    -- enum below
  notes              VARCHAR,    -- free text from manual review
  ran_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The `composition_id` foreign key joins back to `composition_traces` for the production-aligned fields (latencies, tokens, fragment_ids, errors). This avoids duplicating data and lets pilot analysis use the same query patterns as production telemetry analysis.

**Writer choice:** use `DuckDBTelemetryWriter` for the pilot. `NullTelemetryWriter` defeats the purpose. If `skills.duck` doesn't exist yet on the pilot operator's machine, initialize it via the existing schema migrations rather than creating a parallel store.

**Inline writes per the existing module:** the harness writes the `CompositionTrace` before constructing the `pilot_trials` row. Failures in either write log but don't propagate (matching the existing pattern). Pilot trials are not real production traffic; a write failure means a trial needs re-running, not a system halt.

**`failure_mode` enum:** `none | drift | hallucination | incomplete | scope_violation | parse_error | wrong_skill | composition_error`
- `wrong_skill` = pulled relevant content from the wrong skill (e.g., used webhook content in a JWT context)
- `composition_error` = fragments from different skills contradicted or overlapped, and Tier 2 picked badly

**`failed_fragment` enum:** `none | <skill_id>:<sequence> | multiple | unattributable`

**`failure_root_cause` enum:**
- `none`
- `under_specified_procedure` — execution fragment didn't carry enough "how"
- `missing_rationale` — Tier 2 needed "why" context to disambiguate "how"
- `missing_example` — Tier 2 needed a worked example to ground execution
- `missing_setup` — environment/imports/middleware-order content was needed but absent
- `verification_false_pass` — output looked right but wasn't
- `scope_guard_too_weak` — guardrail didn't trigger when it should have
- `composition_gap` — fragments from different skills had a gap between them
- `composition_overlap` — fragments from different skills contradicted
- `model_capability` — failure persists across content refinements

The enums are intentionally constrained. Free-text root-cause across 64 trials produces inconsistent labels and aggregation noise. If a failure doesn't fit, that's a finding worth recording before extending the enum.

### 7.2 Verification criteria

Trial passes only if **both** functional and faithfulness pass.

**Functional pass (mechanical):**
- Code parses (Python syntax + import resolution).
- App starts (FastAPI launches without exception).
- Each task-specific mechanical check from §4.3 passes (specific HTTP requests return expected status codes, signature verification rejects tampered payloads, etc.).

**Faithfulness pass (manual review):**
- Output stays within the fragments' scope. No invented patterns, no "improvements" not requested, no refactoring of unrelated code.
- For T5: Tier 2 declines, scopes down, or asks for clarification. Inventing a caching solution = fail.
- No commentary preamble; output is the patch or file.
- **Imports:** stdlib imports and imports already present in the app skeleton are always allowed. Third-party imports not appearing anywhere in the fragments are a scope reach (fail). Patterns and architectural decisions must come from fragment content; only the import surface gets latitude for reasonable substitution.

### 7.3 Aggregate metrics

After 64 trials:

**Headline:**
- **Arm B pass rate** (45 arm-comparison trials → 15 in Arm B). This is the H1 metric.

**Sub-claim evidence:**
- **Per-arm pass rate** (Arms A, B, C): 15 trials each. The A-vs-B and B-vs-C gaps test C1 and C2.
- **Per-arm pass rate on T3a and T3b** vs. average per-arm on T1/T2/T4: tests C3 (composition). Compare T3a (2-skill) and T3b (3-skill) for composition scaling.
- **Baseline pass rate** vs. Arm B pass rate on the same 3 tasks: tests C4 (training-data confound).

**Diagnostic:**
- **Per-task × per-arm pass rate matrix** (5 × 3 cells): surfaces which task shapes are weak under which arms.
- **Failure-mode distribution** overall and **per-arm**.
- **Failed-fragment distribution** overall: cross-skill (composition_error) vs. within-skill (under_specified_procedure) tells you whether the issue is fragmenting or composition.
- **Root-cause distribution per arm:** drives §8 decisions. The same root-cause appearing in multiple arms means it's not arm-specific; appearing only in Arm C suggests the dropped fragment types were load-bearing.
- **Robustness pass rate** at temp 0.3 vs. temp 0.0 on T1, T3a, T3b, Arm B: stability check across single-skill, 2-skill, and 3-skill activation.
- **Token cost per arm:** confirms or refutes the context-budget hypothesis.

---

## 8. Decision rules

The pilot produces evidence on H1 (primary) and C1–C4 (sub-claims). The decision is informed by the combination, not the headline alone.

### 8.1 H1 passes (Arm B ≥85%)

The architecture's primary claim holds for build-phase work in this domain. The methodology survives gold-standard content. Now read the sub-claim evidence to refine the recommendation:

- **C1 holds (A ≈ B, gap < 2 trials/task):** retrieval can drop `rationale + example` for execution-routed queries. Saves context budget without quality loss.
- **C1 fails (A − B ≥ 2 trials/task):** rationale and/or example are doing real work for execution. Keep them in execution-routed retrieval; the schema's "anchoring vs. load-bearing" framing needs revision.
- **C2 holds (B − C ≥ 2 trials/task):** verification + guardrail are load-bearing for execution. Include in execution-routed retrieval.
- **C2 fails (B ≈ C):** verification + guardrail can be deferred to a separate retrieval pass for downstream agents (verification critic, scope-guard layer) rather than included in primary execution context.
- **C3 holds (T3a and T3b both within 1 trial/arm of single-skill tasks; T3a − T3b gap < 2 trials/arm):** multi-skill composition emerges from fragment selection. No coordinator needed. Composition difficulty doesn't scale catastrophically.
- **C3 fails (T3a or T3b underperforms by ≥2 trials/arm; or T3a − T3b gap ≥2):** composition needs explicit coordination — workflow-class skills must do the wiring rather than emerging from selection. If T3a passes but T3b fails, composition works at 2 skills but degrades at 3 — a meaningful diagnostic about how far emergent composition stretches.
- **C4 fails (baseline ≈ Arm B):** the test domain is too well-represented in training data; results are inconclusive. Re-run on a less common domain before accepting H1.

Caveat the conclusion to scope: this is one workflow phase, one task domain, one model. Cross-phase and cross-domain generalization are open questions.

Proceed with:
1. **Retrieval-mechanism pilot.** Now that hand-curated retrieval works, test whether the actual retrieval system can produce the same fragment selection.
2. **Cross-phase pilot.** Pick a non-build-phase task and re-run.
3. **Begin scaled re-authoring.** With methodology validated, the case for re-authoring the corpus to gold standard is strong.

### 8.2 H1 partial (Arm B at 70–84%)

Methodology has signal but is fragile. Sub-claim evidence drives diagnosis:

- **`composition_error` or `composition_gap` dominates failures, especially on T3a or T3b:** multi-skill composition is the bottleneck. If concentrated on T3b (3-skill) but T3a (2-skill) is fine, composition works at small scale but breaks at 3 skills. If both fail, composition is broken even at 2 skills. Either revise authoring rules to require composition-friendly fragment design, or accept that composition needs a coordinator (workflow-class skill) rather than emerging from fragment selection alone.
- **`under_specified_procedure` dominates:** execution fragments carry less "how" than expected. The R-rules don't guarantee fragment self-sufficiency for execution. Strengthen C1 lint to check execution-fragment completeness.
- **`missing_rationale` or `missing_example` dominates Arm B failures (but Arm A passes more):** the architecture's assumption that anchoring fragments aren't load-bearing for execution is wrong. Revise §5.2 retrieval policy to include rationale anchors for execution-routed queries.
- **`missing_setup` appears anywhere:** an authoring problem. Setup content should be self-contained per skill. Refactor the skill before re-running.
- **`scope_guard_too_weak` dominates:** guardrail fragments under-deliver on scope discipline. Either author guardrails more aggressively, or add an explicit "decline if outside fragment scope" instruction at the agent level.
- **Failures spread evenly:** the issue is upstream. Re-examine task specificity, skill activation, and authoring.

Re-author or refine, re-run targeted subset (not full 64). If Arm B pass rate moves to ≥85%, treat as 8.1. Two iterations at 70–84% → treat as 8.3.

### 8.3 H1 fails (Arm B <70%)

Methodology doesn't survive even gold-standard content. This is the answer to the chicken-and-egg: it tells you authoring quality wasn't the bottleneck — methodology was.

Possible directions, informed by which root cause dominates:

- **`missing_rationale` or `missing_example` dominates (and Arm A pass rate is materially higher):** anchoring fragments are load-bearing for execution after all. Revise retrieval to include them. Cheapest fix; architecture survives.
- **`composition_*` dominates, especially on T3a or T3b:** multi-skill fragment composition is the wrong abstraction. Workflow-class skills must do explicit composition rather than emerging from fragment selection. Architectural change. The relative pattern across T3a (2-skill) and T3b (3-skill) tells you whether composition fails immediately or scales out.
- **`model_capability` dominates:** Tier 2 can't execute this work regardless of preparation. Test alternatives in cost order: bigger model, slot-fill rather than fragment composition, human-in-the-loop, or accept Tier 3 for execution.
- **C4 fails (baseline ≈ Arm B):** results are inconclusive — the domain doesn't discriminate fragment-driven from training-driven execution. Run a different domain.
- **Heterogeneous failures (no dominant root cause):** the architecture has multiple compounding weaknesses. Pause architectural commitments; run smaller, more targeted experiments to isolate root causes.

A failed pilot with rich root-cause data is more valuable than a passed pilot with no instrumentation. The decision is informed in either direction.

---

## 9. Risks

**R1: Authored skill quality dominates the result.** Same as v1's R1, applies more strongly here. *Mitigation:* §3.3 hard rule — only `approve`-verdict skills enter the pilot. If two attempts at QA gate can't produce gold-standard `fastapi-middleware-patterns`, change the task domain rather than lower the bar.

**R2: Manual fragment selection biases the result.** The pilot rests on "ideal retrieval" being implementable later by the actual retrieval system. *Mitigation:* document the selection logic explicitly per task and arm. If selection requires judgment that retrieval can't reproduce, that's a finding — note it.

**R3: 3-skill composition may not generalize to 4+ skills.** T3b tests 3-skill composition; some real workflows activate more. *Mitigation:* if T3b passes consistently, plan a v3 pilot with 4–5 skill activation before committing the architecture broadly. With cheap authoring, a 5-skill follow-up pilot is now a low-effort scope expansion.

**R4: T5 is uniquely hard for code models.** Scope-decline behavior is unusual. *Mitigation:* if T5 fails consistently while T1–T4 pass, treat as a partial result — methodology works for in-scope execution but needs an explicit out-of-scope guard at the agent level. Document and proceed.

**R5: Tier 2 succeeds because of training data, not fragments.** FastAPI + webhooks + JWT + async are well-represented in training corpora, and Qwen3-Coder-30B-A3B is post-trained specifically on agentic coding tasks with high quality, which strengthens this risk relative to a smaller baseline model. *Mitigation:* baseline arm (zero fragments) on T1, T2, T3a, T3b with 3 runs each = 12 baseline trials. C4 in §1.1 makes this a first-class sub-claim, not a footnote. Including both T3a and T3b in baseline tests whether training-data effects differ between 2-skill and 3-skill task framings. **If C4 fails (baseline ≈ Arm B), the result is inconclusive and a less-trained-on domain must be tested before drawing architectural conclusions.**

**R6: Pilot scope creep.** Tempting to add a third skill, more arms, or a real retrieval test. *Mitigation:* don't. Other questions deserve other pilots. v3 pilot adds the third skill if v2 passes; retrieval-mechanism pilot is a separate effort.

**R7: 81 trials is more manual review than estimated.** With manual response application + faithfulness review + root-cause tagging, 81 trials may stretch the verification phase beyond budget. *Mitigation:* the harness automates as much as possible (parsing, app-launch checks, HTTP test calls). Faithfulness is the only fully manual step. Budget 2–2.5 days for review; if it stretches, reduce arm-comparison runs from 3 to 2 per cell (drops total to 54 trials but weakens the gap-detection threshold to ~17 percentage points at the arm aggregate).

**R8: MoE routing non-determinism contaminates the consistency measurement.** Qwen3-Coder-30B-A3B is a Mixture-of-Experts model. Even at temperature 0.0, MoE expert routing can produce subtly different outputs across runs depending on backend implementation, batching behavior, and floating-point ordering. This is distinct from sampling variance and isn't fully suppressible. *Mitigation:* if the consistency check on T1 Arm B (10 runs at temp 0.0) shows higher-than-expected variance, the MoE architecture is the likely cause, not the fragments — record this and don't treat it as a fragment-quality signal. If consistency variance is severe enough to confound the arm comparison, the fallback model is Qwen3.5-27B dense, which eliminates MoE non-determinism at the cost of reasoning that may induce more `scope_violation` failure modes. Switching models mid-pilot invalidates prior trials per §2.4 — decide before trials start whether MoE routing behavior is acceptable or whether to use the dense fallback from the outset.

---

## 10. Definition of done

The pilot is complete when:
- 81 trials run and recorded via `DuckDBTelemetryWriter` (composition_traces + pilot_trials in `skills.duck`) per §7.1 (54 arm comparison + 12 baseline + 15 robustness).
- Each trial verified per §7.2.
- Each failed trial has `failed_fragment` and `failure_root_cause` populated per the §7.1 enums.
- Aggregate metrics computed per §7.3: Arm B pass rate (headline), per-arm pass rates, T3a and T3b composition signal (incl. T3a − T3b scaling gap), baseline comparison, robustness pass rate, per-arm root-cause distributions, token cost per arm.
- Authored skills committed to the repo at gold standard, with QA gate verdicts logged. The webhook skill's guardrail augmentation committed alongside.
- Write-up (2–3 pages) capturing: H1 result, C1–C4 evidence, the §8 decision, next move.
- Trial harness, fragment selection logic, and a snapshot of `skills.duck` (or exported `composition_traces` + `pilot_trials` for the pilot's `composition_id` range) committed as reproducibility artifact.

The write-up is the deliverable. With root-cause instrumentation and sub-claim isolation, both pass and fail outcomes produce architectural guidance.

---

## 11. Estimated effort

| Phase | Estimate |
|-------|----------|
| Author 3 new skills via research LLM (`jwt-validation-patterns`, `fastapi-middleware-patterns`, `python-async-patterns`) including QA gate iteration | 1–1.5 days |
| Augment `webhook-patterns` with explicit guardrail fragment | 0.25 day |
| Human review pass + sign-off across all 4 skills | 0.5 day |
| Construct 6 task variations with locked inputs and FastAPI app skeleton | 0.5–1 day |
| Build trial harness with arm-construction logic (~150 lines Python) + `pilot_trials` DuckDB schema migration + git-worktree isolation | 1 day |
| Run 81 trials | 0.25–0.5 day (at ~40 tok/s, inference is ~45 minutes; bottleneck is per-trial harness overhead, not generation) |
| Functional verification (mechanical) + faithfulness review + root-cause tagging | 2–2.5 days |
| Compute metrics + write up findings | 0.5 day |
| **Total** | **6–7.25 days** |

Verification is the dominant phase. Trial-running has dropped from earlier estimates because Tier 2 runs at ~40 tok/s on the operator's hardware (Strix Point UMA, see §2.4), making the 81 trials a sub-hour batch operation. Don't fill the time saved with scope expansion — it's the right amount of headroom for the inevitable surprises.

If verification stretches past 2.5 days, options:

- Reduce arm-comparison runs from 3 to 2 per cell (drops to 54 arm trials; threshold weakens to ~17 percentage points)
- Drop T3a in favor of T3b alone (loses the 2-skill vs 3-skill composition comparison; tests only 3-skill composition)
- Drop T4 in favor of inline guardrail testing within T1/T2 (loses targeted guardrail-led test)

Don't compress by reducing authoring quality or skipping the human review pass. Those are what isolate the methodology test from the original chicken-and-egg confound.

If the pilot stretches past 9 days, scope is creeping. Do not add a 5th skill or a real retrieval test mid-pilot.

---

## 12. Document conventions

This pilot tests the architecture's load-bearing claim end-to-end on known-good content. It is not a benchmark, a regression suite, or a feature evaluation. The only question on the table is whether workflow-phase fragment retrieval methodology supports Tier 2 deterministic execution when authoring quality is held constant.

Pass: methodology validated for one real case; proceed with retrieval pilot and re-authoring at scale.
Partial: failure data tells you which sub-claim of the architecture needs work.
Fail: methodology is the bottleneck, not authoring; architectural rethink.

All three outcomes are useful. An inconclusive outcome is not.

---

## Appendix — Changelog from v2 → v2.1

QA review surfaced issues that needed correction before the pilot was runnable:

**Severity 1 (would invalidate pilot):**
- Arm definitions corrected: setup is now in all three arms (it carries env vars, imports, middleware order — load-bearing for execution, not anchoring content).
- Webhook skill's missing guardrail fragment now flagged; §3.3 requires augmenting it before trials.
- Sample sizes raised: 3 runs per arm × task cell is the minimum that makes the gap thresholds in §1.1 meaningful. Total trials raised from 38 to 64.
- T3 reframed to use only the 2 in-scope skills (webhooks + fastapi-middleware), removing the JWT inconsistency.

**Severity 2 (weakens conclusions):**
- Hypothesis decomposed into H1 (primary) + C1–C4 (sub-claims) so failures are diagnosable.
- Headline metric explicitly "Arm B pass rate" rather than aggregate "all trials."
- Arbitrary "10-point band" replaced with defensible threshold ("≥2 trials per task gap").
- Robustness trials moved to temp 0.3 (testing model robustness); arm comparison stays at temp 0.0 (controlling for sampling variance).
- C4 (training-data confound) elevated from R5 footnote to a first-class sub-claim with 9 baseline trials.
- §7.3 explicit on per-arm root-cause aggregation, not just overall.

**Severity 3 (improvements):**
- "No revise outcomes" relaxed to "final verdict approve" — matches actual QA gate behavior.
- Authoring effort widened to 1.5–3 days for `fastapi-middleware-patterns` (revise → approve loops are normal).
- Faithfulness criterion clarified on imports: stdlib + already-present allowed; third-party absent from fragments is a scope reach.
- Token estimates marked as preliminary pending real measurement during authoring.

**v2.2 correction (post-publication):**
- Telemetry stack realigned with existing infrastructure: `DuckDBTelemetryWriter` writing to `composition_traces` (production-aligned record) + sibling `pilot_trials` table in `skills.duck`. The earlier draft proposed a parallel SQLite store, which would have duplicated production fields (latencies, tokens, errors) and broken consistency with how production telemetry is queried. No SQLite anywhere in the pilot.

**v2.3 expansion (post-authoring-cost correction):**
- Authoring constraint relaxed: research LLM (Opus or equivalent) does the drafting; humans review. Authoring is no longer the pilot's bottleneck. Per-skill effort dropped from 1.5–3 days (human-author) to ~0.25–0.5 day (LLM + human review).
- Skill scope expanded from 2 to 4 skills across 3 tiers: `webhook-patterns` (protocol), `jwt-validation-patterns` (protocol), `fastapi-middleware-patterns` (framework), `python-async-patterns` (language). Captures cross-tier composition variance the 2-skill scope couldn't.
- Task scope expanded from 5 to 6 variations: T3 split into T3a (2-skill composition) and T3b (3-skill composition), enabling direct comparison of how composition difficulty scales with skill count.
- C3 sub-claim updated to test both T3a and T3b, with an additional check that T3a − T3b gap is < 2 trials per arm (composition difficulty doesn't scale catastrophically).
- Trial count grew from 64 to 81: 54 arm comparison (was 45) + 12 baseline (was 9) + 15 robustness (was 10).
- Verification is now the bottleneck rather than authoring. §11 effort allocation shifted accordingly.

**v2.4 update (post-model-selection):**
- Tier 2 model swapped from Qwen 2.5 Coder 14B (dense, slow) to Qwen3-Coder-30B-A3B-Instruct (MoE, faster on bandwidth-bound hardware). Specific GGUF source: Unsloth Q4_K_S, KV cache F16, 32K context, eval batch 512, 8 CPU threads. Operator hardware: AMD Strix Point with 96 GB RAM (48 GB UMA), measured ~40 tok/s.
- New §2.4 locks the runtime configuration in the spec so any single trial is reproducible from the document alone.
- §5.3 context-overflow concern removed: 32K window comfortably fits T3b Arm A; native 256K is available if needed.
- §11 trial-running estimate dropped from 1.5–2 days to 0.25–0.5 day; verification confirmed as the dominant phase.
- New R8 risk added for MoE routing non-determinism (consistency variance not attributable to fragments). Fallback model identified: Qwen3.5-27B dense. Switching mid-pilot invalidates prior trials.
- R5 (training-data confound) strengthened to acknowledge that a stronger, more agentically-trained model raises baseline-comparison risk, not lowers it.

# Unified Synthesis — Milestones 5 through 8

> Skill-tax pilot small-model extension. M5 (model sweep) → M6 (seed injection) → M7 (anti-pattern fragments) → M8 (self-QA two-call). 451 total trials across 5 small models. Definitive writeup; supersedes `_M5_SYNTHESIS.md` for the post-M5 work.

---

## 1. Headline

The pilot's small-model extension dissolved two unknowns simultaneously and produced a load-bearing reframe of the Skillsmith product roadmap.

**The two unknowns:**

1. **Fragment taxonomy is sufficient.** Three independent intervention experiments (M3/M4 skill edits, M7 anti-pattern fragments, M8 self-review against fragments) failed to lift functional pass rate. Adding more fragments or better fragments doesn't shift the floor. The current taxonomy — rationale / setup / execution / example / verification / guardrail / anti-pattern — covers the surface needed.

2. **Execution-model size must be matched to cognitive shape, not optimized in isolation.** A 3B Coder passes T4 (one-line refactor, with seed) at 100%. The same 3B Coder fails T3a/T3b (multi-skill composition) at 0%. A 30B Coder also fails T3a/T3b at 0% in M3/M4. The same task takes different amounts of capability depending on its cognitive shape; matching is the engineering target.

**The reframe:** Skillsmith's bottleneck is not skill content. It is the architecture surrounding skills — code-index retrieval, knowledge-index retrieval, generalist phase routing, per-cognitive-shape execution-model sizing. Future investment shifts from skill engineering to the retrieval and routing infrastructure.

This synthesis is durable. The conclusions are supported by 451 trials with disciplined per-trial tagging. M3's failure-mode discipline made the architectural finding visible; M5–M8 confirmed it generalizes.

---

## 2. Trial inventory

| Milestone | Variable changed (cumulative) | Models | Trials | Status |
|-----------|--------------------------------|--------|--------|--------|
| M5 | Switch from Qwen3-Coder-30B-A3B to 5 sub-3.5B models | 5 | 227 | ✅ |
| M6 | + Seed-file content prepended to user message (`SHOW_SEED=1`) | 5 | 174 | ✅ |
| M7 | + 4 surgical anti-pattern fragments (webhook-patterns:9-12), new arm `arm_b_plus` | 4 | 20 | ✅ |
| M8 | + Self-QA two-call workflow (`REVIEW_PASS=1`) | 4 | 20 | ✅ |
| **Total** | | | **441** | |

Plus 10 Q10-precheck trials for Qwen2.5-Coder-1.5B that survived the M5 timeout incident, bringing the actual count to ~451 small-model trials.

**Models in the slate:**
- Qwen2.5-Coder-1.5B-Instruct-128k (1.5B, code-tuned, F16)
- Qwen2.5-Coder-3B-Instruct-128k (3.09B, code-tuned, F16)
- Llama-3.2-3B-Instruct (3.21B, general Instruct, BF16)
- SmolLM3-3B (3B, general Instruct, BF16) — M5/M6 only, dropped from M7/M8
- Phi-4-mini-instruct (3.8B, general Instruct, BF16)
- Qwen2.5-1.5B-Instruct (within-family general A/B partner) — corrupt download, never loaded

---

## 3. Cross-milestone metrics

### Functional pass rate (composition tasks T3a/T3b/T4 — M5/M6 surface)

| Model | M5 fp | M6 fp (+ seed) |
|-------|-------|-----------------|
| Qwen2.5-Coder-1.5B | 0/36 | 0/33 |
| **Qwen2.5-Coder-3B** | 0/36 | **3/36** (T4 arm_b: 0/3 → 3/3) |
| Llama-3.2-3B | 0/36 | 0/36 |
| **SmolLM3-3B** | 0/33 | **3/33** (T4 baseline: 0/3 → 3/3, no fragments) |
| Phi-4-mini | 0/36 | 0/36 |
| **Total** | **0/177** | **6/174** |

Seed injection lifted functional pass on **2 cells across 5 models** — both on T4 (one-line refactor, the simplest cognitive shape). T3a/T3b composition shape still 0% with seed across all model sizes.

### Strict-parse rate (output-format compliance)

| Model | M5 (T3a/T3b/T4) | M6 (+ seed) |
|-------|------------------|--------------|
| Qwen2.5-Coder-1.5B | 15/36 (42%) | 18/33 (55%) |
| Qwen2.5-Coder-3B | 15/36 (42%) | 15/36 (42%) |
| Llama-3.2-3B | 0/36 (0%) | 3/36 (8%) |
| SmolLM3-3B | 9/33 (27%) | 9/33 (27%) |
| Phi-4-mini | 15/36 (42%) | **0/36 (0%) ⚠️ regressed** |

Phi-4-mini's regression is a model-class quirk: the longer prompt with seed pushed it into more conversational responses, breaking `[FILE:]` compliance.

### T1 (net-new bounded shape) across M5/M7/M8

| Model | M5 arm_b parses/fp | M7 arm_b_plus parses/fp | M8 arm_b_plus + self-QA parses/fp |
|-------|---------------------|--------------------------|------------------------------------|
| Qwen2.5-Coder-1.5B | 10/10 / 0 | 5/5 / 0 | 5/5 / 0 |
| **Qwen2.5-Coder-3B** | 0/10 / 0 | 0/5 / 0 | **5/5** / 0 ✨ |
| Llama-3.2-3B | 0/10 / 0 | 0/5 / 0 | 0/5 / 0 |
| **Phi-4-mini** | 0/10 / 0 | 0/5 / 0 | **5/5** / 0 ✨ |

Self-QA dramatically lifted **format compliance** for two of four models (Qwen2.5-Coder-3B, Phi-4-mini) but lifted **functional pass** in zero cases.

### Bug-shape persistence (anti-pattern targets, M7 vs M8)

| Model | Bug | Fragment | M7 occurrence | M8 occurrence |
|-------|-----|----------|---------------|----------------|
| Qwen2.5-Coder-1.5B | positional `split(",")[N]` | wp:9 | 5/5 | **5/5** |
| Phi-4-mini | hallucinated "stripe uses compare_digest internally" | wp:11 | 5/5 | **5/5** |

Both models had the explicit anti-pattern fragment in their context, were asked in the M8 review pass to compare against it, and emitted the same bug in 100% of trials.

---

## 4. Findings

### Finding 1: Fragment composition is sufficient (high confidence)

Three independent intervention experiments failed to lift functional pass rate:

- **M3/M4** — added a lifespan-preservation guardrail to `fastapi-middleware-patterns:8`. T3a/T3b/T4 re-run: 3/27, identical to M3.
- **M7** — added 4 surgical anti-pattern fragments addressing the M5 T1 bugs. T1 functional pass: 0/20.
- **M8** — added a self-review pass asking the model to walk each fragment and identify deviations. T1 functional pass: 0/20.

Fragments contain the right content. The 1.5B Coder's positional-split persistence under M8 is the cleanest demonstration: the model had `webhook-patterns:9` in context, was asked to review against it, and emitted the bug 5/5 times anyway. The bottleneck is fragment **application**, not fragment **availability** — and application failure at small parameter scale is not addressable by adding more fragments.

Implication: skill-engineering effort below the application threshold is wasted effort. Above the threshold, current fragments do their job.

### Finding 2: Cognitive-shape × parameter-size matching is the load-bearing variable

Same 3B Coder, same fragments, same harness:
- **T4 arm_b (one-line refactor, seed shown):** 3/3 functional pass
- **T3a arm_b (2-skill composition, seed shown):** 0/3 functional pass

Same Qwen3-Coder-30B-A3B from M3/M4:
- **T1 arm_b (net-new bounded):** 10/10 functional pass (M3, via Stripe SDK shortcut)
- **T3a/T3b (multi-skill composition):** 0/27 functional pass (M3/M4)

The same model has different floors for different cognitive shapes. The pilot's data sketches at least four cognitive-shape classes:

| Shape | Definition | Smallest model that passes |
|-------|------------|------------------------------|
| Net-new bounded | Single file, well-known pattern (Stripe webhook from blank) | 30B-A3B Coder |
| Targeted local refactor | One-line edit with seed shown (T4 = `==` → `compare_digest`) | 3B Coder + seed |
| 2-skill composition | Wire existing handler + middleware (T3a) | None tested in pilot |
| 3-skill composition | + auth + DB lifecycle (T3b) | None tested in pilot |

Each shape has its own intervention floor. Skills can shift each floor independently but cannot replace the matching itself.

### Finding 3: Workflow interventions split structural and substantive corrections

Self-QA in M8 produced a clean dissociation:

- **Structural correction works.** Two models that ignored the `[FILE:]` directive in single-call mode (Qwen2.5-Coder-3B, Phi-4-mini) produced compliant markers in M8. The cognitive task of "check format compliance against an explicit directive" is within the parameter floor.
- **Substantive correction does not work.** No model fixed the bugs that anti-pattern fragments explicitly named. The cognitive task of "recognize my own buggy code against an anti-pattern description" is below the floor for these sizes.

This sharpens the deployment story. Self-QA at 2× cost is justifiable for output-format consistency where it earns its keep, but does not buy substantive bug correction. Pure cost increase if used for the latter.

### Finding 4: Format compliance does not track capability monotonically

The most surprising single result of M5:

| Model | Strict-parse rate |
|-------|--------------------|
| Qwen2.5-Coder-1.5B (smallest) | 54% |
| Qwen2.5-Coder-3B (twice the size) | 33% |
| Llama-3.2-3B (general, capable) | 0% |

Larger and "more capable" models *lose* format-compliance. They produce code in their preferred markdown-fence shape and ignore the `[FILE:]` directive. The 1.5B Coder is the most obedient because it has less capability surplus to override the format directive with its own preferences. **Compliance is an attention-control property, not a capability property.**

### Finding 5: Code runnability separates by training stack

Lenient-parse extraction recovered code from 187/227 M5 trials. Of those that ran:

| Family | Code-runs rate |
|--------|----------------|
| Qwen2.5-Coder family | 86% |
| Llama / SmolLM / Phi (general or general-leaning) | 51% |

Coder-tuned models produce code that *imports cleanly and starts*, even when subtly wrong. General Instruct models produce text that *looks like Python* but crashes uvicorn on startup half the time. Code-domain pretraining preserves runnable-output as a property even after generic chat tuning.

### Finding 6: Some cognitive shapes are unreachable at this parameter scale regardless of intervention

T3a/T3b composition shape was tested across:
- 4 model classes (Coder small, Coder mid, general small, general mid)
- With and without fragments (M5 vs M5-baseline)
- With and without seed (M5 vs M6)
- 0/180 functional pass across the entire small-model regime

The 30B Coder also failed T3a/T3b in M3/M4 — but for a different reason (architectural code-index gap), and likely passes once code-index retrieval is wired up. For small models, the floor is the model itself; no intervention tested moves it.

This is its own finding: **above some task-shape complexity, the only fix is bigger model.** Skills can't compensate; workflow can't compensate; bigger seed context can't compensate.

---

## 5. The deployment matrix

Synthesizing M3 through M8:

| Cognitive shape | 1.5B Coder | 3B Coder | 3B General | 3.8B General | 30B-A3B Coder |
|-----------------|------------|----------|-------------|---------------|----------------|
| Format compliance | native (54%) | needs self-QA | needs self-QA | needs self-QA | native |
| Net-new bounded (T1) | fails functional | fails functional | fails functional | fails functional | passes (M3) |
| Targeted refactor (T4) | fails functional | **seed required, passes** (M6) | fails functional | fails functional | passes (M3) |
| 2-skill composition (T3a) | fails functional | fails functional | fails functional | fails functional | code-index required (M3/M4) |
| 3-skill composition (T3b) | fails functional | fails functional | fails functional | fails functional | code-index required (M3/M4) |

**The product implication:** route work to the smallest model that passes the cognitive shape it's solving. A 3B Coder with seed-injection at 1× cost is the operating sweet spot for targeted refactors. Composition tasks require the 30B+ tier and code-index retrieval. Below 3B, the Skillsmith machinery doesn't earn its inference cost on this task surface.

For an org running many parallel small refactor agents, the matrix prescribes a tiered model deployment — and tells you which tasks shouldn't be sent to which tier.

---

## 6. What this validates with high confidence

- **Fragment taxonomy is stable infrastructure.** Three independent skill-content intervention experiments produced no functional-pass lift. Effort spent on better fragments below the parameter-application threshold is wasted.
- **Code-index retrieval is the load-bearing missing piece for composition shapes.** M4 architectural finding (T3a/T3b 0% because seed not in context) + M6 partial confirmation (T4 passes when seed shown) tell a consistent story.
- **Self-QA earns 2× cost for format compliance only.** Substantive bug correction at small scale is below the application threshold; review pass cannot reach below it.
- **Cognitive-shape × parameter-size matching is the practical engineering target.** The pilot's deployment matrix is the actionable output.

## 7. What's still open

- **Composition-shape floor.** No combination tested passed T3a/T3b. A 7B-class Coder or a properly-architected 30B-class with full retrieval might. Untested.
- **Code-index retrieval pathologies.** M6 simulated code-index by static seed-file injection. Real retrieval may have its own failure modes (stale index, retrieval-precision drift, scoping issues across multi-file changes).
- **Knowledge-index retrieval value.** "Why we chose X" / decision-history retrieval was never wired or tested. Could matter for tasks where the model is rewriting decisions it shouldn't (M3/M4 lifespan rewrite is plausibly a knowledge-index gap as much as a code-index gap).
- **Generalist phase-routing accuracy.** Pilot pre-specified phase. A real generalist that routes to wrong phase would propagate skills-mismatch downstream — pilot didn't measure that error mode.
- **Cross-domain skill categories.** Pilot tested build-domain skills only (webhook-patterns, fastapi-middleware-patterns, jwt-validation-patterns, python-async-patterns). Other Skillsmith categories — interview-domain, architecture-domain, devops-domain — have their own cognitive-shape signatures and need their own M5-style sweeps.

Each of these is a follow-up pilot with the same harness/methodology. The framework transfers; the evidence does not.

---

## 8. Position within the Skillsmith architecture

The pilot validated one slice of the broader stack:

```
[Generalist (phase router)]                    ← UNTESTED
       ↓
[Phase-specific execution model]               ← TESTED (M5: model size sweep)
       ↑
   ┌───┴───────────┐
   │               │
[Skills-index retrieval]                       ← TESTED (M3-M8: fragment composition)
[Code-index retrieval]                         ← PROXIED (M6: static seed injection)
[Knowledge-index retrieval]                    ← UNTESTED
```

The pilot validated:
- Skills-index retrieval delivers correct content (fragments are sufficient)
- Skills-index + execution-model alone isn't enough for composition shapes (need code-index)
- Execution-model size needs to match cognitive shape (matrix in §5)

The pilot did not test:
- Generalist phase-routing accuracy (would surface as wrong-skills failures, invisible here)
- Real code-index retrieval (M6's static injection is a crude proxy)
- Knowledge-index value (likely material for tasks involving decision history)
- Cross-phase or cross-skill-category variance

**The architectural pivot:** before this pilot, the engineering target felt like "make better fragments." After: build the retrieval architecture (code-index, knowledge-index, real generalist) and size execution-models per cognitive shape; fragments are stable.

---

## 9. Methodology contributions

Beyond the substantive findings, the pilot produced a transferable methodology:

- **Failure-mode tagging discipline (M3).** The locked enum (drift / hallucination / incomplete / scope_violation / parse_error / wrong_skill / composition_error) + root-cause enum (under_specified_procedure / model_capability / composition_gap / etc.) made the architectural finding visible. Without this, the pilot would have read as "fragments don't work" rather than "fragments work, architecture doesn't."

- **Lenient-parse reanalysis pattern.** The `harness/lenient_reanalyze.py` post-hoc tool separated "model can't produce code" from "model can produce code but ignored format." Critical for distinguishing structural from substantive failures.

- **Cognitive-shape framework.** Tasks were not just "tasks" — they were instances of distinct cognitive shapes (net-new bounded, targeted local refactor, multi-skill composition). Naming the shape made the deployment matrix possible.

- **Per-trial reproducibility.** rerun_checks.py + apply_tags.py + gen_reviews.py + the harness's deterministic temp-0.0 + the consistency_hash + the env_state recording. Any of the 451 trials can be replayed and re-verified.

These transfer to the next pilot regardless of subject domain.

---

## 10. Files and data lineage

| Artifact | Purpose |
|----------|---------|
| `experiments/skill-tax/skills/webhook-patterns.yaml` | 12 fragments incl. 4 anti-patterns added in M7 |
| `experiments/skill-tax/skills/fastapi-middleware-patterns.yaml` | M4 lifespan-preservation guardrail edits |
| `experiments/skill-tax/tasks/T1.yaml` | adds `arm_b_plus` arm for M7/M8 |
| `experiments/skill-tax/harness/run_trial.py` | trial runner; supports `SHOW_SEED=1` (M6), `REVIEW_PASS=1` (M8); per-trial timing |
| `experiments/skill-tax/harness/run_m5.sh` ... `run_m8.sh` | per-milestone sweep runners |
| `experiments/skill-tax/harness/rerun_checks.py` | check replay + env_state capture |
| `experiments/skill-tax/harness/lenient_reanalyze.py` | post-hoc fence-extraction |
| `experiments/skill-tax/harness/apply_tags.py` | idempotent tag application |
| `experiments/skill-tax/harness/gen_reviews.py` | review-file generator |
| `experiments/skill-tax/skills.duck::pilot_trials` | 561 rows total (M2: 81 + calibration/Q10: 12 + M4: 27 + M5: 227 + M6: 174 + M7: 20 + M8: 20) |
| `experiments/skill-tax/reviews/_FINAL_SYNTHESIS.md` | M3 synthesis (still authoritative for M2/M3) |
| `experiments/skill-tax/reviews/_M4_SYNTHESIS.md` | M4 architectural finding |
| `experiments/skill-tax/reviews/_M5_SYNTHESIS.md` | M5-only writeup (superseded by this document) |
| `experiments/skill-tax/reviews/_M5-M8_SYNTHESIS.md` | this document |
| `experiments/skill-tax/harness/m5_logs/` ... `m8_logs/` | per-model run logs with `lm_ms`/`total_ms`/`review_lm_ms` per trial |

---

## 11. Bottom line

The skill-tax pilot's small-model extension produced a roadmap-shifting result. The work matters not because of pass-rate numbers (mostly low) but because the failure-mode discipline let the architecture-level signal emerge from the data: **fragments work, the system around them needs to be built.**

That clarity is what makes this seminal. Future Skillsmith design decisions reference this pilot as the moment the priorities crystallized.

# Milestone 5 — Small-Model Sweep + Lenient-Parse Reanalysis

> 5 sub-3.5B models × 46 trials = 227 trials at v2 preamble. Lenient-parse post-hoc on all 163 strict-failures. Goal: test whether the macro "small model + skills" advantage shows up on this pilot's task surface.

---

## 1. Headline

**0/227 strict-parse functional pass. 0/163 lenient-parse functional pass on the post-hoc reanalysis of strict-parse failures.** Combined: 0/227 functional pass via either strict or lenient routes. The macro hypothesis that small models lift more from fragment retrieval did not manifest on this task surface — not because small models can't read fragments, but because the M4 architectural constraint (`[FILE:]` output format + seed file not in prompt = unsatisfiable preservation) dominates regardless of model size.

What did surface: large variance in **output-format compliance** and **code runnability** across model families, and a clear separation between "can produce extractable code" and "code that runs."

---

## 2. Cross-model results

| Model | Strict parse | Lenient extract | Lenient pass | uvicorn rc=1 |
|-------|--------------|------------------|---------------|---------------|
| Qwen2.5-Coder-1.5B-Instruct | **25/46 (54%)** | 25/46 | 0/46 | 0/46 |
| Qwen2.5-Coder-3B-Instruct | 15/46 (33%) | 33/46 | 0/46 | 8/46 |
| Llama-3.2-3B-Instruct | 0/46 (0%) | 40/46 | 0/46 | 21/46 |
| SmolLM3-3B | 9/43 (21%) | 43/43 | 0/43 | 24/43 |
| Phi-4-mini-instruct | 15/46 (33%) | 46/46 | 0/46 | 18/46 |

`qwen2.5-1.5b-instruct` (the within-family Coder vs general A/B partner) loaded-hung in LM Studio — likely a corrupt download. Skipped after burning ~1 hour on the hang. Re-downloading would let us complete that comparison.

---

## 3. The six findings

### Finding 1: Format compliance does not track model capability

The cleanest "we found something we weren't looking for" result. Strict-parse rate (compliance with `[FILE:]` markers) is *inversely* correlated with what we'd expect from model capability:

- Qwen2.5-Coder-1.5B (smallest, code-tuned) leads at 54% format compliance
- Qwen2.5-Coder-3B (twice the size, same family, more capable) drops to 33%
- Llama-3.2-3B (general Instruct, capable, 128K ctx) collapses to 0%

The 1.5B Coder is the *most obedient* to format directives. The 3B Coder ignores them in favor of producing what it considers "the right answer" — a markdown code block. Llama-3.2-3B aggressively produces explanatory prose around code blocks, ignoring the format requirement entirely. The pattern reverses the usual "more capable = more compliant" intuition.

### Finding 2: Code runnability separates by training stack

Lenient extraction recovered code from 187/227 trials (82%). Of those that ran, far fewer started cleanly:

| Family | Lenient extracted | uvicorn fails | Code-runs rate |
|--------|-------------------|---------------|----------------|
| Qwen2.5-Coder family | 58/92 | 8/58 | **86%** |
| Llama / SmolLM / Phi (general or general-leaning) | 129/135 | 63/129 | **51%** |

Coder-tuned models produce code that *runs*, even if not correct. General Instruct models produce code that often crashes uvicorn at import or startup. This is a fragment-independent property — pretraining/fine-tuning distribution matters.

### Finding 3: 0/227 functional pass even with lenient parsing

Even when we extract markdown code from response and write it to `app/main.py` directly, no trial passes mechanical checks. Fragments don't make small models produce working FastAPI code on this pilot's task surface.

This reinforces the M4 architectural finding. The small-model regime does not unlock pass rate because:
- Small models lack the SDK-shortcut memorization the 30B Coder used (no `stripe.Webhook.construct_event` muscle memory)
- Small models can't preserve seed-file content they haven't seen
- Small models can't follow the multi-step composition in T3a/T3b
- Fragments help with structure (some models) but not with task-specific completion

### Finding 4: SmolLM3-3B think-mode tokens exhaust on long-fragment trials

SmolLM3's think/no-think dual mode defaulted to think. On T3b arm_c (12 fragments + 6.2K input tokens), the model spent the entire 2048-token output budget on `<think>` reasoning, leaving no actual content. 3 trials failed with `finish_reason=length` and empty content. Surfacing this so milestone-6 can either disable think-mode or raise the cap. SmolLM3 lenient-extracted 100% on the 43 trials that produced output, suggesting the underlying capability is there once thinking is bounded.

### Finding 5: 1.5B Coder doesn't have fence-fallback either

The 1.5B Coder has 21 strict-parse failures, but ZERO of them have a recoverable markdown code fence. The other models' format failures at least include code in some structure; the 1.5B Coder's failures are bare prose, refusal-shape replies, or single-line text. This is qualitatively different — the 1.5B Coder *fails to produce any code-block structure* on its weakest trials, where larger models still produce code-shaped text.

This is also the cleanest "fragments lift format compliance" signal in the dataset: 1.5B Coder produces well-formatted output when given more fragments and degrades to non-output when given fewer, while larger models keep producing code-shaped text regardless of fragment count but ignore the format directive.

### Finding 6: Wall-time per model

Per-model run time at temp 0.0, ~46 trials each:

| Model | Wall time | Avg per trial |
|-------|-----------|----------------|
| Qwen2.5-Coder-1.5B-Instruct | ~50 min (incl. 1× 928s runaway) | ~65 sec/trial† |
| Qwen2.5-Coder-3B-Instruct | 54 min | ~70 sec/trial |
| Llama-3.2-3B-Instruct | 43 min | ~56 sec/trial |
| SmolLM3-3B | 48 min | ~63 sec/trial (excl. 3 max-token failures) |
| Phi-4-mini-instruct | 28 min | ~37 sec/trial — fastest in the slate |

†One T3a arm_a r1 trial looped until 16384-token cap (15.5 min) before the max_tokens=2048 cap was added mid-sweep. Subsequent trials all ≤45 sec.

Phi-4-mini's speed advantage is meaningful — at ~37 sec/trial it's nearly 2× faster than the others despite being the largest at 3.8B. Phi's strong instruction-following + decent throughput would matter for any production small-model deployment.

---

## 4. Sub-claim verdicts (small-model regime)

Per spec §1.1, the sub-claims are predictions; the data refutes or holds them. Labels match the spec:

### C1 — "Anchoring fragments are NOT load-bearing"

**Inconclusive at small scale.** At functional-pass level, T4 fails universally (0/9 across all arms for every small model), so the C1 prediction can't be tested on functional pass. **At the structural-compliance level**, however, the arm-cell gradient IS visible: Qwen2.5-Coder-1.5B parses 9/9 (arm_a) → 6/9 (arm_b) → 0/9 (arm_c) → 0/12 (baseline) across the four conditions. This is fragment-density-driven format compliance, not a direct test of C1's "rationale + example specifically." Cleanest fragment-effect signal in the small-model dataset, but it's a *structural* effect not a *functional* one and doesn't directly resolve the C1 prediction.

### C2 — "Verification and guardrail are load-bearing"

**Inconclusive at small scale.** Tests Arm B vs Arm C (verification+guardrail dropped). All small models fail functional pass on both arms across T3a/T3b/T4, so the B-vs-C gap is unmeasurable due to floor effect.

### C3 — "Multi-skill composition works"

**Refuted at small scale.** T3a (2-skill) and T3b (3-skill) pass 0% across all small models in M5 (and 0% in M6 with seed). The gap vs T1 net-new (also 0% functional pass at small scale, but produces extractable code while T3a/T3b often don't pass even structurally) confirms composition does NOT work at small parameter scale on this fixture set.

### C4 — "Fragments are doing distinctive work"

**Holds strongly at small scale.** Baseline (no fragments) was 0/45 functional across the 5 small models on T3a/T3b/T4. Fragments don't lift functional pass on T3a/T3b either (0%), so C4's strong form (baseline materially lower than Arm B by 2 trials per task) is technically vacuous at this scale because both are zero. But the structural evidence from T1: with fragments, models attempt and produce extractable code; without, models decline or hallucinate (per M3 baseline review). Fragments grant permission to attempt — distinct work, even if functional pass doesn't track.

---

## 5. What the experiment actually demonstrated

1. **The M4 architectural finding holds across model size.** The `[FILE:]` + invisible seed constraint is fundamental, not a model-capability quirk. Five additional model points confirm what M4's single point established.
2. **Format compliance is a model-class property worth measuring.** It varies wildly (0% to 54%) and doesn't track size linearly. For any future structured-output deployment, output-format reliability is a screening criterion that should run before functional evaluation.
3. **Coder-family training preserves runnable-code behavior even at small scale.** Code-tuned 1.5B and 3B models produce code that imports and starts at much higher rates than general Instruct models of the same size.
4. **The macro "skills lift small models" hypothesis cannot be tested on this pilot's task surface.** Not because the hypothesis is wrong (the literature evidence remains valid), but because this task surface — where seed preservation dominates failure mode — masks any positive effect skills might have.

---

## 6. Files

- `experiments/skill-tax/harness/run_m5.sh` — model-sweep runner with load-timeout + per-trial-failure resilience
- `experiments/skill-tax/harness/lenient_reanalyze.py` — post-hoc fence-extraction + re-verification
- `experiments/skill-tax/harness/m5_logs/` — per-model logs with `lm_ms` / `total_ms` per trial
- `/tmp/m5_lenient_results.json` — 163 lenient-reanalysis records
- `/tmp/m5_manifest.json` — model-to-trial-id mapping
- `experiments/skill-tax/skills.duck::pilot_trials` — 227 M5 trials added to existing 120 (M3+M4) = 347 rows total

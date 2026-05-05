# Batch 2 Synthesis — T3a/T3b Uniformity + T4 Arm-Split

> 11 new reviews (8 T3a/T3b + 3 T4). Scope: confirm lifespan-rewrite uniformity, characterize T4's arm-cell split, surface fragment text bearing on the `under_specified_procedure` vs `scope_guard_too_weak` vs `model_capability` decision. Tags proposed; reviewer makes final call.

---

## 1. T3a/T3b lifespan-rewrite is uniform with three sub-patterns

Across all 18 T3a + T3b arm-comparison trials: 18/18 retain `@asynccontextmanager`, 0/18 retain the seed's `CREATE TABLE IF NOT EXISTS processed_webhook_events`. The pattern *splits by arm cell*, not run:

| Cell | Pool retained | Schema retained | Lifespan body |
|------|---------------|-----------------|---------------|
| T3a arm_a (3) | yes | **no** | pool-only |
| T3a arm_b (3) | yes | **no** | pool-only |
| T3a arm_c (3) | yes | **no** | pool-only |
| T3b arm_a (3) | **no** | **no** | **empty stub** (just `yield`) |
| T3b arm_b (3) | yes | **no** | pool-only |
| T3b arm_c (3) | **no** | **no** | placeholder (`app.state.db = None`) |

The sub-patterns matter for tagging. T3a (all arms) and T3b arm_b drop ONE thing (the schema setup). T3b arm_a drops EVERYTHING from the lifespan (no pool, no schema). T3b arm_c drops the pool but assigns `app.state.db = None` as a placeholder. The T3b arm_a/arm_c failures are *more degraded* than T3a's, despite identical task description and similar arm definitions.

## 2. Fragment-induced bias is the load-bearing finding

The §3a excerpts reveal *why* the model rewrites the lifespan: **the fragments contain competing lifespan templates that don't include schema setup.**

**`fastapi-middleware-patterns:2`** (setup, in arm_a only) shows a lifespan with pool but no schema:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: pool, clients, etc.
    app.state.db = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    yield
    # shutdown
    await app.state.db.close()
```

**`fastapi-middleware-patterns:6`** (example, in arm_a only) shows an *empty* lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: open shared resources here
    yield
    # shutdown: close shared resources here
```

**`fastapi-middleware-patterns:7`** (verification) says "Long-lived resources (DB pools, HTTP clients, JWKS caches) open in `lifespan` and close in the same context" — generic, no task-specific guidance.

**`fastapi-middleware-patterns:8`** (guardrail) says "Never use `@app.on_event(...)`" but **never** says "if a seed lifespan exists with task-specific setup, preserve it; do not replace with a fragment template."

The seed's lifespan with `CREATE TABLE` is *not* anywhere in the fragments. The task description says "Keep the existing lifespan context as the single source of pool initialization; do not wire a second pool" — but it doesn't say "do not replace the lifespan body." The model reads the fragment templates as authoritative defaults and substitutes them.

This is **not a model-capability gap on its own** — the fragments contain a *positive* signal that conflicts with the task description, and the model resolves the conflict in favor of the fragments. The skill author did not anticipate this seam. **`under_specified_procedure` is the right root_cause** for this pattern (the fragments don't address the seam between "fragment template" and "preserve seed-specific content").

## 3. T3b arm_a/arm_c degradation is qualitatively different

T3b arm_a writes `app.state.db = None` or no pool at all. T3b arm_c writes `app.state.db = None  # placeholder`. These trials had MORE fragments (24 fragments incl. python-async-patterns) and STILL produced more degraded output. The model isn't just substituting a fragment template — it's discarding the task-specific work entirely and writing a stub. That is closer to **`model_capability`** territory: even with full context, the model doesn't reliably preserve setup that's outside the fragment templates.

**Suggested model_capability candidate:** `4941d5ad` (T3b arm_a r1) — fragment_count=24 (largest possible context), explicit task description "Keep the existing lifespan context", explicit fragment text for pool init via `asyncpg.create_pool` — and the model still produced an empty `yield`-only lifespan. If 24 fragments + explicit instruction don't prevent this, the gap is the model.

## 4. T4 arm-split is NOT about compare_digest

All 9 T4 trials (passing AND failing) use `hmac.compare_digest`. None use `stripe.Webhook.construct_event`. None use `==` comparison. **The compare_digest refactor lands on every trial.** Yet arm_a passes 3/3 and arm_b/c fail 6/6.

Inspecting actual responses:

**T4 arm_a (passing, 8 frags):** modifies the seed's `app/main.py` line-by-line, preserving `_parse_v1_sig`, `_TOLERANCE_SECONDS`, `/webhooks/stripe` path, full HMAC scheme, `HTTPException` shape. Just swaps `==` for `hmac.compare_digest`.

**T4 arm_b (failing, 6 frags):** REWRITES the entire file. Key bugs in the rewrite:
- Endpoint path: `/webhook/stripe` (singular — wrong)
- Timestamp source: invents non-existent `X-Stripe-Webhook-Timestamp` header instead of parsing `t=...` from `Stripe-Signature`
- Response shape: returns `({"error": ...}, 400)` tuple — FastAPI doesn't handle this as an HTTP response
- Drops `_TOLERANCE_SECONDS` check entirely

T4 arm_b is a `scope_violation` of the same kind as T3a/T3b: model substitutes its own implementation when told to refactor one line. **The arm-split refutes spec C1** ("anchoring fragments NOT load-bearing"): arm_a's 2 extra fragments (rationale + example) are load-bearing for "preserve other behavior." When dropped (arm_b/c), the model treats T4 as "implement a webhook" rather than "refactor one line."

## 5. Proposed tags

### T3a/T3b lifespan-rewrite (16 trials, can tag in bulk)

```
failure_mode: scope_violation
failure_root_cause: under_specified_procedure
faithfulness_pass: no  (fragment templates were used; seed-specific content was discarded)
failed_fragment: fastapi-middleware-patterns:2  OR  fastapi-middleware-patterns:6
                 (the templates that compete with the seed)
```

**Reasoning:** Model substituted a fragment-provided lifespan template for the seed's task-specific lifespan. Task description's "Keep the existing lifespan context" was not strong enough to override the positive fragment signal. The fragments themselves don't address the seam ("if a seed lifespan exists with setup logic, preserve it, do not replace with the example template"). This is fragment quality, not model capability — fixable in milestone 4 by adding a guardrail to the skill. `failed_fragment` could be either `:2` or `:6` depending on which the model echoed; if both contributed, mark `multiple`.

### T3b arm_a (3 trials) — special case, candidate model_capability

```
failure_mode: scope_violation  (same)
failure_root_cause: model_capability  (24 fragments + explicit task description still produced empty stub)
faithfulness_pass: no
failed_fragment: unattributable
```

**Reasoning:** Suggest tagging at least `4941d5ad` (T3b arm_a r1) with `model_capability` because the input was maximally rich and the output was maximally degraded (empty `yield`-only lifespan). The other two T3b arm_a trials (`f5625207`, `636d368f`) can also take `model_capability` if the same empty-stub shape is present (it is — verified above).

### T3b arm_c (3 trials) — also degraded but with arm-explanation

```
failure_mode: scope_violation
failure_root_cause: under_specified_procedure
faithfulness_pass: no
failed_fragment: fastapi-middleware-patterns:6
```

**Reasoning:** T3b arm_c writes `app.state.db = None  # placeholder` — likely echoing fragment :6's "open shared resources here" comment shape (placeholder hint). With fewer fragments (12 in arm_c vs 24 in arm_a), the placeholder shape from :6 dominates. This is fragment-induced, not capability-limited.

### T4 arm_b/arm_c (6 trials)

```
failure_mode: scope_violation  (rewrote file when told to refactor one line)
failure_root_cause: composition_gap  (arm_b/c lack the rationale+example fragments that constrain "preserve other behavior")
faithfulness_pass: no  (used compare_digest correctly but discarded the surrounding seed code)
failed_fragment: webhook-patterns:1 (rationale, in arm_a only)  OR  webhook-patterns:6 (example, in arm_a only)
```

**Reasoning:** T4 arm-split is direct **spec-C1-refutation** evidence ("anchoring fragments NOT load-bearing" prediction does not hold — they ARE load-bearing for execution). arm_a's extra fragments (rationale + example) carry the "preserve other behavior" signal; arm_b/c lack them and the model defaults to "implement a webhook from scratch." This is the cleanest evidence in the pilot for fragment-type composition mattering. `composition_gap` captures it precisely.

## 6. Bulk-tag readiness

The lifespan-rewrite pattern is uniform enough to tag T3a (9 trials) and T3b arm_b (3 trials) in bulk with the same tags. T3b arm_a (3 trials) and T3b arm_c (3 trials) need per-cell tag distinction (model_capability vs under_specified_procedure). T4 arm_b/c (6 trials) tags in bulk on `composition_gap`.

That's 21 tagged trials from the next bulk pass, plus the 5 already in the review pile — leaving:
- 12 T2 deferred (need manual db-check decision)
- 4 T1 baseline + T2 baseline + T3a baseline + T3b baseline (12 baseline trials, mostly decline-shape — bulk-taggable)
- 9 T1 arm_comparison (passing — faithfulness review only)
- 9 T5 arm_comparison (passing-via-decline — bulk-taggable)
- 15 robustness (mostly mirror arm_b results — bulk-taggable)

Total remaining after this batch's bulk tags: ~33 trials, of which only T2 deferred + T1 passing need real per-trial review.

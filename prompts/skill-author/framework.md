# Tier addendum: framework

Layer on top of `fixtures/skill-authoring-agent.md` for `framework`-tier skills (FastAPI, NestJS, Airflow, Django, Spring, Rails — frameworks with frequent releases and material API churn).

Recommended local model: `qwen3-coder-30b-a3b-instruct`.

---

## Source policy — MANDATORY fetch

**Before drafting any fragment, fetch the framework's official docs at the version pinned in `pack.yaml`.** Quote relevant snippets into the verification fragment with URL + R5 date-stamp. If fetch fails, STOP and declare — do NOT draft from training data alone.

Why: framework APIs deprecate without notice. Pre-cutoff training data routinely teaches deprecated patterns (e.g., FastAPI `@app.on_event` was deprecated in 0.110+; Airflow operators changed shape between 1.x and 2.x). Drafting from training-data recall produces skills that confidently advise deprecated APIs.

### Fetch protocol

1. Read `pack.yaml` for the pinned version (e.g., `fastapi: ">=0.115,<0.117"`).
2. Fetch the docs at that version's URL (e.g., `fastapi.tiangolo.com/release-notes/#01150`).
3. For every fragment that asserts API behavior, quote the relevant doc snippet verbatim in the verification fragment with URL and date-stamp:

```markdown
- [ ] `lifespan` async context manager replaces deprecated `@app.on_event`.
      Verified against fastapi.tiangolo.com/advanced/events/ on 2026-05-04:
      "FastAPI provides a way to handle the events that should happen
      before the application starts up... using the lifespan parameter."
```

4. If the doc has changed since the verification date, the skill is stale and must be re-verified before re-ingest.

## Code-block discipline

Code blocks must be **runnable on the pinned framework version**. No deprecated APIs, no future-cutoff features. R2 applies — every non-stdlib symbol gets one `import`.

Test before authoring: spin up a venv with the pinned version and confirm the example imports + runs (or a smoke-test equivalent).

## Verification-fragment expectations

Verification items are mechanically checkable AND grounded in fetched docs. Pattern:

```markdown
- [ ] `app.middleware=[Middleware(...)]` declares the full stack at construction time
      (vs. `@app.middleware(...)` decorator which adds to front-of-stack and reverses
      execution order). `grep -rn 'middleware\s*=\s*\[' src/` returns the construction-time
      stack. Verified against fastapi.tiangolo.com/tutorial/middleware/ on 2026-05-04.
```

## Refuse-clauses

Refuse to emit a fragment if you cannot ground it. Specifically:

- Refuse if you would assert API behavior without a fetched doc citation
- Refuse if a code block uses an API symbol you cannot verify exists at the pinned version
- Refuse if version-pinning information conflicts between SKILL.md and pack.yaml (operator must reconcile)

When refusing, declare which specific claim could not be grounded and stop. Do NOT fall back to training-data recall.

## Stop conditions

STOP authoring and declare if:

- Fetch fails and there is no offline-cached canonical source
- pack.yaml's pinned version is no longer supported by the framework (skill should pin to a supported version)
- The framework's API changed materially between the SKILL.md authoring date and your fetch date — flag for human review
- A claim depends on a third-party plugin/middleware not in the pinned dependency set

## Worked-example pattern

Framework skills typically include a complete `example` fragment showing the framework wired end-to-end. The example must:

1. Show the full file (imports, setup, handler, lifespan if applicable)
2. Be runnable on the pinned version
3. Reference real, current API symbols only
4. Cite the doc URL the example was patterned after, with date-stamp, in the verification fragment

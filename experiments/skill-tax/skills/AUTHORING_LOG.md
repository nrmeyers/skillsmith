# skill-tax pilot — Authoring Log

## Milestone 2 — task-fixture phase: COMPLETE (2026-05-01)

All six task fixtures authored and locked under the v4 schema. Authoring done on Opus 4.7 throughout. Schema evolved during authoring through three additive bumps (v2 / v3 / v4), each driven by a load-bearing assertion that emerged in fixture review. Lower-version pins preserved where sufficient.

| Task | Path | Schema pin | Skills activated | Arm A fragments | Mechanical checks | Faithfulness items |
|---|---|---|---|---|---|---|
| T1 | `experiments/skill-tax/tasks/T1.yaml` | task-fixture.v2 | `[webhook-patterns]` | 8 | 8 | 5 |
| T2 | `experiments/skill-tax/tasks/T2.yaml` | task-fixture.v2 | `[webhook-patterns]` | 8 | 12 | 7 |
| T3a | `experiments/skill-tax/tasks/T3a.yaml` | task-fixture.v3 | `[webhook-patterns, fastapi-middleware-patterns]` | 16 | 12 | 7 |
| T3b | `experiments/skill-tax/tasks/T3b.yaml` | task-fixture.v4 | `[jwt-validation-patterns, fastapi-middleware-patterns, python-async-patterns]` | 24 | 15 | 8 |
| T4 | `experiments/skill-tax/tasks/T4.yaml` | task-fixture.v2 | `[webhook-patterns]` | 8 | 10 | 5 |
| T5 | `experiments/skill-tax/tasks/T5.yaml` | task-fixture.v2 | `[]` (inverted-pass) | 0 | 9 | 4 |

**Other locked artifacts of milestone 2 task-fixture phase:**

- Governance preamble — `experiments/skill-tax/prompts/governance-preamble-2026-05-01.md`. Pinned `prompt_version: governance-preamble-2026-05-01`. Two-option decline ladder (implement-partial / out-of-scope), unified-diff-only output format. DO NOT EDIT.
- Task fixture schema — `experiments/skill-tax/tasks/_schema.yaml`. Latest `$id: task-fixture.v4`. Supports v2/v3/v4 fixtures via enum. 7 substitution variables locked (`stripe_signature`, `stripe_signature_tampered`, `stripe_signature_stale`, `jwt_hs256_valid`, `jwt_hs256_expired`, `jwt_hs256_bad_sig`, `jwt_hs256_wrong_aud`). Cross-checks introduced in v4 with `body_bytes_match` type.

**Remaining milestone-2 work (NOT done in the task-fixture phase):**

- App skeleton seed branches: `pilot-seed/T1` … `pilot-seed/T5` need to be authored against the contracts each fixture's `app_skeleton.seed_files` and notes commit to. T4's seed has the most specific authoring contract (deliberately-anti-pattern handler with pinned `computed_sig`/`received_sig` variable names, must pass T1's happy-path before commit, must FAIL T4's `equality-comparison-removed` before any model edit).
- `pilot_trials` migration — standalone SQL file at `experiments/skill-tax/migrations/001_pilot_trials.sql` per pilot spec §7.1 DDL. Q8 decision from milestone-2 prep.
- Trial harness — Python implementation per spec §6.3, ~150 lines. Loads fixtures, resolves substitutions against trial-time wall-clock anchor, builds prompts per arm, calls LM Studio at the SUT endpoint, applies model responses to per-trial git worktrees, runs `mechanical_checks` and `cross_checks`, writes `CompositionTrace` (synthetic; per spec §7.1) + `pilot_trials` row via `DuckDBTelemetryWriter`.
- Q9 SUT verification — confirm LM Studio's loaded `qwen3-coder-30b-a3b-instruct` is the Q4_K_S quant per pilot spec §2.4. Non-negotiable per Q9 lock.
- Q10 pre-check — 10-run T1 Arm B consistency + functional check before committing to the full 81-trial run. Decision thresholds locked: ≤2 distinct outputs → proceed; 3-4 → surface; 5+ → switch to Qwen3.5-27B dense fallback. 100% functional pass rate is a separate prerequisite.
- Postgres dockerization — single shared container for pilot duration, fresh schema per trial. Q1 decision.
- 81-trial execution per spec §6.1.

**Switching to Sonnet** for the remaining milestone-2 work per the model-selection plan (locked schemas + locked fixtures driving locked implementations is largely mechanical; Sonnet handles that complexity fine and the cost savings are meaningful). Hand-off package: this AUTHORING_LOG + locked schema + locked governance preamble + 6 task fixtures + standing-findings. New agent reads fresh, confirms understanding, then continues.

---



One entry per skill. Captures: research model, primary sources consulted (with verification dates), QA gate iteration count, final verdict, human reviewer + sign-off date, and notable issues / divergences / decisions. This log is the defense for "gold standard" if the pilot fails and someone asks whether authoring quality was the bottleneck.

Standing findings (apply across the pilot, recorded once here):

- **Canonical webhook-patterns R3 contiguity gap.** During pre-flight (2026-05-01) the dry-run lint of `src/skillsmith/_packs/webhooks/webhook-patterns.yaml` reported 8/8 fragments failing the contiguity rule against the file's `raw_prose` (raw_prose is a short abstract; long fragment bodies aren't sliced from it). The canonical was approved in batch-3 review and is currently treated as gold standard, but it is grandfathered against R3 — it would not pass a strict contiguity check today. Out of scope for this pilot to fix; recorded here so the post-pilot consolidation work can address it. The same condition is suspected on other batch-3 references; an audit pass over `src/skillsmith/_packs/{graphql,observability,websockets,engineering}/*.yaml` is recommended before any "promote new pilot skills to canonical" action.

- **Supersession intent (post-pilot, contingent on methodology validation).** The pilot authors two skills that overlap canonical territory: `webhook-patterns` (this repo, receiver-side only, FastAPI/Python) and `python-async-patterns` (this repo, language tier). Both are intended as clean replacement candidates for their canonical counterparts (`src/skillsmith/_packs/webhooks/webhook-patterns.yaml` and `src/skillsmith/_packs/python/async-python-patterns.yaml`) IF the pilot validates that fragment-typed retrieval methodology survives gold-standard content. Do NOT consolidate during the pilot — canonical files stay untouched. Consolidation is its own milestone after the §8 decision in the pilot spec.

- **Pilot working-store state.** As of 2026-05-01, the LadybugDB and DuckDB stores at `~/.local/share/skillsmith/corpus/` were re-initialized via `python -m skillsmith.migrate` (they had been deleted, not just cleared). Both stores are present and empty. The `pilot_trials` table from spec §7.1 has not been created yet (that is a later milestone). The pilot is file-based at trial time, so re-ingesting the four authored skills into the stores is not required for trial execution.

- **Forward note for milestone 3 (trial.md design — record kept here so the harness work inherits the requirement).** The faithfulness checklist UI in trial.md needs a THREE-state tick model, not a binary yes/no. Some `task_specific_faithfulness_items` are positive-signal items: behavior the fragments teach but which the task's mechanical checks don't exercise (so a faithful model includes it, an incomplete-but-still-passing model omits it, and absence shouldn't penalize the trial). Confirmed across multiple fixtures during milestone-2 task-fixture authoring: T2 item 7 (rollback-on-handler-failure), T3a item 1 (construction-time vs decorator middleware declaration), T3b item 9 (webhook-regression-with-acceptable-refactor), T5 item 4 (decline-shape canonical vs minimal). The harness must render these as `[ yes / no / not-required-but-acceptable ]` so faithfulness review can record them honestly without conflating "faithful and goes beyond" with "faithful baseline." Implementation lives in milestone 3; logged here so the milestone-2 harness wiring leaves room for the third state without late refactoring.

- **Milestone 3 aggregate-metrics exclusion (T5).** T5's per-arm pass rates will be mathematically identical (modulo sampling variance at temp 0.0) because all four arms receive empty fragment lists — `skills_activated: []` per spec §5.1 invariant for the inverted-pass test. T5 contributes to the overall headline pass rate and to scope-recognition findings; it does NOT contribute arm-comparison signal to C1 / C2 sub-claim evidence in pilot spec §8.1. Milestone-3 aggregate metrics MUST apply a T5-exclusion filter when computing per-arm pass-rate gaps for C1 / C2 analysis. Documented in T5's notes section; surfaced here so the harness aggregator path inherits the requirement.

- **QA gate critic backend (decided 2026-05-01).** Locked for all 4 pilot skills: local LM Studio, dense `qwen3.6-27b` Q8_K_XL as critic. Architecture diversity from the MoE SUT (`qwen3-coder-30b-a3b-instruct`); rubric-driven critic prompt at `fixtures/skill-qa-agent.md` (`prompt_version 2026-04-30.1`) used unmodified — adversarial overlay rejected because Stage 3's structured rubric is exactly what's wanted from a critic. No cloud API calls anywhere in the authoring phase: pilot YAMLs are drafted by Claude Code (Opus, this conversation), QA gate runs against the local critic, and trials run against the local SUT.

  **Env vars** (set per `qa` invocation; trials must restore `LM_STUDIO_BASE_URL` to the SUT-loaded endpoint):

  - `LM_STUDIO_BASE_URL=http://localhost:1234`
  - `AUTHORING_EMBED_BASE_URL=http://localhost:1234`
  - `CRITIC_MODEL=qwen3.6-27b`
  - `AUTHORING_EMBEDDING_MODEL=text-embedding-qwen3-embedding-0.6b`
  - `AUTHORING_MODEL=PLACEHOLDER_NOT_CONFIGURED_pilot_uses_claude_code_drafting` — `require_authoring_config()` enforces non-empty for `qa` to run, but the `qa` subcommand does not invoke `authoring_model` (only `author` / `revise` / `run` / `run-batched` do, and the pilot uses none of them). The placeholder is intentional: if anyone later runs `python -m skillsmith.authoring author` against this env, the failure surfaces "PLACEHOLDER_NOT_CONFIGURED" in the error rather than producing a confusing "model not found" downstream.

  **Operational pattern** (LM Studio model swap, sequential):
  - **Authoring/QA phase:** load `qwen3.6-27b` (Q8_K_XL) + `text-embedding-qwen3-embedding-0.6b`. Unload the SUT and the other 35B MoE if loaded. Run `python -m skillsmith.authoring qa`.
  - **Trial phase:** unload `qwen3.6-27b`, load `qwen3-coder-30b-a3b-instruct` per spec §2.4. Run trial harness.

  **Critic settings to verify before each `qa` run:** context window 16K (skill YAML + critic prompt + structured output stays well under 16K); KV cache F16 if VRAM allows, else Q8; verify UMA headroom (Q8_K_XL ≈ 28GB on disk, plus 16K F16 KV cache and overhead — should fit in 48GB UMA but is tight; multiple concurrently-loaded models will not).

  ### QA gate run history

  | Run | Date | Wall time | Outcome | Notes |
  |---|---|---|---|---|
  | 1 | 2026-05-01 01:29–01:44 | 15m (timeout) | `needs-human` (`critic output unparseable: timed out`) | Q8_K_XL critic + 5 models loaded simultaneously. Embedding call OK; critic chat call hit the 900s `read_timeout`. No partial response captured. |
  | 2 | 2026-05-01 02:55–03:10 | ~15m | **`approve` (first pass, 0 bounces)** | Q4_K_M critic. After two patches: `lm_client.DEFAULT_TIMEOUT` read raised from 900s→1800s; `qa_gate.run_critic` `max_tokens` lowered from 16384 (lm_client default) to explicit 4096. Critic summary: "Draft meets all quality criteria; fragments are correctly typed, self-contained, faithful to source, and tags are highly relevant." Per-fragment notes empty (no flags). |

  **Direct-throughput diagnostics on Q4_K_M (2026-05-01, critic-shaped 13K-token input + 1024-token output cap):**
  - Stock prompt: 251.6s wall, **4.07 tok/s sustained**, 1024/1024 budget on `reasoning_content`, 0 chars `content`, `finish_reason=length`.
  - With `/no_think` system-prompt prefix: 254.2s wall, **4.03 tok/s sustained**, identical reasoning behavior (1023 reasoning tokens, 0 content). **`/no_think` directive is not honored at this quant.**

  Run 2 succeeded because the 4096-token cap let the model finish reasoning + emit JSON within 15 minutes (~3700 reasoning + ~400 JSON output tokens at ~4 tok/s ≈ 1000s wall, comfortably under the new 1800s timeout).

  **Critic-speed diagnostic (run 1 follow-up, direct chat call to LM Studio):** `qwen3.6-27b` produced ~1.8 tokens/sec sustained on a 50-token and 200-token test. Even with `/no_think` system directive, the model emitted ~160 reasoning tokens before any visible content. At that throughput, a typical QA call (≈ 6K input tokens + 500 reasoning + 800 JSON output = 1300 completion tokens) takes ~12 minutes wall time — uncomfortably close to the 15-minute `read_timeout` and likely to exceed it on more complex skills or revise iterations.

  **Suspected cause:** multiple models loaded simultaneously in LM Studio (the embedder + SUT + 27B critic + 35B-A3B = >65GB on a 48GB UMA), causing partial CPU offload / eviction thrashing. The "sequential, not concurrent" operational pattern was decided but not yet enforced — the SUT and the 35B-A3B remained loaded during run 1.

  **Path forward (operator decision — open as of 2026-05-01):**

  1. **Enforce the sequential pattern.** Unload SUT + 35B-A3B in LM Studio; keep only `qwen3.6-27b` + the embedder. Re-measure throughput; expect 5–10× speedup if memory pressure was the bottleneck. If throughput reaches ≥10 tok/s, re-run qa_gate.
  2. **Lower critic precision to Q4 / Q5 of `qwen3.6-27b`** if not already loaded, OR a smaller dense critic. Q4 of a 27B fits in ~16GB and runs much faster on bandwidth-bound hardware.
  3. **Accept slow critic; raise the read_timeout** in `lm_client.DEFAULT_TIMEOUT` from 900s to e.g. 1800s. ~30 min per skill × 4 skills × likely 1–2 revise iterations each = 2–4 hours of wall-clock authoring. Tractable but slow.
  4. **Swap critic to `qwen/qwen3.6-35b-a3b`** (MoE, ~40 tok/s). Trades architectural-diversity-from-SUT for usable throughput. The locked-critic decision was made on a quality basis assuming Qwen3.6-27B would run; if it does not run at usable speed, the choice is forced.
  5. **Open the cloud-critic conversation again** — Anthropic API + LiteLLM, as previously discussed. Was rejected on cloud-dep / API key grounds; if local options 1–4 don't pan out, this becomes the fallback.

  Recommendation: try (1) first (free, no decision reversal); if not enough speedup, (2) or (4) depending on what's available locally.

---

## Milestone 2 — implementation phase: harness fix (2026-05-01)

### Harness fix 7 — markdown-fence normalization and absolute-path rewriting

**Trigger:** Q10 pre-check (10 runs T1 Arm B, temp 0.0) returned `parses=False functional_pass=False` on all 10 runs. Investigation showed `git apply -3` receiving the raw model response, which (a) wrapped the diff in a ` ```diff ``` ` markdown code fence and (b) used absolute worktree paths (`--- a/tmp/pilot-wt-.../wt/app/main.py`) instead of repo-relative paths (`--- a/app/main.py`). The model code itself was structurally correct.

**Root cause (two issues):**
1. The harness passed `response_text` directly to `git apply` without stripping markdown code fences. LLMs trained on markdown-heavy corpora reflexively wrap code output in fences; the governance preamble's "Return the changes as a unified-diff patch, nothing else" was not explicit enough to suppress this behavior in Qwen3-Coder-30B-A3B at temp 0.0.
2. The user message substitution (`fixture["description"].replace("/workspace", str(wt))`) caused the model to embed the absolute worktree path in its diff headers. `git apply` strips the `a/`/`b/` prefix and then looks up the path relative to `cwd=wt`, so an absolute-path diff always fails.

**Decision — fence-wrapping is NOT a faithfulness failure:**
Option (a): treat fence-wrapping as a faithfulness failure, update + re-lock the governance preamble, re-run QA verification. Option (b): treat fence-wrapping as a training artifact of the output format, normalize in the harness, log all fence presence in `pilot_trials.notes` for M3 audit.

**Chose (b).** Rationale: the preamble's "no commentary" clause explicitly lists "no explanation of choices, no follow-up suggestions" — its scope is explanatory prose, not formatting wrappers. A code fence carries no explanatory content. Re-locking the preamble at this stage would invalidate prior QA verification for zero scientific benefit. The harness logs all fence presence and any preamble/postamble text (content outside the fence) in the `notes` column so M3 review can distinguish fence-only normalization from actual governance preamble violations.

**Fix applied in `experiments/skill-tax/harness/run_trial.py`:**
- Added `_normalize_diff_response(response, wt) → (str, list[str])`: strips markdown fences (any language tag, optional whitespace), rewrites absolute worktree paths to repo-relative, logs all normalization events as warnings.
- Updated `_write_pilot_trial` to accept `notes: str | None` and store it in `pilot_trials.notes`.
- Fence normalization: matches `^\s*```\w*\s*\n` open and `\n\s*```\s*$` close; captures content before/after fence as `preamble_violation`/`postamble_violation` warnings; records `fence_stripped` for every normalized response.
- Path normalization: replaces `a/{wt}/`, `b/{wt}/`, ` {wt}/` (for bare `--- /abs/path` lines), and bare `{wt}/` in that order, leaving only repo-relative paths.
- `consistency_hash` is still computed on the **raw** `response_text` before normalization (preserves hash semantics — the hash is over what the model actually produced, not the normalized form).

**Harness fix 8 — hunk-header recomputation.** After fence stripping and path normalization, Q10 re-run #2 still showed `parses=False`. Diagnosis: the model consistently generated wrong line counts in `@@ -N,old +N,new @@` headers (stated new=10–13, actual new=19–20). `git apply` rejects diffs with wrong hunk counts. Fix: added `_fix_hunk_headers()` which rescans each hunk body and rewrites the header with correct counts. Applied before `git apply`.

**Harness fix 9 — trailing-newline preservation.** After fence stripping, the `inner` content lacked a trailing `\n` (the fence close regex captured up to but not including the `\n` before ` ``` `). `git apply` reported "corrupt patch at line N" on the last line. Fix: added `if not text.endswith('\n'): text += '\n'` after `_fix_hunk_headers`.

**Harness fix 10 — switch to `patch --fuzz=3`.** After fixes 8 and 9, `git apply` still failed: "patch does not apply" at app/main.py:1. Diagnosis: the seed file (`pilot-seed/T1:app/main.py`) has 3 lines (`from fastapi import FastAPI` + blank + `app = FastAPI()`), but the task description describes it as 2 lines, so the model's generated context omits the blank line. `git apply` is strict about context matching. Switch to `patch -p1 --fuzz=3 --no-backup-if-mismatch` which handles 1-line context offsets; verified "Hunk #1 succeeded at 2 with fuzz 1 (offset 1 line)". Also: `patch` stdout+stderr both captured for failure logging.

**Harness fix 11 — `stripe` not installed in harness venv.** After fixing patch application, `parses=True` but `functional_pass=False` because uvicorn couldn't import `stripe` (`ModuleNotFoundError: No module named 'stripe'`). The seed branch's `pyproject.toml` declares `stripe>=8.0.0` but the main project venv (used by `sys.executable` in `app_process`) didn't include it. Fix: `uv pip install "stripe>=8.0.0"` into the project venv. After this fix, smoke test returned `parses=True functional_pass=True`.

**Effect on prior Q10 runs:** All prior runs (parses=False) are invalidated. Re-run Q10 with the fully fixed harness.

---

## Skill 1 — webhook-patterns (receiver-side, FastAPI/Python)

| Field | Value |
|---|---|
| Pack tier | protocol |
| `skill_id` | `webhook-patterns` |
| Canonical name | Webhook Receiver Patterns (HMAC, Replay, FastAPI) |
| Status | **APPROVED on first critic pass (run 2, 2026-05-01 03:10). Final at `experiments/skill-tax/skills/webhook-patterns.yaml`. 0 revise iterations.** |
| Authoring model | Claude Opus 4.7 (1M context) — this conversation, 2026-05-01 |
| Scratch dir | `~/work/skill-authoring-runs/webhook-patterns/` |
| Draft path | `~/work/skill-authoring-runs/webhook-patterns/draft-2.yaml` |
| Fragments | 8 (rationale, setup, 3× execution, example, verification, guardrail) |
| Word counts | r 145 / s 194 / e 194 / e 188 / e 233 / ex 289 / v 351 / g 382 — all in 80–800 range |
| Tag count | 8 (at protocol soft-ceiling) |
| Tags | `stripe`, `github`, `slack`, `signature-verification`, `idempotency`, `raw-body`, `event-id`, `compare-digest` |

### Primary sources consulted (all verified 2026-05-01)

- Stripe webhook signatures: https://docs.stripe.com/webhooks/signatures
- Stripe resolve verification errors: https://docs.stripe.com/webhooks/signature
- GitHub validating webhook deliveries: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- Slack verifying requests: https://api.slack.com/authentication/verifying-requests-from-slack
- Standard Webhooks v1.0: https://www.standardwebhooks.com/ + spec at github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
- Python `hmac` module (3.14 docs covering 3.7+ behavior): https://docs.python.org/3/library/hmac.html
- FastAPI Custom Request and APIRoute class: https://fastapi.tiangolo.com/how-to/custom-request-and-route/

The canonical `src/skillsmith/_packs/webhooks/webhook-patterns.yaml` was used as a coverage map only — to verify topical scope (HMAC verify, replay protection, idempotency, status code semantics) was complete — not as a content source. Every code example, header format, tolerance value, and procedural claim in the draft traces to one of the primary sources above. Per-vendor signature scheme details (Stripe `<ts>.<body>`, GitHub raw body + `sha256=` prefix, Slack `v0:<ts>:<body>`, Standard Webhooks `<id>.<ts>.<body>` base64) come from the respective vendor docs.

### Pre-QA dry-runs

Local `_validate` + `_lint` results:

- **draft-1.yaml (2026-05-01):** 0 validation errors, 0 lint warnings.
- **draft-2.yaml (2026-05-01):** 0 validation errors, 0 lint warnings. Includes operator review fixes (a) asyncpg pin in example imports + `db`/`process_event` named, (b) `process_event` defined as a stub in the example, (c) unused `time` import dropped from setup, (d) `constant_time_equal` wrapper removed in execution-3 with `hmac.compare_digest` referenced directly + bytes/str type-match note added, (e) verification fragment's per-provider line split into 4 separate bullets (Stripe, GitHub, Slack, Standard Webhooks). `change_summary` trimmed to one paragraph + pointer to this log.

Both drafts pass: zero contiguity warnings (every fragment is a verbatim slice of `raw_prose` modulo whitespace), zero R2 tag-title overlaps, zero R3-stem pairwise tag synonyms, zero code-fence-heavy execution warnings.

### Decisions and divergences

- **Receiver-side only.** Sender-side concerns (retry, jitter, DLQ) intentionally excluded. Confirmed with operator 2026-05-01. A separate `webhook-delivery-patterns` skill would be the home for sender-side content if ever needed.
- **Python/FastAPI flavored.** Pilot tasks T1–T4 are FastAPI/Python (spec §3.1, §4). A protocol-tier skill could in principle stay language-agnostic, but for the pilot's purposes the receiver code must compose cleanly with `fastapi-middleware-patterns` and `python-async-patterns`. A future cross-language webhook skill (`webhook-receiver-patterns-node`, etc.) is feasible but not in scope.
- **Tag set chose `compare-digest` over `standard-webhooks`.** `standard-webhooks` would have stem-overlapped the title's `webhook` (R2 violation). `compare-digest` adds a queryable Python primitive that surfaces the constant-time-comparison content for queries like "constant time string compare python" without overlapping any other tag.
- **Fork at `experiments/skill-tax/skills/` only after QA approve.** Per handoff §4, only `final-approved.yaml` lands in the pilot's skills directory; iteration drafts stay in scratch.

### QA iterations

| # | Date | Verdict | Blocking issues | Notes |
|---|---|---|---|---|
| 1 | 2026-05-01 03:10 | **approve** | none | Run 2 of the qa_gate (run 1 was a 15-min timeout on the Q8 critic). Critic summary: "Draft meets all quality criteria; fragments are correctly typed, self-contained, faithful to source, and tags are highly relevant." Per-fragment notes empty. 0 bounces. Final-approved YAML copied to `experiments/skill-tax/skills/webhook-patterns.yaml`. |

### Reviewer sign-off

- Human reviewer: Nate Meyers (operator) — pending sight-review of `experiments/skill-tax/skills/webhook-patterns.yaml` against pilot acceptance criteria
- Sign-off date: pending

---

## Skill 2 — jwt-validation-patterns (PyJWT receiver-side)

| Field | Value |
|---|---|
| Pack tier | protocol |
| `skill_id` | `jwt-validation-patterns` |
| Canonical name | JWT Validation Patterns (HS256, RS256, Claim Verification) |
| Status | **APPROVED on first critic pass (2026-05-01 ~03:30). Final at `experiments/skill-tax/skills/jwt-validation-patterns.yaml`. 0 revise iterations.** |
| Authoring model | Claude Opus 4.7 (1M context) — this conversation, 2026-05-01 |
| Scratch dir | `~/work/skill-authoring-runs/jwt-validation-patterns/` |
| Fragments | 8 (rationale, setup, 3× execution, example, verification, guardrail) |
| Word counts | r 196 / s 180 / e 163 / e 184 / e 218 / ex 239 / v 291 / g 435 — all in 80–800 range |
| Tag count | 8 |
| Tags | `pyjwt`, `rfc-8725`, `algorithm-confusion`, `key-rotation`, `jwks`, `expiration`, `audience`, `issuer` |

### Primary sources consulted (all verified 2026-05-01)

- PyJWT 2.12.1 usage docs: https://pyjwt.readthedocs.io/en/stable/usage.html
- RFC 7519 (JSON Web Token): https://datatracker.ietf.org/doc/html/rfc7519
- RFC 8725 (JWT Best Current Practices): https://datatracker.ietf.org/doc/html/rfc8725
- OWASP JWT Cheat Sheet (concept reference; Java-flavored but principles transfer): https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html

### Decisions and divergences

- Receiver-side only — issuance (key generation, signing, claim selection) is excluded; the skill points to identity-provider documentation for that.
- PyJWT 2.x as the reference implementation. Code shapes use PyJWT's idioms (algorithms list required, options.require for missing-claim enforcement, PyJWKClient for JWKS).
- Tag set: `rfc-8725` chosen over `rfc-7519` because BCP guidance is more directly actionable for a receiver-side skill, and the two would have stem-collided on `rfc`. `algorithm-confusion` over `algorithm-list` because the attack name is more queryable.

### QA iterations

| # | Date | Verdict | Blocking issues | Notes |
|---|---|---|---|---|
| 1 | 2026-05-01 ~03:30 | **approve** | none | Critic summary: "Draft accurately structures the source prose into self-contained, correctly typed fragments with strong tags and no dedup conflicts; ready for ingestion." Per-fragment notes empty. 0 bounces. |

### Reviewer sign-off

- Human reviewer: Nate Meyers
- Sign-off date: 2026-05-01
- Reviewer note: Lightweight review pass (voice, scope, change_summary honesty, citation sanity) via Claude. All four pass; python-async fragment 4 cross-reference edit applied per critic suggestion.

---

## Milestone summary (2026-05-01)

All 4 pilot skills authored, QA-gate-approved, and final-approved YAMLs landed at `experiments/skill-tax/skills/`. 0 revise iterations across the milestone (one transport retry on `python-async-patterns` for an unrelated max_tokens budget overflow).

**Post-sign-off (2026-05-01):** Operator sign-off pass approved all four. The critic's non-blocking suggestion on `python-async-patterns` fragment 4 ("see example below" → "See the bounded fan-out example for the complete implementation.") was applied to the final-approved YAML as a quality improvement, not a blocker. Edit re-passes `_validate` + `_lint` cleanly (0 errors, 0 warnings). qa_gate not re-run — the original critic pass approved the structural integrity, and the edit is a self-contained string substitution within an already-approved fragment.

| Skill | Tier | QA verdict | QA iterations | Final path |
|---|---|---|---|---|
| webhook-patterns | protocol | approve | 1 (run 2 of qa_gate; run 1 timeout was a critic-config issue, not a skill issue) | `experiments/skill-tax/skills/webhook-patterns.yaml` |
| jwt-validation-patterns | protocol | approve | 1 | `experiments/skill-tax/skills/jwt-validation-patterns.yaml` |
| fastapi-middleware-patterns | framework | approve | 1 | `experiments/skill-tax/skills/fastapi-middleware-patterns.yaml` |
| python-async-patterns | language | approve | 1 (run 2; run 1 was a JSON-truncation transport failure at the 4096-token critic budget — verdict was already "approve" but JSON didn't terminate; budget bumped to 8192 and re-run) | `experiments/skill-tax/skills/python-async-patterns.yaml` |

### Patches required for qa_gate to run on this hardware (recorded for post-pilot revert)

- `src/skillsmith/authoring/lm_client.py:14` — `httpx.Timeout(read=)` raised from 900s → 1800s. Required because Qwen3.6-27B Q4_K_M sustains ~4 tok/s on this hardware and even a 4096-token critic call approaches the original 900s limit.
- `src/skillsmith/authoring/qa_gate.py:run_critic` chat call — explicit `max_tokens=8192` (was implicitly the lm_client default 16384). Bounds wall time per call (~17 min worst case) while accommodating the verbose JSON the critic emits when it has multi-fragment notes.

**TODO (post-pilot, do NOT revert during trials):** Both patches stay in place through the trial phase to preserve operator parity with the authoring environment if any revise iterations or follow-on skill authoring becomes necessary mid-trial. Revisit after the pilot's §8 decision: revert both if Anthropic/cloud critic infrastructure replaces local LM Studio for steady-state operation, or upstream them if local-critic operation continues. Touchpoints: `lm_client.DEFAULT_TIMEOUT`, `qa_gate.run_critic` `max_tokens=8192` argument.

### Pilot critic-call wall-time observations

- webhook-patterns: ~15 min (run 2; run 1 was a 15-min timeout under the original 900s + Q8 critic config)
- jwt-validation-patterns: ~15 min
- fastapi-middleware-patterns: ~15 min
- python-async-patterns: run 1 ~15 min then JSON-truncated; run 2 ~25 min at 8192 budget

Aggregate authoring wall time across the 4 skills: ~80 min of qa_gate critic calls + drafting time. The throughput floor on this hardware is the limiting factor; the structured rubric itself approved every skill on first critic pass with no per-fragment blocking issues.

### Cross-skill flags worth recording for post-pilot follow-up

- The `python-async-patterns` critic note ("References 'example below' in fragment 4 — could be tightened for standalone retrieval") is a real but non-blocking R3.1 (self-contained fragments) observation. Suggested edit captured in the `.qa.md` report. A post-pilot revision pass could apply this; the pilot ships the approved-as-is form for trial-time fidelity.
- All 4 skills follow the same 8-fragment shape (rationale, setup, 3× execution, example, verification, guardrail). This was incidental, not a constraint — but it gives the pilot's harness consistent fragment-type ratios to filter against per Arm A/B/C definition.
- Pre-existing canonical webhook-patterns R3 contiguity gap (8/8 fragments fail contiguity vs raw_prose) noted at the top of this log — not a pilot scope item, but a real corpus issue to address post-pilot.

### Operator hand-off

- Final-approved YAMLs are in `experiments/skill-tax/skills/`. Iteration drafts remain in `~/work/skill-authoring-runs/<skill>/draft-*.yaml` for audit.
- `AUTHORING_LOG.md` (this file) defends "gold standard" if the pilot fails and someone asks whether authoring quality was the bottleneck.
- Sign-off pending — `Reviewer sign-off` rows in each skill section need operator review before trial work begins.
- Next pilot milestone (per `experiments/skill-tax/handoff.md` §"What's next"): task specification (T1, T2, T3a, T3b, T4, T5), FastAPI app skeleton fixtures, trial harness with arm-construction, `pilot_trials` schema migration, token-budget measurement, then trial execution.

---

## Skill 3 — fastapi-middleware-patterns

| Field | Value |
|---|---|
| Pack tier | framework |
| `skill_id` | `fastapi-middleware-patterns` |
| Canonical name | FastAPI Middleware and Dependency Patterns |
| Status | **APPROVED on first critic pass (2026-05-01 ~03:46). Final at `experiments/skill-tax/skills/fastapi-middleware-patterns.yaml`. 0 revise iterations.** |
| Authoring model | Claude Opus 4.7 (1M context) — this conversation, 2026-05-01 |
| Scratch dir | `~/work/skill-authoring-runs/fastapi-middleware-patterns/` |
| Fragments | 8 (rationale, setup, 3× execution, example, verification, guardrail) |
| Word counts | r 172 / s 156 / e 195 / e 179 / e 227 / ex 283 / v 327 / g 455 — all in 80–800 range |
| Tag count | 8 |
| Tags | `starlette`, `asgi`, `cors`, `trusted-host`, `exception-handler`, `depends`, `lifespan`, `raw-body` |

### Primary sources consulted (all verified 2026-05-01)

- FastAPI Middleware tutorial: https://fastapi.tiangolo.com/tutorial/middleware/
- FastAPI Advanced Middleware: https://fastapi.tiangolo.com/advanced/middleware/
- FastAPI Dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/
- Starlette Middleware reference: https://www.starlette.io/middleware/

### Decisions and divergences

- Covers BOTH ASGI middleware (`@app.middleware("http")` and `Middleware()` class form) AND dependency injection (`Depends()`) — the two complementary request-wrapping mechanisms. Single skill rather than splitting because they only make sense together (the rule "auth in dependencies, cross-cutting in middleware" is the load-bearing decision).
- FastAPI 0.115+ targeted; `lifespan` context manager replaces deprecated `on_event` hooks per FastAPI docs.
- Cross-references `webhook-patterns` for the `APIRoute.get_route_handler` raw-body pattern; this is intentional pilot-friendly composition surface for T3a (webhook + fastapi-middleware) per spec §4.2.

### QA iterations

| # | Date | Verdict | Blocking issues | Notes |
|---|---|---|---|---|
| 1 | 2026-05-01 ~03:46 | **approve** | none | Critic summary: "Draft faithfully preserves source prose, correctly maps fragment types to content, uses precise and queryable tags, and presents no dedup or structural conflicts." Per-fragment notes empty. 0 bounces. |

### Reviewer sign-off

- Human reviewer: Nate Meyers
- Sign-off date: 2026-05-01
- Reviewer note: Lightweight review pass (voice, scope, change_summary honesty, citation sanity) via Claude. All four pass; python-async fragment 4 cross-reference edit applied per critic suggestion.

---

## Skill 4 — python-async-patterns

| Field | Value |
|---|---|
| Pack tier | language |
| `skill_id` | `python-async-patterns` |
| Canonical name | Python Async Patterns (asyncio, TaskGroup, Cancellation) |
| Status | **APPROVED on first critic pass (qa run 2 — run 1 was a JSON-truncation transport failure, not a content failure; verdict was already "approve" before budget overflow). Final at `experiments/skill-tax/skills/python-async-patterns.yaml`. 0 revise iterations.** |
| Authoring model | Claude Opus 4.7 (1M context) — this conversation, 2026-05-01 |
| Scratch dir | `~/work/skill-authoring-runs/python-async-patterns/` |
| Fragments | 8 (rationale, setup, 3× execution, example, verification, guardrail) |
| Word counts | r 194 / s 210 / e 242 / e ~210 / e 192 / ex 263 / v 315 / g 496 — all in 80–800 range |
| Tag count | 8 |
| Tags | `create-task`, `gather`, `timeout`, `shield`, `exception-group`, `event-loop`, `structured-concurrency`, `run-in-executor` |

### Primary sources consulted (all verified 2026-05-01)

- Python `asyncio.run` runner: https://docs.python.org/3/library/asyncio-runner.html
- Python `asyncio` coroutines and tasks (TaskGroup, create_task, gather): https://docs.python.org/3/library/asyncio-task.html
- Python `asyncio` event loop reference (run_in_executor, get_running_loop): https://docs.python.org/3/library/asyncio-eventloop.html
- PEP 654 (Exception Groups and `except*`): https://peps.python.org/pep-0654/

### Decisions and divergences

- **Supersession candidate.** This skill is intended as a clean replacement candidate for the canonical `src/skillsmith/_packs/python/async-python-patterns.yaml` post-pilot if the methodology validates. Canonical untouched in the meantime; consolidation is its own milestone.
- **Python 3.11+ targeted** for `TaskGroup`, `asyncio.timeout`, `ExceptionGroup`/`except*`. Pre-3.11 compatibility note included in setup fragment but the canonical patterns are the modern surface. Operator codebases on 3.10 or earlier would need a different shape (raw `gather` + manual exception aggregation).
- **Code-fence-heavy lint warning on draft-1 fragment 4** (cancellation/timeouts/shield) — fixed by removing one of the two code blocks (the redundant `fetch_with_deadline` example, which exists in fragment 6) and converting to inline prose. Final draft has no lint warnings.

### QA iterations

| # | Date | Verdict | Blocking issues | Notes |
|---|---|---|---|---|
| 1 | 2026-05-01 ~04:00 | **needs-human (transport)** | JSON truncation at line 9 col 30 | Critic content was approving — verbose `per_fragment` notes overflowed the 4096-token max_tokens cap mid-string. Bumped `max_tokens` to 8192 in `qa_gate.run_critic` and re-ran. |
| 2 | 2026-05-01 ~07:40 | **approve** | none | Critic summary: "Draft accurately reflects source prose, fragment types align with content categories, and tags are relevant; minor cross-reference phrasing could be tightened for standalone retrieval." Per-fragment note on seq 4 ("References 'example below' which may be confusing if surfaced standalone; consider rephrasing") — non-blocking, suggested edit captured in the .qa.md report. 0 bounces. |

### Reviewer sign-off

- Human reviewer: Nate Meyers
- Sign-off date: 2026-05-01
- Reviewer note: Lightweight review pass (voice, scope, change_summary honesty, citation sanity) via Claude. All four pass; python-async fragment 4 cross-reference edit applied per critic suggestion.

### Reviewer sign-off

- Human reviewer: TBD
- Sign-off date: TBD

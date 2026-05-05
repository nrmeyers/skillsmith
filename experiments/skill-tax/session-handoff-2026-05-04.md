# Session Handoff — 2026-05-04

## What this session accomplished

Redesigned the R1 (authoritative source fetch) step of the skill authoring
pipeline, replacing ad-hoc web research with a tiered sourcing strategy backed
by llms.txt/llms-full.txt and curated URL lists. Both commits are pushed to
main.

---

## Corpus state — clean slate confirmed

- **Active stores** (`~/.local/share/skillsmith/corpus/`): 0 fragments, schema
  tables present and current. This is the intended POC starting state.
- **Pre-POC corpus** (153 skills, 1658 fragments) archived to
  `~/.local/share/skillsmith/archive/pre-poc-2026-04-27/`. Does not meet POC
  quality bar — only 35/153 had all 6 fragment types, R3 verification severely
  underrepresented. Do not use.
- **POC eval store** (`experiments/skill-tax/skills.duck`): 561 composition
  traces, 561 pilot trials, 0 fragment embeddings. Eval-only — not a corpus.

---

## What was built

### fixtures/upstream/registry.yaml
57-vendor tier map probed 2026-05-04. Three tiers:
- **Tier-1** (21 vendors): both llms.txt + llms-full.txt available. Best case —
  index + full source. Includes: Anthropic, LaunchDarkly, Linear, Vercel,
  Supabase, Cloudflare, Hono, Drizzle, Prisma, Slack API, Expo, Vue, Fastify,
  NestJS, Temporal, dbt, Sentry (use sentry.io root, NOT docs.sentry.io),
  Docker, Turborepo, Vite, Vitest, Pydantic, Django, SQLAlchemy, Kotlin.
- **Tier-2** (11 vendors): llms.txt index only. Fetch the pages it lists.
  Includes: Stripe, GrowthBook, Resend, Svix, GitHub, Next.js, TanStack,
  MongoDB, Redis, React, PyTorch.
- **Tier-3** (35+ vendors): neither. Use curated URL list or fallback_root.
  All language stdlibs (Python, Java, Go, Rust, Node, TypeScript, C#, Ruby,
  PHP, Swift, Elixir, etc.) are systematically tier-3 — standards orgs haven't
  adopted llms.txt.

**Key gotcha:** Oracle `docs.oracle.com/javase` returns HTTP 200 but is an HTML
soft-404. Java SE is tier-3; use `fallback_root` in the registry.

### fixtures/upstream/curated/
Per-language canonical URL lists for 10 tier-3 languages. All verified with
HEAD checks (349/352 URLs survived, 99.1%).

| Language | Version anchor | URLs | Notes |
|---|---|---|---|
| Python | 3.13 | 48 | All survived |
| Java | 21 LTS | 34 | All survived |
| Go | 1.23 | 48 | 1 killed (fuzz blog moved) |
| TypeScript | 5.7 | 27 | 1 killed (archived spec); no formal spec URL |
| Node.js | 22 LTS | 36 | All survived |
| Rust | stable 1.83+ | 39 | 1 killed (generics reference path wrong) |
| C# | .NET 9 / C# 13 | 35 | All survived |
| Ruby | 3.4 | 22 | 4 killed — docs.ruby-lang.org/en/master/ class pages don't resolve. Supplement with ruby-doc.org |
| PHP | 8.4 | 35 | All survived |
| Swift | 6.0 | 28 | 1 killed (release notes blog post) |

Supporting files:
- `_prompt-template.md` — prompt for adding more languages. Includes
  verification script. Re-run with a new language entry in `_targets.yaml`.
- `_targets.yaml` — 16-language target list. Priority 3 languages (Elixir,
  Scala, Clojure, Haskell, OCaml, Zig) deferred — user unfamiliar with them.
- `curated_url_summary.md` — Sonnet's verification summary table.

### fixtures/skill-authoring-guidelines.md — R1 updated
R1 rule now has an explicit "Tiered Sourcing" subsection. Authoring agents
must check `registry.yaml` before any web research. Tier-1 → slice
llms-full.txt. Tier-2 → fetch pages from llms.txt index. Tier-3 → use
curated yaml. If vendor not in registry, add it first.

---

## Pre-flight checks status (from handoff.md)

1. ✅ Schema state — tables present and current in both stores.
2. ✅ Pack registry — file-based (`src/skillsmith/_packs/*/pack.yaml`), fully
   intact. No database dependency. Tiers: language, framework, protocol,
   platform, domain.
3. ⬜ Webhook-patterns skill — still needs guardrail fragment augmentation
   (first milestone task #1).
4. ✅ Embeddings / retrieval indexes — `fragment_embeddings` empty, expected.
   Pilot uses manual fragment selection (spec §5).
5. ⬜ Re-ingestion strategy — spec assumes file-based (option a). Not yet
   confirmed for this session; verify before authoring.

---

## What's next — first milestone tasks (do in order)

### 1. Augment webhook-patterns.yaml with a guardrail fragment
File: `src/skillsmith/_packs/webhooks/webhook-patterns.yaml`
Has 8 fragments, no guardrail. Candidate content exists inline in execution
fragments ("never use `===` for HMAC comparison"). Promote to a dedicated
guardrail fragment. Fork to `experiments/skill-tax/skills/` as a pilot-local
copy (don't touch the canonical pack file unless there's a strong reason).

R1 sources for webhook-patterns:
- Registry: `stripe` (tier-2), `svix` (tier-2), `cloudflare` (tier-1)
- Stripe: `https://docs.stripe.com/llms.txt` → fetch signing/webhook pages
- Svix: `https://docs.svix.com/llms.txt` → fetch signing/replay pages
- Cloudflare: `https://developers.cloudflare.com/llms-full.txt` → slice Workers/Queues/Webhooks section

### 2. Author jwt-validation-patterns (protocol tier)
R1 sources: RFC 7519 (IETF), OWASP JWT Cheat Sheet, PyJWT docs. All tier-3
(no llms.txt). Use web fetch. curated/python.yaml has relevant typing/security
URLs but JWT is protocol-level — use RFC + OWASP directly.

### 3. Author fastapi-middleware-patterns (framework tier)
R1 sources: FastAPI is tier-3 (`fallback_root: https://fastapi.tiangolo.com/`).
Pydantic is tier-1 (`https://docs.pydantic.dev/llms-full.txt`). Fetch FastAPI
middleware docs directly; use Pydantic llms-full.txt for request validation patterns.

### 4. Author python-async-patterns (language tier)
R1 sources: tier-3. Use `fixtures/upstream/curated/python.yaml`
`topics.concurrency_and_async` URLs — asyncio docs + PEPs 492/530/3156.

Quality bar for all four skills (non-negotiable for POC):
- All 6 fragment types: rationale, setup, execution, verification, example, guardrail
- Explicit guardrail fragment (pilot Arm B vs C comparison depends on it)
- QA gate verdict: `approve`
- Primary source citations per R1
- Date-stamped per R5

---

## Key decisions made this session

- **Pre-POC 153-skill corpus is archived, not patched.** Starting fresh —
  user's call, correct given the quality gap.
- **Kotlin curated list skipped** — already tier-1 in registry, redundant.
- **Priority 3 languages skipped** (Elixir/Scala/Clojure/Haskell/OCaml/Zig) —
  user unfamiliar, deferred indefinitely.
- **Authoring model recommendation:** Qwen2.5 72B Instruct Q8 (local) or
  Sonnet 4.6 no-extended-thinking temperature 0.3–0.5 (API). Q8 over Q4 for
  structured output quality. Dense over MoE for instruction following.
  General instruct over code-tuned for balanced prose/code fragment mix.
- **Embedding model:** qwen3-embedding:0.6b (current, unchanged).

---

## Commits pushed to main

- `480a000` — `feat(corpus): tiered R1 sourcing — upstream registry, curated URL lists, docs`
- `1171c65` — `docs(authoring): update R1 rule with tiered sourcing strategy`

---

## Files to read before starting work

In priority order:
1. `experiments/skill-tax/workflow-phase-retrieval-pilot-spec.md` (v2.3) — full experimental design
2. `experiments/skill-tax/handoff.md` — updated this session with verified state
3. `fixtures/skill-authoring-guidelines.md` — R1-R8 rules, now includes tiered sourcing
4. `fixtures/skill-authoring-agent.md` — transform contract (source → review YAML)
5. `fixtures/upstream/registry.yaml` — before any R1 fetch

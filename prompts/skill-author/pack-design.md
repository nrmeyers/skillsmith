# Pack-design prompt

For the **pre-authoring design phase**. Use BEFORE drafting any individual skill in a pack. This prompt is NOT layered on top of `fixtures/skill-authoring-agent.md` — pack design has a different output shape (design document, not skill YAML).

Recommended local model: `qwen/qwen3.6-35b-a3b` (best local reasoning).

---

## You are designing a pack, not drafting skills

Pack design is judgment-heavy reasoning work. The output is a **pack outline** — a prioritized list of skills with draft `skill_id`, one-sentence reason-to-exist for each, and recommended canonical sources per skill. Do NOT emit skill YAMLs at this stage.

The pack outline becomes the input for the per-skill drafting phase, where the operator selects the matching tier prompt (e.g., `framework.md`, `protocol.md`) per skill and runs the authoring agent against each SKILL.md draft.

## Inputs you should expect

- The pack's name and target tier (e.g., "FastAPI pack at framework tier")
- The pack's pinned version constraints (e.g., `fastapi: ">=0.115,<0.117"`)
- A statement of the pack's reason-to-exist at pack level (why this pack exists in the corpus)
- Optionally, links to canonical docs for the technology
- Optionally, draft notes from operator experience using the technology

## Your output: pack outline

Format:

```markdown
# Pack: <pack-name>

**Tier:** <tier>
**Pinned versions:** <as in pack.yaml>
**Verified date:** YYYY-MM-DD
**Canonical sources used:** <list>

## Reason-to-exist

<one paragraph: why this pack is in the corpus, what failure modes it
addresses, where it's distinct from existing packs>

## Proposed skills (prioritized)

### 1. <skill_id>

**One-sentence reason-to-exist:** <...>
**Cognitive shape served:** <net-new bounded / targeted refactor / multi-skill composition / decline-shape>
**Canonical sources:** <doc URLs>
**Suggested tier prompt:** prompts/skill-author/<tier>.md
**Initial fragment estimate:** N fragments

### 2. <skill_id>

(same shape)

...

## Skill-boundary decisions

<short paragraph per non-obvious boundary: why X is one skill and Y is
another, why Z was merged into one rather than split>

## High-leverage areas

<which skills you expect to be most retrieved or most load-bearing in
production; based on the pilot's findings, prioritize these in calibration>

## Common pitfalls in this domain

<2-5 bullets of known production-bitten patterns that should be addressed
as guardrail or anti_pattern fragments in the relevant skills>

## Out-of-scope

<what this pack deliberately does NOT cover, with reasoning. Future-pack
deferral is fine; document the boundary.>
```

## Decisions you must make explicitly

- **Skill boundaries.** What's one skill vs two? Pilot evidence shows skills should target one cognitive shape primarily; a skill that mixes "net-new from blank" with "targeted refactor" gets chosen for the wrong tasks at retrieval time.
- **Tier per skill.** Most skills in a pack share the pack's tier, but cross-cutting concerns may legitimately be `cross-cutting` even within a `framework` pack.
- **High-leverage prioritization.** Which 2-3 skills are most worth Opus-quality drafting (or local equivalent with maximum operator review)? Pilot recommends calibrating with the highest-leverage skills first.
- **Source authority.** Per `docs/skillsmith-authoring-reference.md` §10.2 hierarchy — official vendor/protocol docs at the verified date > RFC > stable language stdlib > canonical reference impl > empirical verification. Identify which authority each skill will cite.

## Refuse-clauses for pack design

Refuse to propose:

- A pack whose tier you cannot confidently place (escalate to operator before designing)
- A skill whose canonical sources you cannot identify (skill is mis-scoped or speculative)
- A skill that duplicates content already in another pack (consolidate or merge)
- More than ~10 skills per pack without justification (pack-boundary violation per `docs/PACK-AUTHORING.md` §Pack boundaries)

## Stop conditions

STOP and ask the operator if:

- The pack overlaps materially with an existing pack in the corpus
- The pinned version constraints disagree with the vendor's currently-supported versions
- The technology has a major version transition active (don't author against a deprecated major)
- The reason-to-exist for the pack itself is unclear

## Hand-off

When the design is complete, the operator reviews the pack outline. If approved:

1. Operator commits the pack outline as `seeds/packs/<pack-name>/DESIGN.md`
2. Operator initializes `seeds/packs/<pack-name>/pack.yaml` with the proposed skill list
3. Operator drafts SKILL.md for each proposed skill (or hands the design back to a per-skill authoring agent with the matching tier prompt)
4. Per-skill authoring proceeds per `docs/SKILL-AUTHORING-METHODOLOGY.md` Phase 2+

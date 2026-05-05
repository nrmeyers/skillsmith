# Skill-Author Tier Prompts

> Tier-specific prompt addenda for skill authoring. Layered on top of `fixtures/skill-authoring-agent.md` (the base transform prompt). One file per pack tier; the operator selects the matching tier file when configuring the local authoring agent for a given pack.

## Usage

The base authoring prompt at `fixtures/skill-authoring-agent.md` defines the transform contract: take a SKILL.md, emit schema-compliant YAML. It is tier-agnostic.

Tier-specific files in this directory layer additional directives on top — source-fetch policy, code-block discipline, verification-fragment grounding requirements. Pick the file matching the pack tier and prepend or append it to the base prompt when starting an authoring session.

```bash
# Example: author a framework-tier pack
SYSTEM_PROMPT="$(cat fixtures/skill-authoring-agent.md)\n\n$(cat prompts/skill-author/framework.md)"
```

Or pass both as separate system messages if the agent supports multi-turn system context.

## File index

| File | Tier | Recommended local model | Fetch policy |
|------|------|--------------------------|---------------|
| `workflow.md` | `workflow` | qwen3.6-27b@q4_k_m | Not required |
| `foundation.md` | `foundation` | qwen3.6-27b@q4_k_m | Optional |
| `language.md` | `language` | qwen3.6-27b@q8_k_xl | Recommended |
| `framework.md` | `framework` | qwen3-coder-30b-a3b-instruct | **Mandatory** |
| `protocol.md` | `protocol` | qwen3-coder-30b-a3b-instruct | **Mandatory** |
| `store.md` | `store` | qwen3-coder-30b-a3b-instruct | **Mandatory** |
| `domain.md` | `domain` | qwen3-coder-30b-a3b-instruct or qwen3.6-35b-a3b | **Mandatory** |
| `cross-cutting.md` | `cross-cutting` | qwen3.6-35b-a3b | Recommended |
| `pack-design.md` | (pack design — pre-authoring) | qwen3.6-35b-a3b | Optional |
| `mechanical-lint.md` | (lint-fix between iterations) | qwen2.5-coder-3b-instruct-128k | Not required |

See `docs/SKILL-AUTHORING-METHODOLOGY.md` §2.1a for the full routing rationale.

## Why these prompts exist

Per the skill-tax pilot's findings, authoring cognitive shape is constant across tiers — what varies is *training-data depth* and *fetch dependency*. Local 27B–35B models will produce more fabrications than Opus would on source-grounded drafting. The tier prompts encode the discipline that closes that gap: hard fetch requirements, verbatim citation rules, refuse-clauses for uncited claims.

If you bypass these prompts and use only the base authoring prompt with a local model, expect to find fabricated API claims, wrong status codes, hallucinated SDK behaviors, and verification fragments that read as filler. The pilot validated 27B-class models at the *critic* role but not at the *first-pass source-verification authoring* role.

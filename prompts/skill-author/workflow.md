# Tier addendum: workflow

Layer on top of `fixtures/skill-authoring-agent.md` for `workflow`-tier skills (SDD process docs, code-review checklists, RFC authoring guides, incident-response playbooks).

Recommended local model: `qwen3.6-27b@q4_k_m`.

---

## Source policy

The source for `workflow` content is the operator's own SKILL.md and any organizational practice it cites. **Do NOT fetch external docs.** This tier is process content, not external API content. If the source SKILL.md lacks detail you would need to invent, STOP and declare — do not paraphrase from training data.

If the SKILL.md cites an external standard (RFC, OWASP, NIST), copy the citation verbatim into the relevant fragment but do not extend or interpret beyond what SKILL.md states.

## Verification-fragment expectations

Verification items must describe **auditable practices**, not external API claims:

Good:
```markdown
- [ ] Reviewer confirms PR description names the failure mode the change addresses.
- [ ] Reviewer confirms test added covers the failure mode (not just the happy path).
- [ ] CI pipeline passes type-check + format-check + unit tests before merge.
```

Bad (this is for `framework` or `protocol` tier, not `workflow`):
```markdown
- [ ] HTTP response status is 200.
- [ ] FastAPI lifespan context creates the asyncpg pool.
```

## Code blocks

Workflow skills typically have minimal code. If a code block is included, it's illustrative (e.g., a sample PR template, a sample CI step). Code blocks are NOT runtime contracts in this tier — they're examples of the documented practice.

## R6 honesty

`change_summary` names the organizational source of the practice — e.g., "documents the team's PR review checklist as practiced since 2026-Q1; supersedes the verbal convention." If the practice has no formal source, say so honestly: "synthesizes operator's spoken description of the team's current practice."

## Stop conditions

STOP authoring and declare if:

- SKILL.md lacks detail required for a fragment and you would need to invent process steps not in the source
- A claim involves a specific tool/version that isn't in SKILL.md (this content belongs in a different tier)
- The practice documented contradicts another approved workflow skill in the corpus (escalate to operator)

## Worked example

A `workflow`-tier SKILL.md describes the team's "PR review checklist" practice. Author the YAML with:

- `rationale` fragment: why this practice exists, what failure modes it prevents
- `setup` fragment: when to apply (which PRs trigger this checklist)
- `execution` fragment(s): the steps the reviewer follows, in order, copied verbatim from SKILL.md
- `example` fragment: a worked example of one PR going through the checklist
- `verification` fragment: auditable practice items (per above)
- `guardrail` fragment: anti-patterns ("never approve without running the test plan")

Tags: from operator vocabulary — `pr-review`, `code-review`, `merge-checklist`, NOT internal jargon.

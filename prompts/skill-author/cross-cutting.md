# Tier addendum: cross-cutting

Layer on top of `fixtures/skill-authoring-agent.md` for `cross-cutting`-tier skills (security patterns, observability semantic conventions, performance principles — concerns that apply across multiple tools).

Recommended local model: `qwen/qwen3.6-35b-a3b` (general MoE, high reasoning).

---

## Source policy

Fetch is **recommended** for any specific recommendation that may rotate over time. Cross-cutting content synthesizes across tools; pull the canonical source per claim:

| Topic | Primary source | Notes |
|-------|----------------|-------|
| Web app security | OWASP Top 10 (owasp.org/Top10/) | Recommendations rotate; date-stamp the version (e.g., "2021 edition" or current) |
| Network security | NIST SP 800-series (nvlpubs.nist.gov) | Specific publications stable; cite the SP number |
| Observability | OTLP semantic conventions (opentelemetry.io/docs/specs/semconv/) | Active spec; cite the version + section |
| Performance | Vendor-specific (Postgres, Redis, etc.) | When cross-cutting, prefer benchmark methodology over absolute numbers |
| CVE references | nvd.nist.gov / cve.org | Cite CVE-YYYY-NNNN with date-stamp |

R5 date-stamps every recommendation against the doc revision fetched.

## Skill scope discipline

The skill scope is the **cross-cutting concern itself**, not any single tool. Example fragments may cite multiple tools (e.g., "this principle applies to Postgres, Redis, and Kafka equally, with tool-specific commands shown below") but the rationale generalizes.

If a draft skill drifts into being mostly about one tool, scope-split:
- Keep the cross-cutting principle in this skill (`cross-cutting`)
- Move tool-specific guidance to a `store` or `framework` skill that this skill cross-references

## Code-block discipline

Cross-cutting skills often have minimal code (the rationale is the load-bearing content). When code is included, it's illustrative across multiple tools — show 2-3 short examples in different languages/tools rather than one long example.

R2 still applies — every non-stdlib symbol gets one `import`. R3 still applies — verification items must be mechanically checkable.

## Verification-fragment expectations

Verification items are observable practices that span tools:

```markdown
- [ ] Inputs from external sources are validated before being used in queries,
      log messages, or downstream calls. Per OWASP Top 10 2021 §A03 (verified
      2026-05-04 at owasp.org/Top10/A03_2021-Injection/): "Source code review
      is the best method of detecting if applications are vulnerable to injection."

- [ ] Service emits structured logs with trace_id propagation. Per OTLP
      semantic conventions §1.27.0 (verified 2026-05-04 at
      opentelemetry.io/docs/specs/semconv/general/trace/): "trace_id MUST be
      included in all log records emitted from instrumented applications."

- [ ] No secrets in source. `grep -rnE "(api_key|secret|token|password)\s*=\s*[\"']" src/`
      returns nothing in committed files (test files using fake values noted as
      acceptable per project convention).
```

Note the explicit version citation (OWASP edition, OTLP semconv version) — these change.

## Refuse-clauses

Refuse to emit a fragment if:

- A recommendation lacks a citable canonical source (vendor blog posts and conference talks are NOT canonical for cross-cutting tier — at minimum, peer-reviewed or formally published)
- A security claim cites an outdated OWASP edition without flagging the rotation
- A performance claim cites an absolute benchmark number without methodology + date + hardware
- A "best practice" claim has no traceable source

## Stop conditions

STOP authoring and declare if:

- Multiple central claims cannot be sourced to canonical references (skill is opinion, not cross-cutting practice)
- The skill scope has narrowed to a single tool (re-tier to `store` / `framework` / `domain`)
- Recommendations conflict across the canonical sources you've fetched (operator must pick one or document the conflict)

## R6 honesty for cross-cutting

`change_summary` names every canonical source cited and the fetched dates. Cross-cutting skills age faster than they look — security guidance rotates annually, observability conventions rev frequently. The change_summary is the audit trail for "when does this skill need re-verification."

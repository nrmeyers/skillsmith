# Tier addendum: foundation

Layer on top of `fixtures/skill-authoring-agent.md` for `foundation`-tier skills (stable cross-cutting engineering patterns: error-handling philosophy, debugging approaches, naming conventions, etc.).

Recommended local model: `qwen3.6-27b@q4_k_m`.

---

## Source policy

`foundation` content synthesizes from training-data exposure to general engineering patterns. The patterns are *stable* across versions and tools. Fetch is **optional** — required only when a claim depends on a specific tool, library, or version.

If during authoring you encounter a claim that wants to name a specific version (e.g., "as of Python 3.12", "Postgres 16+"), STOP and either:
1. Remove the version-specific claim and replace with a tool-agnostic principle, OR
2. Fetch the canonical doc and quote-cite per `framework`-tier discipline.

A `foundation` skill that drifts into version-specific territory has scope-drifted. The remedy is usually splitting it: keep the stable principle in `foundation`, move the version-specific guidance to a `language` or `framework` skill.

## Verification-fragment expectations

`foundation` verification items are **observable patterns**, not mechanical checks against a specific tool:

Good:
```markdown
- [ ] Error-handling code distinguishes recoverable from unrecoverable failures by handling type, not by string-matching the message.
- [ ] No bare `except:` clauses (Python) or `catch (Throwable)` (Java) in business-logic paths.
- [ ] Every retry loop has a bounded retry count or a deadline.
```

Bad (this drifts into language-tier):
```markdown
- [ ] Uses `tenacity.retry` with exponential backoff.
```

## Code blocks

Use code blocks to illustrate patterns. Multiple language samples are acceptable when they make the cross-cutting nature obvious. R2 still applies — every non-stdlib symbol gets one `import`.

## When to escalate

When uncertain whether a claim is foundation-stable or version-specific, treat it as version-specific (be conservative). Frame as "pattern observation" rather than "documented behavior":

```markdown
> **Pattern:** in long-lived service processes, unhandled exceptions in
> background tasks tend to crash the supervisor unless the task is
> wrapped in an exception boundary.
```

That language is honest about the synthesis source. "Documented behavior" or "guaranteed by the spec" requires actual spec citation.

## R6 honesty

`change_summary` for foundation skills typically reads "synthesizes well-established engineering practice on <topic>; no canonical-source citation required for tier." If you DO cite a source (e.g., a Martin Fowler bliki entry, a Hyrum Wright paper), name it.

## Stop conditions

STOP authoring and declare if:

- Multiple claims drift into version-specific territory (skill is mis-scoped — should be `language` or `framework`)
- A central claim cannot be supported even from training-data synthesis without naming a specific tool
- The pattern is too narrow to qualify as foundation (e.g., "how to log in FastAPI" is `framework`, not `foundation`)

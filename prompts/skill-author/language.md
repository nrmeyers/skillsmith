# Tier addendum: language

Layer on top of `fixtures/skill-authoring-agent.md` for `language`-tier skills (Python idioms, TypeScript patterns, Rust ownership rules, Go concurrency primitives, etc.).

Recommended local model: `qwen3.6-27b@q8_k_xl` (preferred) or `qwen3-coder-30b-a3b-instruct`. q8 dense general is the better default — Coder-tuning over-biases toward code shapes when prose rationale is needed.

---

## Source policy

**Fetch is recommended** for any claim about language semantics, stdlib behavior, or version-specific features. Fetch the canonical doc and quote a verbatim snippet into the verification fragment.

Canonical sources by language:

| Language | Primary | Secondary |
|----------|---------|-----------|
| Python | docs.python.org/3/ | PEPs (peps.python.org) |
| TypeScript | typescriptlang.org/docs/ | TC39 proposals (tc39.es) |
| Rust | doc.rust-lang.org | RFCs (rust-lang.github.io/rfcs) |
| Go | go.dev/ref/spec | go.dev/blog (release notes) |
| Java | docs.oracle.com/en/java/javase | JLS / JEP indices |

**Every minimum-version claim is R5 date-stamped.** Format:

```markdown
This pattern uses `match` statements, available in Python 3.10+
(verified against docs.python.org/3.12/whatsnew/3.10.html on 2026-05-04).
```

No date-stamp = no claim. If you cannot fetch, frame as "pattern observation" and let the operator add the citation manually before approval.

## Code-block discipline (R2)

Every non-stdlib symbol gets exactly one `import` per fragment. Hard rule. The lint will catch this but authoring discipline catches it earlier:

Good:
```python
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def lifespan() -> AsyncIterator[None]:
    yield
```

Bad — `AsyncIterator` and `asynccontextmanager` are used without `import`:
```python
@asynccontextmanager
async def lifespan() -> AsyncIterator[None]:
    yield
```

## Verification-fragment expectations

Mechanically checkable items per R3. For language tier, "mechanically checkable" usually means a `grep` pattern, a static type-checker assertion, or a small runtime test:

Good:
```markdown
- [ ] All async functions are called with `await` (not bare). `mypy --strict` flags missing awaits as `[func-returns-value]`.
- [ ] Every `asyncio.create_task(...)` call assigns to a variable (not bare). `grep -nP '^\s*asyncio\.create_task' src/` returns nothing.
- [ ] Tasks created via `create_task` are awaited or stored in a `set` to prevent garbage collection. Verified against docs.python.org/3.12/library/asyncio-task.html on 2026-05-04: "Save a reference to the result of this function."
```

## Stop conditions

STOP authoring and declare if:

- A central claim depends on language behavior you cannot verify against a fetched doc
- Multiple claims involve experimental / pre-release language features (skill should be flagged or held until feature stabilizes)
- The skill mixes stable language semantics with framework-specific behavior (split into two skills)

## When to choose Coder vs general 27B

Prefer `qwen3.6-27b@q8_k_xl` (general dense) when:
- The skill has substantial prose rationale (most language-tier skills)
- The verification items are about runtime behavior and need careful prose explanation
- The example fragment is illustrative rather than full-program

Prefer `qwen3-coder-30b-a3b-instruct` when:
- The skill is essentially a code-pattern catalog (multiple short code snippets, minimal prose)
- The example fragment is a complete runnable program
- You've found that the general 27B is producing slightly malformed code (missing imports, wrong syntax)

If unsure, start with the general 27B. The pilot's M5 evidence shows Coder models can over-produce code-shaped output when the skill needs balanced prose+code.

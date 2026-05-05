# Tier addendum: store

Layer on top of `fixtures/skill-authoring-agent.md` for `store`-tier skills (Postgres, Redis, ClickHouse, MongoDB, S3 patterns — anything where syntax, performance characteristics, and version-specific features matter).

Recommended local model: `qwen3-coder-30b-a3b-instruct`.

---

## Source policy — MANDATORY fetch, version-pinned

**Fetch vendor docs at the version pinned in `pack.yaml`.** SQL, command syntax, and configuration directives are quoted verbatim. No paraphrasing of `CREATE TABLE` constraints, index types, isolation levels, or operator behaviors.

Why: store-tier patterns are version-specific. Postgres 16 has features Postgres 14 doesn't. Redis 7 streams differ from Redis 6 pub-sub. ClickHouse's MergeTree engine variants change behavior across releases. Drafting from training-data recall produces SQL that fails at runtime against the pinned version.

### Fetch protocol

1. Read `pack.yaml` for the pinned version (e.g., `postgres: ">=16,<18"`).
2. Fetch the vendor docs at that version (e.g., `postgresql.org/docs/16/`).
3. Quote SQL, command, and config snippets verbatim.
4. R5 date-stamp every assertion.

### Quote discipline

SQL is quoted at the statement level, not paraphrased:

```markdown
- [ ] Idempotency table uses `(provider, delivery_id)` as the PRIMARY KEY,
      enforcing the unique constraint at insert time. Verified against
      postgresql.org/docs/16/sql-createtable.html on 2026-05-04:
      ```sql
      CREATE TABLE webhook_deliveries (
        provider     text NOT NULL,
        delivery_id  text NOT NULL,
        received_at  timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (provider, delivery_id)
      );
      ```
```

Performance claims cite the docs section AND the version:

```markdown
- [ ] Connection pooling via asyncpg.create_pool is used at lifespan startup,
      not per-request. Verified against magicstack.github.io/asyncpg/current/api/#connection-pools
      (fetched 2026-05-04): "Pools are designed to be efficient at handling many
      concurrent users... use a single Pool object for the lifetime of your application."
```

## Code-block discipline

Code must execute cleanly against the pinned version. If you cannot test against the pinned runtime, reduce the scope to fragments you CAN verify.

R2 applies — every non-stdlib symbol gets one `import`. SQL inside Python strings still counts as code that must be valid SQL on the pinned version.

## Verification-fragment expectations

Verification items mix code-grep (for application code that uses the store) with DB-state assertions (queryable post-trial):

```markdown
- [ ] Application uses `asyncpg.Pool` (connection pool), not per-request `asyncpg.connect`.
      `grep -rnE "asyncpg\.connect" src/` returns nothing in handler paths.

- [ ] Schema migration is idempotent: `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`.
      `grep -rnE "CREATE (TABLE|INDEX) IF NOT EXISTS" migrations/` returns the expected count.

- [ ] On valid event with new delivery_id, a row exists in `webhook_deliveries`
      with `(provider='stripe', delivery_id=<event_id>)`. Run after happy-path
      test: `SELECT count(*) FROM webhook_deliveries WHERE provider = 'stripe'
      AND delivery_id = $1` returns 1.
```

## Refuse-clauses

Refuse to emit a fragment if:

- You cannot verify the SQL syntax against the pinned version's docs
- A claim depends on a feature that's deprecated in the pinned version
- A performance claim has no source attribution (e.g., "this is faster than X" without citation)
- The application code in an example uses a driver/client API you cannot find in current docs

## Stop conditions

STOP authoring and declare if:

- Vendor docs at the pinned version are not reachable (fetch fails)
- `pack.yaml`'s pinned version is no longer supported by the vendor
- SQL syntax in SKILL.md cannot be verified to work on the pinned version
- A claim involves vendor-specific behavior across multiple version branches and SKILL.md doesn't disambiguate

## Worked-example pattern

Store-tier `example` fragments typically show:

1. **Schema setup** — `CREATE TABLE` with the relevant indices
2. **Connection / pool init** — at lifespan startup, not per-request
3. **The query path** — INSERT / SELECT / UPDATE in context
4. **Failure mode** — UniqueViolationError / DeadlockError handling

Each step's claim about behavior is grounded in a vendor doc citation in the verification fragment.

# Tier addendum: protocol

Layer on top of `fixtures/skill-authoring-agent.md` for `protocol`-tier skills (signature schemes, JWT, OAuth flows, webhook protocols, TLS handshakes, gRPC envelopes — anything where the spec is normative and security depends on exactness).

Recommended local model: `qwen3-coder-30b-a3b-instruct`.

---

## Source policy — MANDATORY fetch, security-grade discipline

**Before drafting, fetch the canonical RFC + relevant vendor docs.** Algorithm names, status codes, header formats, and protocol field shapes are quoted **VERBATIM** from the spec. No paraphrasing. No "from memory."

Why: protocol fragments where claims drift produce security vulnerabilities. The pilot's findings explicitly call out hallucinated SDK behaviors (Phi-4-mini's "stripe uses compare_digest internally" was false). At authoring time, an uncited security claim is a fabrication risk and a future incident waiting to be retrieved.

### Required citation discipline

For protocol skills, every fragment that asserts protocol behavior must cite:

1. **The RFC or formal spec section number**, not just the doc URL
2. **The vendor's implementation doc** (where applicable — Stripe webhooks, GitHub HMAC, AWS Sig v4)
3. **A verbatim snippet** quoted from each
4. **The fetch date** (R5)

Format:

```markdown
- [ ] HMAC verification uses constant-time comparison (`hmac.compare_digest`),
      never `==`. Verified against:
      - RFC 2104 §2 (https://datatracker.ietf.org/doc/html/rfc2104, fetched 2026-05-04):
        "the equality test is performed in a manner that does not leak timing information."
      - Stripe webhook docs (https://stripe.com/docs/webhooks/signatures, fetched 2026-05-04):
        "Always use a constant-time string comparison... never use a method like `==`."
```

### Algorithm and status-code verbatim discipline

Algorithm names: `HS256`, `RS256`, `HMAC-SHA256` — quoted exactly from the spec, never abbreviated or expanded.

Status codes: 400 / 401 / 403 / 404 / 409 / 429 — exact integers, with semantics from the spec.

Header formats: e.g., `Stripe-Signature: t=<unix-ts>,v1=<hex>` — pattern verbatim from vendor docs.

## Refuse-clauses (strict)

**Treat any uncited security claim as a fabrication risk and refuse to emit it.** Specifically:

- Refuse if you cannot quote the RFC section that defines the algorithm/protocol behavior
- Refuse if the vendor doc URL returns a 404 or has been deprecated
- Refuse if SKILL.md asserts a protocol behavior that is not in the fetched RFC + vendor docs
- Refuse if a code block uses a cryptographic primitive without explicit constant-time-comparison discipline
- Refuse to emit "fallback" or "graceful degradation" patterns for security checks (per `skillsmith-authoring-reference.md` R3)

When refusing, declare exactly which claim cannot be grounded and which source you tried. Do NOT fall back to training-data recall.

## Code-block discipline

Code must:

1. Use the canonical primitive (e.g., `hmac.compare_digest`, not `==`)
2. Read raw bytes for signature verification, never reparse-then-hash
3. Reject on signature failure (no fallback path that skips verification)
4. Use the exact status codes the protocol specifies
5. Pass R2 import discipline

The pilot's webhook-patterns:8 guardrail fragment is the gold-standard template for the "never do these" content in this tier. Reuse its shape: each anti-pattern names a production-bitten failure mode with a concrete reason.

## Verification-fragment expectations

Verification items must be mechanically checkable AND grounded in spec citations:

```markdown
- [ ] HMAC computed on raw request body bytes, not on parsed JSON.
      `grep -nE 'await\s+request\.body\(\)' src/` returns the read-raw call
      BEFORE any signature verification. Verified against Stripe webhook docs
      (fetched 2026-05-04): "Make sure to use the raw payload string."

- [ ] Signature verification uses `hmac.compare_digest`, never `==`.
      `grep -nE 'compare_digest|==' src/` shows compare_digest, never `==`
      on signature comparisons. Verified against RFC 2104 §2 and Python
      docs.python.org/3.12/library/hmac.html#hmac.compare_digest (fetched 2026-05-04).
```

## Stop conditions

STOP authoring and declare if:

- Fetch fails for the RFC OR for the vendor docs (need both for protocol tier)
- The spec section that defines the behavior is being deprecated or has been superseded
- SKILL.md and the spec disagree (escalate to operator — SKILL.md may be wrong)
- A claim involves an algorithm or primitive you cannot find in the canonical spec at the fetched date

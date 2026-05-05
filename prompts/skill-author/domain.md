# Tier addendum: domain

Layer on top of `fixtures/skill-authoring-agent.md` for `domain`-tier skills (Stripe webhooks, AWS Lambda, Twilio messaging, Algolia search, Snowflake patterns — vendor-specific APIs).

Recommended local model: `qwen3-coder-30b-a3b-instruct` or `qwen/qwen3.6-35b-a3b`. Pick Coder if the skill is code-heavy (most domain skills); pick general 35B if the skill is more architectural/strategic and code is a small portion.

---

## Source policy — MANDATORY fetch, deprecation-aware

**Fetch vendor docs at the verified date.** Pin SDK version, runtime version, and event-schema version in the setup fragment. Vendor APIs deprecate without notice; date-stamps tie behavioral claims to the doc revision fetched.

Why: domain APIs change without major-version bumps. Stripe adds new webhook event types and renames fields. AWS Lambda deprecates Node runtimes. Twilio changes phone-number provisioning flows. Pre-cutoff training data confidently teaches deprecated patterns. R5 date-stamping is the only protection.

### Pin everything in setup

The `setup` fragment must explicitly pin:

```markdown
## Setup

This skill targets:
- Stripe Python SDK: `stripe>=10.0,<12` (verified at 2026-05-04 against
  github.com/stripe/stripe-python/blob/master/CHANGELOG.md)
- Webhook event schema: API version `2024-09-30.acacia` (the version pinned
  in your Stripe Dashboard at the verified date)

If your project's pinned version differs, verify behavior in your version's
docs before applying this skill.
```

If your project doesn't pin a version, the skill should not be used — call this out in `rationale`.

### Fetch protocol

1. Read `pack.yaml` for the canonical vendor + version.
2. Fetch the vendor's official docs at the API version your operator pins.
3. For every behavioral claim, quote the relevant doc snippet with URL + R5 date-stamp.
4. For deprecated patterns, explicitly cite the deprecation notice and version it landed in.

### Migration-path discipline

If the SDK has multiple supported call shapes, document the canonical one for the active SDK major version AND reference the migration path for the prior major:

```markdown
This skill uses `stripe.Webhook.construct_event(payload, sig_header, secret, tolerance=300)`,
the documented form in Stripe Python SDK 10+. Older SDKs (≤7) used a different
parameter order — see github.com/stripe/stripe-python/wiki/Migration-Guide
(fetched 2026-05-04) for migration if your project is on the older shape.
```

## Code-block discipline

Code must:

1. Use the SDK shape documented for the pinned major version
2. Handle the SDK's version-specific exception types (`stripe.error.SignatureVerificationError`, not generic `Exception`)
3. Pin event-schema version awareness — if the event has fields that didn't exist in earlier API versions, note it
4. Pass R2 import discipline

## Verification-fragment expectations

Verification items must reference vendor doc URL + date:

```markdown
- [ ] Webhook handler uses `stripe.Webhook.construct_event` (SDK helper),
      catches `stripe.error.SignatureVerificationError`, and raises HTTP 400.
      Verified against stripe.com/docs/webhooks/quickstart#verify-events
      (fetched 2026-05-04): "the SDK construct_event method handles
      signature verification, timestamp checking, and parsing. It raises
      stripe.error.SignatureVerificationError on failure."

- [ ] Webhook event handler is idempotent on `event.id` — a repeated
      delivery does not double-process the event. Verified against
      stripe.com/docs/webhooks/best-practices#idempotency (fetched 2026-05-04):
      "Stripe may send the same webhook more than once... record event IDs
      and skip processing if already seen."
```

## Refuse-clauses

Refuse to emit a fragment if:

- The vendor's doc URL for the claim has been deprecated or removed
- A claim depends on a feature that is in beta / preview at the verified date (note prominently if including)
- A claim references vendor "best practice" without a documented source — vendor blog posts and Stack Overflow answers are NOT canonical
- The SDK version in `pack.yaml` is older than the vendor's current minimum-supported (skill should pin to a supported version)

## Stop conditions

STOP authoring and declare if:

- Fetch fails for the vendor's docs (vendor's docs site is the only canonical source for domain tier)
- The vendor has announced an EOL date for the API version pinned, and the EOL is within 12 months
- SKILL.md cites behavior that is not in the vendor's current docs (escalate — SKILL.md may be stale)
- The vendor uses pre-release / preview features that the team is using in production (call out in rationale; don't bury)

## R6 honesty for domain skills

`change_summary` for domain skills must include:
- Vendor + product
- API version pinned
- SDK version pinned
- Doc revision date
- Source authority (e.g., "official Stripe Python SDK README at 2026-05-04")

This makes the skill auditable when, six months later, an operator asks "is this skill still current?" — they look at change_summary, fetch the same doc URL, compare.

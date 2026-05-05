#!/usr/bin/env python3
"""Re-run mechanical checks for an existing pilot_trials row.

Reads response from the DB, applies [FILE:] blocks to a fresh worktree,
runs mechanical_checks + cross_checks against a live app process, and
emits per-check JSON results for milestone-3 review.

Usage:
    python rerun_checks.py <trial_id>  → prints JSON to stdout
"""
from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
from pathlib import Path

import duckdb
import yaml

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))
from run_trial import (  # noqa: E402
    _parse_file_response,
    _apply_file_blocks,
    _forbidden_present,
    _stripe_sig,
    _jwt_token,
    _reset_app_schema,
    git_worktree,
    app_process,
    run_checks,
    run_cross_checks,
)


def _capture_env_state() -> dict:
    """Capture environment state at rerun time for reproducibility audit."""
    db_url = os.environ.get("DATABASE_URL", "")
    pg_reachable = None
    if db_url:
        try:
            import asyncio, asyncpg  # noqa: E401
            async def _ping():
                c = await asyncpg.connect(db_url)
                v = await c.fetchval("SELECT 1")
                await c.close()
                return v == 1
            pg_reachable = asyncio.run(_ping())
        except Exception as e:
            pg_reachable = f"unreachable:{type(e).__name__}"
    return {
        "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "DATABASE_URL_set_in_os_env": bool(db_url),
        "DATABASE_URL_value_redacted": (db_url.split("@")[-1] if "@" in db_url else db_url[:20]) if db_url else None,
        "postgres_reachable_at_rerun_time": pg_reachable,
        "LM_STUDIO_BASE_URL": os.environ.get("LM_STUDIO_BASE_URL", ""),
        "TIER2_MODEL": os.environ.get("TIER2_MODEL", "qwen3-coder-30b-a3b"),
        "SKILLS_DUCK_PATH": os.environ.get("SKILLS_DUCK_PATH", ""),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


def _attach_evidence(
    results: list[dict],
    checks: list[dict],
    captured_bodies: dict,
    wt: Path,
) -> None:
    """Add an `actually` field to each check result for reviewer convenience."""
    chk_by_id = {c["id"]: c for c in checks}
    for r in results:
        cid = r["id"]
        chk = chk_by_id.get(cid)
        if not chk:
            r["actually"] = ""
            continue
        ctype = chk["type"]
        actually = ""
        try:
            if ctype == "app_starts":
                actually = "openapi.json reachable" if r.get("pass") else "app did not start"
            elif ctype == "http":
                body = captured_bodies.get(cid, b"")
                txt = body.decode("utf-8", errors="replace") if body else ""
                txt = txt.replace("\n", " ").strip()
                actually = (txt[:140] + ("…" if len(txt) > 140 else "")) if txt else "(empty body)"
            elif ctype == "code_grep":
                text = (wt / chk["file"]).read_text(errors="replace")
                pat = re.compile(chk["pattern"], re.MULTILINE)
                hits = pat.findall(text)
                if not hits:
                    actually = "(no match)"
                else:
                    first_line = next(
                        (ln.strip() for ln in text.splitlines() if pat.search(ln)),
                        str(hits[0]),
                    )
                    actually = f"{len(hits)} match(es); first: `{first_line[:120]}`"
            elif ctype == "diff_imports":
                text = (wt / chk["file"]).read_text(errors="replace")
                forbidden = chk.get("expect", {}).get("forbidden_imports", [])
                present = [f for f in forbidden if _forbidden_present(text, f)]
                actually = f"forbidden present: {present}" if present else "no forbidden imports"
            elif ctype == "diff":
                actually = "(manual diff review)"
            else:
                actually = f"({ctype} — no evidence extractor)"
        except FileNotFoundError:
            actually = "(file not found)"
        except Exception as e:
            actually = f"(evidence extraction error: {type(e).__name__}: {e})"
        r["actually"] = actually

PILOT = HARNESS.parent
SKILLS_DUCK = os.environ.get(
    "SKILLS_DUCK_PATH", str(PILOT / "skills.duck")
)


def main() -> None:
    trial_id = sys.argv[1]
    conn = duckdb.connect(SKILLS_DUCK)
    row = conn.execute(
        "SELECT task_variation, retrieval_arm, response FROM pilot_trials WHERE trial_id = ?",
        [trial_id],
    ).fetchone()
    if not row:
        raise SystemExit(f"trial not found: {trial_id}")
    task, arm, response_text = row

    fixture = yaml.safe_load((PILOT / "tasks" / f"{task}.yaml").read_text())
    seed_branch = fixture["app_skeleton"]["seed_branch"]

    file_blocks, decline_reasons, parse_warnings = _parse_file_response(response_text)

    with git_worktree(seed_branch) as wt:
        host_cfg = wt / "seed" / "test-host-config.yaml"
        if host_cfg.exists():
            hdata = yaml.safe_load(host_cfg.read_text())
            trusted_host = hdata.get("trusted_hosts", ["api.example.com"])[0]
        else:
            trusted_host = "api.example.com"

        secrets: dict[str, str] = {}
        secrets_env = wt / "seed" / "test-secrets.env"
        if secrets_env.exists():
            for line in secrets_env.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    secrets[k.strip()] = v.strip()

        ts = int(time.time())
        body_bytes = b""
        fixture_body = wt / "seed" / "fixtures" / "stripe-event.json"
        if fixture_body.exists():
            body_bytes = fixture_body.read_bytes()
        stripe_secret = secrets.get("STRIPE_WEBHOOK_SECRET", "")
        subs: dict[str, str] = {
            "stripe_signature": _stripe_sig(stripe_secret, body_bytes, ts),
            "stripe_signature_tampered": f"t={ts},v1={'0'*64}",
            "stripe_signature_stale": _stripe_sig(stripe_secret, body_bytes, ts - 600),
        }
        jwt_secret = secrets.get("JWT_HS256_SECRET", "")
        if jwt_secret:
            jwt_iss = secrets.get("JWT_EXPECTED_ISSUER", "pilot-test-issuer")
            jwt_aud = secrets.get("JWT_EXPECTED_AUDIENCE", "pilot-test-api")
            jwt_sub = "pilot-test-user"
            subs["jwt_hs256_valid"] = _jwt_token(jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts)
            subs["jwt_hs256_expired"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, expired=True)
            subs["jwt_hs256_bad_sig"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, wrong_secret=True)
            subs["jwt_hs256_wrong_aud"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, wrong_aud=True)

        write_ok, write_errors = (True, [])
        if file_blocks:
            write_ok, write_errors = _apply_file_blocks(file_blocks, wt)

        app_env = dict(secrets)
        if "DATABASE_URL" not in app_env:
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url:
                app_env["DATABASE_URL"] = db_url
        db_url_for_reset = app_env.get("DATABASE_URL", "")
        if db_url_for_reset:
            import asyncio
            asyncio.run(_reset_app_schema(db_url_for_reset))

        checks = fixture.get("mechanical_checks", [])
        needs_http = any(c["type"] in ("http", "app_starts") for c in checks)
        captured: dict[str, bytes] = {}
        mech_results: list[dict] = []

        app_started = False
        app_error = None
        if not checks:
            mech_pass = True
        elif needs_http:
            timeout_s = next(
                (c.get("timeout_s", 15.0) for c in checks if c["type"] == "app_starts"),
                15.0,
            )
            try:
                with app_process(wt, app_env, timeout_s=timeout_s) as base_url:
                    app_started = True
                    mech_pass, mech_results, captured = run_checks(
                        checks, base_url, subs, wt, task, trusted_host)
            except RuntimeError as e:
                app_error = str(e)
                mech_pass, mech_results, captured = run_checks(
                    checks, None, subs, wt, task, trusted_host)
        else:
            mech_pass, mech_results, captured = run_checks(
                checks, None, subs, wt, task, trusted_host)

        cross_pass, cross_results = run_cross_checks(fixture.get("cross_checks", []), captured)

        # Attach inline "actually" evidence to each mechanical result for reviewer
        _attach_evidence(mech_results, checks, captured, wt)

        out = {
            "trial_id": trial_id,
            "task": task, "arm": arm,
            "env_state": _capture_env_state(),
            "parse_warnings": parse_warnings,
            "decline_reasons": decline_reasons,
            "file_blocks": [{"path": p, "bytes": len(c)} for p, c in file_blocks],
            "write_errors": write_errors,
            "app_started": app_started,
            "app_error": app_error,
            "mechanical_results": mech_results,
            "mechanical_pass": mech_pass,
            "cross_results": cross_results,
            "cross_pass": cross_pass,
        }
        print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()

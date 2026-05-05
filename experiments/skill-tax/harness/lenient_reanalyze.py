#!/usr/bin/env python3
"""Post-hoc lenient parsing: re-evaluate trial responses by extracting
python code from markdown fences (when [FILE: <path>] markers are missing)
and writing to app/main.py — then re-run mechanical checks.

Goal: separate "model can do it but ignored format" from "model can't do it."

Usage:
    python lenient_reanalyze.py <trial_id_1> [<trial_id_2> ...]
    python lenient_reanalyze.py --all-m5            # all M5 trials with parses=False
    python lenient_reanalyze.py --since 2026-05-02  # by timestamp

Emits one JSON record per trial:
    {trial_id, lenient_parsed, lenient_functional_pass, code_chars, ...}
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from pathlib import Path

import duckdb
import yaml

HARNESS = Path(__file__).resolve().parent
PILOT = HARNESS.parent
sys.path.insert(0, str(HARNESS))
from run_trial import (  # noqa: E402
    _stripe_sig, _jwt_token, _reset_app_schema,
    git_worktree, app_process, run_checks, run_cross_checks,
)

DUCK = str(PILOT / "skills.duck")

# Match the largest python (or unlabeled) fenced block; ignore prose around it.
_FENCE_RE = re.compile(
    r"```(?:python|py)?[ \t]*\n(.*?)\n[ \t]*```",
    re.DOTALL,
)
_FILE_MARKER_RE = re.compile(r"^\[FILE:\s*(.+?)\s*\]$", re.MULTILINE)


def lenient_extract(response: str) -> tuple[list[tuple[str, str]], str]:
    """Try to recover (path, content) blocks from a response that lacked
    [FILE:] markers. Strategy: take the largest python fenced block and
    assume target=app/main.py. Returns (file_blocks, strategy_note)."""
    # If [FILE:] markers exist, do nothing (strict parser already handled it)
    if _FILE_MARKER_RE.search(response):
        return [], "had_file_marker_use_strict"

    fences = _FENCE_RE.findall(response)
    if not fences:
        return [], "no_fence_no_marker"
    # Use the largest fenced block — most likely the implementation
    longest = max(fences, key=len)
    if not longest.strip():
        return [], "empty_fence"
    if not longest.endswith("\n"):
        longest += "\n"
    return [("app/main.py", longest)], f"lenient:largest_fence_chars={len(longest)}"


def reverify(trial_id: str, conn) -> dict:
    row = conn.execute(
        "SELECT task_variation, retrieval_arm, response FROM pilot_trials WHERE trial_id = ?",
        [trial_id],
    ).fetchone()
    if not row:
        return {"trial_id": trial_id, "error": "not_found"}
    task, arm, response = row

    file_blocks, strategy = lenient_extract(response)
    if not file_blocks:
        return {
            "trial_id": trial_id, "task": task, "arm": arm,
            "lenient_parsed": False, "strategy": strategy,
        }

    fixture = yaml.safe_load((PILOT / "tasks" / f"{task}.yaml").read_text())
    seed_branch = fixture["app_skeleton"]["seed_branch"]

    with git_worktree(seed_branch) as wt:
        secrets = {}
        secrets_env = wt / "seed" / "test-secrets.env"
        if secrets_env.exists():
            for line in secrets_env.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    secrets[k.strip()] = v.strip()
        ts = int(time.time())
        body_bytes = b""
        fb_path = wt / "seed" / "fixtures" / "stripe-event.json"
        if fb_path.exists():
            body_bytes = fb_path.read_bytes()
        sw = secrets.get("STRIPE_WEBHOOK_SECRET", "")
        subs = {
            "stripe_signature": _stripe_sig(sw, body_bytes, ts),
            "stripe_signature_tampered": f"t={ts},v1={'0'*64}",
            "stripe_signature_stale": _stripe_sig(sw, body_bytes, ts - 600),
        }
        jwt_secret = secrets.get("JWT_HS256_SECRET", "")
        if jwt_secret:
            jwt_iss = secrets.get("JWT_EXPECTED_ISSUER", "pilot-test-issuer")
            jwt_aud = secrets.get("JWT_EXPECTED_AUDIENCE", "pilot-test-api")
            jwt_sub = "pilot-test-user"
            subs["jwt_hs256_valid"] = _jwt_token(jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts)
            subs["jwt_hs256_expired"] = _jwt_token(jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, expired=True)
            subs["jwt_hs256_bad_sig"] = _jwt_token(jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, wrong_secret=True)
            subs["jwt_hs256_wrong_aud"] = _jwt_token(jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, wrong_aud=True)

        # Write the lenient-extracted code
        for path, content in file_blocks:
            target = (wt / path).resolve()
            try:
                target.relative_to(wt.resolve())
            except ValueError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

        app_env = dict(secrets)
        if "DATABASE_URL" not in app_env:
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url:
                app_env["DATABASE_URL"] = db_url
        if app_env.get("DATABASE_URL"):
            import asyncio
            asyncio.run(_reset_app_schema(app_env["DATABASE_URL"]))

        checks = fixture.get("mechanical_checks", [])
        needs_http = any(c["type"] in ("http", "app_starts") for c in checks)
        captured = {}
        try:
            if needs_http:
                with app_process(wt, app_env, timeout_s=15.0) as base_url:
                    mech_pass, mech_results, captured = run_checks(
                        checks, base_url, subs, wt, task, "api.example.com")
            else:
                mech_pass, mech_results, captured = run_checks(
                    checks, None, subs, wt, task, "api.example.com")
            cross_pass, _ = run_cross_checks(fixture.get("cross_checks", []), captured)
        except Exception as e:
            return {"trial_id": trial_id, "task": task, "arm": arm,
                    "lenient_parsed": True, "strategy": strategy,
                    "error": str(e)}

        if mech_pass is False or cross_pass is False:
            fp = False
        elif mech_pass is None or cross_pass is None:
            fp = None
        else:
            fp = True

    return {
        "trial_id": trial_id, "task": task, "arm": arm,
        "lenient_parsed": True, "strategy": strategy,
        "lenient_functional_pass": fp,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("trial_ids", nargs="*")
    ap.add_argument("--since", help="ISO timestamp; trials with ran_at >= this")
    args = ap.parse_args()

    conn = duckdb.connect(DUCK)
    if args.since:
        rows = conn.execute(
            "SELECT trial_id FROM pilot_trials WHERE ran_at >= ? AND parses = false",
            [args.since],
        ).fetchall()
        ids = [r[0] for r in rows]
    else:
        ids = args.trial_ids

    print(f"Re-evaluating {len(ids)} trials with lenient parser...")
    results = []
    for i, tid in enumerate(ids, 1):
        r = reverify(tid, conn)
        results.append(r)
        if i % 10 == 0:
            print(f"  {i}/{len(ids)} done")

    out = Path("/tmp/m5_lenient_results.json")
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

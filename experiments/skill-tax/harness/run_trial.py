#!/usr/bin/env python3
"""Trial harness for the workflow-phase retrieval pilot (spec §6.3).

Usage:
    python run_trial.py --task T1 --arm arm_b [--run 1] \
        [--temperature 0.0] [--trial-class arm_comparison]

Required env:
    LM_STUDIO_BASE_URL    e.g. http://localhost:1234
    SKILLS_DUCK_PATH      path to skills.duck DuckDB file

Optional env:
    TIER2_MODEL           default: qwen3-coder-30b-a3b
    DATABASE_URL          required for tasks T2 / T3a / T3b
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import yaml

# pyjwt must be importable at startup — fail fast rather than on first T3b trial
try:
    import jwt as pyjwt
except ImportError as _jwt_exc:
    raise SystemExit(
        "pyjwt is required by the pilot harness; run: pip install pyjwt"
    ) from _jwt_exc

# ── repo + pilot layout ───────────────────────────────────────────────────────
# run_trial.py lives at experiments/skill-tax/harness/run_trial.py
REPO = Path(__file__).resolve().parents[3]   # repo root
PILOT = REPO / "experiments" / "skill-tax"

sys.path.insert(0, str(REPO / "src"))
from skillsmith.authoring.lm_client import OpenAICompatClient   # noqa: E402
from skillsmith.storage.vector_store import (                   # noqa: E402
    CompositionTrace,
    open_or_create,
)

# ── env ───────────────────────────────────────────────────────────────────────
LM_STUDIO_BASE_URL: str = os.environ["LM_STUDIO_BASE_URL"]
SKILLS_DUCK_PATH: str = os.environ["SKILLS_DUCK_PATH"]
TIER2_MODEL: str = os.environ.get("TIER2_MODEL", "qwen3-coder-30b-a3b")

# Check types that are always manual-only in v1; skipping them does not
# defer functional_pass. (db is wired externally; cross_checks are handled
# separately via run_cross_checks; diff is manual.)
_MANUAL_CHECK_TYPES = frozenset({"diff"})


# ── governance preamble ───────────────────────────────────────────────────────
def _load_preamble() -> str:
    raw = (PILOT / "prompts" / "governance-preamble-2026-05-01.v2.md").read_text()
    # strip YAML frontmatter: content is everything after the second "---"
    parts = raw.split("---", 2)
    return parts[2].strip() if len(parts) >= 3 else raw.strip()


# ── skill fragment loader ─────────────────────────────────────────────────────
def _load_skill(skill_id: str) -> dict[int, dict[str, Any]]:
    path = PILOT / "skills" / f"{skill_id}.yaml"
    data = yaml.safe_load(path.read_text())
    return {f["sequence"]: f for f in data.get("fragments", [])}


_skill_cache: dict[str, dict[int, dict[str, Any]]] = {}


def _get_fragment(skill_id: str, sequence: int) -> dict[str, Any]:
    if skill_id not in _skill_cache:
        _skill_cache[skill_id] = _load_skill(skill_id)
    frag = _skill_cache[skill_id].get(sequence)
    if frag is None:
        raise KeyError(f"fragment {skill_id}:{sequence} not found")
    return frag


def build_system_msg(
    fixture: dict[str, Any], arm: str
) -> tuple[str, list[str], str]:
    """Return (system_msg, fragment_ids, fragment_types_csv)."""
    preamble = _load_preamble()
    refs: list[dict[str, Any]] = fixture["arm_fragments"].get(arm, [])

    blocks: list[str] = []
    frag_ids: list[str] = []
    frag_types: list[str] = []
    for ref in refs:
        skill_id = ref["skill_id"]
        seq = int(ref["sequence"])
        frag = _get_fragment(skill_id, seq)
        ftype = frag.get("fragment_type", "unknown")
        content = frag.get("content", "")
        frag_id = f"{skill_id}:{seq}"
        frag_ids.append(frag_id)
        frag_types.append(ftype)
        blocks.append(f"<!-- fragment {frag_id} type={ftype} -->\n{content}")

    skill_section = "\n\n".join(blocks) if blocks else "(no fragments provided)"
    system_msg = f"{preamble}\n\n## Skill Fragments\n\n{skill_section}"
    return system_msg, frag_ids, ",".join(sorted(set(frag_types)))


# ── stripe / jwt helpers ──────────────────────────────────────────────────────
def _stripe_sig(secret: str, body: bytes, ts: int) -> str:
    signed = f"{ts}.".encode() + body
    digest = hmac.new(secret.encode(), signed, digestmod=hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _jwt_token(
    secret: str, sub: str, iss: str, aud: str, ts: int,
    *, expired: bool = False, wrong_secret: bool = False, wrong_aud: bool = False,
) -> str:
    sign_secret = "wrong-secret-skilltax-pilot-2026" if wrong_secret else secret
    actual_aud = "api://wrong-relying-party" if wrong_aud else aud
    exp = ts - 3600 if expired else ts + 300
    payload = {"sub": sub, "iss": iss, "aud": actual_aud,
                "iat": ts, "nbf": ts, "exp": exp}
    return pyjwt.encode(payload, sign_secret, algorithm="HS256")


# ── schema migration ──────────────────────────────────────────────────────────
def _ensure_schema(conn: Any) -> None:
    """Create pilot_trials table if it doesn't exist (once per DB file)."""
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'pilot_trials'"
    ).fetchone()
    if not (row and row[0] > 0):
        conn.execute((PILOT / "migrations" / "001_pilot_trials.sql").read_text())


async def _reset_app_schema(db_url: str) -> None:
    """Drop and recreate public schema in the pilot Postgres database.

    Runs before the app starts each trial so the lifespan's CREATE TABLE IF
    NOT EXISTS always sees a clean slate. DROP SCHEMA CASCADE handles cold-
    start (tables don't exist yet) and warm-start (leftover rows from prior
    trial) uniformly. Requires the pilot user to own the public schema.
    """
    import asyncpg  # conditional import — only present for DB tasks
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("DROP SCHEMA public CASCADE")
        await conn.execute("CREATE SCHEMA public")
        await conn.execute("GRANT ALL ON SCHEMA public TO pilot")
    finally:
        await conn.close()


# ── worktree / app management ─────────────────────────────────────────────────
@contextlib.contextmanager
def git_worktree(seed_branch: str):
    with tempfile.TemporaryDirectory(prefix="pilot-wt-") as tmp:
        wt = Path(tmp) / "wt"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt), seed_branch],
            check=True, capture_output=True, cwd=REPO,
        )
        try:
            yield wt
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt)],
                capture_output=True, cwd=REPO,
            )


@contextlib.contextmanager
def app_process(wt: Path, env: dict[str, str], timeout_s: float = 15.0):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    full_env = {**os.environ, **env}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=wt, env=full_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"uvicorn exited (rc={proc.returncode})")
            try:
                httpx.get(f"{base_url}/openapi.json", timeout=1.0)
                break
            except Exception:
                time.sleep(0.3)
        else:
            raise RuntimeError(f"app did not start within {timeout_s}s")
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ── check runners ─────────────────────────────────────────────────────────────
def _forbidden_present(text: str, forbidden: str) -> bool:
    # pyjwt pip package imports as "jwt"
    check = "jwt" if forbidden == "pyjwt" else forbidden
    parts = check.split(".", 1)
    module = parts[0]
    if len(parts) == 2:
        symbol = parts[1]
        from_pat = rf'^from\s+{re.escape(module)}\s+import\b.*\b{re.escape(symbol)}\b'
        return bool(
            re.search(from_pat, text, re.MULTILINE)
            or re.search(re.escape(check), text)
        )
    return bool(re.search(rf'^(?:import|from)\s+{re.escape(module)}\b', text, re.MULTILINE))


def run_checks(
    checks: list[dict[str, Any]],
    base_url: str | None,
    subs: dict[str, str],
    wt: Path,
    task_id: str,
    trusted_host: str,
) -> tuple[bool | None, list[dict[str, Any]], dict[str, bytes]]:
    """Run mechanical checks and return (pass_state, results, captured_bodies).

    pass_state is True (all passed), False (at least one failed), or None
    (at least one non-manual check was skipped — deferred to operator review).
    captured_bodies maps check_id → response bytes for cross_checks.
    """
    results: list[dict[str, Any]] = []
    captured_bodies: dict[str, bytes] = {}
    all_pass = True
    has_skipped = False  # non-manual check was skipped

    for chk in checks:
        ctype = chk["type"]
        cid = chk["id"]

        if ctype == "app_starts":
            passed = base_url is not None
            results.append({"id": cid, "pass": passed})
            if not passed:
                all_pass = False
            continue

        if ctype == "http":
            if base_url is None:
                results.append({"id": cid, "pass": False, "skip_reason": "app not running"})
                all_pass = False
                continue
            req = chk["request"]
            headers: dict[str, str] = {}
            for k, v in (req.get("headers") or {}).items():
                for var, val in subs.items():
                    v = v.replace(f"${{{var}}}", val)
                headers[k] = v
            # T3a/T3b: inject Host header so TrustedHostMiddleware sees the right value
            if task_id in ("T3a", "T3b"):
                headers.setdefault("Host", trusted_host)
            body: bytes | None = None
            if "body_fixture" in req:
                body = (wt / req["body_fixture"]).read_bytes()
            elif "body_inline" in req:
                inline = req["body_inline"]
                for var, val in subs.items():
                    inline = inline.replace(f"${{{var}}}", val)
                body = inline.encode()
            try:
                resp = httpx.request(
                    req["method"], f"{base_url}{req['path']}",
                    headers=headers, content=body, timeout=10.0,
                )
            except Exception as exc:
                results.append({"id": cid, "pass": False, "error": str(exc)})
                all_pass = False
                continue
            captured_bodies[cid] = resp.content
            exp = chk["expect"]
            status_ok = (
                resp.status_code == exp["status"] if "status" in exp
                else resp.status_code in exp["status_in"]
            )
            ok = status_ok
            if "body_json_matches" in exp:
                try:
                    rj = resp.json()
                    if not all(rj.get(k) == v for k, v in exp["body_json_matches"].items()):
                        ok = False
                except Exception:
                    ok = False
            if "headers_contains" in exp:
                for hname, hval in exp["headers_contains"].items():
                    if resp.headers.get(hname.lower()) != hval:
                        ok = False
                        break
            if "headers_does_not_contain" in exp:
                for hname, hval in exp["headers_does_not_contain"].items():
                    if resp.headers.get(hname.lower()) == hval:
                        ok = False
                        break
            if not ok:
                all_pass = False
            results.append({"id": cid, "pass": ok, "status": resp.status_code})
            continue

        if ctype == "code_grep":
            try:
                text = (wt / chk["file"]).read_text(errors="replace")
            except FileNotFoundError:
                results.append({"id": cid, "pass": False, "error": "file not found"})
                all_pass = False
                continue
            count = len(re.findall(chk["pattern"], text, re.MULTILINE))
            exp = chk["expect"]
            passed = True
            if "min_matches" in exp and count < exp["min_matches"]:
                passed = False
            if "max_matches" in exp and count > exp["max_matches"]:
                passed = False
            if not passed:
                all_pass = False
            results.append({"id": cid, "pass": passed, "count": count})
            continue

        if ctype == "diff_imports":
            try:
                text = (wt / chk["file"]).read_text(errors="replace")
            except FileNotFoundError:
                results.append({"id": cid, "pass": False, "error": "file not found"})
                all_pass = False
                continue
            exp = chk["expect"]
            passed = True
            for forbidden in exp.get("forbidden_imports", []):
                if _forbidden_present(text, forbidden):
                    passed = False
                    break
            if not passed:
                all_pass = False
            results.append({"id": cid, "pass": passed})
            continue

        if ctype in _MANUAL_CHECK_TYPES:
            # known manual in v1; skip without affecting pass state
            results.append({"id": cid, "pass": None, "skipped": True, "manual": True})
            continue

        # unrecognized / not yet wired (db, etc.) — defers functional_pass
        results.append({"id": cid, "pass": None, "skipped": True})
        has_skipped = True

    # Combine: a hard fail wins over a defer. Without this ordering, a deferred
    # non-manual check masks a failing http/code-grep check. (Found in M3 review:
    # T2's manual db check was deferring trials whose http checks were 500'ing.)
    if not all_pass:
        state: bool | None = False
    elif has_skipped:
        state = None
    else:
        state = True
    return state, results, captured_bodies


def run_cross_checks(
    cross_checks: list[dict[str, Any]],
    captured_bodies: dict[str, bytes],
) -> tuple[bool | None, list[dict[str, Any]]]:
    """Second pass: validate cross-check assertions using captured http bodies.

    Returns (pass_state, results) with the same None-deferred semantics as
    run_checks. body_bytes_match checks that named check_ids all returned
    byte-identical response bodies (anti-enumeration assertion).
    """
    results: list[dict[str, Any]] = []
    all_pass = True
    has_skipped = False

    for xchk in cross_checks:
        xtype = xchk["type"]
        xid = xchk["id"]

        if xtype == "body_bytes_match":
            check_ids: list[str] = xchk["check_ids"]
            missing = [cid for cid in check_ids if cid not in captured_bodies]
            if missing:
                results.append({"id": xid, "pass": None, "skipped": True,
                                 "missing_captures": missing})
                has_skipped = True
                continue
            bodies = [captured_bodies[cid] for cid in check_ids]
            passed = len(set(bodies)) == 1
            if not passed:
                all_pass = False
            results.append({"id": xid, "pass": passed})
            continue

        # unknown cross-check type — defer
        results.append({"id": xid, "pass": None, "skipped": True})
        has_skipped = True

    # Combine: a hard fail wins over a defer. Without this ordering, a deferred
    # non-manual check masks a failing http/code-grep check. (Found in M3 review:
    # T2's manual db check was deferring trials whose http checks were 500'ing.)
    if not all_pass:
        state: bool | None = False
    elif has_skipped:
        state = None
    else:
        state = True
    return state, results


# ── response normalization ────────────────────────────────────────────────────
_FILE_MARKER_RE = re.compile(r"^\[FILE:\s*(.+?)\s*\]$", re.MULTILINE)
_DECLINE_MARKER_RE = re.compile(r"^\[DECLINE:\s*(.+?)\s*\]$", re.MULTILINE)


def _parse_file_response(
    response: str,
) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """Parse [FILE: <path>] / [DECLINE: <reason>] markers from model response.

    Returns (files, declines, warnings).
      files    — list of (path, content) pairs, in document order
      declines — list of decline reason strings
      warnings — anomalies to log (unknown content outside markers, etc.)
    """
    warnings: list[str] = []
    files: list[tuple[str, str]] = []
    declines: list[str] = []

    # Collect all marker positions in document order
    positions: list[tuple[int, str, str]] = []  # (start, kind, value)
    for m in _FILE_MARKER_RE.finditer(response):
        positions.append((m.start(), "file", m.group(1)))
    for m in _DECLINE_MARKER_RE.finditer(response):
        positions.append((m.start(), "decline", m.group(1)))
    positions.sort(key=lambda x: x[0])

    if not positions:
        warnings.append("no_markers:response_contains_no_FILE_or_DECLINE_markers")
        return files, declines, warnings

    # Check for content before the first marker
    first_start = positions[0][0]
    before_first = response[:first_start].strip()
    if before_first:
        warnings.append(f"preamble_violation:{before_first[:120]!r}")

    # Extract file content: text between [FILE: path] marker and the next marker
    for i, (pos, kind, value) in enumerate(positions):
        if kind == "decline":
            declines.append(value)
            continue

        # kind == "file": content runs from end-of-line after marker to next marker (or EOF)
        line_end = response.index("\n", pos) + 1 if "\n" in response[pos:] else len(response)
        if i + 1 < len(positions):
            content_end = positions[i + 1][0]
        else:
            content_end = len(response)

        content = response[line_end:content_end]
        # strip trailing blank lines but preserve the final newline
        content = content.rstrip("\n")
        if content:
            content += "\n"
        files.append((value, content))

    # Check for content after the last marker's block (already handled by preamble check above)
    return files, declines, warnings


_FENCE_OPEN_RE = re.compile(r"^\s*```[ \t]*\w*[ \t]*\n", re.MULTILINE)
_FENCE_CLOSE_RE = re.compile(r"\n[ \t]*```[ \t]*$")


def _strip_fence(content: str) -> tuple[str, bool]:
    """Strip a single wrapping markdown code fence from file content, if present."""
    open_m = _FENCE_OPEN_RE.search(content)
    if not open_m:
        return content, False
    close_m = _FENCE_CLOSE_RE.search(content, open_m.end())
    if not close_m:
        return content, False
    inner = content[open_m.end() : close_m.start()]
    if not inner.endswith("\n"):
        inner += "\n"
    return inner, True


def _normalize_path(path: str) -> str:
    """Strip /workspace/ prefix and leading slashes; return repo-relative path."""
    if path.startswith("/workspace/"):
        path = path[len("/workspace/"):]
    elif path.startswith("/workspace"):
        path = path[len("/workspace"):]
    path = path.lstrip("/")
    return path


def _apply_file_blocks(
    files: list[tuple[str, str]], wt: Path
) -> tuple[bool, list[str]]:
    """Write [FILE: <path>] blocks to the worktree. Returns (success, errors)."""
    errors: list[str] = []
    for raw_path, content in files:
        rel_path = _normalize_path(raw_path)
        # Reject paths that escape the worktree
        target = (wt / rel_path).resolve()
        try:
            target.relative_to(wt.resolve())
        except ValueError:
            errors.append(f"path_escape:{raw_path!r}")
            continue
        content, fenced = _strip_fence(content)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return len(errors) == 0, errors


def _normalized_content(
    files: list[tuple[str, str]], declines: list[str]
) -> str:
    """Canonical string for consistency_hash: FILE blocks + DECLINE lines, document order."""
    parts: list[str] = []
    for path, content in files:
        parts.append(f"[FILE: {path}]\n{content}")
    for reason in declines:
        parts.append(f"[DECLINE: {reason}]")
    return "\n".join(parts)


# ── pilot_trials writer ───────────────────────────────────────────────────────
def _write_pilot_trial(
    conn: Any,
    trial_id: str,
    composition_id: str,
    fixture: dict[str, Any],
    arm: str,
    frag_ids: list[str],
    frag_types_csv: str,
    temperature: float,
    trial_class: str,
    prompt: str,
    response: str,
    parses: bool,
    functional_pass: bool | None,  # None = deferred (skipped checks)
    notes: str | None = None,
    normalized_content: str = "",
) -> None:
    hash_input = normalized_content if normalized_content else response
    consistency_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]
    conn.execute(
        """
        INSERT INTO pilot_trials (
            trial_id, composition_id, trial_class, task_variation,
            retrieval_arm, fragment_types, fragment_count, temperature,
            prompt, response, parses, functional_pass,
            faithfulness_pass, consistency_hash,
            failure_mode, failed_fragment, failure_root_cause, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,?,NULL,NULL,NULL,?)
        """,
        [
            trial_id, composition_id, trial_class,
            fixture["task_id"], arm, frag_types_csv,
            len(frag_ids), temperature, prompt, response,
            parses, functional_pass, consistency_hash, notes,
        ],
    )


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    _t_start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Skill-tax pilot trial runner")
    parser.add_argument("--task", required=True,
                        choices=["T1", "T2", "T3a", "T3b", "T4", "T5"])
    parser.add_argument("--arm", required=True,
                        choices=["arm_a", "arm_b", "arm_c", "baseline", "arm_b_plus"])
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--trial-class", default="arm_comparison",
                        choices=["arm_comparison", "baseline", "robustness"])
    args = parser.parse_args()

    fixture = yaml.safe_load((PILOT / "tasks" / f"{args.task}.yaml").read_text())
    seed_branch: str = fixture["app_skeleton"]["seed_branch"]

    system_msg, frag_ids, frag_types_csv = build_system_msg(fixture, args.arm)

    with git_worktree(seed_branch) as wt:
        # trusted host: T3b seed carries test-host-config.yaml; default for others
        host_cfg = wt / "seed" / "test-host-config.yaml"
        if host_cfg.exists():
            hdata = yaml.safe_load(host_cfg.read_text())
            trusted_host = hdata.get("trusted_hosts", ["api.example.com"])[0]
        else:
            trusted_host = "api.example.com"

        # load seed secrets
        secrets: dict[str, str] = {}
        secrets_env = wt / "seed" / "test-secrets.env"
        if secrets_env.exists():
            for line in secrets_env.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    secrets[k.strip()] = v.strip()

        # ts anchor — single read, frozen for all substitutions this trial
        ts = int(time.time())

        # stripe substitutions — body_bytes read directly from the fixture file
        # (no JSON round-trip) to match exactly what the http checks will send
        body_bytes = b""
        fixture_body = wt / "seed" / "fixtures" / "stripe-event.json"
        if fixture_body.exists():
            body_bytes = fixture_body.read_bytes()
        stripe_secret = secrets.get("STRIPE_WEBHOOK_SECRET", "")
        subs: dict[str, str] = {
            "stripe_signature": _stripe_sig(stripe_secret, body_bytes, ts),
            "stripe_signature_tampered": f"t={ts},v1={'0' * 64}",
            "stripe_signature_stale": _stripe_sig(stripe_secret, body_bytes, ts - 600),
        }

        # jwt substitutions (T3b)
        jwt_secret = secrets.get("JWT_HS256_SECRET", "")
        if jwt_secret:
            jwt_iss = secrets.get("JWT_EXPECTED_ISSUER", "pilot-test-issuer")
            jwt_aud = secrets.get("JWT_EXPECTED_AUDIENCE", "pilot-test-api")
            jwt_sub = "pilot-test-user"
            subs["jwt_hs256_valid"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts)
            subs["jwt_hs256_expired"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, expired=True)
            subs["jwt_hs256_bad_sig"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, wrong_secret=True)
            subs["jwt_hs256_wrong_aud"] = _jwt_token(
                jwt_secret, jwt_sub, jwt_iss, jwt_aud, ts, wrong_aud=True)

        # user message: /workspace is the literal mount point; do not substitute
        # M6 seed-injection: when SHOW_SEED=1, prepend the seed file contents
        # to the user message in a fenced block so the model can see what it's
        # supposed to preserve / extend. Files are listed in fixture seed_files.
        seed_block = ""
        if os.environ.get("SHOW_SEED") == "1":
            seed_files = fixture.get("app_skeleton", {}).get("seed_files", [])
            seed_parts = []
            for sf in seed_files:
                if not sf.endswith(".py"):
                    continue
                p = wt / sf
                if p.exists():
                    seed_parts.append(f"### `{sf}`\n```python\n{p.read_text().rstrip()}\n```")
            if seed_parts:
                seed_block = (
                    "## Existing seed files (preserve verbatim except where the "
                    "task explicitly directs otherwise)\n\n"
                    + "\n\n".join(seed_parts)
                    + "\n\n---\n\n"
                )

        user_msg = seed_block + fixture["description"]

        # model call
        lm = OpenAICompatClient(LM_STUDIO_BASE_URL)
        full_prompt = f"[SYSTEM]\n{system_msg}\n\n[USER]\n{user_msg}"
        _t_lm0 = time.perf_counter()
        # max_tokens=2048 caps runaway-loop trials. Legitimate trial outputs
        # observed empirically at 200-800 tokens; 2048 leaves safety margin
        # while preventing the 15+ min wall-time blowups seen on small Coders.
        call1_response, in_tok, out_tok = lm.chat_with_stats(
            model=TIER2_MODEL,
            system=system_msg,
            user=user_msg,
            temperature=args.temperature,
            max_tokens=2048,
        )
        _lm_ms = int((time.perf_counter() - _t_lm0) * 1000)

        # M8 self-QA two-call mode: when REVIEW_PASS=1, make a second LM call
        # asking the model to review its own output against the activated
        # fragments and revise. Verifier consumes the call-2 output.
        review_lm_ms = 0
        review_in_tok = 0
        review_out_tok = 0
        if os.environ.get("REVIEW_PASS") == "1":
            review_user_msg = (
                f"{user_msg}\n\n"
                "---\n\n"
                "## Self-review pass\n\n"
                "You produced the following initial implementation. Now review "
                "it against the activated skill fragments above before submitting.\n\n"
                "For each fragment in your context, check:\n"
                "1. Does the implementation use the procedures and primitives the "
                "fragment prescribes? (Compare verbatim where the fragment shows code.)\n"
                "2. Are there deviations the fragment would flag? Pay particular "
                "attention to any anti-pattern fragments — your code must not "
                "exhibit any of the documented bug patterns.\n"
                "3. Are status codes, error types, and parsing logic faithful to "
                "the fragment-specified shape?\n\n"
                "If you find deviations, emit a revised `[FILE: <path>]` block "
                "(using the locked output format from the system message) that "
                "fixes them. If you find none, emit the same `[FILE: <path>]` "
                "block unchanged. The verifier consumes whatever you emit in "
                "this turn — return only `[FILE: ...]` blocks (or `[DECLINE: ...]`), "
                "no other prose.\n\n"
                "## Initial implementation under review\n\n"
                "<<<INITIAL_IMPLEMENTATION_START>>>\n"
                f"{call1_response}\n"
                "<<<INITIAL_IMPLEMENTATION_END>>>\n\n"
                "Review now and produce the final `[FILE: <path>]` block(s)."
            )
            _t_lm1 = time.perf_counter()
            response_text, review_in_tok, review_out_tok = lm.chat_with_stats(
                model=TIER2_MODEL,
                system=system_msg,
                user=review_user_msg,
                temperature=args.temperature,
                max_tokens=2048,
            )
            review_lm_ms = int((time.perf_counter() - _t_lm1) * 1000)
        else:
            response_text = call1_response

        # parse [FILE: <path>] / [DECLINE: <reason>] markers
        file_blocks, decline_reasons, norm_warnings = _parse_file_response(response_text)

        # parses=True iff at least one valid FILE or DECLINE marker was found
        parses = bool(file_blocks or decline_reasons)

        # write file blocks to worktree
        if file_blocks:
            write_ok, write_errors = _apply_file_blocks(file_blocks, wt)
            if not write_ok:
                norm_warnings.extend(write_errors)
        if decline_reasons:
            norm_warnings.append(
                "scope_decline:" + "; ".join(decline_reasons)
            )

        norm_content = _normalized_content(file_blocks, decline_reasons)

        # build app env from seed secrets + optional external DATABASE_URL
        app_env = dict(secrets)
        if "DATABASE_URL" not in app_env:
            db_url = os.environ.get("DATABASE_URL", "")
            if db_url:
                app_env["DATABASE_URL"] = db_url

        # per-trial schema reset for DB-using tasks (spec §6.5: fresh schema per trial)
        db_url_for_reset = app_env.get("DATABASE_URL", "")
        if db_url_for_reset:
            import asyncio
            asyncio.run(_reset_app_schema(db_url_for_reset))

        # run mechanical checks
        checks = fixture.get("mechanical_checks", [])
        needs_http = any(c["type"] in ("http", "app_starts") for c in checks)
        captured: dict[str, bytes] = {}
        mech_results: list[dict[str, Any]] = []

        if not checks:
            mech_pass: bool | None = True
        elif needs_http:
            timeout_s = next(
                (c.get("timeout_s", 15.0) for c in checks if c["type"] == "app_starts"),
                15.0,
            )
            try:
                with app_process(wt, app_env, timeout_s=timeout_s) as base_url:
                    mech_pass, mech_results, captured = run_checks(
                        checks, base_url, subs, wt, args.task, trusted_host)
            except RuntimeError:
                # app failed to start — code_grep/diff_imports checks still run
                mech_pass, mech_results, captured = run_checks(
                    checks, None, subs, wt, args.task, trusted_host)
        else:
            mech_pass, mech_results, captured = run_checks(
                checks, None, subs, wt, args.task, trusted_host)

        # cross checks (second pass using captured http bodies)
        cross_pass, _ = run_cross_checks(fixture.get("cross_checks", []), captured)

        # combine: False wins; None propagates if neither is False
        if mech_pass is False or cross_pass is False:
            functional_pass: bool | None = False
        elif mech_pass is None or cross_pass is None:
            functional_pass = None
        else:
            functional_pass = True

        # write telemetry
        trial_id = str(uuid.uuid4())
        composition_id = str(uuid.uuid4())
        trace_status = (
            "functional_pass" if functional_pass is True
            else "functional_deferred" if functional_pass is None
            else "functional_fail"
        )

        with open_or_create(SKILLS_DUCK_PATH) as vs:
            _ensure_schema(vs._conn)
            _write_pilot_trial(
                vs._conn, trial_id, composition_id, fixture,
                args.arm, frag_ids, frag_types_csv,
                args.temperature, args.trial_class,
                full_prompt, response_text,
                parses, functional_pass,
                notes="; ".join(norm_warnings) if norm_warnings else None,
                normalized_content=norm_content,
            )
            vs.record_composition_trace(CompositionTrace(
                trace_id=composition_id,
                request_ts=ts,
                phase="build",
                task_prompt=user_msg,
                status=trace_status,
                selected_fragment_ids=frag_ids,
                source_skill_ids=list(fixture.get("skills_activated", [])),
                assembly_tier="2",
                assembly_model=TIER2_MODEL,
                retrieval_latency_ms=0,
                error_code="simulated-retrieval",
            ))

    _total_ms = int((time.perf_counter() - _t_start) * 1000)
    review_suffix = (
        f" review_lm_ms={review_lm_ms} review_in_tok={review_in_tok} "
        f"review_out_tok={review_out_tok}"
        if os.environ.get("REVIEW_PASS") == "1"
        else ""
    )
    print(
        f"trial={trial_id} task={args.task} arm={args.arm} run={args.run} "
        f"parses={parses} functional_pass={functional_pass} "
        f"frags={len(frag_ids)} in_tok={in_tok} out_tok={out_tok} "
        f"lm_ms={_lm_ms} total_ms={_total_ms}{review_suffix}"
    )


if __name__ == "__main__":
    main()

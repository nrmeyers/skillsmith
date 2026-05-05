#!/usr/bin/env python3
"""Generate milestone-3 trial review markdown files."""
from __future__ import annotations
import json, pathlib, re
import duckdb, yaml

PILOT = pathlib.Path("experiments/skill-tax")
REVIEWS = PILOT / "reviews"

TRIALS = [
    # batch 1
    "5d9ac3a7-5171-40da-857e-b961e717f98f",  # T1 arm_b run=1 PASS
    "db58e966-a249-41c7-84dc-54a395c6541c",  # T1 baseline run=1 DECLINED
    "9656c3ec-80b6-4203-9677-a622d406488e",  # T3a arm_a run=1 FAIL
    "4941d5ad-4a92-422c-a883-ac941a4e98c4",  # T3b arm_a run=1 FAIL
    "d0459cf8-a4ce-4ac3-a5d0-5a0780b87a48",  # T4 arm_b run=1 FAIL
    # batch 2 — uniformity check + T4 arm-split characterization
    "5bceb13a-3c14-462a-a72e-14dc124c7f1c",  # T3a arm_a run=2
    "08974993-a795-4975-9e75-8c067624eb4e",  # T3a arm_a run=3
    "cc2253b7-4f1d-4803-acb3-beecbcc96a83",  # T3a arm_b run=1
    "8645abe8-e6eb-49e2-af2f-01c309cc8619",  # T3a arm_c run=1
    "f5625207-6f61-4f36-babf-b862f00fcbb9",  # T3b arm_a run=2
    "636d368f-12dc-40b6-bc7f-3275f7290b3c",  # T3b arm_a run=3
    "d5a8fc9e-d1a5-40a4-96fe-fb2be87632a2",  # T3b arm_b run=1
    "a0637198-1f44-43b6-b85d-f3b517439765",  # T3b arm_c run=1
    "99fd5da3-f688-4eb9-a2e6-ed5799696b94",  # T4  arm_b run=2
    "13ce8a7a-8255-42a6-b301-c826f167a02d",  # T4  arm_c run=1
    "009ff9ae-bd61-4961-861f-e2e9f5865b55",  # T4  arm_c run=2
]

# Per-task keywords for §3a "Relevant fragment excerpts" extraction.
# Goal: surface fragments that bear directly on the failure hypothesis
# so reviewer can judge under_specified_procedure vs scope_guard_too_weak
# without opening fragment files.
TASK_FRAGMENT_KEYWORDS = {
    "T3a": ["lifespan", "asynccontextmanager", "on_event",
            "create_pool", "create table", "preserve", "existing",
            "do not modify", "scope"],
    "T3b": ["lifespan", "asynccontextmanager", "on_event",
            "create_pool", "create table", "preserve", "existing",
            "do not modify", "scope"],
    "T4":  ["compare_digest", "constant time", "constant-time",
            "hmac.compare", "timing", "secrets.compare",
            "stripe.webhook", "construct_event"],
}

# Fragment types treated as required by default (per milestone-3 batch-1 feedback)
REQUIRED_TYPES = {"procedure", "guardrail", "contract", "interface", "execution"}

CHECK_ICONS = {True: "✅", False: "❌", None: "⏭"}


def fmt_check_result(r: dict) -> tuple[str, str]:
    """Return (icon, observed_text) for a check result."""
    p = r.get("pass")
    icon = CHECK_ICONS.get(p, "?")
    parts = []
    for k in ("status","count","skip_reason","manual","skipped","error","missing_captures"):
        if k in r and r[k] is not None and r[k] != "":
            parts.append(f"{k}={r[k]}")
    return icon, "; ".join(parts) if parts else "—"


def fmt_check_expected(chk: dict) -> str:
    t = chk["type"]
    exp = chk.get("expect", {})
    if t == "app_starts":
        return f"app reachable on /openapi.json within {chk.get('timeout_s',15)}s"
    if t == "http":
        bits = []
        if "status" in exp: bits.append(f"status={exp['status']}")
        if "status_in" in exp: bits.append(f"status∈{exp['status_in']}")
        if "body_json_matches" in exp: bits.append(f"body_json⊇{exp['body_json_matches']}")
        if "headers_contains" in exp: bits.append(f"hdrs⊇{exp['headers_contains']}")
        if "headers_does_not_contain" in exp: bits.append(f"hdrs∌{exp['headers_does_not_contain']}")
        return f"{chk['request']['method']} {chk['request']['path']} → " + ", ".join(bits)
    if t == "code_grep":
        bits = []
        if "min_matches" in exp: bits.append(f"≥{exp['min_matches']}")
        if "max_matches" in exp: bits.append(f"≤{exp['max_matches']}")
        return f"`{chk['pattern']}` in `{chk['file']}` " + " ".join(bits)
    if t == "diff_imports":
        return f"`{chk['file']}` forbidden: {exp.get('forbidden_imports',[])}"
    if t == "diff":
        return "(manual diff review)"
    return f"({t})"


def parse_fragments_from_prompt(prompt: str) -> list[dict]:
    """Extract fragments listed in the system message of the prompt."""
    pattern = re.compile(
        r"<!-- fragment\s+([\w\-/]+):(\d+)\s+type=([\w_]+)\s*-->\n(.*?)(?=\n<!-- fragment |\Z)",
        re.DOTALL,
    )
    out = []
    for m in pattern.finditer(prompt):
        skill, seq, ftype, content = m.groups()
        out.append({
            "skill": skill, "seq": int(seq), "type": ftype,
            "content": content.strip(),
        })
    return out


def first_chars(s: str, n: int = 80) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) > n:
        s = s[:n] + "…"
    return s


def render_relevant_excerpts(task: str, fragments: list[dict]) -> str:
    """Section 3a: full text of fragments containing failure-relevant keywords."""
    keywords = TASK_FRAGMENT_KEYWORDS.get(task, [])
    if not keywords or not fragments:
        return ""
    relevant: list[tuple[dict, list[str]]] = []
    for f in fragments:
        content_lower = f["content"].lower()
        hit = [kw for kw in keywords if kw.lower() in content_lower]
        if hit:
            relevant.append((f, hit))
    if not relevant:
        return ("## 3a. Relevant fragment excerpts\n\n"
                f"_Searched fragments for keywords: `{', '.join(keywords)}`. "
                "No fragments matched; the failure-mode hypothesis cannot be "
                "evaluated against fragment content directly. This itself is "
                "evidence — fragments did not address the failure surface._\n\n")
    md = "## 3a. Relevant fragment excerpts\n\n"
    md += (f"_Fragments containing failure-relevant keywords "
           f"(`{', '.join(keywords)}`). Surfaced verbatim so reviewer can "
           "judge `under_specified_procedure` vs `scope_guard_too_weak` "
           "without opening fragment files._\n\n")
    for f, hits in relevant:
        md += f"### `{f['skill']}:{f['seq']}` (`{f['type']}`)  matched: {', '.join('`'+h+'`' for h in hits)}\n\n"
        md += "```\n" + f["content"].strip() + "\n```\n\n"
    return md


def render_review(trial: dict, rerun: dict, fixture: dict) -> str:
    tid = trial["trial_id"]
    fp = trial["functional_pass"]
    fp_str = "True" if fp is True else "False" if fp is False else "None (deferred)"
    parses_str = "True" if trial["parses"] else "False"
    notes = trial["notes"] or "none"
    in_tok, out_tok = "—", "—"
    # Token counts aren't in pilot_trials; pull from prompt length as approx, or omit
    fragments = parse_fragments_from_prompt(trial["prompt"])

    # Header
    md = f"# Trial Review — `{tid}`\n\n"
    md += "## 1. Header\n\n"
    md += "| Field | Value |\n|-------|-------|\n"
    md += f"| trial_id | `{tid}` |\n"
    md += f"| task | `{trial['task']}` |\n"
    md += f"| arm | `{trial['arm']}` |\n"
    md += f"| trial_class | `{trial['trial_class']}` |\n"
    md += f"| temperature | `{trial['temperature']}` |\n"
    md += f"| parses | `{parses_str}` |\n"
    md += f"| functional_pass | `{fp_str}` |\n"
    md += f"| fragment_count | `{trial['fragment_count']}` |\n"
    md += f"| consistency_hash | `{trial['consistency_hash']}` |\n"
    md += f"| harness notes | {notes if notes == 'none' else '`'+notes[:160]+('…' if len(notes)>160 else '')+'`'} |\n\n"

    # Task description
    desc = fixture["description"].rstrip()
    md += "## 2. Task description\n\n"
    md += "```\n" + desc + "\n```\n\n"

    # Fragments
    md += "## 3. Fragments provided\n\n"
    if not fragments:
        md += "_No fragments — baseline arm._\n\n"
    else:
        md += "| # | fragment_id | type | first 80 chars |\n|---|-------------|------|----------------|\n"
        for i, f in enumerate(fragments, 1):
            md += f"| {i} | `{f['skill']}:{f['seq']}` | `{f['type']}` | {first_chars(f['content'])} |\n"
        md += "\n"

    # Section 3a: relevant fragment excerpts (task-specific keyword scan)
    md += render_relevant_excerpts(trial["task"], fragments)

    # Model response
    md += "## 4. Model response\n\n"
    md += "```\n" + trial["response"].rstrip() + "\n```\n\n"

    # Mechanical checks
    md += "## 5. Mechanical check results\n\n"
    md += f"_Re-run via `harness/rerun_checks.py {tid}`. App started: "
    md += f"`{rerun.get('app_started')}`._\n\n"
    env = rerun.get("env_state") or {}
    if env:
        md += f"_Rerun env: ran_at=`{env.get('ran_at_utc','?')}`, "
        md += f"DATABASE_URL_set=`{env.get('DATABASE_URL_set_in_os_env')}`, "
        md += f"postgres_reachable=`{env.get('postgres_reachable_at_rerun_time')}`._\n\n"
    md += "| check_id | type | result | observed | actually wrote | expected |\n"
    md += "|----------|------|--------|----------|----------------|----------|\n"
    fixture_checks = {c["id"]: c for c in fixture.get("mechanical_checks", [])}
    for r in rerun.get("mechanical_results", []):
        cid = r["id"]
        chk = fixture_checks.get(cid, {})
        ctype = chk.get("type", "?")
        icon, obs = fmt_check_result(r)
        actually = (r.get("actually") or "—").replace("|", "\\|")
        exp = fmt_check_expected(chk) if chk else "—"
        md += f"| `{cid}` | `{ctype}` | {icon} | {obs} | {actually} | {exp} |\n"
    md += "\n"

    # Cross-checks
    cross_results = rerun.get("cross_results") or []
    cross_defs = {c["id"]: c for c in fixture.get("cross_checks", [])}
    if cross_results or fixture.get("cross_checks"):
        md += "Cross-checks:\n\n"
        md += "| cross_id | type | result | notes |\n|----------|------|--------|-------|\n"
        for r in cross_results:
            cid = r["id"]
            cdef = cross_defs.get(cid, {})
            icon, obs = fmt_check_result(r)
            md += f"| `{cid}` | `{cdef.get('type','?')}` | {icon} | {obs or '—'} |\n"
        md += "\n"

    # Faithfulness
    md += "## 6. Faithfulness checklist\n\n"
    if not fragments:
        decline_reasons = rerun.get("decline_reasons") or []
        if decline_reasons:
            md += "_Model declined; no fragments to check._\n\n"
            md += "**Decline reason(s):**\n\n"
            for r in decline_reasons:
                md += f"- `{r}`\n"
            md += "\n"
        else:
            md += "_No fragments — baseline arm. Model attempted implementation without fragment guidance._\n\n"
    else:
        md += "| # | fragment_id | type | required_for_task | model_used_it | evidence (reviewer fills) |\n"
        md += "|---|-------------|------|-------------------|---------------|----------------------------|\n"
        for i, f in enumerate(fragments, 1):
            req = "yes" if f["type"] in REQUIRED_TYPES else "?"
            md += f"| {i} | `{f['skill']}:{f['seq']}` | `{f['type']}` | `{req}` | ☐ yes  ☐ no  ☐ n-r-b-p |  |\n"
        md += "\n"
        md += "_`required_for_task` column pre-filled by heuristic (procedure/guardrail/contract/interface/execution = yes; rationale/example/setup/verification = ?). Reviewer should override `?` cells based on task variant._\n\n"

    # Failure summary
    md += "## 7. Failure summary\n\n"
    if fp is True:
        md += "_Trial passed all mechanical checks. Faithfulness review only._\n\n"
    else:
        # Build factual summary of which checks failed
        failed_mech = [r for r in rerun.get("mechanical_results", []) if r.get("pass") is False]
        failed_cross = [r for r in cross_results if r.get("pass") is False]
        skipped = [r for r in rerun.get("mechanical_results", []) if r.get("pass") is None]
        if not failed_mech and not failed_cross and skipped:
            md += "**Mechanical state: deferred.** No checks failed outright; one or more non-manual checks were skipped (the harness flags this as `functional_pass=None`).\n\n"
            md += "Skipped check IDs: " + ", ".join(f"`{r['id']}`" for r in skipped) + "\n\n"
        else:
            md += "**Failed checks:**\n\n"
            for r in failed_mech + failed_cross:
                cid = r["id"]
                chk = fixture_checks.get(cid) or cross_defs.get(cid, {})
                _, obs = fmt_check_result(r)
                exp = fmt_check_expected(chk) if chk else "—"
                md += f"- `{cid}`: observed `{obs}`, expected `{exp}`\n"
            if rerun.get("decline_reasons"):
                md += f"\n**Decline marker(s) emitted alongside response:**\n"
                for r in rerun["decline_reasons"]:
                    md += f"- `{r}`\n"
            md += "\n"

    # Tagging slots
    md += "## 8. Tagging slots — reviewer fills\n\n"
    md += "```\n"
    md += "failure_mode:\n"
    md += "  [ ] drift              [ ] hallucination     [ ] incomplete\n"
    md += "  [ ] scope_violation    [ ] parse_error       [ ] wrong_skill\n"
    md += "  [ ] composition_error  [ ] n/a (passed)\n\n"
    md += "failure_root_cause:\n"
    md += "  [ ] under_specified_procedure  [ ] missing_rationale\n"
    md += "  [ ] missing_example            [ ] missing_setup\n"
    md += "  [ ] verification_false_pass    [ ] scope_guard_too_weak\n"
    md += "  [ ] composition_gap            [ ] composition_overlap\n"
    md += "  [ ] model_capability           [ ] n/a (passed)\n\n"
    md += "faithfulness_pass:\n"
    md += "  [ ] yes  [ ] no  [ ] partial\n\n"
    md += "failed_fragment:\n"
    md += "  [ ] none  [ ] <skill:seq>  [ ] multiple  [ ] unattributable\n"
    md += "```\n\n"

    md += "## 9. Reviewer notes\n\n_(free text)_\n"
    return md


def main() -> None:
    conn = duckdb.connect(str(PILOT / "skills.duck"))
    REVIEWS.mkdir(parents=True, exist_ok=True)
    for tid in TRIALS:
        row = conn.execute("""
            SELECT trial_id, trial_class, task_variation, retrieval_arm,
                   fragment_types, fragment_count, temperature, prompt, response,
                   parses, functional_pass, consistency_hash, notes
            FROM pilot_trials WHERE trial_id = ?
        """, [tid]).fetchone()
        trial = {
            "trial_id": row[0], "trial_class": row[1], "task": row[2], "arm": row[3],
            "fragment_types": row[4], "fragment_count": row[5], "temperature": row[6],
            "prompt": row[7], "response": row[8], "parses": row[9],
            "functional_pass": row[10], "consistency_hash": row[11], "notes": row[12],
        }
        rerun = json.load(open(f"/tmp/m3_{tid}.json"))
        fixture = yaml.safe_load((PILOT / "tasks" / f"{trial['task']}.yaml").read_text())
        md = render_review(trial, rerun, fixture)
        out_path = REVIEWS / f"{tid}.md"
        out_path.write_text(md)
        print(f"wrote {out_path}  ({len(md)} bytes)")


if __name__ == "__main__":
    main()

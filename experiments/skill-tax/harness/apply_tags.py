#!/usr/bin/env python3
"""Apply milestone-3 review tags to pilot_trials.

Each tag application includes failure_mode, failure_root_cause,
faithfulness_pass, and failed_fragment. Uses parameterized UPDATEs
so trial_ids are validated against the table.

Run idempotently — re-running with the same args overwrites the same
fields. To audit changes, query before/after.
"""
from __future__ import annotations
import sys
import duckdb

DUCK = "experiments/skill-tax/skills.duck"


def apply(conn, trial_ids: list[str], failure_mode: str | None,
          root_cause: str | None, faith: bool | None,
          failed_fragment: str | None, note: str) -> int:
    """Update tags. failure_mode='' / None → set to NULL. faith=None → NULL."""
    n = 0
    for tid in trial_ids:
        existing = conn.execute(
            "SELECT notes FROM pilot_trials WHERE trial_id = ?", [tid]
        ).fetchone()
        if not existing:
            print(f"  WARN: trial not found: {tid}")
            continue
        prev_notes = existing[0] or ""
        # Append review note, separated by '|', if not already present
        if note and note not in prev_notes:
            new_notes = (prev_notes + " | " + note) if prev_notes else note
        else:
            new_notes = prev_notes
        conn.execute("""
            UPDATE pilot_trials
            SET failure_mode = ?,
                failure_root_cause = ?,
                faithfulness_pass = ?,
                failed_fragment = ?,
                notes = ?
            WHERE trial_id = ?
        """, [failure_mode, root_cause, faith, failed_fragment, new_notes, tid])
        n += 1
    return n


def main() -> None:
    conn = duckdb.connect(DUCK)

    # ── BATCH 2 APPROVED TAGS ────────────────────────────────────────────────

    # T3a (9) + T3b arm_b (3): scope_violation / under_specified_procedure
    set_a = [
        # T3a all 9
        "9656c3ec-80b6-4203-9677-a622d406488e", "5bceb13a-3c14-462a-a72e-14dc124c7f1c",
        "08974993-a795-4975-9e75-8c067624eb4e",
        "cc2253b7-4f1d-4803-acb3-beecbcc96a83", "fdcf9d21-59ab-4d67-92ff-9b5f93dfc2d8",
        "0ad5dd6a-46a3-4bb3-96c1-1d317c588c65",
        "8645abe8-e6eb-49e2-af2f-01c309cc8619", "0560c4a6-fcfd-40ab-8d0e-97ff270f8cc5",
        "8fb394a4-9513-4cb4-847e-b0195302dd7d",
        # T3b arm_b (3)
        "d5a8fc9e-d1a5-40a4-96fe-fb2be87632a2", "f948aa97-9f7d-4ea3-ba9e-ee307ee912c8",
        "6ce5b42f-4930-4d4f-827c-467c846dcf26",
    ]
    n = apply(conn, set_a, "scope_violation", "under_specified_procedure", False,
              "fastapi-middleware-patterns:2_or_:6",
              "m3:lifespan_rewrite_via_fragment_template")
    print(f"set_a (T3a 9 + T3b arm_b 3): tagged {n}/12")

    # T3b arm_a (3): scope_violation / model_capability / unattributable
    set_b = [
        "4941d5ad-4a92-422c-a883-ac941a4e98c4",
        "f5625207-6f61-4f36-babf-b862f00fcbb9",
        "636d368f-12dc-40b6-bc7f-3275f7290b3c",
    ]
    n = apply(conn, set_b, "scope_violation", "model_capability", False,
              "unattributable",
              "m3:empty_yield_lifespan_with_24_frags_explicit_instr")
    print(f"set_b (T3b arm_a 3): tagged {n}/3")

    # T3b arm_c (3): scope_violation / under_specified_procedure / fmp:6
    set_c = [
        "a0637198-1f44-43b6-b85d-f3b517439765",
        "cbb71fb8-2f6c-4475-8871-bd8bd2fad755",
        "0463b68c-ac3e-4f8f-baf4-88a19e45752c",
    ]
    n = apply(conn, set_c, "scope_violation", "under_specified_procedure", False,
              "fastapi-middleware-patterns:6",
              "m3:placeholder_lifespan_app.state.db_eq_None")
    print(f"set_c (T3b arm_c 3): tagged {n}/3")

    # T4 arm_b/arm_c (6): scope_violation / composition_gap
    set_d = [
        # arm_b
        "d0459cf8-a4ce-4ac3-a5d0-5a0780b87a48", "99fd5da3-f688-4eb9-a2e6-ed5799696b94",
        "68911c34-453e-449b-b2bc-21ef30f7abf1",
        # arm_c
        "13ce8a7a-8255-42a6-b301-c826f167a02d", "009ff9ae-bd61-4961-861f-e2e9f5865b55",
        "3d440972-d346-4edd-b8bc-0c92d8a6db4d",
    ]
    n = apply(conn, set_d, "scope_violation", "composition_gap", False,
              "webhook-patterns:1_or_:6",
              "m3:wholesale_rewrite_when_targeted_refactor_asked")
    print(f"set_d (T4 arm_b/c 6): tagged {n}/6")

    conn.close()


if __name__ == "__main__":
    main()

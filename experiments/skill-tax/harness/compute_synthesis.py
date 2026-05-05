#!/usr/bin/env python3
"""Compute aggregate metrics for milestone-3 final synthesis."""
import duckdb, json
from collections import Counter, defaultdict

# Official 81 trial_ids (excluding Q10/smoke calibration)
OFFICIAL = {
    # Arm comparison — 54
    "arm_comparison": {
        "T1": {"arm_a": ["ed55906a-09fc-4a56-aafa-1f99b3c93e0c","97ba1647-bcb3-48e7-bacb-6d3be30a9526","bc68a744-f2f8-403b-becb-4c49873824e6"],
               "arm_b": ["5d9ac3a7-5171-40da-857e-b961e717f98f","3571f264-86c8-4303-aa03-b89c532c26a7","11e0dc83-8aae-4bd0-8c8c-63b8379bb7d2"],
               "arm_c": ["a801a292-c85d-4e3a-b559-b2b7fb53d0da","7a396af0-3a91-4554-9da3-8fcffd433268","46bd10ca-ed92-4382-bfa9-59e35d428b0a"]},
        "T2": {"arm_a": ["44e5348a-2487-4f62-a7e2-d1ba90a72d72","fdfbbd42-7553-45b0-977c-aaf68f8f7393","c136f6bb-cf3a-44c1-9412-e7ea97bdeba1"],
               "arm_b": ["ea5fccc6-c831-4e61-9333-88bb0c67a9d3","7d64b4f2-e534-45c1-99b5-8af55bf5f474","2b6891fe-29b3-4a64-98ed-fd3e20ff764a"],
               "arm_c": ["46a5f864-3111-4b4e-9c0c-88ca9daf9442","1efbb4cf-6196-47af-8dc3-e86253ba5a71","b34a0dad-994d-45b8-af35-c93fc28d53ef"]},
        "T3a": {"arm_a": ["9656c3ec-80b6-4203-9677-a622d406488e","5bceb13a-3c14-462a-a72e-14dc124c7f1c","08974993-a795-4975-9e75-8c067624eb4e"],
                "arm_b": ["cc2253b7-4f1d-4803-acb3-beecbcc96a83","fdcf9d21-59ab-4d67-92ff-9b5f93dfc2d8","0ad5dd6a-46a3-4bb3-96c1-1d317c588c65"],
                "arm_c": ["8645abe8-e6eb-49e2-af2f-01c309cc8619","0560c4a6-fcfd-40ab-8d0e-97ff270f8cc5","8fb394a4-9513-4cb4-847e-b0195302dd7d"]},
        "T3b": {"arm_a": ["4941d5ad-4a92-422c-a883-ac941a4e98c4","f5625207-6f61-4f36-babf-b862f00fcbb9","636d368f-12dc-40b6-bc7f-3275f7290b3c"],
                "arm_b": ["d5a8fc9e-d1a5-40a4-96fe-fb2be87632a2","f948aa97-9f7d-4ea3-ba9e-ee307ee912c8","6ce5b42f-4930-4d4f-827c-467c846dcf26"],
                "arm_c": ["a0637198-1f44-43b6-b85d-f3b517439765","cbb71fb8-2f6c-4475-8871-bd8bd2fad755","0463b68c-ac3e-4f8f-baf4-88a19e45752c"]},
        "T4": {"arm_a": ["517da856-c895-4354-8f76-c228fd82dce2","c5358b7d-a7fa-47aa-8b71-53dfead72f92","8eb268ed-d3f9-48ef-9940-0bbf95d45da5"],
               "arm_b": ["d0459cf8-a4ce-4ac3-a5d0-5a0780b87a48","99fd5da3-f688-4eb9-a2e6-ed5799696b94","68911c34-453e-449b-b2bc-21ef30f7abf1"],
               "arm_c": ["13ce8a7a-8255-42a6-b301-c826f167a02d","009ff9ae-bd61-4961-861f-e2e9f5865b55","3d440972-d346-4edd-b8bc-0c92d8a6db4d"]},
        "T5": {"arm_a": ["2875ee2d-1e97-4e4e-a0fc-2cdb29cce1c2","b767761f-2b16-4338-8a61-9e67f476669d","fe76477e-aa74-4b12-bd44-84052bd2a490"],
               "arm_b": ["6a08d2f1-1ee3-47a8-94cf-7112f7a34ec9","c32c1d84-f229-4f12-96b3-f8a15a875f05","48d2a645-9608-4508-abf3-2bc4fb0761eb"],
               "arm_c": ["e303ff82-f6c4-4fbe-beed-354970a0ac49","589659de-ee97-44e1-a854-5bf214fca6d2","6d3d5940-7683-4954-9934-068cb1efb89a"]},
    },
    "baseline": {
        "T1":  ["db58e966-a249-41c7-84dc-54a395c6541c","0fb1b2ff-72ad-4f2a-b089-601d94a0bb06","ab0b4323-12f2-4e41-8fb9-6dcdf80d8a89"],
        "T2":  ["09af0864-79d2-4afc-9dcc-bebc288b1df3","66961e2f-c601-470a-bb95-e308781e16ed","5196c1f4-09f4-42e3-8d1d-de8c4939c39e"],
        "T3a": ["8eef02b4-c7d4-4f20-a2ef-bf0198206c61","f8a6ea50-5b29-407f-b7b8-aa9c1fe23136","a31b418f-a97c-4448-aeea-a74f18b2808e"],
        "T3b": ["9efd295d-ad5b-4a00-b902-b38f9c2cb1df","00b69e4f-fdb7-4424-8b59-1a82013da6a7","c05cb763-3725-4617-8132-94f120311672"],
    },
    "robustness": {
        "T1":  ["fc1a38b6-a7f0-4798-8aaf-2752fcc87bf0","7769d675-c202-48a4-94a3-6452a23e1694","49c2acbe-c214-417f-9689-bb4845fead3f","1e28fb5c-e2b2-49d6-aec8-232dce152b0f","d76d42bb-25ba-4339-86c6-cd6e1f52d856"],
        "T3a": ["9cac8b02-b023-4bdb-ba23-2ff606a645bb","06cc60a7-1132-4773-90b1-0baaee6f903d","773ec3d6-c352-4087-8a99-18767507b6e6","b19433b7-381b-42ee-b7e8-432f9b9c03c6","7e5b5ad9-c864-4d37-a553-0edff6d99dd5"],
        "T3b": ["1821df6d-5a7e-4e91-bb5d-0be6876be62e","c4f8eb15-c9eb-4b66-85ce-455298ef0e25","85a6ee17-1e03-4828-8267-db47d75effb3","afb62c80-057b-4c64-9087-5ab225c4c025","9b5b0bf6-ff5b-40b1-a073-b54deb9ef8ff"],
    },
}

ALL_OFFICIAL = []
for task, arms in OFFICIAL["arm_comparison"].items():
    for arm, ids in arms.items():
        for tid in ids:
            ALL_OFFICIAL.append((tid, "arm_comparison", task, arm))
for task, ids in OFFICIAL["baseline"].items():
    for tid in ids:
        ALL_OFFICIAL.append((tid, "baseline", task, "baseline"))
for task, ids in OFFICIAL["robustness"].items():
    for tid in ids:
        ALL_OFFICIAL.append((tid, "robustness", task, "arm_b"))

assert len(ALL_OFFICIAL) == 81, f"expected 81, got {len(ALL_OFFICIAL)}"
print(f"Loaded {len(ALL_OFFICIAL)} official trials")

conn = duckdb.connect("experiments/skill-tax/skills.duck")
ph = ",".join("?" for _ in ALL_OFFICIAL)
ids = [t[0] for t in ALL_OFFICIAL]
rows = conn.execute(f"""
    SELECT trial_id, trial_class, task_variation, retrieval_arm,
           parses, functional_pass, faithfulness_pass,
           failure_mode, failure_root_cause, failed_fragment,
           fragment_count
    FROM pilot_trials WHERE trial_id IN ({ph})
""", ids).fetchall()

cols = ["tid","tc","task","arm","parses","fp","faith","fm","frc","ff","fcount"]
data = [dict(zip(cols,r)) for r in rows]
print(f"Pulled {len(data)} rows")

def fp_pass(r):
    """Definition of pass for aggregate metrics. T5 inverted-criterion is excluded
    from arm-comparison because fragment_count=0 makes T5 retrieval-content-empty."""
    return r["fp"] is True

# === H1: Arm B pass rate across arm_comparison (excl. T5 per spec §7.3 footnote) ===
ac_excl_t5 = [r for r in data if r["tc"]=="arm_comparison" and r["task"]!="T5"]
arm_b_excl_t5 = [r for r in ac_excl_t5 if r["arm"]=="arm_b"]
arm_b_pass = sum(1 for r in arm_b_excl_t5 if fp_pass(r))
arm_b_total = len(arm_b_excl_t5)
print(f"\n=== H1 (Arm B pass rate, arm_comparison excl. T5) ===")
print(f"  {arm_b_pass}/{arm_b_total} = {100*arm_b_pass/arm_b_total:.1f}%")

# Per-arm pass rates (excl T5)
print(f"\n=== Per-arm pass rate (arm_comparison excl. T5) ===")
for arm in ["arm_a","arm_b","arm_c"]:
    sub = [r for r in ac_excl_t5 if r["arm"]==arm]
    p = sum(1 for r in sub if fp_pass(r))
    t = len(sub)
    print(f"  {arm}: {p}/{t} = {100*p/t:.1f}%")

# Per-arm pass rate INCLUDING T5 (for comparison)
ac_all = [r for r in data if r["tc"]=="arm_comparison"]
print(f"\n=== Per-arm pass rate (arm_comparison incl. T5 — for completeness) ===")
for arm in ["arm_a","arm_b","arm_c"]:
    sub = [r for r in ac_all if r["arm"]==arm]
    p = sum(1 for r in sub if fp_pass(r))
    t = len(sub)
    print(f"  {arm}: {p}/{t} = {100*p/t:.1f}%")

# Per-task pass rate (arm_comparison, excl T5 in totals)
print(f"\n=== Per-task pass rate (arm_comparison) ===")
for task in ["T1","T2","T3a","T3b","T4","T5"]:
    sub = [r for r in ac_all if r["task"]==task]
    p = sum(1 for r in sub if fp_pass(r))
    t = len(sub)
    note = " [T5 inverted-criterion via decline]" if task=="T5" else ""
    print(f"  {task}: {p}/{t} = {100*p/t:.1f}%{note}")

# Baseline (C4)
print(f"\n=== Baseline (C4 — training-data confound) ===")
bl = [r for r in data if r["tc"]=="baseline"]
for task in ["T1","T2","T3a","T3b"]:
    sub = [r for r in bl if r["task"]==task]
    p = sum(1 for r in sub if fp_pass(r))
    t = len(sub)
    print(f"  {task} baseline: {p}/{t} = {100*p/t:.1f}%")
print(f"  Total baseline: {sum(1 for r in bl if fp_pass(r))}/{len(bl)} = "
      f"{100*sum(1 for r in bl if fp_pass(r))/len(bl):.1f}%")

# Robustness
print(f"\n=== Robustness (temp 0.3) ===")
rb = [r for r in data if r["tc"]=="robustness"]
for task in ["T1","T3a","T3b"]:
    sub = [r for r in rb if r["task"]==task]
    p = sum(1 for r in sub if fp_pass(r))
    t = len(sub)
    print(f"  {task} robustness: {p}/{t} = {100*p/t:.1f}%")

# T3a vs T3b composition gap (C2)
print(f"\n=== C2 — Composition gap (T3a 2-skill vs T3b 3-skill) ===")
for arm in ["arm_a","arm_b","arm_c"]:
    t3a_sub = [r for r in ac_all if r["arm"]==arm and r["task"]=="T3a"]
    t3b_sub = [r for r in ac_all if r["arm"]==arm and r["task"]=="T3b"]
    p3a = sum(1 for r in t3a_sub if fp_pass(r))
    p3b = sum(1 for r in t3b_sub if fp_pass(r))
    gap = 100*(p3a-p3b)/3
    print(f"  {arm}: T3a {p3a}/3 = {100*p3a/3:.0f}% vs T3b {p3b}/3 = {100*p3b/3:.0f}%  gap={gap:+.0f}pp")

# Failure-mode distributions (per arm, arm_comparison failures only)
print(f"\n=== Failure-mode distribution (arm_comparison FAILS only) ===")
for arm in ["arm_a","arm_b","arm_c"]:
    fails = [r for r in ac_all if r["arm"]==arm and r["fp"] is False]
    fm = Counter(r["fm"] for r in fails)
    print(f"  {arm} ({len(fails)} fails): {dict(fm)}")

# Root-cause distributions
print(f"\n=== Failure root-cause distribution (arm_comparison FAILS only) ===")
for arm in ["arm_a","arm_b","arm_c"]:
    fails = [r for r in ac_all if r["arm"]==arm and r["fp"] is False]
    frc = Counter(r["frc"] for r in fails)
    print(f"  {arm} ({len(fails)} fails): {dict(frc)}")

# Token cost per arm
print(f"\n=== Fragment count per arm (proxy for token cost) ===")
for task in ["T1","T2","T3a","T3b","T4"]:
    cnts = {}
    for arm in ["arm_a","arm_b","arm_c"]:
        sub = [r for r in ac_all if r["arm"]==arm and r["task"]==task]
        if sub:
            cnts[arm] = sub[0]["fcount"]
    print(f"  {task}: {cnts}")
EOF

#!/usr/bin/env bash
# run_81.sh — full 81-trial execution per spec §6.1
# Outputs: trial log lines + milestone summaries + parse-fail alerts
set -euo pipefail

HARNESS="$(cd "$(dirname "$0")" && pwd)/run_trial.py"
PYTHON=/home/nmeyers/dev/skillsmith/.venv/bin/python
LOG=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/run_81.log
export LM_STUDIO_BASE_URL=http://localhost:1234
export SKILLS_DUCK_PATH=/home/nmeyers/dev/skillsmith/experiments/skill-tax/skills.duck

trial_n=0
parse_fails=0

run_trial() {
    local task=$1 arm=$2 run=$3 temp=$4 class=$5
    trial_n=$((trial_n + 1))
    local out
    out=$("$PYTHON" "$HARNESS" --task "$task" --arm "$arm" --run "$run" \
        --temperature "$temp" --trial-class "$class" 2>&1)
    echo "$out" | tee -a "$LOG"
    # Alert on parse failure
    if echo "$out" | grep -q "parses=False"; then
        echo "PARSE_FAIL[$trial_n]: $task $arm run=$run temp=$temp class=$class" | tee -a "$LOG"
        parse_fails=$((parse_fails + 1))
    fi
    # Milestone every 20 trials
    if (( trial_n % 20 == 0 )); then
        echo "=== MILESTONE: $trial_n / 81 trials complete (parse_fails=$parse_fails) ===" | tee -a "$LOG"
    fi
}

echo "=== run_81 start: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG"

# ── arm_comparison: 6 tasks × 3 arms × 3 runs @ temp 0.0 ─────────────────────
echo "--- ARM COMPARISON (54 trials) ---" | tee -a "$LOG"
for task in T1 T2 T3a T3b T4 T5; do
    for arm in arm_a arm_b arm_c; do
        for run in 1 2 3; do
            run_trial "$task" "$arm" "$run" 0.0 arm_comparison
        done
    done
done

# ── baseline: 4 tasks × 3 runs @ temp 0.0 ────────────────────────────────────
echo "--- BASELINE (12 trials) ---" | tee -a "$LOG"
for task in T1 T2 T3a T3b; do
    for run in 1 2 3; do
        run_trial "$task" baseline "$run" 0.0 baseline
    done
done

# ── robustness: 3 tasks × 5 runs @ temp 0.3 ──────────────────────────────────
echo "--- ROBUSTNESS (15 trials) ---" | tee -a "$LOG"
for task in T1 T3a T3b; do
    for run in 1 2 3 4 5; do
        run_trial "$task" arm_b "$run" 0.3 robustness
    done
done

echo "=== run_81 complete: $(date -u +%Y-%m-%dT%H:%M:%SZ) parse_fails=$parse_fails / $trial_n ===" | tee -a "$LOG"

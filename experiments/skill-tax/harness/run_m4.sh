#!/usr/bin/env bash
# Milestone-4 re-run: T3a, T3b, T4 across 3 arms × 3 runs = 27 trials at temp 0.0
set -euo pipefail

HARNESS="$(cd "$(dirname "$0")" && pwd)/run_trial.py"
PYTHON=/home/nmeyers/dev/skillsmith/.venv/bin/python
LOG=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/run_m4.log
export LM_STUDIO_BASE_URL=http://localhost:1234
export SKILLS_DUCK_PATH=/home/nmeyers/dev/skillsmith/experiments/skill-tax/skills.duck
export DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilotdb

trial_n=0
parse_fails=0

run_trial() {
    local task=$1 arm=$2 run=$3
    trial_n=$((trial_n + 1))
    local out
    out=$("$PYTHON" "$HARNESS" --task "$task" --arm "$arm" --run "$run" \
        --temperature 0.0 --trial-class arm_comparison 2>&1)
    echo "$out" | tee -a "$LOG"
    if echo "$out" | grep -q "parses=False"; then
        echo "PARSE_FAIL[$trial_n]: $task $arm run=$run" | tee -a "$LOG"
        parse_fails=$((parse_fails + 1))
    fi
    if (( trial_n % 9 == 0 )); then
        echo "=== MILESTONE: $trial_n / 27 trials complete (parse_fails=$parse_fails) ===" | tee -a "$LOG"
    fi
}

echo "=== run_m4 start: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG"
for task in T3a T3b T4; do
    for arm in arm_a arm_b arm_c; do
        for run in 1 2 3; do
            run_trial "$task" "$arm" "$run"
        done
    done
done
echo "=== run_m4 complete: $(date -u +%Y-%m-%dT%H:%M:%SZ) parse_fails=$parse_fails / $trial_n ===" | tee -a "$LOG"

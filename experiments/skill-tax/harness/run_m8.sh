#!/usr/bin/env bash
# Milestone 8 — anti-pattern fragments + self-QA two-call workflow.
# Same task as M7 (T1 arm_b_plus) but model gets a second pass to review
# its own output against the activated fragments before submitting.
# Direct compare: M5 T1 arm_b (0/50) → M7 T1 arm_b_plus (?) → M8 T1 arm_b_plus + review (?)
set -uo pipefail

PYTHON=/home/nmeyers/dev/skillsmith/.venv/bin/python
HARNESS=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/run_trial.py
LOG_DIR=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/m8_logs
mkdir -p "$LOG_DIR"

export LM_STUDIO_BASE_URL=http://localhost:1234
export SKILLS_DUCK_PATH=/home/nmeyers/dev/skillsmith/experiments/skill-tax/skills.duck
export DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilotdb
export REVIEW_PASS=1

MODELS=(
    "qwen2.5-coder-1.5b-instruct-128k"
    "qwen2.5-coder-3b-instruct-128k"
    "llama-3.2-3b-instruct"
    "phi-4-mini-instruct"
)

run_one() {
    local task=$1 arm=$2 run=$3 mlog=$4
    local out
    out=$("$PYTHON" "$HARNESS" --task "$task" --arm "$arm" --run "$run" \
        --temperature 0.0 --trial-class arm_comparison 2>&1)
    local rc=$?
    if [ $rc -ne 0 ]; then
        local snippet=$(echo "$out" | tail -3 | tr '\n' ' ')
        echo "TRIAL_FAILED rc=$rc task=$task arm=$arm run=$run | $snippet" | tee -a "$mlog"
    else
        echo "$out" | tee -a "$mlog"
    fi
}

run_for_model() {
    local model=$1
    local mlog="$LOG_DIR/${model}.log"
    echo "=== $(date -u +%H:%M:%S) START $model (M8 arm_b_plus + review) ===" | tee -a "$mlog"

    lms unload --all 2>&1 | tail -3 | tee -a "$mlog" || true
    sleep 2
    timeout 90 lms load "$model" --gpu max --context-length 32768 2>&1 | tail -5 | tee -a "$mlog"
    local rc=$?
    if [ $rc -ne 0 ]; then
        echo "LOAD_FAILED rc=$rc model=$model — SKIPPING" | tee -a "$mlog"
        return 0
    fi
    sleep 3
    export TIER2_MODEL="$model"

    echo "--- T1 arm_b_plus × 5 runs (with self-review pass) ---" | tee -a "$mlog"
    for run in 1 2 3 4 5; do
        run_one T1 arm_b_plus $run "$mlog"
    done

    echo "=== $(date -u +%H:%M:%S) END $model ===" | tee -a "$mlog"
}

echo "M8 START $(date -u +%Y-%m-%dT%H:%M:%SZ) REVIEW_PASS=$REVIEW_PASS" \
    | tee -a "$LOG_DIR/_summary.log"
for model in "${MODELS[@]}"; do
    run_for_model "$model"
done
lms unload --all 2>&1 | tail -3
echo "M8 COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG_DIR/_summary.log"

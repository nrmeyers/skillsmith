#!/usr/bin/env bash
# Milestone 7 — anti-pattern-augmented fragments on T1.
# Same task as M5's Q10 (T1, blank-slate seed) but with 4 new anti-pattern
# fragments (webhook-patterns:9-12) added to arm_b_plus.
# Direct comparison: M5 T1 arm_b (0/50 fp) vs M7 T1 arm_b_plus (?/25 fp).
set -uo pipefail

PYTHON=/home/nmeyers/dev/skillsmith/.venv/bin/python
HARNESS=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/run_trial.py
LOG_DIR=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/m7_logs
mkdir -p "$LOG_DIR"

export LM_STUDIO_BASE_URL=http://localhost:1234
export SKILLS_DUCK_PATH=/home/nmeyers/dev/skillsmith/experiments/skill-tax/skills.duck
export DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilotdb
# Note: SHOW_SEED is NOT set — M7 isolates the anti-pattern variable.
# T1 has a near-empty seed anyway (just `from fastapi import FastAPI; app = FastAPI()`)

MODELS=(
    "qwen2.5-coder-1.5b-instruct-128k"
    "qwen2.5-coder-3b-instruct-128k"
    "llama-3.2-3b-instruct"
    "phi-4-mini-instruct"
)
# SmolLM3-3B dropped per M5 review — think-mode budget exhaustion + no
# distinguishing signal from the other 3B-class models.

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
    echo "=== $(date -u +%H:%M:%S) START $model (M7 arm_b_plus) ===" | tee -a "$mlog"

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

    echo "--- T1 arm_b_plus × 5 runs ---" | tee -a "$mlog"
    for run in 1 2 3 4 5; do
        run_one T1 arm_b_plus $run "$mlog"
    done

    echo "=== $(date -u +%H:%M:%S) END $model ===" | tee -a "$mlog"
}

echo "M7 START $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG_DIR/_summary.log"
for model in "${MODELS[@]}"; do
    run_for_model "$model"
done
lms unload --all 2>&1 | tail -3
echo "M7 COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG_DIR/_summary.log"

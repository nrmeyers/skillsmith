#!/usr/bin/env bash
# Milestone 5 — sweep small models on v2 preamble. Resilient to per-trial failures.
# Usage: run_m5.sh [start_model_index]   default 0
set -uo pipefail   # NOTE: no -e — single trial failure should not kill the sweep

PYTHON=/home/nmeyers/dev/skillsmith/.venv/bin/python
HARNESS=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/run_trial.py
LOG_DIR=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/m5_logs
mkdir -p "$LOG_DIR"

export LM_STUDIO_BASE_URL=http://localhost:1234
export SKILLS_DUCK_PATH=/home/nmeyers/dev/skillsmith/experiments/skill-tax/skills.duck
export DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilotdb

MODELS=(
    "qwen2.5-coder-1.5b-instruct-128k"
    "qwen2.5-1.5b-instruct"
    "qwen2.5-coder-3b-instruct-128k"
    "llama-3.2-3b-instruct"
    "smollm3-3b"
    "phi-4-mini-instruct"
)

# Per-model: skip Q10 if already completed (used to resume)
SKIP_Q10="${SKIP_Q10:-}"

START_IDX="${1:-0}"

run_one() {
    local task=$1 arm=$2 run=$3 cls=$4 mlog=$5
    local out
    out=$("$PYTHON" "$HARNESS" --task "$task" --arm "$arm" --run "$run" \
        --temperature 0.0 --trial-class "$cls" 2>&1)
    local rc=$?
    if [ $rc -ne 0 ]; then
        local snippet=$(echo "$out" | tail -3 | tr '\n' ' ')
        echo "TRIAL_FAILED rc=$rc task=$task arm=$arm run=$run | $snippet" | tee -a "$mlog"
    else
        echo "$out" | tee -a "$mlog"
    fi
}

run_for_model() {
    local model=$1 skip_q10=$2
    local mlog="$LOG_DIR/${model}.log"
    echo "=== $(date -u +%H:%M:%S) START $model (skip_q10=$skip_q10) ===" | tee -a "$mlog"

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

    if [ "$skip_q10" != "1" ]; then
        echo "--- Q10 precheck (T1 arm_b ×10) ---" | tee -a "$mlog"
        for run in 1 2 3 4 5 6 7 8 9 10; do
            run_one T1 arm_b $run arm_comparison "$mlog"
        done
    else
        echo "--- Q10 precheck SKIPPED (already in DB) ---" | tee -a "$mlog"
    fi

    echo "--- Frag arms (T3a/T3b/T4 ×3 ×3) ---" | tee -a "$mlog"
    for task in T3a T3b T4; do
        for arm in arm_a arm_b arm_c; do
            for run in 1 2 3; do
                run_one $task $arm $run arm_comparison "$mlog"
            done
        done
    done

    echo "--- Baseline (T3a/T3b/T4 ×3) ---" | tee -a "$mlog"
    for task in T3a T3b T4; do
        for run in 1 2 3; do
            run_one $task baseline $run baseline "$mlog"
        done
    done

    echo "=== $(date -u +%H:%M:%S) END $model ===" | tee -a "$mlog"
}

echo "M5 START $(date -u +%Y-%m-%dT%H:%M:%SZ) start_idx=$START_IDX" | tee -a "$LOG_DIR/_summary.log"

i=0
for model in "${MODELS[@]}"; do
    if [ $i -lt $START_IDX ]; then
        echo "skip $model (i=$i < $START_IDX)" | tee -a "$LOG_DIR/_summary.log"
        i=$((i+1))
        continue
    fi
    # First model on resume gets Q10 skipped if it's already in DB
    skip="0"
    if [ "$i" = "0" ] && [ "$SKIP_Q10" = "1" ]; then
        skip="1"
    fi
    run_for_model "$model" "$skip"
    i=$((i+1))
done

lms unload --all 2>&1 | tail -3
echo "M5 COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG_DIR/_summary.log"

#!/usr/bin/env bash
# Milestone 6 — small-model sweep with SEED CONTENT INJECTED into prompt.
# Tests whether showing the model the existing code unlocks pass rates.
# Same task surface as M5; only difference is SHOW_SEED=1.
set -uo pipefail

PYTHON=/home/nmeyers/dev/skillsmith/.venv/bin/python
HARNESS=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/run_trial.py
LOG_DIR=/home/nmeyers/dev/skillsmith/experiments/skill-tax/harness/m6_logs
mkdir -p "$LOG_DIR"

export LM_STUDIO_BASE_URL=http://localhost:1234
export SKILLS_DUCK_PATH=/home/nmeyers/dev/skillsmith/experiments/skill-tax/skills.duck
export DATABASE_URL=postgresql://pilot:pilot@localhost:5432/pilotdb
export SHOW_SEED=1

# Skip qwen2.5-1.5b-instruct (broken download from M5)
MODELS=(
    "qwen2.5-coder-1.5b-instruct-128k"
    "qwen2.5-coder-3b-instruct-128k"
    "llama-3.2-3b-instruct"
    "smollm3-3b"
    "phi-4-mini-instruct"
)

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
    local model=$1
    local mlog="$LOG_DIR/${model}.log"
    echo "=== $(date -u +%H:%M:%S) START $model (M6 SHOW_SEED=1) ===" | tee -a "$mlog"

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

    # Skip Q10 since T1 is single-file and we already have M5 baseline for T1
    # Run same surface as M5: 27 frag arms + 9 baseline = 36 trials per model

    echo "--- Frag arms (T3a/T3b/T4 ×3 ×3) with seed injected ---" | tee -a "$mlog"
    for task in T3a T3b T4; do
        for arm in arm_a arm_b arm_c; do
            for run in 1 2 3; do
                run_one $task $arm $run arm_comparison "$mlog"
            done
        done
    done

    echo "--- Baseline (T3a/T3b/T4 ×3) with seed injected ---" | tee -a "$mlog"
    for task in T3a T3b T4; do
        for run in 1 2 3; do
            run_one $task baseline $run baseline "$mlog"
        done
    done

    echo "=== $(date -u +%H:%M:%S) END $model ===" | tee -a "$mlog"
}

echo "M6 START $(date -u +%Y-%m-%dT%H:%M:%SZ) start_idx=$START_IDX SHOW_SEED=$SHOW_SEED" \
    | tee -a "$LOG_DIR/_summary.log"

i=0
for model in "${MODELS[@]}"; do
    if [ $i -lt $START_IDX ]; then
        i=$((i+1)); continue
    fi
    run_for_model "$model"
    i=$((i+1))
done

lms unload --all 2>&1 | tail -3
echo "M6 COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG_DIR/_summary.log"

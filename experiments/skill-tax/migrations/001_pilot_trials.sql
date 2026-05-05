-- Migration 001: pilot_trials sibling table in skills.duck
-- Per workflow-phase-retrieval-pilot-spec.md §7.1
-- Run once against the DuckDB file used by DuckDBTelemetryWriter
-- (the same skills.duck that holds composition_traces).

CREATE TABLE IF NOT EXISTS pilot_trials (
  trial_id           VARCHAR PRIMARY KEY,
  composition_id     VARCHAR,    -- FK to composition_traces.composition_id
  trial_class        VARCHAR,    -- 'arm_comparison' | 'baseline' | 'robustness'
  task_variation     VARCHAR,    -- 'T1' | 'T2' | 'T3a' | 'T3b' | 'T4' | 'T5'
  retrieval_arm      VARCHAR,    -- 'A' | 'B' | 'C' | 'baseline'
  fragment_types     VARCHAR,    -- comma-separated fragment_type values present in context
  fragment_count     INTEGER,
  temperature        DOUBLE,
  prompt             VARCHAR,    -- full prompt sent to Tier 2 (for reproducibility)
  response           VARCHAR,    -- full model response (raw diff or decline text)
  -- verification fields
  parses             BOOLEAN,    -- diff applied cleanly / response is well-formed
  functional_pass    BOOLEAN,    -- all mechanical checks passed
  faithfulness_pass  BOOLEAN,    -- all faithfulness items passed
  consistency_hash   VARCHAR,    -- normalized output hash for run-to-run dedup
  -- failure attribution
  failure_mode       VARCHAR,    -- 'none' | 'drift' | 'hallucination' | 'incomplete'
                                 -- | 'scope_violation' | 'parse_error'
                                 -- | 'wrong_skill' | 'composition_error'
  failed_fragment    VARCHAR,    -- 'none' | '<skill_id>:<sequence>' | 'multiple'
                                 -- | 'unattributable'
  failure_root_cause VARCHAR,    -- 'none' | 'under_specified_procedure'
                                 -- | 'missing_rationale' | 'missing_example'
                                 -- | 'missing_setup' | 'verification_false_pass'
                                 -- | 'scope_guard_too_weak' | 'composition_gap'
                                 -- | 'composition_overlap' | 'model_capability'
  notes              VARCHAR,    -- free text from manual review
  ran_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

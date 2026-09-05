-- =====================================================================
-- HiveBlot beta -- Migration 001: Western Blot Evidence Record (additive)
-- =====================================================================
-- SAFETY: This migration is strictly ADDITIVE and IDEMPOTENT.
--   * It only ADDs nullable columns / indexes with IF NOT EXISTS.
--   * It does NOT drop, rename, or retype any existing column.
--   * The existing `band_detected`, `western_blot_type`, `target`, etc. are
--     untouched, so the deployed /search and /proteins endpoints and the
--     current frontend keep working unchanged.
--   * Existing rows get NULLs in the new columns and needs_review = true, so
--     un-enriched legacy data surfaces as "needs review" rather than as
--     silently-complete records.
--
-- ROLLBACK: see migrations/001_evidence_record.down.sql (drops only the columns
-- this migration adds). No data in pre-existing columns is affected.
--
-- Run against your Supabase (SQL editor or psql). Requires no extensions.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Paper provenance (denormalized onto the flat band table for the beta;
-- a normalized papers/figures model is provided separately in 002).
-- ---------------------------------------------------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS pmid TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS pmcid TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS doi TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS authors TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS source_url TEXT;

-- Figure ------------------------------------------------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS panel_label TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS figure_caption TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS image_crop_ref TEXT;

-- Protein identity --------------------------------------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS raw_target_name TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS canonical_target TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS uniprot_id TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS aliases_used_in_paper JSONB;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS protein_status TEXT;   -- SUPPORTED/AMBIGUOUS/MISSING

-- Modification ------------------------------------------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS modification_type TEXT; -- phosphorylation/cleavage/...
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS residue TEXT;           -- Tyr/Ser/Thr
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS residue_position INTEGER;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS modification_label TEXT; -- e.g. phospho-Tyr705
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS modification_status TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS phospho_specific_antibody BOOLEAN;

-- Experiment --------------------------------------------------------------
-- experiment_type in {standard_western, phospho_western, co_ip,
--                     purified_protein, loading_control, unknown}
-- experiment_flags is non-exclusive (co_ip + phospho_western can coexist).
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS experiment_type TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS experiment_flags JSONB;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS experiment_type_confidence DOUBLE PRECISION;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS experiment_type_evidence JSONB;

-- Sample extras -----------------------------------------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS cell_line TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS tissue TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS genotype TEXT;

-- Treatment (deterministic parse; never invented) -------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS treatment_name TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS dose DOUBLE PRECISION;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS dose_unit TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS duration DOUBLE PRECISION;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS duration_unit TEXT;

-- Antibody (UCSF researchers care about this a lot) -----------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS antibody_target TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS antibody_vendor TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS antibody_catalog_number TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS antibody_clone TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS antibody_dilution TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS antibody_source_evidence JSONB;

-- Band / blot observation -------------------------------------------------
-- band_detected (BOOLEAN) already exists; keep it. We add the richer state.
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS band_state TEXT;         -- present/absent/uncertain
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS lane_condition TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS loading_control BOOLEAN;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS reported_molecular_weight_kda DOUBLE PRECISION;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS expected_molecular_weight_kda DOUBLE PRECISION;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS molecular_weight_source TEXT; -- caption_or_methods_text / uniprot_reference / NULL

-- Provenance + validation + audit ----------------------------------------
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS provenance JSONB;         -- per-field sources/status
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS validation JSONB;         -- Phase 4 fills this
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS anomaly_flags JSONB;      -- Phase 4 fills this
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT TRUE;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS extraction_stage TEXT;    -- deterministic / deterministic+vlm
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS extraction_model TEXT;
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS extraction_version TEXT;

-- =====================================================================
-- FUTURE / UNPOPULATED: quantitative densitometry.
-- These columns exist for schema-forward-compatibility ONLY. They MUST stay
-- NULL until a real, deterministic measurement pipeline (lane detection +
-- ladder calibration + IOD) writes them. HiveBlot must never present a value
-- here as "measured" unless that pipeline actually ran.
-- =====================================================================
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS raw_intensity DOUBLE PRECISION;                 -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS background_corrected_intensity DOUBLE PRECISION; -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS normalized_intensity DOUBLE PRECISION;         -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS band_width_px DOUBLE PRECISION;                -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS band_height_px DOUBLE PRECISION;               -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS band_area_px DOUBLE PRECISION;                 -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS smearing_score DOUBLE PRECISION;               -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS saturation_flag BOOLEAN;                       -- FUTURE
ALTER TABLE western_blot_records ADD COLUMN IF NOT EXISTS densitometry_source TEXT;                      -- FUTURE (e.g. hiveblot_cv / imagej / published)

-- ---------------------------------------------------------------------
-- Indexes to support structured filtering (Phase 5).
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_wbr_canonical_target ON western_blot_records (canonical_target);
CREATE INDEX IF NOT EXISTS idx_wbr_modification     ON western_blot_records (modification_type);
CREATE INDEX IF NOT EXISTS idx_wbr_residue          ON western_blot_records (residue, residue_position);
CREATE INDEX IF NOT EXISTS idx_wbr_experiment_type  ON western_blot_records (experiment_type);
CREATE INDEX IF NOT EXISTS idx_wbr_vendor           ON western_blot_records (antibody_vendor);
CREATE INDEX IF NOT EXISTS idx_wbr_catalog          ON western_blot_records (antibody_catalog_number);
CREATE INDEX IF NOT EXISTS idx_wbr_cell_line        ON western_blot_records (cell_line);
CREATE INDEX IF NOT EXISTS idx_wbr_needs_review     ON western_blot_records (needs_review);

COMMIT;

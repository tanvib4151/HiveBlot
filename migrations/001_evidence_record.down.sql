-- Rollback for 001_evidence_record.sql. Drops ONLY the columns/indexes that
-- migration added. Pre-existing columns (target, band_detected, sample,
-- western_blot_type, condition, confidence, ...) are never touched.
BEGIN;

DROP INDEX IF EXISTS idx_wbr_canonical_target;
DROP INDEX IF EXISTS idx_wbr_modification;
DROP INDEX IF EXISTS idx_wbr_residue;
DROP INDEX IF EXISTS idx_wbr_experiment_type;
DROP INDEX IF EXISTS idx_wbr_vendor;
DROP INDEX IF EXISTS idx_wbr_catalog;
DROP INDEX IF EXISTS idx_wbr_cell_line;
DROP INDEX IF EXISTS idx_wbr_needs_review;

ALTER TABLE western_blot_records
  DROP COLUMN IF EXISTS pmid,
  DROP COLUMN IF EXISTS pmcid,
  DROP COLUMN IF EXISTS doi,
  DROP COLUMN IF EXISTS title,
  DROP COLUMN IF EXISTS authors,
  DROP COLUMN IF EXISTS source_url,
  DROP COLUMN IF EXISTS panel_label,
  DROP COLUMN IF EXISTS figure_caption,
  DROP COLUMN IF EXISTS image_crop_ref,
  DROP COLUMN IF EXISTS raw_target_name,
  DROP COLUMN IF EXISTS canonical_target,
  DROP COLUMN IF EXISTS uniprot_id,
  DROP COLUMN IF EXISTS aliases_used_in_paper,
  DROP COLUMN IF EXISTS protein_status,
  DROP COLUMN IF EXISTS modification_type,
  DROP COLUMN IF EXISTS residue,
  DROP COLUMN IF EXISTS residue_position,
  DROP COLUMN IF EXISTS modification_label,
  DROP COLUMN IF EXISTS modification_status,
  DROP COLUMN IF EXISTS phospho_specific_antibody,
  DROP COLUMN IF EXISTS experiment_type,
  DROP COLUMN IF EXISTS experiment_flags,
  DROP COLUMN IF EXISTS experiment_type_confidence,
  DROP COLUMN IF EXISTS experiment_type_evidence,
  DROP COLUMN IF EXISTS cell_line,
  DROP COLUMN IF EXISTS tissue,
  DROP COLUMN IF EXISTS genotype,
  DROP COLUMN IF EXISTS treatment_name,
  DROP COLUMN IF EXISTS dose,
  DROP COLUMN IF EXISTS dose_unit,
  DROP COLUMN IF EXISTS duration,
  DROP COLUMN IF EXISTS duration_unit,
  DROP COLUMN IF EXISTS antibody_target,
  DROP COLUMN IF EXISTS antibody_vendor,
  DROP COLUMN IF EXISTS antibody_catalog_number,
  DROP COLUMN IF EXISTS antibody_clone,
  DROP COLUMN IF EXISTS antibody_dilution,
  DROP COLUMN IF EXISTS antibody_source_evidence,
  DROP COLUMN IF EXISTS band_state,
  DROP COLUMN IF EXISTS lane_condition,
  DROP COLUMN IF EXISTS loading_control,
  DROP COLUMN IF EXISTS reported_molecular_weight_kda,
  DROP COLUMN IF EXISTS expected_molecular_weight_kda,
  DROP COLUMN IF EXISTS molecular_weight_source,
  DROP COLUMN IF EXISTS provenance,
  DROP COLUMN IF EXISTS validation,
  DROP COLUMN IF EXISTS anomaly_flags,
  DROP COLUMN IF EXISTS needs_review,
  DROP COLUMN IF EXISTS extraction_stage,
  DROP COLUMN IF EXISTS extraction_model,
  DROP COLUMN IF EXISTS extraction_version,
  DROP COLUMN IF EXISTS raw_intensity,
  DROP COLUMN IF EXISTS background_corrected_intensity,
  DROP COLUMN IF EXISTS normalized_intensity,
  DROP COLUMN IF EXISTS band_width_px,
  DROP COLUMN IF EXISTS band_height_px,
  DROP COLUMN IF EXISTS band_area_px,
  DROP COLUMN IF EXISTS smearing_score,
  DROP COLUMN IF EXISTS saturation_flag,
  DROP COLUMN IF EXISTS densitometry_source;

COMMIT;

'use client';

import { type ReactNode } from 'react';

// NOTE: every Evidence Record field below is OPTIONAL. Legacy rows (pre-migration
// 001) simply omit them and the card falls back to the original base fields, so
// existing search never breaks. New fields render only when present -- a missing
// value shows as "not reported", never as fabricated data.
interface DatabaseResult {
  id: number;
  paper_id: string;
  page: number | null;
  western_blot_type: string | null;
  sample: string | null;
  organism: string | null;
  treatment_context: string | null;
  figure_label: string | null;
  target: string;
  condition: string | null;
  band_detected: boolean | null;
  confidence: number | null;
  // --- Evidence Record additions (all optional) ---
  canonical_target?: string | null;
  uniprot_id?: string | null;
  protein_status?: string | null;
  modification_label?: string | null;
  modification_status?: string | null;
  experiment_type?: string | null;
  cell_line?: string | null;
  treatment_name?: string | null;
  dose?: number | null;
  dose_unit?: string | null;
  duration?: number | null;
  duration_unit?: string | null;
  antibody_vendor?: string | null;
  antibody_catalog_number?: string | null;
  antibody_dilution?: string | null;
  band_state?: string | null;
  reported_molecular_weight_kda?: number | null;
  expected_molecular_weight_kda?: number | null;
  figure_caption?: string | null;
  image_crop_ref?: string | null;
  needs_review?: boolean | null;
  anomaly_flags?: Array<{ code?: string; message?: string }> | null;
  doi?: string | null;
  pmcid?: string | null;
  title?: string | null;
}

export interface LaneSummary {
  condition: string | null;
  band_state: string | null;
}

interface DatabaseResultCardProps {
  data: DatabaseResult;
  // When search results are grouped into one card per experiment (paper +
  // panel + target), `lanes` carries every lane of the group so a researcher
  // reads ONE experiment instead of N near-identical rows. Optional: a card
  // without it renders the single row exactly as before.
  lanes?: LaneSummary[];
}

const MONO = 'var(--font-mono), monospace';
const SERIF = 'var(--font-serif), serif';
const SANS = 'var(--font-sans), sans-serif';
const LABEL = 'var(--text-subtle)';
const TEXT = 'var(--text-primary)';
const TEAL = 'var(--accent)';
const GOLD = 'var(--warning)';
const RED = 'var(--error)';

function titleCase(s?: string | null): string {
  if (!s) return '';
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMeasurement(value: number, unit?: string | null): string {
  return unit ? `${value} ${unit}` : String(value);
}

// Display-only lane-label formatting (semantics untouched): " / " separators
// become interpuncts and a TRAILING +/− state marker gets a colon, so
// "IL-6 + / CL-E -" reads "IL-6: + · CL-E: −". A "+" that joins a drug name
// ("CL-E + Bis II") is a conjunction and is left alone.
export function formatLaneLabel(c?: string | null): string {
  if (!c) return '';
  return c
    .replace(/(\S+) ([+-])(?=$| \/ )/g, (_m, name, sign) => `${name}: ${sign === '-' ? '−' : '+'}`)
    .replace(/ \/ /g, ' · ');
}

// Deterministic experiment-design tag derived ONLY from the group's own lane
// labels + the reviewed treatment context (data-backed, never invented).
// Abstention is the default: no supported semantics -> no tag.
const DOSE_UNIT_RE = /(\d+(\.\d+)?)\s*(ng\/ml|[uµμ]g\/ml|mg\/ml|[nuµμ]M\b|mmol|nmol|[uµμ]mol|mg\/kg|%)/i;
// Embryonic/postnatal developmental-stage nomenclature: E14.5, P0, P7,
// P28M/P25F (optional sex suffix). These are SAMPLE STAGES, never doses.
const DEV_STAGE_RE = /^[EP]\d+(\.\d+)?[FM]?$/;

export function deriveDesignTag(lanes?: LaneSummary[], treatmentContext?: string | null): string | null {
  if (!lanes || lanes.length < 3) return null;
  const conds = lanes.map((l) => (l.condition || '').trim()).filter(Boolean);
  if (conds.length < 3) return null;
  // Developmental series takes precedence: E/P-day labels also end in digits
  // and previously false-fired the dose heuristic (GAPDH mouse, "P0..P28M").
  const dev = conds.filter((c) => DEV_STAGE_RE.test(c));
  if (dev.length >= 3) return 'developmental series';
  const timepoints = conds.filter((c) => /^\d+(\.\d+)?\s*(min|mins|h|hr|hrs)$/i.test(c));
  if (timepoints.length >= 3) return 'time course';
  // DOSE SERIES needs explicit dose semantics, not just trailing numbers:
  // either the lane labels carry a unit, or the reviewed treatment context
  // states a concentration series the lane numbers correspond to.
  const trailing = conds
    .map((c) => /^(.*?)(\d+(?:\.\d+)?)$/.exec(c))
    .filter((m): m is RegExpExecArray => !!m && m[1].trim().length > 0 && !DEV_STAGE_RE.test(m.input));
  if (trailing.length >= 3) {
    const prefixes = new Set(trailing.map((m) => m[1].trim()));
    const numbers = new Set(trailing.map((m) => m[2]));
    const doseSemantics =
      conds.some((c) => DOSE_UNIT_RE.test(c)) ||
      (treatmentContext ? DOSE_UNIT_RE.test(treatmentContext) : false);
    if (prefixes.size === 1 && numbers.size >= 3 && doseSemantics) return 'dose series';
  }
  return null;
}

// Supported / Needs review / Conflicting -- derived, never asserted beyond evidence.
function reviewState(d: DatabaseResult): { label: string; color: string } | null {
  const statuses = [d.protein_status, d.modification_status];
  if (statuses.includes('CONFLICTING')) return { label: 'Conflicting', color: RED };
  if (d.needs_review === true || statuses.includes('AMBIGUOUS')) return { label: 'Needs review', color: GOLD };
  if (d.needs_review === false) return { label: 'Supported', color: TEAL };
  return null;
}

function Field({ label, value, mono, color }: { label: string; value: ReactNode; mono?: boolean; color?: string }) {
  return (
    <div className="hb-result-field">
      <div style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: LABEL, marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontFamily: mono ? MONO : SANS, fontSize: mono ? '13px' : '14px', color: color || TEXT, lineHeight: 1.3 }}>
        {value}
      </div>
    </div>
  );
}

function Metadata({ label, value, mono }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="hb-result-metadata-row">
      <div className="hb-result-metadata-label">{label}</div>
      <div className={mono ? 'hb-result-metadata-value hb-result-metadata-value-mono' : 'hb-result-metadata-value'}>
        {value}
      </div>
    </div>
  );
}

function EmptyFieldValue() {
  return <span className="hb-result-empty-value">not reported</span>;
}

function Chip({ children }: { children: ReactNode }) {
  return <span className="hb-result-chip">{children}</span>;
}

function experimentLabel(blotType?: string | null): string | null {
  if (!blotType) return null;
  if (blotType === 'co_ip') return 'co-IP';
  if (blotType.includes('western')) return 'WB';
  return titleCase(blotType);
}

export default function DatabaseResultCard({ data, lanes }: DatabaseResultCardProps) {
  const headline = data.canonical_target || data.target;
  const headlineMod = data.modification_label ? ` · ${data.modification_label}` : '';
  const review = reviewState(data);
  const blotType = data.experiment_type || data.western_blot_type;
  const sampleText = data.cell_line || data.sample;
  const bandText = data.band_state || (data.band_detected == null ? null : data.band_detected ? 'present' : 'absent');
  const antibody = [data.antibody_vendor, data.antibody_catalog_number ? `#${data.antibody_catalog_number}` : null]
    .filter(Boolean)
    .join(' · ');
  // Structured name·dose·duration only. The verbatim treatment_context now has
  // its own identity line under the headline — falling back to it here printed
  // the same sentence twice on cards with no parsed treatment name.
  const treatment =
    data.treatment_name || data.dose != null
      ? [
          data.treatment_name,
          data.dose != null ? formatMeasurement(data.dose, data.dose_unit) : null,
          data.duration != null ? formatMeasurement(data.duration, data.duration_unit) : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;
  // Multi-condition experiments (P0-4): surface co-conditions that are
  // literally named on this group's lane labels (CL-E, Bis II, U0126 …) so the
  // summary doesn't understate the design. "±" = the lanes carry both with-
  // and without- states; nothing is asserted beyond the printed labels.
  const extraAgents = (() => {
    if (!treatment || !lanes || lanes.length < 2) return [] as string[];
    const seen = new Set<string>();
    for (const l of lanes) {
      for (const tok of (l.condition || '').split(/[+/·,]/)) {
        const t = tok.trim().replace(/[+−-]+$/, '').trim();
        if (!t || /^\d/.test(t)) continue;
        if (/^(ctrl|control|input|igg|ip:.*)$/i.test(t)) continue;
        if (DEV_STAGE_RE.test(t)) continue;
        const base = t.replace(/\s+\d+(\.\d+)?$/, '').trim();
        if (!base) continue;
        if (data.treatment_name && base.toLowerCase() === data.treatment_name.toLowerCase()) continue;
        seen.add(base);
      }
    }
    return [...seen];
  })();
  const treatmentDisplay = treatment
    ? `${treatment}${extraAgents.length ? ` (± ${extraAgents.join(', ')})` : ''}`
    : null;
  // co-IP context from this group's own lane labels (P1): "IP:PIK3CA" printed
  // on a lane IS the bait statement for the panel.
  const ipBait = (() => {
    if (blotType !== 'co_ip' || !lanes) return null;
    for (const l of lanes) {
      const m = /\bIP:\s*([A-Za-z0-9-]+)/.exec(l.condition || '');
      if (m) return m[1];
    }
    return null;
  })();
  const mw =
    data.reported_molecular_weight_kda != null || data.expected_molecular_weight_kda != null
      ? [
          data.reported_molecular_weight_kda != null ? `reported ${data.reported_molecular_weight_kda} kDa` : null,
          data.expected_molecular_weight_kda != null ? `expected ${data.expected_molecular_weight_kda} kDa` : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;

  const bandColor = bandText === 'present' ? TEAL : bandText === 'absent' ? RED : GOLD;
  const previewSrc = /\bSTAT3\b/i.test([data.canonical_target, data.target].filter(Boolean).join(' '))
    ? '/images/STATE3.png'
    : null;
  const designTag = deriveDesignTag(lanes, data.treatment_context);
  const sourceId = data.doi || data.paper_id;
  const indicatorChips = [
    experimentLabel(blotType),
    data.modification_label?.toLowerCase().includes('phospho') ? 'Phospho' : null,
    designTag ? titleCase(designTag) : null,
    lanes && lanes.length > 1 ? `${lanes.length} lanes` : null,
  ].filter((chip): chip is string => Boolean(chip));

  return (
    <div className="hb-result-card">
      <div className="hb-result-card-main">
        <section className="hb-result-card-primary">
          <div className="hb-result-title-row">
            <div className="hb-result-title" style={{ fontFamily: SERIF }}>
              {headline}
              <span>{headlineMod}</span>
            </div>
            {review && (
              <span className="hb-status-badge" style={{ color: review.color, borderColor: review.color }}>
                {review.label}
              </span>
            )}
          </div>

          {data.canonical_target && data.target && data.canonical_target !== data.target && (
            <div className="hb-printed-target">as printed: {data.target}</div>
          )}

          {(designTag || data.treatment_context) && (
            <div className="hb-result-context" style={{ fontFamily: SERIF }}>
              {designTag && <span className="hb-result-context-tag">{designTag.toUpperCase()}</span>}
              {data.treatment_context && (
                data.treatment_context.length > 130
                  ? `${data.treatment_context.slice(0, 130)}...`
                  : data.treatment_context
              )}
            </div>
          )}
        </section>

        <section className="hb-result-card-sample">
          {sampleText && <Field label="SAMPLE" value={sampleText} />}
          {blotType && <Field label="EXPERIMENT" value={blotType === 'co_ip' ? 'co-IP' : titleCase(blotType)} />}
          {data.organism && !data.cell_line && <Field label="ORGANISM" value={data.organism} />}
          {ipBait && <Field label="IP BAIT" value={ipBait} mono />}
        </section>

        <section className="hb-result-card-treatment">
          <Field label="TREATMENT" value={treatmentDisplay || <EmptyFieldValue />} />
          {lanes && lanes.length > 1 ? (
            <div className="hb-treatment-lanes">
              <Field
                label={`LANES (${lanes.length})`}
                value={
                  <span className="hb-lane-strip">
                    {lanes.map((l, i) => (
                      <span
                        key={i}
                        className="hb-lane-pill"
                        style={{ color: l.band_state === 'present' ? TEAL : l.band_state === 'absent' ? RED : GOLD }}
                      >
                        {formatLaneLabel(l.condition) || `lane ${i + 1}`}
                      </span>
                    ))}
                  </span>
                }
              />
            </div>
          ) : (
            bandText && <Field label="BAND" value={titleCase(bandText)} color={bandColor} />
          )}
        </section>

        <section className="hb-result-card-figure">
          {previewSrc ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewSrc}
                alt={`Sample Western blot preview for ${headline}`}
                className="hb-result-preview-image"
              />
              <div className="hb-result-preview-caption">Sample figure preview</div>
            </>
          ) : (
            <div className="hb-result-preview-placeholder">Figure preview unavailable</div>
          )}
        </section>

        <section className="hb-result-card-metadata">
          <div className="hb-result-chip-group" aria-label="Experiment indicators">
            {indicatorChips.map((chip) => (
              <Chip key={chip}>{chip}</Chip>
            ))}
          </div>
          {antibody && <Metadata label="Antibody" value={antibody} mono />}
          {mw && <Metadata label="Molecular weight" value={mw} mono />}
          {data.uniprot_id && <Metadata label="UniProt" value={data.uniprot_id} mono />}
          {(data.figure_label || data.page || sourceId) && (
            <Metadata
              label="Source"
              mono
              value={
                <>
                  {data.figure_label && <span>{data.figure_label}</span>}
                  {data.page && <span>Page {data.page}</span>}
                  {sourceId && <span>DOI: {sourceId}</span>}
                </>
              }
            />
          )}
        </section>
      </div>
    </div>
  );
}

'use client';

// "Why HiveBlot says this" — full provenance for one Evidence Record, plus the
// researcher feedback controls. Feedback is stored BESIDE the AI extraction
// (separate table, insert-only role); a correction never mutates the record.
// Uncertainty rendering rule: silence = settled. Only AMBIGUOUS (?),
// CONFLICTING (⚠) and MISSING (—) get glyphs; disagreement is always shown,
// never silently resolved.

import { useEffect, useState } from 'react';

import { formatLaneLabel } from '@/components/DatabaseResultCard';
import { submitFeedback } from '@/lib/feedback';

const MONO = 'var(--font-mono), monospace';
const SERIF = 'var(--font-serif), serif';
const LABEL = 'var(--text-subtle)';
const TEXT = 'var(--text-primary)';
const DIM = 'var(--text-secondary)';
const TEAL = 'var(--accent)';
const GOLD = 'var(--warning)';
const RED = 'var(--error)';

interface FieldEvidence {
  value: unknown;
  confidence: number | null;
  status: string | null;
  sources: { type?: string; text?: string }[];
  candidates: { value?: unknown; source_type?: string; confidence?: number }[];
}

interface PriorFeedback {
  feedback_id: number;
  created_at: string;
  feedback_scope: string;
  field_name?: string | null;
  model_value?: string | null;
  feedback_type?: string | null;
  suggested_value?: string | null;
  comment?: string | null;
}

interface RecordDetailData {
  id: number;
  stable_row_key?: string | null;
  paper_id?: string | null;
  title?: string | null;
  doi?: string | null;
  pmcid?: string | null;
  pmid?: string | null;
  figure_label?: string | null;
  panel_label?: string | null;
  page?: number | null;
  figure_caption?: string | null;
  image_crop_ref?: string | null;
  raw_target_name?: string | null;
  canonical_target?: string | null;
  uniprot_id?: string | null;
  modification_label?: string | null;
  experiment_type?: string | null;
  cell_line?: string | null;
  organism?: string | null;
  fields: Record<string, FieldEvidence>;
  antibodies: {
    target?: string | null; vendor?: string | null; catalog_number?: string | null;
    clone?: string | null; dilution?: string | null; role?: string | null;
    phospho_specific?: boolean | null; association_confidence?: number | null;
    source_text?: string | null;
  }[];
  bands: {
    lane_index?: number | null; lane_condition?: string | null; band_state?: string | null;
    lane_dose?: string | null; lane_duration?: string | null;
    band_pattern?: string | null; band_count?: number | null; band_notes?: string | null;
  }[];
  record_status?: string | null;
  needs_review?: boolean | null;
  anomaly_flags: { code?: string | null; message?: string | null }[];
}

// Friendly labels for the audit list; order = display order.
const FIELD_LABELS: [string, string][] = [
  ['canonical_target', 'Protein identity'],
  ['uniprot_id', 'UniProt'],
  ['modification_type', 'Modification'],
  ['residue_position', 'Phosphosite'],
  ['experiment_type', 'Experiment type'],
  ['ip_bait_protein', 'IP bait'],
  ['cell_line', 'Cell line'],
  ['organism', 'Organism'],
  ['treatment_name', 'Treatment'],
  ['dose', 'Dose'],
  ['duration', 'Duration'],
  ['reported_molecular_weight_kda', 'Reported MW (paper)'],
  ['expected_molecular_weight_kda', 'Expected MW (UniProt reference)'],
];

const SOURCE_NAMES: Record<string, string> = {
  antibody: 'antibody', figure_caption: 'caption', methods: 'methods',
  model_target: 'row label', image: 'image', uniprot_reference: 'UniProt',
};

function statusGlyph(status?: string | null): { g: string; color: string; title: string } | null {
  if (status === 'AMBIGUOUS') return { g: '?', color: GOLD, title: 'Ambiguous — unsettled best guess' };
  if (status === 'CONFLICTING') return { g: '⚠', color: RED, title: 'Sources disagree — no settled value' };
  if (status === 'MISSING') return { g: '—', color: LABEL, title: 'Not reported' };
  return null; // SUPPORTED: silence = settled
}

function fmtValue(name: string, fe: FieldEvidence, all: Record<string, FieldEvidence>): string {
  if (name === 'residue_position') {
    const res = all['residue']?.value;
    if (fe.value == null && !res) return '';
    return `${res ?? ''}${fe.value ?? ''}`;
  }
  if (name === 'dose') {
    const unit = all['dose_unit']?.value;
    return fe.value == null ? '' : `${fe.value}${unit ? ` ${unit}` : ''}`;
  }
  if (name === 'duration') {
    const unit = all['duration_unit']?.value;
    return fe.value == null ? '' : `${fe.value}${unit ? ` ${unit}` : ''}`;
  }
  if (fe.value == null) return '';
  if (Array.isArray(fe.value)) return fe.value.join(', ');
  return String(fe.value);
}

// --- small building blocks ---------------------------------------------------

function Btn({ onClick, color, children, title }: {
  onClick: () => void; color?: string; children: React.ReactNode; title?: string;
}) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      title={title}
      style={{
        background: 'transparent', border: `1px solid ${color || 'rgba(255,255,255,.2)'}`,
        color: color || DIM, borderRadius: '4px', padding: '1px 7px',
        fontFamily: MONO, fontSize: '10px', cursor: 'pointer', lineHeight: 1.6,
      }}
    >
      {children}
    </button>
  );
}

function CorrectionForm({ placeholder, onSubmit, onCancel, askValue = true }: {
  placeholder: string;
  onSubmit: (value: string, comment: string) => void;
  onCancel: () => void;
  askValue?: boolean;
}) {
  const [value, setValue] = useState('');
  const [comment, setComment] = useState('');
  const input = {
    background: 'var(--input-background)', border: '1px solid var(--border-strong)', color: TEXT,
    borderRadius: '4px', padding: '4px 8px', fontFamily: MONO, fontSize: '11px', width: '100%',
  } as const;
  return (
    <div onClick={(e) => e.stopPropagation()}
         style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px', maxWidth: '420px' }}>
      {askValue && (
        <input style={input} placeholder={placeholder} value={value}
               onChange={(e) => setValue(e.target.value)} />
      )}
      <input style={input} placeholder="Optional comment" value={comment}
             onChange={(e) => setComment(e.target.value)} />
      <div style={{ display: 'flex', gap: '6px' }}>
        <Btn color={TEAL} onClick={() => onSubmit(value, comment)}>Submit</Btn>
        <Btn onClick={onCancel}>Cancel</Btn>
      </div>
    </div>
  );
}

function Ack() {
  return <span style={{ fontFamily: MONO, fontSize: '10px', color: TEAL }}>✓ recorded — thank you</span>;
}

// --- one auditable field row --------------------------------------------------

// Prior researcher feedback for one field — rendered as a clearly separated
// annotation. It NEVER alters the HiveBlot extraction shown above it.
function PriorFeedbackNote({ items }: { items: PriorFeedback[] }) {
  if (!items.length) return null;
  return (
    <div style={{
      marginTop: '5px', padding: '5px 10px', borderLeft: `2px solid ${GOLD}`,
      background: 'rgba(224,178,60,.05)',
    }}>
      <div style={{ fontFamily: MONO, fontSize: '9px', fontWeight: 600, color: GOLD, letterSpacing: '0.5px' }}>
        RESEARCHER FEEDBACK (stored beside the extraction — does not change it)
      </div>
      {items.map((f) => (
        <div key={f.feedback_id} style={{ fontFamily: SERIF, fontSize: '11px', color: TEXT, marginTop: '2px' }}>
          {f.feedback_type === 'correct' ? '✓ marked correct'
            : f.feedback_type === 'not_useful' ? 'marked not useful'
            : f.feedback_type === 'missing_context' ? 'flagged missing context'
            : `✗ marked incorrect${f.suggested_value ? ` — suggested: “${f.suggested_value}”` : ''}`}
          {f.comment ? <span style={{ color: DIM }}> · “{f.comment}”</span> : null}
          <span style={{ fontFamily: MONO, fontSize: '9px', color: LABEL }}> · {f.created_at.slice(0, 10)}</span>
        </div>
      ))}
    </div>
  );
}

// Human-readable reason a field is CONFLICTING, generated ONLY from the
// structured candidates (never selects a winner).
function conflictSummary(label: string, fe: FieldEvidence): string | null {
  if (fe.status !== 'CONFLICTING' || fe.candidates.length < 2) return null;
  const parts = fe.candidates.map((c) =>
    `“${String(c.value ?? 'none')}” via ${SOURCE_NAMES[c.source_type || ''] || c.source_type || 'unknown source'}`);
  return `Why unresolved: the sources make different claims about ${label.toLowerCase()} — ${parts.join(' vs ')}. ` +
    `Neither independently settles it, so HiveBlot records no value rather than choosing.`;
}

function FieldRow({ name, label, fe, all, recordId, paperId, prior, stableRowKey }: {
  name: string; label: string; fe: FieldEvidence;
  all: Record<string, FieldEvidence>; recordId: number; paperId?: string | null;
  prior?: PriorFeedback[]; stableRowKey?: string | null;
}) {
  const [mode, setMode] = useState<'idle' | 'correcting' | 'done'>('idle');
  const glyph = statusGlyph(fe.status);
  const value = fmtValue(name, fe, all);
  const snippet = fe.sources.find((s) => s.text)?.text || '';
  const srcName = fe.sources.length
    ? SOURCE_NAMES[fe.sources[0].type || ''] || fe.sources[0].type
    : null;

  const send = (feedback_type: string, suggested?: string, comment?: string) => {
    submitFeedback({
      feedback_scope: 'field', record_id: recordId, stable_row_key: stableRowKey, paper_id: paperId,
      field_name: name, model_value: value || null, feedback_type,
      suggested_value: suggested || null, comment: comment || null,
      ui_location: 'evidence_panel',
    });
    setMode('done');
  };

  // Lane-series fields (time course / dose response): the per-lane values are
  // NOT competing candidates for one scalar — the experiment-level value
  // genuinely varies by lane. Render as a range pointing to the lane strip.
  const isLaneSeries =
    fe.status === 'AMBIGUOUS' && fe.candidates.length >= 2 &&
    fe.candidates.every((c) => c.source_type === 'lane_series');
  const seriesText = isLaneSeries
    ? (() => {
        const nums = fe.candidates.map((c) => Number(c.value)).filter((n) => !Number.isNaN(n));
        const unit = all[`${name}_unit`]?.value ? ` ${all[`${name}_unit`]!.value}` : '';
        return nums.length
          ? `varies by lane: ${Math.min(...nums)}–${Math.max(...nums)}${unit} (see lanes below)`
          : 'varies by lane (see lanes below)';
      })()
    : null;

  return (
    <div style={{ padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,.05)' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
        <span style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: LABEL, letterSpacing: '0.4px', minWidth: '180px' }}>
          {label.toUpperCase()}
        </span>
        <span style={{ fontFamily: SERIF, fontSize: '13px', color: value || seriesText ? TEXT : LABEL }}>
          {seriesText || value || (fe.status === 'CONFLICTING' ? 'unsettled — sources disagree' : 'not reported')}
        </span>
        {glyph && (
          <span title={glyph.title} style={{ fontFamily: MONO, fontSize: '11px', color: glyph.color, fontWeight: 600 }}>
            {glyph.g}
          </span>
        )}
        {srcName && (
          <span style={{ fontFamily: MONO, fontSize: '9px', color: LABEL }}>via {srcName}</span>
        )}
        <span style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
          {mode === 'done' ? <Ack /> : mode === 'idle' && (
            <>
              <Btn color={TEAL} title="Correct / useful" onClick={() => send('correct')}>✓</Btn>
              <Btn color={RED} title="Incorrect — suggest a correction" onClick={() => setMode('correcting')}>✗</Btn>
              <Btn title="Not useful to me" onClick={() => send('not_useful')}>not useful</Btn>
            </>
          )}
        </span>
      </div>
      {snippet && (
        <div style={{ fontFamily: SERIF, fontSize: '11px', color: DIM, marginTop: '3px', fontStyle: 'italic' }}>
          “{snippet.length > 180 ? snippet.slice(0, 180) + '…' : snippet}”
        </div>
      )}
      {fe.status === 'CONFLICTING' && conflictSummary(label, fe) && (
        <div style={{ fontFamily: SERIF, fontSize: '11.5px', color: DIM, marginTop: '4px', lineHeight: 1.45 }}>
          {conflictSummary(label, fe)}
        </div>
      )}
      {!isLaneSeries && (fe.status === 'CONFLICTING' || fe.status === 'AMBIGUOUS') && fe.candidates.length > 0 && (
        <div style={{ marginTop: '6px' }}>
          <div style={{ fontFamily: MONO, fontSize: '9px', color: fe.status === 'CONFLICTING' ? RED : GOLD, marginBottom: '4px' }}>
            {fe.status === 'CONFLICTING' ? 'COMPETING CLAIMS — HiveBlot did not pick one. Which is right?' : 'CANDIDATES — unsettled. Which is right?'}
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {fe.candidates.map((c, i) => (
              <button key={i}
                onClick={() => send('incorrect', String(c.value ?? 'none'), 'picked from candidates')}
                style={{
                  background: 'rgba(255,255,255,.04)', border: '1px solid var(--border-strong)',
                  borderRadius: '4px', padding: '4px 10px', cursor: 'pointer', textAlign: 'left',
                }}>
                <span style={{ fontFamily: SERIF, fontSize: '12px', color: TEXT }}>{String(c.value ?? 'none')}</span>
                <span style={{ fontFamily: MONO, fontSize: '9px', color: LABEL, marginLeft: '6px' }}>
                  via {SOURCE_NAMES[c.source_type || ''] || c.source_type}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
      {mode === 'correcting' && (
        <CorrectionForm placeholder={`Corrected ${label.toLowerCase()}`}
          onSubmit={(v, c) => send('incorrect', v, c)} onCancel={() => setMode('idle')} />
      )}
      <PriorFeedbackNote items={prior || []} />
    </div>
  );
}

// --- main panel ----------------------------------------------------------------

export default function EvidencePanel({ recordId }: { recordId: number }) {
  const [detail, setDetail] = useState<RecordDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missingMode, setMissingMode] = useState<'idle' | 'open' | 'done'>('idle');
  const [flagMode, setFlagMode] = useState<'idle' | 'open' | 'done'>('idle');
  const [flagType, setFlagType] = useState('wrong_interpretation');
  const [cropFailed, setCropFailed] = useState(false);

  const [priorFeedback, setPriorFeedback] = useState<PriorFeedback[]>([]);

  useEffect(() => {
    let alive = true;
    fetch(`/api/record/${recordId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d) => { if (alive) setDetail(d); })
      .catch((e) => { if (alive) setError(String(e.message || e)); });
    // Prior researcher feedback (rehydration). Failure is non-fatal: the
    // evidence still renders; only the annotations are absent.
    fetch(`/api/record/${recordId}/feedback`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => { if (alive) setPriorFeedback(d.items || []); })
      .catch(() => {});
    return () => { alive = false; };
  }, [recordId]);

  const priorByField = new Map<string, PriorFeedback[]>();
  for (const f of priorFeedback) {
    if (f.feedback_scope === 'field' && f.field_name) {
      const k = f.field_name;
      priorByField.set(k, [...(priorByField.get(k) || []), f]);
    }
  }
  const priorRecordScope = priorFeedback.filter((f) => f.feedback_scope !== 'field');

  if (error) {
    return <div style={{ padding: '16px', fontFamily: SERIF, fontSize: '12px', color: DIM }}>
      Evidence unavailable ({error}).
    </div>;
  }
  if (!detail) {
    return <div style={{ padding: '16px', fontFamily: MONO, fontSize: '11px', color: LABEL }}>
      loading evidence…
    </div>;
  }

  const chain = [detail.raw_target_name, detail.canonical_target,
    detail.uniprot_id ? `UniProt ${detail.uniprot_id}` : null].filter(Boolean);

  const RECORD_FLAGS: [string, string][] = [
    ['wrong_interpretation', 'Wrong biological interpretation'],
    ['wrong_experiment_type', 'Wrong experiment type'],
    ['wrong_target_modification', 'Wrong target / modification'],
    ['wrong_phosphosite', 'Wrong phosphosite'],
    ['wrong_antibody_association', 'Wrong antibody association'],
    ['wrong_figure_association', 'Wrong figure association'],
    ['missing_methods_context', 'Missing methods context'],
    ['irrelevant_result', 'Irrelevant search result'],
    ['other', 'Other'],
  ];

  const sect = { fontFamily: MONO, fontSize: '10px', fontWeight: 600 as const, color: TEAL, letterSpacing: '0.6px', margin: '14px 0 4px' };

  return (
    <div style={{ padding: '18px 28px 22px', borderTop: '1px solid var(--border)', backgroundColor: 'var(--input-background)' }}>
      <div style={{ fontFamily: MONO, fontSize: '10px', fontWeight: 600, color: TEAL, letterSpacing: '0.6px' }}>
        WHY HIVEBLOT SAYS THIS
      </div>

      {/* biological normalization chain */}
      {chain.length > 1 && (
        <div style={{ fontFamily: MONO, fontSize: '12px', color: TEXT, marginTop: '8px' }}>
          {chain.join('  →  ')}
        </div>
      )}

      {/* figure / caption evidence */}
      {(detail.figure_caption || detail.image_crop_ref) && (
        <div>
          <div style={sect}>FIGURE EVIDENCE</div>
          {detail.image_crop_ref && !cropFailed && (
            // The actual panel this evidence refers to. On any error (crop
            // archive absent in a deployment) fall back to the filename note.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`/api/record/${recordId}/crop`}
              alt={`Panel crop for ${detail.raw_target_name ?? 'this record'}`}
              onError={() => setCropFailed(true)}
              style={{
                maxWidth: '520px', width: '100%', borderRadius: '4px',
                border: '1px solid var(--border-strong)', marginBottom: '6px',
                backgroundColor: 'var(--figure-background)',
              }}
            />
          )}
          {detail.image_crop_ref && cropFailed && (
            <div style={{ fontFamily: MONO, fontSize: '10px', color: LABEL }}>
              panel crop: {detail.image_crop_ref.split('/').slice(-1)[0]} (image not available in this deployment)
            </div>
          )}
          {detail.figure_caption && (
            <div style={{ fontFamily: SERIF, fontSize: '12px', color: TEXT, lineHeight: 1.45, marginTop: '4px' }}>
              {detail.figure_caption}
            </div>
          )}
        </div>
      )}

      {/* field-level audit list */}
      <div style={sect}>FIELD-LEVEL EVIDENCE — mark anything wrong</div>
      <div>
        {FIELD_LABELS.filter(([k]) => detail.fields[k]).map(([k, label]) => (
          <FieldRow key={k} name={k} label={label} fe={detail.fields[k]} all={detail.fields}
                    prior={priorByField.get(k)} stableRowKey={detail.stable_row_key}
                    recordId={detail.id} paperId={detail.paper_id} />
        ))}
      </div>

      {/* antibodies */}
      {detail.antibodies.length > 0 && (
        <div>
          <div style={sect}>ANTIBODIES</div>
          {detail.antibodies.map((ab, i) => (
            <div key={i} style={{ fontFamily: SERIF, fontSize: '12px', color: TEXT, padding: '3px 0' }}>
              <span style={{ fontFamily: MONO, fontSize: '10px', color: ab.role === 'immunoprecipitation' ? GOLD : LABEL }}>
                [{ab.role === 'immunoprecipitation' ? 'IP bait' : 'detection'}]
              </span>{' '}
              {ab.target}
              {ab.vendor ? ` — ${ab.vendor}` : ''}
              {ab.catalog_number ? ` · #${ab.catalog_number}` : ''}
              {ab.dilution ? ` · ${ab.dilution}` : ''}
              {ab.phospho_specific ? <span style={{ color: TEAL }}> · phospho-specific</span> : ''}
              {ab.association_confidence != null && ab.association_confidence < 0.8 && (
                <span style={{ fontFamily: MONO, fontSize: '9px', color: GOLD }}>
                  {' '}· association uncertain
                </span>
              )}
              {ab.source_text && (
                <div style={{ fontFamily: SERIF, fontSize: '11px', color: DIM, fontStyle: 'italic' }}>
                  “{ab.source_text}”
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* lanes */}
      {detail.bands.length > 0 && (
        <div>
          <div style={sect}>LANES (band presence — categorical, not densitometry)</div>
          {detail.bands.some((b) => b.band_pattern) && (
            <div style={{ fontFamily: SERIF, fontSize: '11px', color: DIM, marginBottom: '6px', fontStyle: 'italic' }}>
              Pattern is descriptive (what the blot shows{detail.bands.find((b) => b.band_notes)?.band_notes ? `: “${detail.bands.find((b) => b.band_notes)?.band_notes}”` : ''}) — no isoform or cleavage interpretation is implied.
            </div>
          )}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {detail.bands.map((b, i) => (
              <span key={i} style={{
                fontFamily: MONO, fontSize: '10px', padding: '3px 8px', borderRadius: '4px',
                border: '1px solid var(--border)',
                color: b.band_state === 'present' ? TEAL : b.band_state === 'absent' ? RED : GOLD,
              }}>
                {formatLaneLabel(b.lane_condition) || `lane ${b.lane_index}`}: {b.band_state || '?'}
                {b.band_pattern && (
                  <span style={{ color: TEXT }}>{' · '}{b.band_pattern}</span>
                )}
                {(b.lane_dose || b.lane_duration) && (
                  <span style={{ color: LABEL }}>
                    {' · '}{[b.lane_dose, b.lane_duration].filter(Boolean).join(' · ')}
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* anomalies */}
      {detail.anomaly_flags.length > 0 && (
        <div>
          <div style={{ ...sect, color: GOLD }}>FLAGS</div>
          {detail.anomaly_flags.map((a, i) => (
            <div key={i} style={{ fontFamily: MONO, fontSize: '11px', color: GOLD }}>
              {a.code}{a.message ? ` — ${a.message}` : ''}
            </div>
          ))}
        </div>
      )}

      {/* record-level actions */}
      <div style={{ display: 'flex', gap: '10px', marginTop: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        {missingMode === 'done' ? <Ack /> : missingMode === 'idle' ? (
          <Btn color={TEAL} onClick={() => setMissingMode('open')}>+ Missing information?</Btn>
        ) : null}
        {flagMode === 'done' ? <Ack /> : flagMode === 'idle' ? (
          <Btn color={GOLD} onClick={() => setFlagMode('open')}>⚑ Flag this result</Btn>
        ) : null}
        {priorRecordScope.length > 0 && (
          <span style={{ fontFamily: MONO, fontSize: '9px', color: GOLD }}>
            {priorRecordScope.length} prior record-level feedback item{priorRecordScope.length > 1 ? 's' : ''} on file
          </span>
        )}
        {detail.doi && (
          <a href={`https://doi.org/${detail.doi}`} target="_blank" rel="noreferrer"
             style={{ fontFamily: MONO, fontSize: '10px', color: DIM, marginLeft: 'auto' }}>
            {detail.pmcid ? `${detail.pmcid} · ` : ''}doi.org/{detail.doi} ↗
          </a>
        )}
      </div>
      {missingMode === 'open' && (
        <div style={{ marginTop: '8px' }}>
          <div style={{ fontFamily: SERIF, fontSize: '12px', color: DIM }}>
            What information do you wish HiveBlot showed here? (e.g. antibody dilution, IP bait,
            membrane type, exposure time, replicates, knockout control, species reactivity, epitope)
          </div>
          <CorrectionForm placeholder="Field you need (e.g. antibody dilution)"
            onSubmit={(v, c) => {
              submitFeedback({
                feedback_scope: 'missing_field', record_id: detail.id, stable_row_key: detail.stable_row_key, paper_id: detail.paper_id,
                field_name: v || 'unspecified', comment: c || null, ui_location: 'evidence_panel',
              });
              setMissingMode('done');
            }}
            onCancel={() => setMissingMode('idle')} />
        </div>
      )}
      {flagMode === 'open' && (
        <div style={{ marginTop: '8px' }} onClick={(e) => e.stopPropagation()}>
          <select value={flagType} onChange={(e) => setFlagType(e.target.value)}
            style={{ background: 'var(--input-background)', color: TEXT, border: '1px solid var(--border-strong)',
                     borderRadius: '4px', fontFamily: MONO, fontSize: '11px', padding: '4px 8px' }}>
            {RECORD_FLAGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <CorrectionForm placeholder="" askValue={false}
            onSubmit={(_v, c) => {
              submitFeedback({
                feedback_scope: 'record', record_id: detail.id, stable_row_key: detail.stable_row_key, paper_id: detail.paper_id,
                feedback_type: flagType, comment: c || null, ui_location: 'evidence_panel',
              });
              setFlagMode('done');
            }}
            onCancel={() => setFlagMode('idle')} />
        </div>
      )}
    </div>
  );
}

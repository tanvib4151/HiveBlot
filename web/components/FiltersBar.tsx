'use client';

// Optional advanced biological filters. Natural-language search stays primary;
// this composes a structured query string that the backend's deterministic
// biological parser (bio_query.py) already understands, so no API shape changes
// are needed when these controls move between layouts.

import type { ReactNode } from 'react';

const MONO = 'var(--font-mono), monospace';
const SANS = 'var(--font-sans), sans-serif';
const LABEL = 'var(--text-subtle)';
const TEAL = 'var(--accent)';

export interface SearchFilters {
  protein: string;
  site: string;
  expType: string;
  cellLine: string;
  vendor: string;
  catalog: string;
  needsReview: boolean;
}

export type SearchFilterKey = keyof SearchFilters;

export const EMPTY_SEARCH_FILTERS: SearchFilters = {
  protein: '',
  site: '',
  expType: '',
  cellLine: '',
  vendor: '',
  catalog: '',
  needsReview: false,
};

export interface ActiveFilterChip {
  key: SearchFilterKey;
  label: string;
  value: string;
}

const EXPERIMENT_TYPES = [
  ['', 'Any experiment'],
  ['phospho', 'Phospho-Western'],
  ['co-IP', 'Co-IP'],
  ['loading control', 'Loading control'],
] as const;

const EXPERIMENT_LABELS: Record<string, string> = Object.fromEntries(EXPERIMENT_TYPES);

export function emptySearchFilters(): SearchFilters {
  return { ...EMPTY_SEARCH_FILTERS };
}

export function hasFilters(filters: SearchFilters): boolean {
  return Boolean(
    filters.protein.trim() ||
      filters.site.trim() ||
      filters.expType ||
      filters.cellLine.trim() ||
      filters.vendor.trim() ||
      filters.catalog.trim() ||
      filters.needsReview
  );
}

export function buildFilterQuery(filters: SearchFilters): string {
  return [
    filters.expType,
    filters.protein.trim(),
    filters.site.trim(),
    filters.cellLine.trim(),
    filters.vendor.trim(),
    filters.catalog.trim() ? `#${filters.catalog.trim().replace(/^#/, '')}` : '',
    filters.needsReview ? 'needs review' : '',
  ]
    .filter(Boolean)
    .join(' ');
}

export function activeFilterChips(filters: SearchFilters): ActiveFilterChip[] {
  const chips: ActiveFilterChip[] = [];
  if (filters.protein.trim()) chips.push({ key: 'protein', label: 'Protein', value: filters.protein.trim() });
  if (filters.site.trim()) chips.push({ key: 'site', label: 'Site', value: filters.site.trim() });
  if (filters.expType) {
    chips.push({ key: 'expType', label: 'Experiment', value: EXPERIMENT_LABELS[filters.expType] || filters.expType });
  }
  if (filters.cellLine.trim()) chips.push({ key: 'cellLine', label: 'Cell line', value: filters.cellLine.trim() });
  if (filters.vendor.trim()) chips.push({ key: 'vendor', label: 'Vendor', value: filters.vendor.trim() });
  if (filters.catalog.trim()) chips.push({ key: 'catalog', label: 'Catalog', value: `#${filters.catalog.trim().replace(/^#/, '')}` });
  if (filters.needsReview) chips.push({ key: 'needsReview', label: 'Review', value: 'Needs review' });
  return chips;
}

export function clearFilter(filters: SearchFilters, key: SearchFilterKey): SearchFilters {
  return { ...filters, [key]: EMPTY_SEARCH_FILTERS[key] };
}

interface FiltersBarProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
  onApply: () => void;
  onClearField: (key: SearchFilterKey) => void;
  onReset: () => void;
  open?: boolean;
  onClose?: () => void;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="hb-filter-section">
      <div className="hb-filter-section-title">{title}</div>
      <div className="hb-filter-section-fields">{children}</div>
    </section>
  );
}

function ClearFieldButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" className="hb-filter-clear-field" onClick={onClick} aria-label={label}>
      x
    </button>
  );
}

function TextFilter({
  label,
  value,
  placeholder,
  onChange,
  onClear,
}: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
  onClear: () => void;
}) {
  return (
    <label className="hb-filter-field">
      <span>{label}</span>
      <span className="hb-filter-input-wrap">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="hb-filter-input"
        />
        {value && <ClearFieldButton onClick={onClear} label={`Clear ${label}`} />}
      </span>
    </label>
  );
}

export default function FiltersBar({
  filters,
  onChange,
  onApply,
  onClearField,
  onReset,
  open = false,
  onClose,
}: FiltersBarProps) {
  const setFilter = <K extends SearchFilterKey>(key: K, value: SearchFilters[K]) => {
    onChange({ ...filters, [key]: value });
  };
  const hasAnyFilter = hasFilters(filters);

  return (
    <aside
      id="hb-search-filters"
      className={`hb-filter-sidebar${open ? ' is-open' : ''}`}
      aria-label="Search filters"
    >
      <div className="hb-filter-mobile-header">
        <span>Filters</span>
        <button type="button" onClick={onClose} aria-label="Close filters">
          &times;
        </button>
      </div>
      <div className="hb-filter-sidebar-heading">
        <div>
          <div style={{ fontFamily: MONO, fontSize: '11px', fontWeight: 600, color: TEAL }}>
            FILTERS
          </div>
          <div style={{ fontFamily: SANS, fontSize: '12px', color: LABEL, marginTop: '4px', lineHeight: 1.35 }}>
            Applied when you press Apply.
          </div>
        </div>
        <button type="button" onClick={onReset} disabled={!hasAnyFilter} className="hb-filter-reset">
          Reset
        </button>
      </div>

      <Section title="Biology">
        <TextFilter
          label="Protein"
          value={filters.protein}
          placeholder="STAT3"
          onChange={(value) => setFilter('protein', value)}
          onClear={() => onClearField('protein')}
        />
        <TextFilter
          label="Site / modification"
          value={filters.site}
          placeholder="Tyr705"
          onChange={(value) => setFilter('site', value)}
          onClear={() => onClearField('site')}
        />
        <label className="hb-filter-field">
          <span>Experiment</span>
          <span className="hb-filter-input-wrap">
            <select
              value={filters.expType}
              onChange={(e) => setFilter('expType', e.target.value)}
              className="hb-filter-input"
            >
              {EXPERIMENT_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            {filters.expType && <ClearFieldButton onClick={() => onClearField('expType')} label="Clear Experiment" />}
          </span>
        </label>
      </Section>

      <Section title="Sample">
        <TextFilter
          label="Cell line"
          value={filters.cellLine}
          placeholder="Hep3B"
          onChange={(value) => setFilter('cellLine', value)}
          onClear={() => onClearField('cellLine')}
        />
      </Section>

      <Section title="Antibody">
        <TextFilter
          label="Vendor"
          value={filters.vendor}
          placeholder="CST"
          onChange={(value) => setFilter('vendor', value)}
          onClear={() => onClearField('vendor')}
        />
        <TextFilter
          label="Catalog number"
          value={filters.catalog}
          placeholder="9145"
          onChange={(value) => setFilter('catalog', value)}
          onClear={() => onClearField('catalog')}
        />
      </Section>

      <Section title="Review">
        <label className="hb-filter-checkbox">
          <input
            type="checkbox"
            checked={filters.needsReview}
            onChange={(e) => setFilter('needsReview', e.target.checked)}
          />
          <span>Needs review</span>
          {filters.needsReview && <ClearFieldButton onClick={() => onClearField('needsReview')} label="Clear Needs review" />}
        </label>
      </Section>

      <button type="button" onClick={onApply} disabled={!hasAnyFilter} className="hb-filter-apply">
        Apply
      </button>
    </aside>
  );
}

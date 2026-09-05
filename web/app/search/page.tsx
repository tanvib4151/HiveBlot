'use client';

import { useState, useEffect } from 'react';
import { SearchInput } from '@/components/SearchInput';
import DatabaseResultCard, { type LaneSummary } from '@/components/DatabaseResultCard';
import FiltersBar, {
  activeFilterChips,
  buildFilterQuery,
  clearFilter,
  emptySearchFilters,
  hasFilters,
  type SearchFilterKey,
  type SearchFilters,
} from '@/components/FiltersBar';
import SearchFeedback from '@/components/SearchFeedback';
import BetaFeedback from '@/components/BetaFeedback';

interface DatabaseResult {
  id: number;
  paper_id: string;
  page: number | null;
  western_blot_type: string;
  sample: string;
  organism: string | null;
  treatment_context: string | null;
  figure_label: string | null;
  target: string;
  condition: string;
  band_detected: boolean;
  confidence: number | null;
  // Evidence Record extras used for grouping / lane display (optional —
  // legacy rows simply lack them).
  image_crop_ref?: string | null;
  lane_condition?: string | null;
  band_state?: string | null;
  experiment_type?: string | null;
  cell_line?: string | null;
  modification_label?: string | null;
  stable_row_key?: string | null;
}

// One card per EXPERIMENT, not per lane row: a 6-lane time course reads as one
// result with a lane strip, not 6 near-identical cards.
//
// The card boundary IS the experiment identity that researcher feedback keys
// to: `stable_row_key` is `<experiment hash>:<lane index>`, so the hash half
// groups the lanes. Deriving the card from a separate composite key used to be
// a second, parallel notion of "one experiment" — and the two disagreed. One
// crop in PMC12706926 (page_004_cand_0025) prints H1792 and A549 side by side;
// grouping split them on cell line while the identity hash did not, so feedback
// left on the H1792 arm could rehydrate onto the A549 arm. The identity hash
// now carries the sample, and grouping reads that same hash, so the two cannot
// drift apart again.
//
// The composite fallback below is for rows with no stable_row_key (legacy rows
// predating migration 003). It keeps its own cell-line component for exactly
// the reason above.
interface ResultGroup {
  first: DatabaseResult;
  lanes: LaneSummary[];
}

function groupResults(rows: DatabaseResult[]): ResultGroup[] {
  const groups = new Map<string, ResultGroup>();
  for (const r of rows) {
    const key = r.stable_row_key
      ? r.stable_row_key.split(':')[0]
      : [
          r.paper_id,
          r.image_crop_ref ?? `p${r.page}`,
          r.target,
          r.experiment_type ?? '',
          r.cell_line ?? r.sample ?? '',
          r.modification_label ?? '',
        ].join('|');
    const lane: LaneSummary = {
      condition: r.lane_condition ?? r.condition ?? null,
      band_state: r.band_state ?? (r.band_detected == null ? null : r.band_detected ? 'present' : 'absent'),
    };
    const g = groups.get(key);
    if (g) g.lanes.push(lane);
    else groups.set(key, { first: r, lanes: [lane] });
  }
  return [...groups.values()];
}

interface SearchResponse {
  count: number;
  results: DatabaseResult[];
  question?: string;
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState<DatabaseResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [draftFilters, setDraftFilters] = useState<SearchFilters>(emptySearchFilters);
  const [appliedFilters, setAppliedFilters] = useState<SearchFilters>(emptySearchFilters);

  // Support /search?q=… (home-page searches route here so there is ONE
  // results surface — the Evidence Record card, not the legacy table).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) handleSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!filtersOpen) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFiltersOpen(false);
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [filtersOpen]);

  const clearSearchUrl = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete('q');
    window.history.replaceState(null, '', url.toString());
  };

  const clearResults = () => {
    setQuery('');
    setShowResults(false);
    setResults([]);
    setError(null);
    clearSearchUrl();
  };

  async function handleSearch(searchQuery: string) {
    setQuery(searchQuery);
    if (!searchQuery.trim()) {
      clearResults();
      return;
    }

    // Submitted searches are shareable/refreshable: reflect the query in the
    // URL (replaceState — no history spam; only SUBMITTED queries land here,
    // typing never does).
    const url = new URL(window.location.href);
    url.searchParams.set('q', searchQuery);
    window.history.replaceState(null, '', url.toString());

    setLoading(true);
    setError(null);
    setShowResults(true);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data: SearchResponse = await response.json();
      setResults(data.results || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  const handlePrimarySearch = (searchQuery: string) => {
    setDraftFilters(emptySearchFilters());
    setAppliedFilters(emptySearchFilters());
    handleSearch(searchQuery);
  };

  const handleApplyFilters = () => {
    const filterQuery = buildFilterQuery(draftFilters);
    if (!filterQuery) return;
    setAppliedFilters({ ...draftFilters });
    setFiltersOpen(false);
    handleSearch(filterQuery);
  };

  const handleClearDraftFilter = (key: SearchFilterKey) => {
    setDraftFilters((current) => clearFilter(current, key));
  };

  const handleClearAppliedFilter = (key: SearchFilterKey) => {
    const next = clearFilter(appliedFilters, key);
    setDraftFilters(next);
    setAppliedFilters(next);
    const filterQuery = buildFilterQuery(next);
    if (filterQuery) handleSearch(filterQuery);
    else clearResults();
  };

  const handleResetFilters = () => {
    setDraftFilters(emptySearchFilters());
    if (hasFilters(appliedFilters)) {
      setAppliedFilters(emptySearchFilters());
      clearResults();
    }
  };

  const groups = groupResults(results);
  const filterChips = activeFilterChips(appliedFilters);

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--background)', paddingTop: '16px' }}>
      {/* Search Bar */}
      <div className="hb-search-workspace-header">
        <div className="hb-search-workspace-grid">
          <div className="hb-search-sidebar-spacer" aria-hidden="true" />
          <SearchInput
            heading="Search Western blot evidence"
            placeholder="Search protein, phosphosite, antibody, cell line..."
            onSearch={handlePrimarySearch}
            initialValue={query}
            examples={['STAT3 Tyr705', 'Hep3B', 'CST #9145']}
            loading={loading}
          />
        </div>
      </div>

      <div className="hb-search-body">
        <button
          type="button"
          className={`hb-filter-backdrop${filtersOpen ? ' is-open' : ''}`}
          onClick={() => setFiltersOpen(false)}
          aria-label="Close filters"
          tabIndex={filtersOpen ? 0 : -1}
        />
        <FiltersBar
          filters={draftFilters}
          onChange={setDraftFilters}
          onApply={handleApplyFilters}
          onClearField={handleClearDraftFilter}
          onReset={handleResetFilters}
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
        />

        {/* Results Section */}
        <main className="hb-search-results">
          <button
            type="button"
            className="hb-mobile-filter-trigger"
            onClick={() => setFiltersOpen(true)}
            aria-expanded={filtersOpen}
            aria-controls="hb-search-filters"
          >
            <svg aria-hidden="true" viewBox="0 0 20 20" focusable="false">
              <path d="M3 5h14M5.5 10h9M8 15h4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.6" />
            </svg>
            <span>Filters</span>
            {filterChips.length > 0 && <span className="hb-mobile-filter-count">{filterChips.length}</span>}
          </button>
        {showResults ? (
          <div>
            {/* Results Header */}
            <div className="hb-results-header">
              <div className="hb-results-title">
                <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: '16px', fontWeight: 600, color: 'var(--accent)' }}>RESULTS</span>
                <span style={{ fontFamily: 'var(--font-mono), monospace', fontSize: '16px', fontWeight: 600, color: 'var(--text-subtle)' }}>-</span>
                <span style={{ fontFamily: 'var(--font-serif), serif', fontSize: '20px', fontWeight: 500, color: 'var(--text-primary)' }}>Western Blot Evidence</span>
              </div>
              <p className="hb-results-count">
                {loading
                  ? 'Searching database...'
                  : (() => {
                      const n = groups.length;
                      return `Found ${n} experiment${n !== 1 ? 's' : ''} (${results.length} lane record${results.length !== 1 ? 's' : ''})`;
                    })()}
              </p>
              {filterChips.length > 0 && (
                <div className="hb-active-filters" aria-label="Active filters">
                  {filterChips.map((chip) => (
                    <button
                      key={chip.key}
                      type="button"
                      className="hb-active-filter-chip"
                      onClick={() => handleClearAppliedFilter(chip.key)}
                      aria-label={`Clear ${chip.label}`}
                    >
                      <span>{chip.value}</span>
                      <span aria-hidden="true">x</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Loading State */}
            {loading && (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <div style={{ fontFamily: 'var(--font-serif), serif', fontSize: '16px', color: 'var(--text-secondary)' }}>
                  Querying database...
                </div>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div
                style={{
                  padding: '24px',
                  backgroundColor: 'var(--error-soft)',
                  border: '1px solid var(--error-border)',
                  borderRadius: '8px',
                  color: 'var(--error)',
                  fontFamily: 'var(--font-serif), serif',
                  fontSize: '14px',
                  marginBottom: '40px',
                }}
              >
                Error: {error}
              </div>
            )}

            {/* Results Cards */}
            {!loading && results.length > 0 && (
              <>
                <div className="hb-search-feedback-wrap">
                  <SearchFeedback query={query} />
                </div>
                <div className="hb-result-list">
                  {groups.map((g) => (
                    <DatabaseResultCard key={g.first.id} data={g.first} lanes={g.lanes} />
                  ))}
                </div>
              </>
            )}

            {/* No Results */}
            {!loading && results.length === 0 && !error && (
              <div style={{ textAlign: 'center', paddingTop: '40px', color: 'var(--text-secondary)' }}>
                <p style={{ fontFamily: 'var(--font-serif), serif', fontSize: '16px', lineHeight: 1.6 }}>
                  No matching Western blot evidence was found in the current HiveBlot
                  beta dataset (3 reviewed papers). This does not mean no such evidence
                  exists in the literature — the beta corpus is deliberately small.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', paddingTop: '80px', color: 'var(--text-secondary)' }}>
            <p style={{ fontFamily: 'var(--font-serif), serif', fontSize: '18px', lineHeight: 1.6 }}>
              Enter a natural language query to search for western blot evidence
            </p>
            <p style={{ fontFamily: 'var(--font-serif), serif', fontSize: '14px', marginTop: '12px', color: 'var(--text-subtle)' }}>
              Example: &quot;Show western blot evidence for phospho-TBK1 in p53 wild-type versus p53 knockout mouse embryonic fibroblasts.&quot;
            </p>
          </div>
        )}
        </main>
      </div>
      <BetaFeedback query={query} />
    </div>
  );
}

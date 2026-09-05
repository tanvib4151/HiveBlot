'use client';

import { useRef, useState, type FormEvent } from 'react';

interface SearchInputProps {
  placeholder: string;
  onSearch: (query: string) => void;
  // Populates the box for ?q= deep links / programmatic searches (filters).
  initialValue?: string;
  heading?: string;
  examples?: string[];
  loading?: boolean;
}

export function SearchInput({
  placeholder,
  onSearch,
  initialValue = '',
  heading,
  examples = [],
  loading = false,
}: SearchInputProps) {
  return (
    <SearchInputDraft
      key={initialValue}
      placeholder={placeholder}
      onSearch={onSearch}
      initialValue={initialValue}
      heading={heading}
      examples={examples}
      loading={loading}
    />
  );
}

// EXPLICIT SUBMIT ONLY. Typing never triggers a search: partial biological
// queries change meaning with every token ("phospho STAT3" vs "phospho STAT3
// Tyr705"), so firing mid-typing showed wrong results and burned the shared
// rate limit. Search runs on Enter or the Search button.
function SearchInputDraft({
  placeholder,
  onSearch,
  initialValue,
  heading,
  examples = [],
  loading = false,
}: Required<Pick<SearchInputProps, 'placeholder' | 'onSearch' | 'initialValue'>> &
  Pick<SearchInputProps, 'heading' | 'examples' | 'loading'>) {
  const [query, setQuery] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (loading) return;
    const q = query.trim();
    if (q) onSearch(q);
  };

  const chooseExample = (example: string) => {
    setQuery(example);
    inputRef.current?.focus();
  };

  return (
    <div className="hb-search-input-shell">
      {heading && <div className="hb-search-input-heading">{heading}</div>}
      <form className="hb-search-control" onSubmit={submit} role="search">
        <div className="hb-search-field">
          <svg
            className="hb-search-icon"
            aria-hidden="true"
            viewBox="0 0 20 20"
            focusable="false"
          >
            <path
              d="M8.7 14.4a5.7 5.7 0 1 1 0-11.4 5.7 5.7 0 0 1 0 11.4Zm0-1.6a4.1 4.1 0 1 0 0-8.2 4.1 4.1 0 0 0 0 8.2Zm4.6.3 3.7 3.7"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="1.7"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            placeholder={placeholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search Western blot evidence"
            className="hb-search-input"
          />
          {query && (
            <button
              type="button"
              className="hb-search-clear"
              onClick={() => {
                setQuery('');
                inputRef.current?.focus();
              }}
              aria-label="Clear search"
            >
              &times;
            </button>
          )}
        </div>
        <button
          type="submit"
          className="hb-search-submit"
          disabled={loading || !query.trim()}
          aria-label="Search"
        >
          {loading ? 'SEARCHING...' : 'SEARCH'}
        </button>
      </form>
      {examples.length > 0 && (
        <div className="hb-search-examples" aria-label="Example searches">
          <span>Try:</span>
          {examples.map((example, index) => (
            <span key={example} className="hb-search-example-item">
              {index > 0 && (
                <span className="hb-search-example-separator" aria-hidden="true">
                  &middot;
                </span>
              )}
              <button type="button" onClick={() => chooseExample(example)}>
                {example}
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

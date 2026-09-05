'use client';

// Subtle post-search prompt: "Did HiveBlot understand what you were looking
// for?" Persisted with the query so misunderstood searches become training
// signal for the search layer.

import { useEffect, useState } from 'react';

import { submitFeedback } from '@/lib/feedback';

const MONO = 'var(--font-mono), monospace';
const SANS = 'var(--font-sans), sans-serif';

export default function SearchFeedback({ query }: { query: string }) {
  const [state, setState] = useState<'idle' | 'explain' | 'done'>('idle');
  const [expected, setExpected] = useState('');

  // A new query resets the prompt.
  useEffect(() => { setState('idle'); setExpected(''); }, [query]);

  if (!query) return null;
  if (state === 'done') {
    return (
      <div style={{ fontFamily: MONO, fontSize: '10px', color: 'var(--accent)', padding: '10px 0' }}>
        ✓ thanks — recorded
      </div>
    );
  }

  const send = (type: 'understood_yes' | 'understood_partially' | 'understood_no', comment?: string) => {
    submitFeedback({
      feedback_scope: 'search', search_query: query, feedback_type: type,
      comment: comment || null, ui_location: 'search_results',
    });
    if (type === 'understood_yes' || comment !== undefined) setState('done');
    else setState('explain');
  };

  const btn = {
    background: 'transparent', border: '1px solid var(--border-strong)',
    color: 'var(--text-secondary)', borderRadius: '4px', padding: '2px 10px',
    fontFamily: SANS, fontSize: '10px', fontWeight: 500, cursor: 'pointer',
  } as const;

  return (
    <div style={{ padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {state === 'idle' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontFamily: SANS, fontSize: '12px', color: 'var(--text-subtle)' }}>
            Beta — did HiveBlot understand what you were looking for?
          </span>
          <button style={btn} onClick={() => send('understood_yes')}>Yes</button>
          <button style={btn} onClick={() => send('understood_partially')}>Partially</button>
          <button style={btn} onClick={() => send('understood_no')}>No</button>
        </div>
      )}
      {state === 'explain' && (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            value={expected}
            onChange={(e) => setExpected(e.target.value)}
            placeholder="What did you expect instead?"
            style={{
              background: 'var(--input-background)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)',
              borderRadius: '4px', padding: '4px 10px', fontFamily: SANS, fontSize: '11px', width: '320px',
            }}
          />
          <button style={{ ...btn, color: 'var(--accent)', borderColor: 'var(--accent)' }}
                  onClick={() => send('understood_partially', expected)}>
            Send
          </button>
        </div>
      )}
    </div>
  );
}

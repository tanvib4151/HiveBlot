import { NextRequest, NextResponse } from 'next/server';

// Server-side proxy for researcher feedback. Feedback is stored in a separate
// table (hiveblot_feedback) via an insert-only DB role — it can never mutate
// the AI-extracted records; corrections live BESIDE the AI claim for audit.
const BACKEND_URL = process.env.API_BASE_URL;
const BACKEND_API_KEY = process.env.INTERNAL_API_KEY;

const ALLOWED_KEYS = new Set([
  'feedback_scope', 'record_id', 'stable_row_key', 'paper_id', 'figure_label', 'search_query',
  'field_name', 'model_value', 'feedback_type', 'suggested_value', 'comment',
  'ui_location', 'session_id',
]);

export async function POST(request: NextRequest) {
  if (!BACKEND_URL) {
    return NextResponse.json({ error: 'Not configured' }, { status: 500 });
  }
  try {
    const raw = await request.json();
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(raw || {})) {
      if (ALLOWED_KEYS.has(k)) body[k] = v;
    }
    const resp = await fetch(`${BACKEND_URL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {}),
      },
      body: JSON.stringify(body),
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 502 });
  }
}

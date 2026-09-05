// Client helpers for the researcher-feedback system (beta).
// Anonymous session id only — no login, no PII.

export interface FeedbackPayload {
  feedback_scope: 'field' | 'record' | 'missing_field' | 'search' | 'ui';
  record_id?: number | null;
  stable_row_key?: string | null;
  paper_id?: string | null;
  figure_label?: string | null;
  search_query?: string | null;
  field_name?: string | null;
  model_value?: string | null;
  feedback_type?: string | null;
  suggested_value?: string | null;
  comment?: string | null;
  ui_location?: string | null;
}

export function sessionId(): string {
  if (typeof window === 'undefined') return 'ssr';
  const KEY = 'hiveblot_session';
  let id = window.localStorage.getItem(KEY);
  if (!id) {
    id = Math.random().toString(36).slice(2) + Date.now().toString(36);
    window.localStorage.setItem(KEY, id);
  }
  return id;
}

export async function submitFeedback(payload: FeedbackPayload): Promise<boolean> {
  try {
    const resp = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, session_id: sessionId() }),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

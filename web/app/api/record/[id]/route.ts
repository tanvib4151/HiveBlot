import { NextRequest, NextResponse } from 'next/server';

// Server-side proxy to the backend's record-detail endpoint ("Why does
// HiveBlot say this?"). Same trust model as /api/search: the INTERNAL_API_KEY
// never reaches the browser.
const BACKEND_URL = process.env.API_BASE_URL;
const BACKEND_API_KEY = process.env.INTERNAL_API_KEY;

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!BACKEND_URL) {
    return NextResponse.json({ error: 'Not configured' }, { status: 500 });
  }
  const { id } = await params;
  if (!/^\d+$/.test(id)) {
    return NextResponse.json({ error: 'Invalid record id' }, { status: 400 });
  }
  try {
    const resp = await fetch(`${BACKEND_URL}/records/${id}`, {
      headers: BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {},
    });
    if (!resp.ok) {
      return NextResponse.json({ error: `Backend returned ${resp.status}` }, { status: resp.status });
    }
    return NextResponse.json(await resp.json());
  } catch {
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 502 });
  }
}

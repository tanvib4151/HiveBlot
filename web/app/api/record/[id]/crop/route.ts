import { NextRequest, NextResponse } from 'next/server';

// Streams the record's panel-crop PNG from the backend. Same trust model as
// the other proxies: the INTERNAL_API_KEY never reaches the browser. 404s
// pass through so the evidence panel can fall back to text-only.
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
    const resp = await fetch(`${BACKEND_URL}/records/${id}/crop`, {
      headers: BACKEND_API_KEY ? { Authorization: `Bearer ${BACKEND_API_KEY}` } : {},
    });
    if (!resp.ok) {
      return NextResponse.json({ error: `Backend returned ${resp.status}` }, { status: resp.status });
    }
    return new NextResponse(resp.body, {
      status: 200,
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'private, max-age=3600',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Failed to reach backend' }, { status: 502 });
  }
}

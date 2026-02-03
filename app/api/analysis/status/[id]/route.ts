import { NextRequest, NextResponse } from 'next/server';
import { readStatus, isValidAnalysisId } from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';

/**
 * GET /api/analysis/status/[id]
 * Returns the current status of an analysis.
 * Now reads from Supabase database (performances table).
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const user = await getAuthenticatedUser();
  if (!user) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  const { id } = await params;
  if (!isValidAnalysisId(id)) {
    return NextResponse.json({ error: 'Invalid analysis ID' }, { status: 400 });
  }

  // Read status from database (reads from performances table)
  const status = await readStatus(id);
  if (!status) {
    return NextResponse.json({ error: 'Analysis not found' }, { status: 404 });
  }

  return NextResponse.json(status, {
    headers: { 'Cache-Control': 'no-store' },
  });
}

import { NextRequest, NextResponse } from 'next/server';
import { readResult, readStatus, isValidAnalysisId } from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';

/**
 * GET /api/analysis/results/[id]
 * Returns the complete analysis results for a performance.
 * Now reads from Supabase database (analysis_results table).
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

  // Check status first (reads from performances table)
  const status = await readStatus(id);
  if (!status) {
    return NextResponse.json({ error: 'Analysis not found' }, { status: 404 });
  }

  if (status.status !== 'complete') {
    return NextResponse.json(
      { error: 'Analysis not yet complete', status: status.status },
      { status: 202 }
    );
  }

  // Read result from database (reads from analysis_results table)
  const result = await readResult(id);
  if (!result) {
    return NextResponse.json({ error: 'Results not available' }, { status: 500 });
  }

  // Return frozen JSON - identical on every request
  return NextResponse.json(result, {
    headers: {
      'Cache-Control': 'public, max-age=31536000, immutable',
    },
  });
}

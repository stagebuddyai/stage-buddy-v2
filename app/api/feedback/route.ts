import { NextRequest, NextResponse } from 'next/server';
import { writeFeedback, isValidAnalysisId } from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';

export async function POST(req: NextRequest) {
  const user = await getAuthenticatedUser();
  if (!user) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  let body: {
    analysis_id?: string;
    clarity?: string;
    accuracy?: string;
    additional?: string;
  };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { analysis_id, clarity, accuracy, additional } = body;
  if (!analysis_id || !isValidAnalysisId(analysis_id)) {
    return NextResponse.json({ error: 'Invalid analysis_id' }, { status: 400 });
  }

  const feedback = {
    analysis_id,
    user_id: user.id,
    clarity: clarity || '',
    accuracy: accuracy || '',
    additional: additional || '',
    submitted_at: new Date().toISOString(),
  };

  await writeFeedback(analysis_id, feedback);

  return NextResponse.json({ success: true });
}

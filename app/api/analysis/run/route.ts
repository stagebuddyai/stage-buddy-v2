import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { promises as fs } from 'fs';
import {
  getUploadDir,
  getResultPath,
  writeStatus,
  readStatus,
  isValidAnalysisId,
  ensureDir,
} from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';

export async function POST(req: NextRequest) {
  const user = await getAuthenticatedUser();
  if (!user) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  let body: { analysis_id?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { analysis_id } = body;
  if (!analysis_id || !isValidAnalysisId(analysis_id)) {
    return NextResponse.json({ error: 'Invalid analysis_id' }, { status: 400 });
  }

  // Verify the upload exists
  const uploadDir = getUploadDir(analysis_id);
  let videoFile: string | null = null;
  try {
    const files = await fs.readdir(uploadDir);
    const video = files.find(f => f.startsWith('video.'));
    if (video) {
      videoFile = path.join(uploadDir, video);
    }
  } catch {
    return NextResponse.json({ error: 'Upload not found' }, { status: 404 });
  }

  if (!videoFile) {
    return NextResponse.json({ error: 'Video file not found' }, { status: 404 });
  }

  // Check if already running
  const currentStatus = await readStatus(analysis_id);
  if (currentStatus?.status === 'running') {
    return NextResponse.json({ error: 'Analysis already running' }, { status: 409 });
  }
  if (currentStatus?.status === 'complete') {
    return NextResponse.json({ error: 'Analysis already complete' }, { status: 409 });
  }

  // Update status to running
  await writeStatus(analysis_id, {
    status: 'running',
    started_at: new Date().toISOString(),
  });

  // Prepare output path
  const resultPath = getResultPath(analysis_id);
  await ensureDir(path.dirname(resultPath));

  // Spawn Python orchestrator subprocess (fire and forget)
  const pythonScript = path.join(process.cwd(), 'python', 'run_analysis.py');
  const child = spawn('python3', [
    pythonScript,
    '--video-path', videoFile,
    '--output-path', resultPath,
    '--analysis-id', analysis_id,
  ], {
    detached: true,
    stdio: 'ignore',
  });

  child.unref();

  // Monitor the subprocess result via a background check
  // The Python script writes the result JSON and we detect completion via status file
  // The Python script itself updates the status on completion/failure
  monitorAnalysis(analysis_id, resultPath, child.pid ?? 0);

  return NextResponse.json({ status: 'running', analysis_id });
}

/**
 * Background monitor that checks for analysis completion.
 * Updates status file when the result JSON appears or after timeout.
 */
async function monitorAnalysis(analysisId: string, resultPath: string, pid: number) {
  const MAX_WAIT_MS = 5 * 60 * 1000; // 5 minutes max
  const POLL_INTERVAL_MS = 2000;
  const startTime = Date.now();

  const check = async () => {
    try {
      // Check if result file exists
      await fs.access(resultPath);
      // Result exists - mark complete
      await writeStatus(analysisId, {
        status: 'complete',
        started_at: new Date(startTime).toISOString(),
        completed_at: new Date().toISOString(),
      });
      return;
    } catch {
      // Result not yet available
    }

    if (Date.now() - startTime > MAX_WAIT_MS) {
      // Timeout
      await writeStatus(analysisId, {
        status: 'failed',
        error: 'Analysis timed out after 5 minutes',
        started_at: new Date(startTime).toISOString(),
      });
      return;
    }

    // Continue polling
    setTimeout(check, POLL_INTERVAL_MS);
  };

  setTimeout(check, POLL_INTERVAL_MS);
}

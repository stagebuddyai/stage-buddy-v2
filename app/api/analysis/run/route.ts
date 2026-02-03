import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { promises as fs } from 'fs';
import {
  createPerformance,
  updatePerformanceStatus,
  writeResult,
  isValidAnalysisId,
} from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';
import { createSupabaseServer } from '@/lib/supabase/server';
import type { PerformanceReport } from '@/lib/analysis/types';

// Temporary directory for video processing (still needed by Python script)
const TEMP_DIR = process.env.STAGE_BUDDY_DATA_DIR || '/tmp/stage-buddy';

export async function POST(req: NextRequest) {
  const user = await getAuthenticatedUser();
  if (!user) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  let body: { analysis_id?: string; storage_path?: string; video_extension?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { analysis_id, storage_path, video_extension } = body;
  if (!analysis_id || !isValidAnalysisId(analysis_id)) {
    return NextResponse.json({ error: 'Invalid analysis_id' }, { status: 400 });
  }

  if (!storage_path) {
    return NextResponse.json({ error: 'storage_path is required' }, { status: 400 });
  }

  console.log('[run/route] Starting analysis:', { analysis_id, storage_path, video_extension });

  // Create performance record in database
  const createResult = await createPerformance(analysis_id, user.id, storage_path);
  if (!createResult.success) {
    console.error('[run/route] Failed to create performance record:', createResult.error);
    return NextResponse.json({ error: 'Failed to initialize analysis' }, { status: 500 });
  }

  // Create temporary directory for video processing
  const tempUploadDir = path.join(TEMP_DIR, 'uploads', analysis_id);
  await fs.mkdir(tempUploadDir, { recursive: true });

  const ext = video_extension || 'mp4';
  const videoFile = path.join(tempUploadDir, `video.${ext}`);

  console.log('[run/route] Downloading from Supabase Storage:', storage_path);

  // Use server client with user's session
  const supabase = await createSupabaseServer();
  const { data, error: downloadError } = await supabase.storage
    .from('sb-uploads')
    .download(storage_path);

  if (downloadError || !data) {
    console.error('[run/route] Storage download error:', downloadError);
    await updatePerformanceStatus(analysis_id, 'error', {
      error: 'Failed to download video from storage',
    });
    return NextResponse.json({ error: 'Failed to download video from storage' }, { status: 500 });
  }

  // Save to temporary local file for Python analysis
  const buffer = Buffer.from(await data.arrayBuffer());
  await fs.writeFile(videoFile, buffer);
  console.log('[run/route] Video downloaded to:', videoFile, 'size:', buffer.length);

  // Update status to processing in database
  const updateResult = await updatePerformanceStatus(analysis_id, 'processing', {
    startedAt: new Date().toISOString(),
  });

  if (!updateResult.success) {
    console.error('[run/route] Failed to update status:', updateResult.error);
  }

  // Prepare temporary output path for Python script
  const tempResultDir = path.join(TEMP_DIR, 'results', analysis_id);
  await fs.mkdir(tempResultDir, { recursive: true });
  const tempResultPath = path.join(tempResultDir, 'report.json');

  // Spawn Python orchestrator subprocess (fire and forget)
  const pythonScript = path.join(process.cwd(), 'python', 'run_analysis.py');

  // Ensure ffprobe is in PATH for the subprocess
  const env = {
    ...process.env,
    PATH: `${process.env.PATH}:/usr/local/bin:/usr/bin:/bin`,
  };

  const child = spawn('python3', [
    pythonScript,
    '--video-path', videoFile,
    '--output-path', tempResultPath,
    '--analysis-id', analysis_id,
  ], {
    detached: true,
    stdio: ['ignore', 'inherit', 'inherit'], // pipe stdout/stderr to console
    env,
  });

  child.unref();

  // Monitor the subprocess result via a background check
  monitorAnalysis(analysis_id, user.id, tempResultPath);

  return NextResponse.json({ status: 'processing', analysis_id });
}

/**
 * Background monitor that checks for analysis completion.
 * Reads result from temporary file and writes to database.
 */
async function monitorAnalysis(analysisId: string, userId: string, tempResultPath: string) {
  const MAX_WAIT_MS = 5 * 60 * 1000; // 5 minutes max
  const POLL_INTERVAL_MS = 2000;
  const startTime = Date.now();

  const check = async () => {
    try {
      // Check if result file exists
      await fs.access(tempResultPath);

      // Read result from temporary file
      const resultData = await fs.readFile(tempResultPath, 'utf-8');
      const result = JSON.parse(resultData) as PerformanceReport;

      console.log('[monitorAnalysis] Analysis complete, writing to database:', analysisId);

      // Write result to database
      const writeResultStatus = await writeResult(analysisId, userId, result);
      if (!writeResultStatus.success) {
        console.error('[monitorAnalysis] Failed to write result to database:', writeResultStatus.error);
        await updatePerformanceStatus(analysisId, 'error', {
          error: `Failed to save results: ${writeResultStatus.error}`,
        });
        return;
      }

      // Update status to complete in database
      await updatePerformanceStatus(analysisId, 'complete', {
        completedAt: new Date().toISOString(),
      });

      console.log('[monitorAnalysis] Successfully persisted results to database:', analysisId);

      // Clean up temporary files
      try {
        await fs.rm(path.dirname(tempResultPath), { recursive: true, force: true });
        await fs.rm(path.join(TEMP_DIR, 'uploads', analysisId), { recursive: true, force: true });
        console.log('[monitorAnalysis] Cleaned up temporary files for:', analysisId);
      } catch (cleanupErr) {
        console.warn('[monitorAnalysis] Failed to clean up temporary files:', cleanupErr);
      }

      return;
    } catch (err) {
      // Result not yet available or read error
      if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
        console.error('[monitorAnalysis] Error reading result:', err);
      }
    }

    if (Date.now() - startTime > MAX_WAIT_MS) {
      // Timeout
      console.error('[monitorAnalysis] Analysis timed out:', analysisId);
      await updatePerformanceStatus(analysisId, 'error', {
        error: 'Analysis timed out after 5 minutes',
      });
      return;
    }

    // Continue polling
    setTimeout(check, POLL_INTERVAL_MS);
  };

  setTimeout(check, POLL_INTERVAL_MS);
}

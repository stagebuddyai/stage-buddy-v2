'use server'

import { promises as fs } from 'fs';
import {
  generateAnalysisId,
  getUploadDir,
  getVideoPath,
  ensureDir,
  writeStatus,
  SUPPORTED_VIDEO_TYPES,
  SUPPORTED_EXTENSIONS,
  MAX_FILE_SIZE,
} from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';

type UploadResult = {
  error: string | null;
  analysis_id: string | null;
  video_extension: string | null;
}

type RunResult = {
  error: string | null;
  success: boolean;
}

/**
 * Server Action: Upload a video file for analysis
 * Uses Server Actions' bodySizeLimit (600mb) to allow large uploads
 */
export async function uploadVideo(formData: FormData): Promise<UploadResult> {
  console.log('[uploadVideo] Server action called');
  try {
    console.log('[uploadVideo] Checking auth...');
    const user = await getAuthenticatedUser();
    if (!user) {
      return { error: 'Authentication required', analysis_id: null, video_extension: null };
    }

    const file = formData.get('video') as File | null;
    if (!file) {
      return { error: 'No video file provided', analysis_id: null, video_extension: null };
    }

    // Validate MIME type
    if (!SUPPORTED_VIDEO_TYPES.includes(file.type as typeof SUPPORTED_VIDEO_TYPES[number])) {
      return { 
        error: `Unsupported file type: ${file.type}. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`,
        analysis_id: null,
        video_extension: null
      };
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return { 
        error: 'File too large. Maximum size is 500MB.',
        analysis_id: null,
        video_extension: null
      };
    }

    // Determine extension from MIME type
    const mimeToExt: Record<string, string> = {
      'video/mp4': 'mp4',
      'video/webm': 'webm',
      'video/quicktime': 'mov',
      'video/x-msvideo': 'avi',
      'video/x-matroska': 'mkv',
    };
    const extension = mimeToExt[file.type] || 'mp4';

    const analysisId = generateAnalysisId();
    const uploadDir = getUploadDir(analysisId);
    const videoPath = getVideoPath(analysisId, extension);

    await ensureDir(uploadDir);

    // Stream file to disk
    const buffer = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(videoPath, buffer);

    // Write initial status
    await writeStatus(analysisId, {
      status: 'pending',
      started_at: new Date().toISOString(),
    });

    console.log(`[uploadVideo] Video uploaded: ${analysisId}, size: ${file.size}, ext: ${extension}`);
    
    return {
      error: null,
      analysis_id: analysisId,
      video_extension: extension,
    };
  } catch (error) {
    console.error('[uploadVideo] exception:', error);
    return {
      error: error instanceof Error ? error.message : 'Upload failed',
      analysis_id: null,
      video_extension: null,
    };
  }
}

/**
 * Server Action: Start analysis for an uploaded video
 */
export async function runAnalysis(analysisId: string): Promise<RunResult> {
  try {
    const user = await getAuthenticatedUser();
    if (!user) {
      return { error: 'Authentication required', success: false };
    }

    // Call the run API internally
    const response = await fetch(`${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'}/api/analysis/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: analysisId }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      return { error: data.error || 'Failed to start analysis', success: false };
    }

    console.log(`[runAnalysis] Analysis started: ${analysisId}`);
    return { error: null, success: true };
  } catch (error) {
    console.error('[runAnalysis] exception:', error);
    return {
      error: error instanceof Error ? error.message : 'Failed to start analysis',
      success: false,
    };
  }
}

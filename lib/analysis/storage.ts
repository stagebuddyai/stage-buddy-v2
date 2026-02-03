/**
 * Stage Buddy V2 - Supabase Database Storage
 * Manages performance analysis data in Supabase database.
 * Replaces local filesystem storage with persistent database operations.
 */

import crypto from 'crypto';
import type { AnalysisStatus, PerformanceReport } from './types';
import { createSupabaseServer } from '@/lib/supabase/server';

export function generateAnalysisId(): string {
  return crypto.randomUUID();
}

/** Validate analysis ID format (UUID or timestamp-random) to prevent SQL injection */
export function isValidAnalysisId(id: string): boolean {
  // Accept UUID format: 8-4-4-4-12 hex digits
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  // Accept timestamp-random format: digits-alphanumeric
  const timestampPattern = /^[0-9]+-[a-z0-9]+$/i;

  return uuidPattern.test(id) || timestampPattern.test(id);
}

/** Supported video MIME types for upload */
export const SUPPORTED_VIDEO_TYPES = [
  'video/mp4',
  'video/webm',
  'video/quicktime',
  'video/x-msvideo',
  'video/x-matroska',
] as const;

/** Supported video file extensions */
export const SUPPORTED_EXTENSIONS = ['mp4', 'webm', 'mov', 'avi', 'mkv'] as const;

/** Max file size: 500MB for Beta */
export const MAX_FILE_SIZE = 500 * 1024 * 1024;

/**
 * Create a new performance record in the database
 */
export async function createPerformance(
  analysisId: string,
  userId: string,
  videoPath: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const supabase = await createSupabaseServer();

    const { error } = await supabase
      .from('performances')
      .insert({
        id: analysisId,
        user_id: userId,
        status: 'uploaded',
        video_path: videoPath,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

    if (error) {
      console.error('[createPerformance] Database error:', error);
      return { success: false, error: error.message };
    }

    return { success: true };
  } catch (err) {
    console.error('[createPerformance] Exception:', err);
    return { success: false, error: String(err) };
  }
}

/**
 * Update performance status
 */
export async function updatePerformanceStatus(
  analysisId: string,
  status: 'uploaded' | 'processing' | 'complete' | 'error',
  options?: {
    startedAt?: string;
    completedAt?: string;
    error?: string;
  }
): Promise<{ success: boolean; error?: string }> {
  try {
    const supabase = await createSupabaseServer();

    const updates: Record<string, unknown> = {
      status,
      updated_at: new Date().toISOString(),
      processing_heartbeat: new Date().toISOString(),
    };

    if (options?.startedAt) {
      updates.processing_started_at = options.startedAt;
    }
    if (options?.completedAt) {
      updates.processing_completed_at = options.completedAt;
    }
    if (options?.error) {
      updates.last_error = options.error;
    }

    const { error } = await supabase
      .from('performances')
      .update(updates)
      .eq('id', analysisId);

    if (error) {
      console.error('[updatePerformanceStatus] Database error:', error);
      return { success: false, error: error.message };
    }

    return { success: true };
  } catch (err) {
    console.error('[updatePerformanceStatus] Exception:', err);
    return { success: false, error: String(err) };
  }
}

/**
 * Write analysis results to database
 */
export async function writeResult(
  analysisId: string,
  userId: string,
  result: PerformanceReport
): Promise<{ success: boolean; error?: string }> {
  try {
    const supabase = await createSupabaseServer();

    // Use upsert to handle both insert and update cases
    const { error } = await supabase
      .from('analysis_results')
      .upsert({
        performance_id: analysisId,
        user_id: userId,
        analysis_output: result as unknown as Record<string, unknown>,
        created_at: new Date().toISOString(),
      }, {
        onConflict: 'performance_id',
      });

    if (error) {
      console.error('[writeResult] Database error:', error);
      return { success: false, error: error.message };
    }

    return { success: true };
  } catch (err) {
    console.error('[writeResult] Exception:', err);
    return { success: false, error: String(err) };
  }
}

/**
 * Read analysis status from database
 */
export async function readStatus(analysisId: string): Promise<AnalysisStatus | null> {
  try {
    const supabase = await createSupabaseServer();

    const { data, error } = await supabase
      .from('performances')
      .select('status, processing_started_at, processing_completed_at, last_error')
      .eq('id', analysisId)
      .single();

    if (error || !data) {
      return null;
    }

    // Map database status to AnalysisStatus
    const statusMap: Record<string, AnalysisStatus['status']> = {
      'uploaded': 'pending',
      'processing': 'running',
      'complete': 'complete',
      'error': 'failed',
    };

    return {
      status: statusMap[data.status] || 'pending',
      started_at: data.processing_started_at || undefined,
      completed_at: data.processing_completed_at || undefined,
      error: data.last_error || undefined,
    };
  } catch (err) {
    console.error('[readStatus] Exception:', err);
    return null;
  }
}

/**
 * Read analysis results from database
 */
export async function readResult(analysisId: string): Promise<PerformanceReport | null> {
  try {
    const supabase = await createSupabaseServer();

    const { data, error } = await supabase
      .from('analysis_results')
      .select('analysis_output')
      .eq('performance_id', analysisId)
      .single();

    if (error || !data) {
      return null;
    }

    return data.analysis_output as unknown as PerformanceReport;
  } catch (err) {
    console.error('[readResult] Exception:', err);
    return null;
  }
}

/**
 * Get performance record with user validation
 */
export async function getPerformance(
  analysisId: string,
  userId: string
): Promise<{ data: unknown | null; error?: string }> {
  try {
    const supabase = await createSupabaseServer();

    const { data, error } = await supabase
      .from('performances')
      .select('*')
      .eq('id', analysisId)
      .eq('user_id', userId)
      .single();

    if (error) {
      return { data: null, error: error.message };
    }

    return { data };
  } catch (err) {
    console.error('[getPerformance] Exception:', err);
    return { data: null, error: String(err) };
  }
}

/**
 * Legacy compatibility: Write status (maps to updatePerformanceStatus)
 * Kept for backward compatibility with existing code
 */
export async function writeStatus(analysisId: string, status: AnalysisStatus): Promise<void> {
  const dbStatus = status.status === 'running' ? 'processing' :
                   status.status === 'failed' ? 'error' :
                   status.status === 'complete' ? 'complete' : 'uploaded';

  await updatePerformanceStatus(analysisId, dbStatus, {
    startedAt: status.started_at,
    completedAt: status.completed_at,
    error: status.error,
  });
}

/**
 * Write user feedback to local filesystem
 * Note: Feedback is not yet migrated to database, still uses local storage
 */
export async function writeFeedback(analysisId: string, feedback: unknown): Promise<void> {
  const fs = await import('fs/promises');
  const path = await import('path');

  const DATA_DIR = process.env.STAGE_BUDDY_DATA_DIR || '/tmp/stage-buddy';
  const feedbackDir = path.join(DATA_DIR, 'feedback');
  const feedbackPath = path.join(feedbackDir, `${analysisId}.json`);

  await fs.mkdir(feedbackDir, { recursive: true });
  await fs.writeFile(feedbackPath, JSON.stringify(feedback, null, 2));
}

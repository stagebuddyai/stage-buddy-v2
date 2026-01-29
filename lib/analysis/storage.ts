/**
 * Stage Buddy V2 - Local File Storage for Beta
 * Manages video uploads, analysis status, results, and feedback on local disk.
 * Production would replace this with S3 + database storage.
 */

import { promises as fs } from 'fs';
import path from 'path';
import crypto from 'crypto';
import type { AnalysisStatus } from './types';

const DATA_DIR = process.env.STAGE_BUDDY_DATA_DIR || '/tmp/stage-buddy';

export function generateAnalysisId(): string {
  return crypto.randomUUID();
}

export function getUploadDir(analysisId: string): string {
  return path.join(DATA_DIR, 'uploads', analysisId);
}

export function getVideoPath(analysisId: string, extension: string): string {
  return path.join(getUploadDir(analysisId), `video.${extension}`);
}

export function getResultPath(analysisId: string): string {
  return path.join(DATA_DIR, 'results', analysisId, 'report.json');
}

export function getStatusPath(analysisId: string): string {
  return path.join(DATA_DIR, 'status', `${analysisId}.json`);
}

export function getFeedbackPath(analysisId: string): string {
  return path.join(DATA_DIR, 'feedback', `${analysisId}.json`);
}

export async function ensureDir(dirPath: string): Promise<void> {
  await fs.mkdir(dirPath, { recursive: true });
}

export async function writeStatus(analysisId: string, status: AnalysisStatus): Promise<void> {
  const statusPath = getStatusPath(analysisId);
  await ensureDir(path.dirname(statusPath));
  await fs.writeFile(statusPath, JSON.stringify(status, null, 2));
}

export async function readStatus(analysisId: string): Promise<AnalysisStatus | null> {
  try {
    const statusPath = getStatusPath(analysisId);
    const data = await fs.readFile(statusPath, 'utf-8');
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export async function readResult(analysisId: string): Promise<unknown | null> {
  try {
    const resultPath = getResultPath(analysisId);
    const data = await fs.readFile(resultPath, 'utf-8');
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export async function writeFeedback(analysisId: string, feedback: unknown): Promise<void> {
  const feedbackPath = getFeedbackPath(analysisId);
  await ensureDir(path.dirname(feedbackPath));
  await fs.writeFile(feedbackPath, JSON.stringify(feedback, null, 2));
}

/** Validate analysis ID format (UUID or timestamp-random) to prevent path traversal */
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

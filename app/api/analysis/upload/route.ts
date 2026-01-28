import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import {
  generateAnalysisId,
  getUploadDir,
  getVideoPath,
  ensureDir,
  writeStatus,
  isValidAnalysisId,
  SUPPORTED_VIDEO_TYPES,
  SUPPORTED_EXTENSIONS,
  MAX_FILE_SIZE,
} from '@/lib/analysis/storage';
import { getAuthenticatedUser } from '@/lib/analysis/auth-guard';

export async function POST(req: NextRequest) {
  const user = await getAuthenticatedUser();
  if (!user) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
  }

  let formData: FormData;
  try {
    formData = await req.formData();
  } catch {
    return NextResponse.json({ error: 'Invalid form data' }, { status: 400 });
  }

  const file = formData.get('video') as File | null;
  if (!file) {
    return NextResponse.json({ error: 'No video file provided' }, { status: 400 });
  }

  // Validate MIME type
  if (!SUPPORTED_VIDEO_TYPES.includes(file.type as typeof SUPPORTED_VIDEO_TYPES[number])) {
    return NextResponse.json(
      { error: `Unsupported file type: ${file.type}. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}` },
      { status: 400 }
    );
  }

  // Validate file size
  if (file.size > MAX_FILE_SIZE) {
    return NextResponse.json(
      { error: `File too large. Maximum size is 500MB.` },
      { status: 400 }
    );
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

  return NextResponse.json({
    analysis_id: analysisId,
    video_extension: extension,
  });
}

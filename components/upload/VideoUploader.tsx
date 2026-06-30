'use client';

import { useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase/client';
import UploadProgress from './UploadProgress';

const SUPPORTED_TYPES = [
  'video/mp4',
  'video/webm',
  'video/quicktime',
  'video/x-msvideo',
  'video/x-matroska',
];

const MAX_SIZE = 750 * 1024 * 1024; // 750MB

const MIME_TO_EXT: Record<string, string> = {
  'video/mp4': 'mp4',
  'video/webm': 'webm',
  'video/quicktime': 'mov',
  'video/x-msvideo': 'avi',
  'video/x-matroska': 'mkv',
};

export default function VideoUploader() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'submitted' | 'error'>('idle');
  const [uploadPercent, setUploadPercent] = useState(0);

  const validateFile = useCallback((f: File): string | null => {
    if (!SUPPORTED_TYPES.includes(f.type)) {
      return `Unsupported file format. Please use MP4, WebM, MOV, AVI, or MKV.`;
    }
    if (f.size > MAX_SIZE) {
      return `File is too large (${(f.size / (1024 * 1024)).toFixed(0)} MB). Maximum is 750 MB.`;
    }
    return null;
  }, []);

  const handleFile = useCallback((f: File) => {
    setError(null);
    const validationError = validateFile(f);
    if (validationError) {
      setError(validationError);
      return;
    }
    setFile(f);
  }, [validateFile]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) handleFile(selected);
  }, [handleFile]);

  const handleUpload = async () => {
    if (!file) return;

    console.log('[handleUpload] Starting upload for file:', file.name, file.size);
    setUploading(true);
    setError(null);
    setProgress('Checking authentication...');

    try {
      // Get current user
      const { data: { user }, error: authError } = await supabase.auth.getUser();
      if (authError || !user) {
        throw new Error('Authentication required. Please sign in again.');
      }
      console.log('[handleUpload] User authenticated:', user.id);

      // Generate analysis ID (UUID format required by database)
      const analysisId = crypto.randomUUID();
      const extension = MIME_TO_EXT[file.type] || 'mp4';
      const storagePath = `${user.id}/${analysisId}/video.${extension}`;

      setProgress('Preparing upload...');
      console.log('[handleUpload] Creating signed upload URL for:', storagePath);

      // Get a signed upload URL so we can track byte-level progress via XHR
      const { data: signedData, error: signedError } = await supabase.storage
        .from('sb-uploads')
        .createSignedUploadUrl(storagePath);

      if (signedError || !signedData?.signedUrl) {
        console.error('[handleUpload] Failed to get signed upload URL:', signedError);
        throw new Error('Failed to prepare upload. Please try again.');
      }

      // Stream the file to Supabase using XHR — gives real byte-level progress events
      setUploadStatus('uploading');
      setUploadPercent(0);
      setProgress('Uploading video...');
      console.log('[handleUpload] Starting XHR upload to Supabase signed URL');

      await new Promise<void>((resolve, reject) => {
        const formData = new FormData();
        formData.append('cacheControl', '3600');
        formData.append('', file); // empty key matches Supabase storage-js SDK convention

        const xhr = new XMLHttpRequest();
        xhr.open('PUT', signedData.signedUrl);
        xhr.setRequestHeader('x-upsert', 'false');

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            setUploadPercent(Math.round((e.loaded / e.total) * 100));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            setUploadPercent(100);
            resolve();
          } else {
            console.error('[handleUpload] XHR upload failed, status:', xhr.status, xhr.responseText);
            reject(new Error(`Upload failed (HTTP ${xhr.status}). Please try again.`));
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload. Check your connection.'));
        xhr.ontimeout = () => reject(new Error('Upload timed out. Try a smaller file or faster connection.'));

        xhr.send(formData);
      });

      console.log('[handleUpload] Upload complete');
      setUploadStatus('submitted');
      setProgress('Starting analysis...');

      // Call API to register the upload and start analysis
      const runRes = await fetch('/api/analysis/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          analysis_id: analysisId,
          storage_path: storagePath,
          video_extension: extension,
        }),
      });
      
      const runResult = await runRes.json();
      console.log('[handleUpload] Run result:', runResult);

      if (!runRes.ok || runResult.error) {
        throw new Error(runResult.error || 'Analysis failed to start');
      }

      // Redirect to analysis page
      router.push(`/analysis/${analysisId}`);
    } catch (err) {
      console.error('[handleUpload] Error:', err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      setUploading(false);
      setProgress('');
      setUploadStatus('error');
    }
  };

  const handleClear = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !file && fileInputRef.current?.click()}
        className={`
          relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-3
          rounded-lg border-2 border-dashed p-8 transition-colors
          ${dragActive
            ? 'border-zinc-400 bg-zinc-100 dark:border-zinc-500 dark:bg-zinc-800'
            : file
              ? 'border-zinc-300 bg-white dark:border-zinc-700 dark:bg-zinc-900'
              : 'border-zinc-300 bg-white hover:border-zinc-400 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600 dark:hover:bg-zinc-800/50'
          }
        `}
      >
        {file ? (
          <div className="flex flex-col items-center gap-2 text-center">
            <svg className="h-10 w-10 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {file.name}
            </p>
            <p className="text-xs text-zinc-500">
              {(file.size / (1024 * 1024)).toFixed(1)} MB
            </p>
            {!uploading && (
              <button
                onClick={(e) => { e.stopPropagation(); handleClear(); }}
                className="mt-1 text-xs text-zinc-500 underline hover:text-zinc-700 dark:hover:text-zinc-300"
              >
                Choose different file
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center">
            <svg className="h-10 w-10 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Drag and drop your video here, or click to browse
            </p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/webm,video/quicktime,video/x-msvideo,video/x-matroska"
          onChange={handleInputChange}
          className="hidden"
        />
      </div>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {/* Upload button */}
      {file && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className={`
            flex h-12 w-full items-center justify-center rounded-lg text-sm font-medium transition-colors
            ${uploading
              ? 'cursor-not-allowed bg-zinc-300 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
              : 'bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200'
            }
          `}
        >
          {uploading ? progress || 'Processing...' : 'Analyze Performance'}
        </button>
      )}

      <UploadProgress
        status={uploadStatus}
        percent={uploadPercent}
        errorMessage={error ?? undefined}
      />
    </div>
  );
}

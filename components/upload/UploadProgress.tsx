'use client';

interface UploadProgressProps {
  status: 'idle' | 'uploading' | 'submitted' | 'error';
  percent: number; // 0-100, only used during 'uploading'
  errorMessage?: string;
}

export default function UploadProgress({ status, percent, errorMessage }: UploadProgressProps) {
  if (status === 'idle') return null;

  return (
    <div className="mt-4 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900">
      {status === 'uploading' && (
        <>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-zinc-700 dark:text-zinc-300">Uploading to storage…</span>
            <span className="font-medium tabular-nums text-zinc-900 dark:text-zinc-100">
              {percent}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
            <div
              className="h-full rounded-full bg-zinc-900 transition-all duration-150 dark:bg-zinc-100"
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            Large files may take several minutes — do not close this tab.
          </p>
        </>
      )}

      {status === 'submitted' && (
        <div className="flex items-center gap-3">
          <svg
            className="h-4 w-4 animate-spin text-zinc-500"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <span className="text-sm text-zinc-600 dark:text-zinc-400">
            Analysis submitted — loading your results…
          </span>
        </div>
      )}

      {status === 'error' && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {errorMessage || 'Upload failed. Please try again.'}
        </p>
      )}
    </div>
  );
}

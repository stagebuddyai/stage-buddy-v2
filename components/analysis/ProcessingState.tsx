'use client';

import type { AnalysisStatus } from '@/lib/analysis/types';

interface ProcessingStateProps {
  status: AnalysisStatus | null;
}

export default function ProcessingState({ status }: ProcessingStateProps) {
  return (
    <div className="flex flex-col items-center gap-8 py-24 text-center">
      {/* Loading indicator */}
      <div className="relative flex h-16 w-16 items-center justify-center">
        <div className="absolute h-16 w-16 animate-spin rounded-full border-2 border-zinc-200 border-t-zinc-600 dark:border-zinc-700 dark:border-t-zinc-300" />
        <svg className="h-6 w-6 text-zinc-500 dark:text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
          />
        </svg>
      </div>

      {/* Status message - calm, grounded, no drama */}
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
          Analyzing your performance
        </h2>
        <p className="max-w-sm text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">
          Examining delivery signals across voice, breath, pacing, body movement,
          and audience engagement patterns.
        </p>
      </div>

      {/* Status indicator */}
      <div className="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
        {status?.status === 'running'
          ? 'Analysis in progress'
          : 'Preparing analysis'
        }
      </div>
    </div>
  );
}

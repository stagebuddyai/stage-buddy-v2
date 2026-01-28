'use client';

import { useState, useEffect, useCallback } from 'react';
import type { AnalysisStatus, PerformanceReport } from '@/lib/analysis/types';
import ReportCard from './ReportCard';
import ProcessingState from './ProcessingState';

interface AnalysisViewProps {
  analysisId: string;
}

export default function AnalysisView({ analysisId }: AnalysisViewProps) {
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/analysis/status/${analysisId}`);
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || 'Failed to check analysis status');
        return null;
      }
      const data: AnalysisStatus = await res.json();
      setStatus(data);
      return data;
    } catch {
      setError('Unable to reach the server. Please try again.');
      return null;
    }
  }, [analysisId]);

  const fetchResults = useCallback(async () => {
    try {
      const res = await fetch(`/api/analysis/results/${analysisId}`);
      if (!res.ok) {
        setError('Results could not be loaded.');
        return;
      }
      const data: PerformanceReport = await res.json();
      setReport(data);
    } catch {
      setError('Unable to load results. Please try again.');
    }
  }, [analysisId]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      const currentStatus = await fetchStatus();
      if (!currentStatus) return;

      if (currentStatus.status === 'complete') {
        if (interval) clearInterval(interval);
        await fetchResults();
      } else if (currentStatus.status === 'failed') {
        if (interval) clearInterval(interval);
        setError(currentStatus.error || 'Analysis encountered an error.');
      }
    };

    // Initial check
    poll();

    // Poll every 2 seconds while processing
    interval = setInterval(async () => {
      const currentStatus = await fetchStatus();
      if (currentStatus?.status === 'complete') {
        clearInterval(interval!);
        await fetchResults();
      } else if (currentStatus?.status === 'failed') {
        clearInterval(interval!);
      }
    }, 2000);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchStatus, fetchResults]);

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center gap-6 py-20 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <svg className="h-7 w-7 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
            Something went wrong
          </h2>
          <p className="max-w-sm text-sm text-zinc-600 dark:text-zinc-400">
            {error}
          </p>
        </div>
        <a
          href="/upload"
          className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Try another upload
        </a>
      </div>
    );
  }

  // Report loaded - render results
  if (report) {
    return <ReportCard report={report} analysisId={analysisId} />;
  }

  // Processing state
  return <ProcessingState status={status} />;
}

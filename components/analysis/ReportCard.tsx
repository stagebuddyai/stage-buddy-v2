'use client';

import type { PerformanceReport } from '@/lib/analysis/types';
import PillarCard from './PillarCard';
import TimelineSection from './TimelineSection';
import GrowthPlanSection from './GrowthPlanSection';
import BetaFeedbackForm from './BetaFeedbackForm';

interface ReportCardProps {
  report: PerformanceReport;
  analysisId: string;
}

export default function ReportCard({ report, analysisId }: ReportCardProps) {
  return (
    <div className="flex flex-col gap-8">
      {/* Header with Beta indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Performance Snapshot
          </h1>
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            Beta
          </span>
        </div>
        <a
          href="/upload"
          className="text-sm text-zinc-500 underline transition-colors hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-300"
        >
          New upload
        </a>
      </div>

      {/* Overall score - presented as a snapshot, not a verdict */}
      <section className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:gap-6">
          {/* Score circle */}
          <div className="flex flex-col items-center gap-1">
            <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-zinc-900 dark:border-zinc-100">
              <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                {report.overall.score}
              </span>
            </div>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">out of 5</span>
          </div>

          {/* Coach summary */}
          <div className="flex flex-1 flex-col gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Coach&apos;s Observation
            </h2>
            <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
              {report.overall.summary}
            </p>
          </div>
        </div>
      </section>

      {/* S.T.A.R.R. Pillars */}
      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          Delivery Dimensions
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {report.pillars.map((pillar) => (
            <PillarCard key={pillar.name} pillar={pillar} />
          ))}
        </div>
      </section>

      {/* Key Moments Timeline */}
      {report.timeline.key_moments.length > 0 && (
        <TimelineSection timeline={report.timeline} />
      )}

      {/* Growth Plan */}
      <GrowthPlanSection plan={report.growth_plan} />

      {/* Determinism notice */}
      <p className="text-xs leading-relaxed text-zinc-400 dark:text-zinc-500">
        This snapshot reflects observable delivery signals at the time of recording.
        The same recording will always produce the same analysis. Scores range from 1 to 5.
      </p>

      {/* Beta Feedback */}
      <BetaFeedbackForm analysisId={analysisId} />
    </div>
  );
}

'use client';

import type { ReportTimeline } from '@/lib/analysis/types';

interface TimelineSectionProps {
  timeline: ReportTimeline;
}

function formatTimestamp(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const MOMENT_TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  peak: {
    bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    text: 'text-emerald-700 dark:text-emerald-400',
    label: 'Peak',
  },
  dip: {
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    text: 'text-amber-700 dark:text-amber-400',
    label: 'Opportunity',
  },
  shift: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-400',
    label: 'Transition',
  },
  opening: {
    bg: 'bg-zinc-100 dark:bg-zinc-800',
    text: 'text-zinc-600 dark:text-zinc-400',
    label: 'Opening',
  },
  close: {
    bg: 'bg-zinc-100 dark:bg-zinc-800',
    text: 'text-zinc-600 dark:text-zinc-400',
    label: 'Close',
  },
};

export default function TimelineSection({ timeline }: TimelineSectionProps) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          Key Moments
        </h2>
        <span className="text-xs text-zinc-400 dark:text-zinc-500">
          {formatTimestamp(timeline.duration_seconds)} total
        </span>
      </div>

      <div className="flex flex-col gap-3">
        {timeline.key_moments.map((moment, index) => {
          const style = MOMENT_TYPE_STYLES[moment.type] || MOMENT_TYPE_STYLES.shift;
          return (
            <div
              key={`${moment.timestamp}-${index}`}
              className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div className="flex items-start gap-3">
                {/* Timestamp */}
                <div className="flex flex-col items-center gap-1 pt-0.5">
                  <span className="text-xs font-mono font-medium text-zinc-900 dark:text-zinc-100">
                    {formatTimestamp(moment.timestamp)}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${style.bg} ${style.text}`}>
                    {style.label}
                  </span>
                </div>

                {/* Content */}
                <div className="flex flex-1 flex-col gap-1.5">
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">
                    {moment.description}
                  </p>
                  <p className="text-sm leading-relaxed text-zinc-500 dark:text-zinc-400 italic">
                    {moment.coach_note}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

'use client';

import { useState } from 'react';
import type { PillarResult } from '@/lib/analysis/types';

interface PillarCardProps {
  pillar: PillarResult;
}

const PILLAR_ICONS: Record<string, React.ReactNode> = {
  flame: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"
      />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"
      />
    </svg>
  ),
  wind: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M3 8h13a3 3 0 110 6h-1M3 12h9a3 3 0 010 6H9M3 16h4a3 3 0 010 6H5"
      />
    </svg>
  ),
  person: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
      />
    </svg>
  ),
  users: (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
      />
    </svg>
  ),
};

function formatSubscoreLabel(key: string): string {
  return key
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export default function PillarCard({ pillar }: PillarCardProps) {
  const [expanded, setExpanded] = useState(false);

  const weightPercent = Math.round(pillar.weight * 100);

  return (
    <div className="flex flex-col rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-3 p-4 text-left transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
          {PILLAR_ICONS[pillar.icon] || PILLAR_ICONS.flame}
        </span>
        <div className="flex flex-1 flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {pillar.name}
            </span>
            <span className="text-xs text-zinc-400 dark:text-zinc-500">
              {weightPercent}% weight
            </span>
          </div>
          {/* Score bar */}
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 rounded-full bg-zinc-100 dark:bg-zinc-800">
              <div
                className="h-1.5 rounded-full bg-zinc-700 dark:bg-zinc-300 transition-all"
                style={{ width: `${(pillar.score / 5) * 100}%` }}
              />
            </div>
            <span className="min-w-[2rem] text-right text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {pillar.score}
            </span>
          </div>
        </div>
        <svg
          className={`h-4 w-4 text-zinc-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="flex flex-col gap-4 border-t border-zinc-100 p-4 dark:border-zinc-800">
          {/* Sub-scores */}
          <div className="flex flex-col gap-2">
            {Object.entries(pillar.subscores).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-zinc-600 dark:text-zinc-400">
                  {formatSubscoreLabel(key)}
                </span>
                <span className="font-medium text-zinc-900 dark:text-zinc-100">
                  {value}
                </span>
              </div>
            ))}
          </div>

          {/* Coach feedback for this pillar */}
          <div className="rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
            <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-1">
              Coach&apos;s Note
            </p>
            <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
              {pillar.feedback}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

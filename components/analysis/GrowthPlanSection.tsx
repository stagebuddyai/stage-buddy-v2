'use client';

import type { GrowthPlan } from '@/lib/analysis/types';

interface GrowthPlanSectionProps {
  plan: GrowthPlan;
}

export default function GrowthPlanSection({ plan }: GrowthPlanSectionProps) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-sm font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
        Growth Map
      </h2>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Strengths */}
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h3 className="mb-3 text-sm font-medium text-zinc-900 dark:text-zinc-100">
            Strongest Signals
          </h3>
          <ul className="flex flex-col gap-2">
            {plan.top_strengths.map((strength, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-emerald-500" />
                {strength}
              </li>
            ))}
          </ul>
        </div>

        {/* Focus areas */}
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h3 className="mb-3 text-sm font-medium text-zinc-900 dark:text-zinc-100">
            Focus Areas
          </h3>
          <ul className="flex flex-col gap-2">
            {plan.focus_areas.map((area, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-500" />
                {area}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

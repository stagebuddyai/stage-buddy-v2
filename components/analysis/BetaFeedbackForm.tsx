'use client';

import { useState } from 'react';

interface BetaFeedbackFormProps {
  analysisId: string;
}

export default function BetaFeedbackForm({ analysisId }: BetaFeedbackFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [clarity, setClarity] = useState('');
  const [accuracy, setAccuracy] = useState('');
  const [additional, setAdditional] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clarity.trim() && !accuracy.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_id: analysisId,
          clarity: clarity.trim(),
          accuracy: accuracy.trim(),
          additional: additional.trim(),
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to submit feedback');
      }

      setSubmitted(true);
    } catch {
      setError('Could not submit feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Thank you for your feedback. It helps us build a better tool.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-5 text-left transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
      >
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            Beta Feedback
          </span>
          <span className="text-xs text-zinc-500 dark:text-zinc-400">
            Help us improve this tool
          </span>
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

      {expanded && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 border-t border-zinc-100 p-5 dark:border-zinc-800">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="clarity" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              What felt clear vs. confusing in the feedback?
            </label>
            <textarea
              id="clarity"
              value={clarity}
              onChange={(e) => setClarity(e.target.value)}
              rows={3}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-500"
              placeholder="Which parts of the analysis made sense? Which parts were unclear?"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="accuracy" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Where did the feedback feel accurate vs. off?
            </label>
            <textarea
              id="accuracy"
              value={accuracy}
              onChange={(e) => setAccuracy(e.target.value)}
              rows={3}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-500"
              placeholder="Did any observations match your experience? Did any feel wrong?"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="additional" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Anything else? <span className="font-normal text-zinc-400">(optional)</span>
            </label>
            <textarea
              id="additional"
              value={additional}
              onChange={(e) => setAdditional(e.target.value)}
              rows={2}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-zinc-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:placeholder:text-zinc-500 dark:focus:border-zinc-500"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting || (!clarity.trim() && !accuracy.trim())}
            className={`
              rounded-lg px-4 py-2.5 text-sm font-medium transition-colors
              ${submitting || (!clarity.trim() && !accuracy.trim())
                ? 'cursor-not-allowed bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500'
                : 'bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200'
              }
            `}
          >
            {submitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </form>
      )}
    </section>
  );
}

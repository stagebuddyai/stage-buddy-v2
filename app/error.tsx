'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    console.error('[Error Boundary]', error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-3xl flex-col items-center gap-8 py-32 px-16 bg-white dark:bg-black">
        <div className="flex flex-col items-center gap-6 text-center max-w-md">
          <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-3xl font-semibold leading-10 tracking-tight text-black dark:text-zinc-50">
            Something went wrong
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400">
            {error.message || 'An unexpected error occurred'}
          </p>
          <div className="flex flex-col gap-3 w-full mt-4">
            <button
              onClick={() => reset()}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-black text-white px-5 transition-colors hover:bg-zinc-800"
            >
              Try again
            </button>
            <button
              onClick={() => router.push('/')}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-5 transition-colors hover:bg-zinc-200 dark:hover:bg-zinc-700"
            >
              Go home
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

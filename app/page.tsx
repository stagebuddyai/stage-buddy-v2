import { Suspense } from "react";
import { createSupabaseServer } from "../lib/supabase/server";
import AuthButtons from "../components/AuthButtons";
import HomeAutoForward from "../components/HomeAutoForward";

export default async function Home({
  searchParams,
}: {
  searchParams?: Promise<{ returnTo?: string }> | { returnTo?: string };
}) {
  const params = await Promise.resolve(searchParams);
  const returnTo = params?.returnTo ?? null;

  let connected = false;

  try {
    const supabase = await createSupabaseServer();
    const { data: { session } } = await supabase.auth.getSession();
    connected = !!session;
  } catch (error) {
    console.error("[Home] Error checking auth:", error);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <Suspense fallback={null}>
        <HomeAutoForward returnTo={returnTo} />
      </Suspense>
      <main className="flex min-h-screen w-full max-w-2xl flex-col items-center justify-center gap-10 py-32 px-6 sm:px-16 bg-white dark:bg-black">
        {/* Logo and Beta indicator */}
        <div className="flex flex-col items-center gap-3">
          <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Stage Buddy
          </h1>
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            Beta
          </span>
        </div>

        {/* Product description */}
        <p className="max-w-md text-center text-base leading-7 text-zinc-600 dark:text-zinc-400">
          Structured performance feedback based on observable delivery signals.
          Voice, breath, pacing, body, and audience engagement — analyzed as craft
          observation, not evaluation of worth.
        </p>

        {/* Main CTA */}
        <div className="flex flex-col items-center gap-4 w-full max-w-sm">
          {connected ? (
            <a
              href="/upload"
              className="flex h-12 w-full items-center justify-center rounded-lg bg-zinc-900 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
            >
              Upload Performance
            </a>
          ) : (
            <p className="text-sm text-zinc-500 dark:text-zinc-500">
              Sign in to get started.
            </p>
          )}
          <AuthButtons connected={connected} />
        </div>
      </main>
    </div>
  );
}

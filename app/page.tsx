import { redirect } from "next/navigation";
import Image from "next/image";
import { Suspense } from "react";
import { createSupabaseServer } from "../lib/supabase/server";
import AuthButtons from "../components/AuthButtons";
import RunPerformanceButton from "../components/RunPerformanceButton";
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
    // Silently fail - page will still load with connected=false
    console.error("[Home] Error checking auth:", error);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <Suspense fallback={null}>
        <HomeAutoForward returnTo={returnTo} />
      </Suspense>
      <main className="flex min-h-screen w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
        <Image
          className="dark:invert"
          src="/next.svg"
          alt="Next.js logo"
          width={100}
          height={20}
          priority
        />
        <div className="flex flex-col items-center gap-6 text-center sm:items-start sm:text-left">
          <h1 className="max-w-xs text-3xl font-semibold leading-10 tracking-tight text-black dark:text-zinc-50">
            {connected ? "Connected" : "Not connected"}
          </h1>
          <p className="max-w-md text-lg leading-8 text-zinc-600 dark:text-zinc-400">
            {connected ? (
              "Ready to analyze your performance. Click below to get started."
            ) : (
              <>
                Looking for a starting point or more instructions? Head over to{" "}
                <a
                  href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
                  className="font-medium text-zinc-950 dark:text-zinc-50"
                >
                  Templates
                </a>{" "}
                or the{" "}
                <a
                  href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
                  className="font-medium text-zinc-950 dark:text-zinc-50"
                >
                  Learning
                </a>{" "}
                center.
              </>
            )}
          </p>
        </div>

        <div className="flex flex-col gap-4 w-full max-w-md">
          {connected && (
            <RunPerformanceButton />
          )}
          <AuthButtons connected={connected} />
        </div>
      </main>
    </div>
  );
}

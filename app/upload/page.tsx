import { redirect } from 'next/navigation';
import { createSupabaseServer } from '@/lib/supabase/server';
import VideoUploader from '@/components/upload/VideoUploader';

export const metadata = {
  title: 'Upload Performance - Stage Buddy (Beta)',
  description: 'Upload your performance video for structured delivery feedback.',
};

export default async function UploadPage() {
  // Auth gate: redirect unauthenticated users
  let user = null;
  try {
    const supabase = await createSupabaseServer();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      redirect('/');
    }
    user = session.user;
  } catch {
    redirect('/');
  }

  return (
    <div className="flex min-h-screen items-start justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-2xl flex-col gap-8 py-16 px-6 sm:px-16 sm:py-24">
        {/* Beta indicator */}
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Stage Buddy
          </h1>
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
            Beta
          </span>
        </div>

        {/* Product promise */}
        <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
          <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            Stage Buddy provides structured performance feedback based on observable
            delivery signals. It does not judge artistic value.
          </p>
        </div>

        {/* Upload section */}
        <section className="flex flex-col gap-4">
          <h2 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
            Upload your performance
          </h2>

          {/* Pre-analysis notice */}
          <div className="rounded-lg bg-zinc-100 p-4 dark:bg-zinc-800/50">
            <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
              Analysis examines delivery signals: voice, breath, pacing, body movement,
              and audience engagement patterns. The same performance will produce the
              same result each time.
            </p>
          </div>

          {/* Upload component */}
          <VideoUploader />

          {/* Supported formats */}
          <p className="text-xs text-zinc-500 dark:text-zinc-500">
            Supported formats: MP4, WebM, MOV, AVI, MKV. Maximum file size: 750 MB.
          </p>
        </section>
      </main>
    </div>
  );
}

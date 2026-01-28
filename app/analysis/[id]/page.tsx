import { redirect } from 'next/navigation';
import { createSupabaseServer } from '@/lib/supabase/server';
import AnalysisView from '@/components/analysis/AnalysisView';

export const metadata = {
  title: 'Analysis - Stage Buddy (Beta)',
  description: 'Your performance analysis results.',
};

export default async function AnalysisPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  // Auth gate
  try {
    const supabase = await createSupabaseServer();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      redirect('/');
    }
  } catch {
    redirect('/');
  }

  const { id } = await params;

  return (
    <div className="flex min-h-screen justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="w-full max-w-3xl px-6 py-12 sm:px-16 sm:py-16">
        <AnalysisView analysisId={id} />
      </main>
    </div>
  );
}

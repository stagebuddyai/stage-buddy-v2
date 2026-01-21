import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServer } from "../../../../lib/supabase/server";

/**
 * POST /api/auth/signout
 * Server-side sign out which clears server cookies and session.
 */
export async function POST(_req: NextRequest) {
  const supabase = await createSupabaseServer();
  const { error } = await supabase.auth.signOut();

  if (error) {
    console.error("[/api/auth/signout] error:", error);
    return new NextResponse(JSON.stringify({ error }), { status: 500 });
  }

  return new NextResponse(null, { status: 204 });
}

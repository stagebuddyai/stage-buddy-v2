import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServer } from "../../../../lib/supabase/server";

/**
 * DEPRECATED: Use Server Action signOut() from app/actions/auth.ts instead
 * 
 * POST /api/auth/signout
 * Server-side sign out which clears server cookies and session.
 * 
 * This route handler is kept for backward compatibility.
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

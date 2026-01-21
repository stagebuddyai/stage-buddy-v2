import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServer } from "../../../../lib/supabase/server";
import { getAuthOrigin } from "../../../../lib/auth/origin";

/**
 * This route is the app callback target used by signInWithOAuth.redirectTo.
 * Supabase will redirect the user to the Supabase-hosted callback (on supabase.co),
 * which then redirects back to this app callback with a code. We exchange that code
 * for a session here using the server helper so cookies are set, then redirect home.
 */
export async function GET(req: NextRequest) {
  const origin = getAuthOrigin(req);
  const code = req.nextUrl.searchParams.get("code");

  console.log("[/api/auth/callback] hit. origin:", origin, "hasCode:", !!code);

  const supabase = await createSupabaseServer();

  if (!code) {
    console.error("[/api/auth/callback] missing code param, redirecting to origin");
    return NextResponse.redirect(`${origin}/?error=missing_code`);
  }

  const { data, error } = await supabase.auth.exchangeCodeForSession(code!);

  console.log("[/api/auth/callback] exchangeCodeForSession result:", {
    error: error ?? null,
    hasSession: !!data?.session,
  });

  if (error) {
    return NextResponse.redirect(`${origin}/?error=oauth_callback_failed`);
  }

  // Redirect back to app origin home. Session cookies are persisted by @supabase/ssr.
  return NextResponse.redirect(`${origin}/`);
}

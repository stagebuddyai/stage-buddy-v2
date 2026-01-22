import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServer } from "../../../../lib/supabase/server";
import { getAuthOrigin } from "../../../../lib/auth/origin";

/**
 * Starts the OAuth flow by returning a redirect to Supabase's OAuth URL.
 * redirectTo uses NEXT_PUBLIC_SITE_URL so forwarded Codespaces origin is used (never localhost).
 */
export async function GET(req: NextRequest) {
  const origin = getAuthOrigin(req);
  const callbackUrl = `${origin}/api/auth/callback`;
  console.log("[/api/auth/google] origin:", origin, "callback:", callbackUrl);

  const supabase = await createSupabaseServer();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: callbackUrl,
      skipBrowserRedirect: false,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      }
    },
  });

  if (error) {
    console.error("[/api/auth/google] signInWithOAuth error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  if (!data?.url) {
    console.error("[/api/auth/google] no redirect url returned");
    return NextResponse.json({ error: "No redirect url returned" }, { status: 500 });
  }

  return NextResponse.redirect(data.url);
}

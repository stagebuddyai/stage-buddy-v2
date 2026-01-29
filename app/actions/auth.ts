'use server'

import { createSupabaseServer } from "@/lib/supabase/server";
import { headers } from "next/headers";

type SignInResult = {
  error: string | null;
  url: string | null;
}

/**
 * Server Action: Initiates Google OAuth flow
 * Returns the OAuth URL for client-side redirect
 * This properly handles cookie setting in Server Actions (not Server Components)
 */
export async function signInWithGoogle(): Promise<SignInResult> {
  try {
    const headersList = await headers();
    
    // Handle GitHub Codespaces forwarded headers
    const forwardedHost = headersList.get('x-forwarded-host');
    const forwardedProto = headersList.get('x-forwarded-proto');
    const host = forwardedHost || headersList.get('host') || 'localhost:3000';
    const protocol = forwardedProto || (process.env.NODE_ENV === 'development' ? 'http' : 'https');
    
    const origin = process.env.NEXT_PUBLIC_SITE_URL || `${protocol}://${host}`;
    const callbackUrl = `${origin}/api/auth/callback`;

    console.log("[signInWithGoogle] origin:", origin, "callback:", callbackUrl);

    const supabase = await createSupabaseServer();
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: callbackUrl,
        skipBrowserRedirect: true, // Return URL instead of auto-redirecting
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        }
      },
    });

    if (error) {
      console.error("[signInWithGoogle] error:", error);
      return { error: error.message, url: null };
    }

    if (!data?.url) {
      console.error("[signInWithGoogle] no redirect url returned");
      return { error: "No redirect url returned", url: null };
    }

    console.log("[signInWithGoogle] OAuth URL generated successfully");
    return { error: null, url: data.url };
  } catch (error) {
    console.error("[signInWithGoogle] exception:", error);
    return { error: error instanceof Error ? error.message : "Unknown error", url: null };
  }
}

type SignOutResult = {
  error: string | null;
  success: boolean;
}

/**
 * Server Action: Signs out the user
 * Returns success status for client-side handling
 * This properly handles cookie removal in Server Actions (not Server Components)
 */
export async function signOut(): Promise<SignOutResult> {
  try {
    const supabase = await createSupabaseServer();
    const { error } = await supabase.auth.signOut();

    if (error) {
      console.error("[signOut] error:", error);
      return { error: error.message, success: false };
    }

    console.log("[signOut] successfully signed out");
    return { error: null, success: true };
  } catch (error) {
    console.error("[signOut] exception:", error);
    return { error: error instanceof Error ? error.message : "Unknown error", success: false };
  }
}

/**
 * Server Action: Gets the current session
 * Safe to call from Server Components as it only reads cookies
 */
export async function getSession() {
  try {
    const supabase = await createSupabaseServer();
    const { data: { session }, error } = await supabase.auth.getSession();

    if (error) {
      console.error("[getSession] error:", error);
      return null;
    }

    return session;
  } catch (error) {
    console.error("[getSession] exception:", error);
    return null;
  }
}

/**
 * Server Action: Refreshes the current session
 * This properly handles cookie updates in Server Actions
 */
export async function refreshSession() {
  try {
    const supabase = await createSupabaseServer();
    const { data: { session }, error } = await supabase.auth.refreshSession();

    if (error) {
      console.error("[refreshSession] error:", error);
      return null;
    }

    console.log("[refreshSession] session refreshed");
    return session;
  } catch (error) {
    console.error("[refreshSession] exception:", error);
    return null;
  }
}

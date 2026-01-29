'use server'

import { createSupabaseServer } from "@/lib/supabase/server";
import { getAuthOrigin } from "@/lib/auth/origin";
import { redirect } from "next/navigation";
import { headers } from "next/headers";

/**
 * Server Action: Initiates Google OAuth flow
 * This properly handles cookie setting in Server Actions (not Server Components)
 */
export async function signInWithGoogle() {
  try {
    const headersList = await headers();
    const host = headersList.get('host') || 'localhost:3000';
    const protocol = process.env.NODE_ENV === 'development' ? 'http' : 'https';
    const origin = process.env.NEXT_PUBLIC_SITE_URL || `${protocol}://${host}`;
    const callbackUrl = `${origin}/api/auth/callback`;

    console.log("[signInWithGoogle] origin:", origin, "callback:", callbackUrl);

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
      console.error("[signInWithGoogle] error:", error);
      throw new Error(error.message);
    }

    if (!data?.url) {
      console.error("[signInWithGoogle] no redirect url returned");
      throw new Error("No redirect url returned");
    }

    // Redirect to OAuth provider
    redirect(data.url);
  } catch (error) {
    console.error("[signInWithGoogle] exception:", error);
    throw error;
  }
}

/**
 * Server Action: Signs out the user
 * This properly handles cookie removal in Server Actions (not Server Components)
 */
export async function signOut() {
  try {
    const supabase = await createSupabaseServer();
    const { error } = await supabase.auth.signOut();

    if (error) {
      console.error("[signOut] error:", error);
      throw new Error(error.message);
    }

    console.log("[signOut] successfully signed out");
    
    // Redirect to home after successful sign out
    redirect('/');
  } catch (error) {
    console.error("[signOut] exception:", error);
    throw error;
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

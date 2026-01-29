import { createServerClient } from "@supabase/ssr";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

/**
 * Server-side Supabase client for Next.js App Router.
 * 
 * IMPORTANT: This client is READ-ONLY in Server Components.
 * - Use for reading session data (e.g., getSession(), getUser())
 * - DO NOT use for auth operations that modify cookies (signIn, signOut, etc.)
 * 
 * For auth operations that modify cookies, use Server Actions from app/actions/auth.ts:
 * - signInWithGoogle()
 * - signOut()
 * - refreshSession()
 * 
 * This client is safe to use in:
 * - Route Handlers (app/api/*)
 * - Server Actions (files with 'use server')
 * - Server Components (read-only operations only)
 * 
 * Exported name matches existing usage in the repo (createSupabaseServer).
 */
export async function createSupabaseServer() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      auth: {
        flowType: 'pkce',
        autoRefreshToken: false,
        persistSession: true,
        detectSessionInUrl: true,
      },
      cookies: {
        get(name: string) {
          const value = cookieStore.get(name)?.value;
          if (!value) return undefined;
          // Decode URL-encoded cookie values
          try {
            return decodeURIComponent(value);
          } catch {
            return value;
          }
        },
        set(name: string, value: string, options: Record<string, unknown>) {
          try {
            cookieStore.set({ name, value, ...options });
          } catch (error) {
            console.debug('[Supabase Server] Could not set cookie:', error);
          }
        },
        getAll() {
          try {
            const allCookies = cookieStore.getAll();
            // Decode URL-encoded cookie values
            return allCookies.map(cookie => ({
              ...cookie,
              value: (() => {
                try {
                  return decodeURIComponent(cookie.value);
                } catch {
                  return cookie.value;
                }
              })()
            }));
          } catch (error) {
            console.error('[Supabase Server] Error getting cookies:', error);
            return [];
          }
        },
        setAll(cookiesToSet: Array<{ name: string; value: string; options: Record<string, unknown> }>) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, String(value), {
                ...options,
                sameSite: 'lax',
                secure: true,
              });
            });
          } catch (error) {
            // NOTE: Cookie writes fail in Server Components (Next.js 13+ restriction)
            // This is expected for read-only operations like getSession() in Server Components
            // For auth operations (signIn, signOut), use Server Actions from app/actions/auth.ts
            console.debug('[Supabase Server] Cookie write failed (expected in Server Components):', error);
          }
        },
        remove(name: string, options: Record<string, unknown>) {
          try {
            cookieStore.set(name, '', {
              ...options,
              maxAge: 0,
            });
          } catch (error) {
            console.debug('[Supabase Server] Could not remove cookie:', error);
          }
        },
      },
    }
  );
}

// Aliases for consistent naming across the codebase
export const createSupabaseServerClient = createSupabaseServer;
export const createClient = createSupabaseServer;

/**
 * Service role client for background tasks that don't have access to user cookies.
 * Only use this for trusted server-side operations that bypass RLS.
 * Falls back to regular client if service role key is not available.
 */
export function createServiceRoleClient() {
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  
  if (!serviceRoleKey) {
    console.warn('[createServiceRoleClient] SUPABASE_SERVICE_ROLE_KEY not set, using anon key instead');
    // Fallback to anon key - will still work for operations that don't bypass RLS
    return createSupabaseClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        auth: {
          autoRefreshToken: false,
          persistSession: true
        }
      }
    );
  }
  
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    serviceRoleKey,
    {
      auth: {
        flowType: 'implicit',
        autoRefreshToken: false,
        persistSession: true,
        detectSessionInUrl: true,
      }
    }
  );
}

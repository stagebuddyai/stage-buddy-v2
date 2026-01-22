import { createServerClient } from "@supabase/ssr";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

/**
 * Server-side Supabase client for Next.js App Router route handlers and server components.
 * Adapter uses next/headers cookies() and implements getAll / setAll as required by @supabase/ssr.
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
        getAll() {
          try {
            return cookieStore.getAll();
          } catch (error) {
            console.error('[Supabase Server] Error getting cookies:', error);
            return [];
          }
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, String(value), {
                ...options,
                sameSite: 'lax',
                secure: true,
              });
            });
          } catch (error) {
            // Cookies cannot be set in Server Components, only in Route Handlers or Server Actions
            // This is expected behavior for read-only operations
            console.debug('[Supabase Server] Could not set cookies:', error);
          }
        },
        remove(name, options) {
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

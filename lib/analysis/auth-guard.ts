/**
 * Auth guard utility for API routes.
 * Returns the authenticated user or null.
 */

import { createSupabaseServer } from '@/lib/supabase/server';

export async function getAuthenticatedUser() {
  try {
    const supabase = await createSupabaseServer();
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error || !user) return null;
    return user;
  } catch {
    return null;
  }
}

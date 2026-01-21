import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServer } from "../../../../lib/supabase/server";

/**
 * GET /api/auth/session
 * Returns current session state (authenticated + user metadata).
 * Used by client to verify session after refresh/navigation.
 */
export async function GET(req: NextRequest) {
  try {
    const supabase = await createSupabaseServer();
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error || !user) {
      return NextResponse.json(
        { authenticated: false, user: null },
        { 
          status: 200,
          headers: { "Cache-Control": "no-store" }
        }
      );
    }

    return NextResponse.json(
      { 
        authenticated: true, 
        user: { 
          id: user.id, 
          email: user.email 
        } 
      },
      { 
        status: 200,
        headers: { "Cache-Control": "no-store" }
      }
    );
  } catch (error) {
    console.error("[/api/auth/session] Error:", error);
    return NextResponse.json(
      { authenticated: false, user: null },
      { 
        status: 200,
        headers: { "Cache-Control": "no-store" }
      }
    );
  }
}

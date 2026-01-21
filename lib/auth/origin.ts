import { NextRequest } from "next/server";

/**
 * Get the canonical auth origin for OAuth flows in Codespaces.
 * Priority:
 * 1. AUTH_BASE_URL env var (explicit canonical URL)
 * 2. Forwarded headers (x-forwarded-proto + x-forwarded-host)
 * 3. Request nextUrl origin
 */
export function getAuthOrigin(req: NextRequest): string {
  // Priority 1: explicit canonical auth base URL
  if (process.env.AUTH_BASE_URL) {
    return process.env.AUTH_BASE_URL.replace(/\/$/, "");
  }

  // Priority 2: forwarded headers (Codespaces, proxies)
  const proto = req.headers.get("x-forwarded-proto");
  const host = req.headers.get("x-forwarded-host");
  if (proto && host) {
    return `${proto}://${host}`;
  }

  // Priority 3: request origin
  return req.nextUrl.origin;
}

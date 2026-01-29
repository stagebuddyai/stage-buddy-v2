import { createBrowserClient } from '@supabase/ssr'
import type { SupabaseClient } from '@supabase/supabase-js'

// Hardcoded credentials (from .env.local)
const SUPABASE_URL = 'https://xhkvfjozqcskwqkcbmsm.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhoa3Zmam96cWNza3dxa2NibXNtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwODE4MzUsImV4cCI6MjA4MTY1NzgzNX0.NsMG0LbPHFITTXdXShXyyT1If8mZfR60YfMZlCilQOA'

// Browser Supabase client with cookie handling
export const supabase = createBrowserClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  {
    cookies: {
      get(name: string) {
        if (typeof document === 'undefined') return null
        const value = `; ${document.cookie}`
        const parts = value.split(`; ${name}=`)
        if (parts.length === 2) {
          const cookieValue = parts.pop()?.split(';').shift() ?? null
          if (cookieValue) {
            // Decode URL-encoded cookie value
            try {
              return decodeURIComponent(cookieValue)
            } catch {
              return cookieValue
            }
          }
        }
        return null
      },
      set(name: string, value: string, options: any) {
        if (typeof document === 'undefined') return
        let cookie = `${name}=${value}`
        if (options?.maxAge) cookie += `; max-age=${options.maxAge}`
        if (options?.path) cookie += `; path=${options.path}`
        if (options?.domain) cookie += `; domain=${options.domain}`
        if (options?.sameSite) cookie += `; samesite=${options.sameSite}`
        if (options?.secure) cookie += '; secure'
        document.cookie = cookie
      },
      remove(name: string, options: any) {
        if (typeof document === 'undefined') return
        this.set(name, '', { ...options, maxAge: 0 })
      }
    },
    isSingleton: true
  }
)

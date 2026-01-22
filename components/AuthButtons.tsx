'use client'

export default function AuthButtons({ connected }: { connected: boolean }) {
  if (connected) {
    return (
      <button
        onClick={() => window.location.href = '/api/auth/signout'}
        className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800"
      >
        Sign Out
      </button>
    )
  }

  return (
    <button
      onClick={() => window.location.href = '/api/auth/google'}
      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
    >
      Sign In with Google
    </button>
  )
}

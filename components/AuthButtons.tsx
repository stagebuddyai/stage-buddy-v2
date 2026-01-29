'use client'

import { signInWithGoogle, signOut } from '@/app/actions/auth'
import { useState } from 'react'

export default function AuthButtons({ connected }: { connected: boolean }) {
  const [isLoading, setIsLoading] = useState(false)

  const handleSignOut = async () => {
    setIsLoading(true)
    try {
      await signOut()
    } catch (error) {
      console.error('Sign out error:', error)
      setIsLoading(false)
    }
  }

  const handleSignIn = async () => {
    setIsLoading(true)
    try {
      await signInWithGoogle()
    } catch (error) {
      console.error('Sign in error:', error)
      setIsLoading(false)
    }
  }

  if (connected) {
    return (
      <button
        onClick={handleSignOut}
        disabled={isLoading}
        className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-900 hover:bg-zinc-50 disabled:opacity-50 disabled:cursor-not-allowed dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800"
      >
        {isLoading ? 'Signing Out...' : 'Sign Out'}
      </button>
    )
  }

  return (
    <button
      onClick={handleSignIn}
      disabled={isLoading}
      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-500 dark:hover:bg-blue-600"
    >
      {isLoading ? 'Signing In...' : 'Sign In with Google'}
    </button>
  )
}

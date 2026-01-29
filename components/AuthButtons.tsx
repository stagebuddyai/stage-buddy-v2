'use client'

import { signInWithGoogle, signOut } from '@/app/actions/auth'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function AuthButtons({ connected }: { connected: boolean }) {
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSignOut = async () => {
    setIsLoading(true)
    try {
      const result = await signOut()
      if (result.error) {
        console.error('Sign out error:', result.error)
        alert(`Sign out failed: ${result.error}`)
        setIsLoading(false)
      } else {
        // Refresh the page to update UI
        router.refresh()
      }
    } catch (error) {
      console.error('Sign out error:', error)
      alert('Sign out failed. Please try again.')
      setIsLoading(false)
    }
  }

  const handleSignIn = async () => {
    setIsLoading(true)
    try {
      const result = await signInWithGoogle()
      if (result.error || !result.url) {
        console.error('Sign in error:', result.error)
        alert(`Sign in failed: ${result.error || 'No URL returned'}`)
        setIsLoading(false)
      } else {
        // Redirect to OAuth provider (loading state remains until redirect)
        window.location.href = result.url
      }
    } catch (error) {
      console.error('Sign in error:', error)
      alert(`Sign in failed: ${error instanceof Error ? error.message : 'Please try again.'}`)
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

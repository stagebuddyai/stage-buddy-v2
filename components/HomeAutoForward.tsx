'use client'

import { useEffect } from 'react'

export default function HomeAutoForward({ returnTo }: { returnTo: string | null }) {
  useEffect(() => {
    if (returnTo) {
      window.location.href = returnTo
    }
  }, [returnTo])

  return null
}

'use client'

import { useEffect } from 'react'
import Link from 'next/link'

export default function EditClientError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-gray-900 font-medium mb-1">Something went wrong</p>
      <p className="text-sm text-gray-500 mb-6">
        {error.message || 'Failed to load client details.'}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Try again
        </button>
        <Link
          href="/dashboard"
          className="px-4 py-2 bg-white hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg border border-gray-300 transition-colors"
        >
          Back to clients
        </Link>
      </div>
    </div>
  )
}

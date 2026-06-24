import Link from 'next/link'

export default function ClientNotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-gray-900 font-medium mb-1">Client not found</p>
      <p className="text-sm text-gray-500 mb-6">This client may have been removed.</p>
      <Link
        href="/dashboard"
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Back to clients
      </Link>
    </div>
  )
}

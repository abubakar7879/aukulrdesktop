export default function DashboardLoading() {
  return (
    <div>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 px-4 py-4">
            <div className="h-3 w-20 bg-gray-100 rounded animate-pulse mb-2" />
            <div className="h-7 w-8 bg-gray-200 rounded animate-pulse" />
          </div>
        ))}
      </div>

      <div className="flex gap-3 mb-3">
        <div className="h-9 w-80 bg-gray-200 rounded-lg animate-pulse" />
        <div className="sm:ml-auto h-9 w-28 bg-gray-200 rounded-lg animate-pulse" />
      </div>

      <div className="flex gap-2 mb-5">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-8 w-20 bg-gray-100 rounded-full animate-pulse" />
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="border-b border-gray-200 bg-gray-50 h-11" />
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="flex gap-6 px-4 py-3 border-b border-gray-100 last:border-0"
          >
            <div className="h-4 w-36 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 w-14 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}

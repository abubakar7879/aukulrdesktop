export default function EditClientLoading() {
  return (
    <div className="max-w-2xl">
      {/* Back + header */}
      <div className="mb-6">
        <div className="h-4 w-28 bg-gray-200 rounded animate-pulse" />
        <div className="flex items-center gap-2 mt-3">
          <div className="h-6 w-48 bg-gray-200 rounded animate-pulse" />
          <div className="h-5 w-16 bg-gray-100 rounded-full animate-pulse" />
        </div>
      </div>

      {/* Identity card */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4 mb-5">
        <div className="h-4 w-16 bg-gray-200 rounded animate-pulse" />
        <div className="space-y-1">
          <div className="h-3 w-10 bg-gray-100 rounded animate-pulse" />
          <div className="h-9 bg-gray-100 rounded-lg animate-pulse" />
        </div>
        <div className="space-y-1">
          <div className="h-3 w-14 bg-gray-100 rounded animate-pulse" />
          <div className="h-9 bg-gray-100 rounded-lg animate-pulse" />
        </div>
        <div className="grid grid-cols-2 gap-4 border-t border-gray-100 pt-4">
          <div className="space-y-1">
            <div className="h-3 w-12 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
          </div>
          <div className="space-y-1">
            <div className="h-3 w-20 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
          </div>
        </div>
      </div>

      {/* License card */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4 mb-5">
        <div className="h-4 w-14 bg-gray-200 rounded animate-pulse" />
        <div className="space-y-1">
          <div className="h-3 w-20 bg-gray-100 rounded animate-pulse" />
          <div className="h-9 bg-gray-100 rounded-lg animate-pulse" />
        </div>
        <div className="flex items-center justify-between border-t border-gray-100 pt-4">
          <div className="space-y-1">
            <div className="h-4 w-12 bg-gray-100 rounded animate-pulse" />
            <div className="h-3 w-40 bg-gray-100 rounded animate-pulse" />
          </div>
          <div className="h-8 w-20 bg-gray-100 rounded-lg animate-pulse" />
        </div>
      </div>

      {/* Notes card */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
        <div className="h-4 w-12 bg-gray-200 rounded animate-pulse mb-3" />
        <div className="h-20 bg-gray-100 rounded-lg animate-pulse" />
      </div>

      {/* Save / Cancel */}
      <div className="flex gap-3">
        <div className="flex-1 h-9 bg-blue-200 rounded-lg animate-pulse" />
        <div className="flex-1 h-9 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    </div>
  )
}

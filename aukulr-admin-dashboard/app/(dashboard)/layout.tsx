import Link from 'next/link'
import { verifySession } from '@/lib/session'
import { logout } from '@/app/actions/auth'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  await verifySession()

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="text-base font-semibold text-gray-900">
              Aukulr Admin
            </span>
            <Link
              href="/dashboard"
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Clients
            </Link>
            <Link
              href="/dashboard/registrations"
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Registrations
            </Link>
          </div>
          <form action={logout}>
            <button
              type="submit"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              Logout
            </button>
          </form>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}

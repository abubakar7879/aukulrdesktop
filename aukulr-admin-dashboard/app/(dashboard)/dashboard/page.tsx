import { getClients } from '@/lib/clients'

function isExpired(expiryDate: string) {
  return new Date(expiryDate) < new Date(new Date().toDateString())
}

function isExpiringSoon(expiryDate: string) {
  const expiry = new Date(expiryDate)
  const soon = new Date()
  soon.setDate(soon.getDate() + 7)
  return expiry >= new Date(new Date().toDateString()) && expiry <= soon
}

function maskUserId(userId: string) {
  return userId.slice(0, 8) + '…'
}

export default async function DashboardPage() {
  const clients = await getClients()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Clients</h1>
          <p className="text-sm text-gray-500 mt-0.5">{clients.length} total</p>
        </div>
        <a
          href="/dashboard/clients/new"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          + Add client
        </a>
      </div>

      {clients.length === 0 ? (
        <div className="text-center py-20 text-gray-400 text-sm">
          No clients yet. Add one to get started.
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-500">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">User ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Expiry</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clients.map((client) => {
                const expired = isExpired(client.expiryDate)
                const soon = isExpiringSoon(client.expiryDate)
                return (
                  <tr key={client.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {client.name}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500">
                      {maskUserId(client.userId)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          client.status === 'enabled'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {client.status === 'enabled' ? 'Enabled' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          expired
                            ? 'text-red-600 font-medium'
                            : soon
                            ? 'text-amber-600 font-medium'
                            : 'text-gray-700'
                        }
                      >
                        {client.expiryDate}
                        {expired && (
                          <span className="ml-1.5 text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded-full">
                            Expired
                          </span>
                        )}
                        {soon && !expired && (
                          <span className="ml-1.5 text-xs bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded-full">
                            Soon
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{client.createdAt}</td>
                    <td className="px-4 py-3 text-right">
                      <a
                        href={`/dashboard/clients/${client.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium mr-3"
                      >
                        Edit
                      </a>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

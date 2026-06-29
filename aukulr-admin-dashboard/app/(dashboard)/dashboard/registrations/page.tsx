import { getRegistrationRequests } from '@/lib/db'
import { approveRegistration, rejectRegistration } from '@/app/actions/registrations'

export default async function RegistrationsPage() {
  const requests = await getRegistrationRequests()
  const pending = requests.filter((r) => r.status === 'pending')
  const processed = requests.filter((r) => r.status !== 'pending')

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Device Registrations</h1>
        <p className="mt-1 text-sm text-gray-500">
          Approve or reject incoming registration requests from client machines.
        </p>
      </div>

      {/* Pending */}
      <section>
        <h2 className="text-sm font-medium text-gray-700 mb-3">
          Pending{' '}
          {pending.length > 0 && (
            <span className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-semibold">
              {pending.length}
            </span>
          )}
        </h2>
        {pending.length === 0 ? (
          <p className="text-sm text-gray-400">No pending requests.</p>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {pending.map((r) => {
              const approve = approveRegistration.bind(null, r.id)
              const reject = rejectRegistration.bind(null, r.id)
              return (
                <div key={r.id} className="px-5 py-4 flex items-start justify-between gap-6">
                  <div className="space-y-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{r.clinicName}</p>
                    <p className="text-sm text-gray-500">{r.contact}</p>
                    <div className="flex flex-wrap gap-4 mt-1">
                      <span className="text-xs text-gray-400">
                        CPU ID:{' '}
                        <span className="font-mono text-gray-600">{r.cpuId}</span>
                      </span>
                      <span className="text-xs text-gray-400">
                        Machine:{' '}
                        <span className="text-gray-600">{r.machineName}</span>
                      </span>
                      <span className="text-xs text-gray-400">
                        Windows User:{' '}
                        <span className="text-gray-600">{r.windowsUser}</span>
                      </span>
                      <span className="text-xs text-gray-400">
                        Requested:{' '}
                        <span className="text-gray-600">
                          {new Date(r.requestedAt).toLocaleString()}
                        </span>
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <form action={approve}>
                      <button
                        type="submit"
                        className="px-3 py-1.5 text-xs font-medium rounded-md bg-green-600 text-white hover:bg-green-700 transition-colors"
                      >
                        Approve
                      </button>
                    </form>
                    <form action={reject}>
                      <button
                        type="submit"
                        className="px-3 py-1.5 text-xs font-medium rounded-md bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
                      >
                        Reject
                      </button>
                    </form>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Processed */}
      {processed.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-gray-700 mb-3">Previously Processed</h2>
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {processed.map((r) => (
              <div key={r.id} className="px-5 py-4 flex items-center justify-between gap-6">
                <div className="space-y-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{r.clinicName}</p>
                  <p className="text-xs text-gray-400 font-mono">{r.cpuId}</p>
                </div>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    r.status === 'approved'
                      ? 'bg-green-50 text-green-700'
                      : 'bg-red-50 text-red-700'
                  }`}
                >
                  {r.status}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

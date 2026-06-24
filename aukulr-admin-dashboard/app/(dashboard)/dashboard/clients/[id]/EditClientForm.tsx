'use client'

import { useActionState, useState, useTransition, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { editClient, toggleClientStatus, removeClient, type ClientFormState } from '@/app/actions/clients'
import type { Client } from '@/lib/clients'
import type { AuditEntry } from '@/lib/audit'
import Link from 'next/link'
import { isExpired, isExpiringSoon } from '@/lib/dates'

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatAuditAction(entry: AuditEntry): string {
  switch (entry.action) {
    case 'created':
      return 'Client created'
    case 'enabled':
      return 'Status set to Enabled'
    case 'disabled':
      return 'Status set to Disabled'
    case 'expiry_changed':
      return `Expiry changed from ${entry.before} to ${entry.after}`
    case 'userid_changed':
      return `User ID changed from ${entry.before?.slice(0, 8)}… to ${entry.after?.slice(0, 8)}…`
    case 'notes_updated':
      return 'Notes updated'
    case 'removed':
      return 'Client removed'
  }
}


export default function EditClientForm({
  client,
  auditLog,
}: {
  client: Client
  auditLog: AuditEntry[]
}) {
  const router = useRouter()
  const boundAction = editClient.bind(null, client.id)
  const [state, action, pending] = useActionState<ClientFormState, FormData>(
    boundAction,
    undefined,
  )

  // userId change confirmation
  const [savedUserId, setSavedUserId] = useState(client.userId)
  const [currentUserId, setCurrentUserId] = useState(client.userId)
  const [userIdConfirmed, setUserIdConfirmed] = useState(false)
  const userIdChanged = currentUserId !== savedUserId

  // Status toggle
  const [localStatus, setLocalStatus] = useState(client.status)
  const [toggling, startToggle] = useTransition()

  // Danger zone
  const [confirmName, setConfirmName] = useState('')
  const [removing, startRemove] = useTransition()

  // Success banner
  const [successVisible, setSuccessVisible] = useState(false)

  useEffect(() => {
    if (state?.success) {
      setSuccessVisible(true)
      setSavedUserId(currentUserId)
      setUserIdConfirmed(false)
      router.refresh()
      const t = setTimeout(() => setSuccessVisible(false), 3000)
      return () => clearTimeout(t)
    }
  }, [state])

  function handleToggle() {
    const newEnabled = localStatus !== 'enabled'
    if (!confirm(`${newEnabled ? 'Enable' : 'Disable'} this client?`)) return
    startToggle(async () => {
      await toggleClientStatus(client.id, newEnabled)
      setLocalStatus(newEnabled ? 'enabled' : 'disabled')
    })
  }

  function handleRemove() {
    startRemove(async () => {
      await removeClient(client.id)
      router.push('/dashboard')
    })
  }

  const expired = isExpired(client.expiryDate)
  const soon = isExpiringSoon(client.expiryDate)
  const canSave = !pending && !(userIdChanged && !userIdConfirmed)

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="mb-6">
        <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-900">
          ← Back to clients
        </Link>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <h1 className="text-xl font-semibold text-gray-900">{client.name}</h1>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
              localStatus === 'enabled'
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {localStatus === 'enabled' ? 'Enabled' : 'Disabled'}
          </span>
          {expired && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-600">
              Expired
            </span>
          )}
          {soon && !expired && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-600">
              Expiring soon
            </span>
          )}
        </div>
      </div>

      {/* Success banner */}
      {successVisible && (
        <div className="mb-4 px-4 py-2.5 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          ✓ Changes saved
        </div>
      )}

      <form action={action} className="space-y-5">
        {/* Identity */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900">Identity</h2>

          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              required
              defaultValue={client.name}
              className="w-full px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="userId" className="block text-sm font-medium text-gray-700 mb-1">
              User ID
            </label>
            <input
              id="userId"
              name="userId"
              type="text"
              required
              value={currentUserId}
              onChange={(e) => {
                setCurrentUserId(e.target.value.toLowerCase())
                setUserIdConfirmed(false)
              }}
              className="w-full px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {userIdChanged && (
              <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <p className="font-medium mb-2">
                  ⚠ Changing the User ID re-points the license to a different machine.
                </p>
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={userIdConfirmed}
                    onChange={(e) => setUserIdConfirmed(e.target.checked)}
                  />
                  I understand, proceed with this change
                </label>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4 border-t border-gray-100 pt-4">
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Created</p>
              <p className="text-sm text-gray-700">{client.createdAt}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Last updated</p>
              <p className="text-sm text-gray-700">{client.lastUpdated}</p>
            </div>
          </div>
        </div>

        {/* License */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900">License</h2>

          <div>
            <label htmlFor="expiryDate" className="block text-sm font-medium text-gray-700 mb-1">
              Expiry date
            </label>
            <input
              id="expiryDate"
              name="expiryDate"
              type="date"
              required
              defaultValue={client.expiryDate}
              className="w-full px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center justify-between border-t border-gray-100 pt-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Status</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {localStatus === 'enabled'
                  ? 'This client can authenticate.'
                  : 'This client cannot authenticate.'}
              </p>
            </div>
            <button
              type="button"
              onClick={handleToggle}
              disabled={toggling}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 ${
                localStatus === 'enabled'
                  ? 'border-amber-300 text-amber-700 hover:bg-amber-50'
                  : 'border-green-300 text-green-700 hover:bg-green-50'
              }`}
            >
              {toggling ? '…' : localStatus === 'enabled' ? 'Disable' : 'Enable'}
            </button>
          </div>
        </div>

        {/* Notes */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <label
            htmlFor="notes"
            className="block text-sm font-semibold text-gray-900 mb-3"
          >
            Notes{' '}
            <span className="font-normal text-gray-400">(optional)</span>
          </label>
          <textarea
            id="notes"
            name="notes"
            rows={3}
            defaultValue={client.notes ?? ''}
            placeholder="Internal notes about this client…"
            className="w-full px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
        </div>

        {state?.error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {state.error}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={!canSave}
            className="flex-1 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {pending ? 'Saving…' : 'Save changes'}
          </button>
          <Link
            href="/dashboard"
            className="flex-1 py-2 px-4 text-center bg-white hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg border border-gray-300 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>

      {/* Activity / audit log */}
      <div className="mt-8 bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">Activity</h2>
        {auditLog.length === 0 ? (
          <p className="text-sm text-gray-400">No activity recorded yet.</p>
        ) : (
          <ul className="space-y-3">
            {auditLog.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 text-sm">
                <span className="text-gray-400 text-xs pt-0.5 w-40 flex-none whitespace-nowrap">
                  {formatTimestamp(entry.timestamp)}
                </span>
                <span className="text-gray-700 flex-1">{formatAuditAction(entry)}</span>
                <span className="text-gray-400 text-xs whitespace-nowrap">
                  by {entry.actor}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Danger zone */}
      <div className="mt-5 border border-red-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-red-700 mb-1">Danger zone</h2>
        <p className="text-sm text-gray-500 mb-4">
          Removing this client is permanent. Type{' '}
          <strong className="text-gray-700">{client.name}</strong> to confirm.
        </p>
        <div className="flex gap-3">
          <input
            type="text"
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
            placeholder={client.name}
            className="flex-1 px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
          <button
            type="button"
            onClick={handleRemove}
            disabled={confirmName !== client.name || removing}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {removing ? 'Removing…' : 'Remove client'}
          </button>
        </div>
      </div>
    </div>
  )
}

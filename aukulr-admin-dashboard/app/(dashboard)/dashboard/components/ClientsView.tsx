'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import type { Client } from '@/lib/clients'
import ClientRowActions from './ClientRowActions'

type FilterType = 'all' | 'active' | 'disabled' | 'expired' | 'expiring-soon'

function todayDate() {
  return new Date(new Date().toDateString())
}

function soonDate() {
  const d = new Date()
  d.setDate(d.getDate() + 7)
  return d
}

function isExpired(expiryDate: string) {
  return new Date(expiryDate) < todayDate()
}

function isExpiringSoon(expiryDate: string) {
  const expiry = new Date(expiryDate)
  return expiry >= todayDate() && expiry <= soonDate()
}

function maskUserId(userId: string) {
  return userId.slice(0, 8) + '…'
}

function computeStats(clients: Client[]) {
  return {
    total: clients.length,
    active: clients.filter(
      (c) => c.status === 'enabled' && new Date(c.expiryDate) >= todayDate(),
    ).length,
    disabled: clients.filter((c) => c.status === 'disabled').length,
    expired: clients.filter((c) => new Date(c.expiryDate) < todayDate()).length,
    expiringSoon: clients.filter(
      (c) =>
        c.status === 'enabled' &&
        new Date(c.expiryDate) >= todayDate() &&
        new Date(c.expiryDate) <= soonDate(),
    ).length,
  }
}

export default function ClientsView({ clients }: { clients: Client[] }) {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterType>('all')

  // Debounce search — flag: move to server-side query once client count grows large
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 300)
    return () => clearTimeout(t)
  }, [searchInput])

  const stats = useMemo(() => computeStats(clients), [clients])

  const filtered = useMemo(() => {
    let result = clients

    if (filter === 'active') {
      result = result.filter(
        (c) => c.status === 'enabled' && new Date(c.expiryDate) >= todayDate(),
      )
    } else if (filter === 'disabled') {
      result = result.filter((c) => c.status === 'disabled')
    } else if (filter === 'expired') {
      result = result.filter((c) => new Date(c.expiryDate) < todayDate())
    } else if (filter === 'expiring-soon') {
      result = result.filter(
        (c) =>
          c.status === 'enabled' &&
          new Date(c.expiryDate) >= todayDate() &&
          new Date(c.expiryDate) <= soonDate(),
      )
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) || c.userId.toLowerCase().includes(q),
      )
    }

    return result
  }, [clients, filter, search])

  const statCards: {
    label: string
    value: number
    color: string
    ring: string
    filterKey: FilterType
  }[] = [
    { label: 'Total clients', value: stats.total, color: 'text-gray-900', ring: 'ring-blue-500 border-blue-500', filterKey: 'all' },
    { label: 'Active', value: stats.active, color: 'text-green-600', ring: 'ring-green-500 border-green-500', filterKey: 'active' },
    { label: 'Expiring soon', value: stats.expiringSoon, color: 'text-amber-600', ring: 'ring-amber-500 border-amber-500', filterKey: 'expiring-soon' },
    { label: 'Disabled', value: stats.disabled, color: 'text-gray-500', ring: 'ring-gray-400 border-gray-400', filterKey: 'disabled' },
    { label: 'Expired', value: stats.expired, color: 'text-red-500', ring: 'ring-red-500 border-red-500', filterKey: 'expired' },
  ]

  const filterChips: { key: FilterType; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: stats.total },
    { key: 'active', label: 'Active', count: stats.active },
    { key: 'disabled', label: 'Disabled', count: stats.disabled },
    { key: 'expired', label: 'Expired', count: stats.expired },
    { key: 'expiring-soon', label: 'Expiring soon', count: stats.expiringSoon },
  ]

  const emptySearchMsg = search.trim() ? `No clients match "${search}"` : null
  const emptyFilterMsg =
    !search.trim() && filter !== 'all'
      ? `No ${filter === 'expiring-soon' ? 'expiring soon' : filter} clients.`
      : null

  return (
    <div>
      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
        {statCards.map((s) => (
          <button
            key={s.filterKey}
            onClick={() => setFilter(s.filterKey)}
            className={`text-left bg-white rounded-xl border px-4 py-4 transition-all ${
              filter === s.filterKey
                ? `border-transparent ring-2 ${s.ring}`
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <p className="text-xs text-gray-500 mb-1">{s.label}</p>
            <p className={`text-2xl font-semibold ${s.color}`}>{s.value}</p>
          </button>
        ))}
      </div>

      {/* Search + Add button */}
      <div className="flex flex-col sm:flex-row gap-3 mb-3">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by name or ID…"
          className="w-full sm:w-80 px-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <div className="sm:ml-auto">
          <Link
            href="/dashboard/clients/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            + Add client
          </Link>
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 overflow-x-auto pb-1 mb-5">
        {filterChips.map((chip) => (
          <button
            key={chip.key}
            onClick={() => setFilter(chip.key)}
            className={`flex-none inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
              filter === chip.key
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-gray-300'
            }`}
          >
            {chip.label}
            <span
              className={`text-xs px-1.5 py-0.5 rounded-full ${
                filter === chip.key
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {chip.count}
            </span>
          </button>
        ))}
      </div>

      {/* Table / empty states */}
      {clients.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-500 mb-1 font-medium">No clients yet</p>
          <p className="text-sm text-gray-400 mb-6">Add your first client to get started.</p>
          <Link
            href="/dashboard/clients/new"
            className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            + Add your first client
          </Link>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="mb-3">{emptySearchMsg ?? emptyFilterMsg ?? 'No clients found.'}</p>
          {search.trim() && (
            <button
              onClick={() => {
                setSearchInput('')
                setSearch('')
              }}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear search
            </button>
          )}
          {!search.trim() && filter !== 'all' && (
            <button
              onClick={() => setFilter('all')}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Show all clients
            </button>
          )}
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
              {filtered.map((client) => {
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
                    <td className="px-4 py-3">
                      <ClientRowActions
                        id={client.id}
                        name={client.name}
                        enabled={client.status === 'enabled'}
                      />
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

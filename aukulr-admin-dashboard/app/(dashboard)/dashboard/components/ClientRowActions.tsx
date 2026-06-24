'use client'

import { useTransition } from 'react'
import { useRouter } from 'next/navigation'
import { toggleClientStatus, removeClient } from '@/app/actions/clients'

type Props = {
  id: string
  name: string
  enabled: boolean
}

export default function ClientRowActions({ id, name, enabled }: Props) {
  const router = useRouter()
  const [toggling, startToggle] = useTransition()
  const [removing, startRemove] = useTransition()

  function handleToggle() {
    if (!confirm(`${enabled ? 'Disable' : 'Enable'} "${name}"?`)) return
    startToggle(async () => {
      await toggleClientStatus(id, !enabled)
      router.refresh()
    })
  }

  function handleRemove() {
    if (!confirm(`Permanently remove "${name}"? This cannot be undone.`)) return
    startRemove(async () => {
      await removeClient(id)
      router.refresh()
    })
  }

  return (
    <div className="flex items-center justify-end gap-3">
      <a
        href={`/dashboard/clients/${id}`}
        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
      >
        Edit
      </a>
      <button
        onClick={handleToggle}
        disabled={toggling || removing}
        className={`text-sm font-medium disabled:opacity-40 ${
          enabled
            ? 'text-amber-600 hover:text-amber-800'
            : 'text-green-600 hover:text-green-800'
        }`}
      >
        {toggling ? '…' : enabled ? 'Disable' : 'Enable'}
      </button>
      <button
        onClick={handleRemove}
        disabled={toggling || removing}
        className="text-sm font-medium text-red-500 hover:text-red-700 disabled:opacity-40"
      >
        {removing ? '…' : 'Remove'}
      </button>
    </div>
  )
}

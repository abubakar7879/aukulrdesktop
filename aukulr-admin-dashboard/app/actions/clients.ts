'use server'

import {
  addClient,
  updateClient,
  setClientStatus,
  deleteClient,
  getClient,
  checkUserIdExists,
} from '@/lib/clients'
import { addAuditEntry } from '@/lib/audit'
import { redirect } from 'next/navigation'

export type ClientFormState = { error?: string; success?: boolean } | undefined

export async function createClient(
  _prevState: ClientFormState,
  formData: FormData,
): Promise<ClientFormState> {
  const name = (formData.get('name')?.toString() ?? '').trim()
  const userId = (formData.get('userId')?.toString() ?? '').trim().toLowerCase()
  const expiryDate = formData.get('expiryDate')?.toString() ?? ''
  const notes = (formData.get('notes')?.toString() ?? '').trim() || undefined

  if (!name) return { error: 'Name is required.' }
  if (!userId) return { error: 'User ID is required.' }
  if (!expiryDate) return { error: 'Expiry date is required.' }

  if (await checkUserIdExists(userId)) {
    return { error: 'This User ID is already assigned to another client.' }
  }

  const client = await addClient({ name, userId, expiryDate, notes })
  await addAuditEntry({ clientId: client.id, actor: 'admin', action: 'created' })
  redirect('/dashboard')
}

export async function editClient(
  id: string,
  _prevState: ClientFormState,
  formData: FormData,
): Promise<ClientFormState> {
  const name = (formData.get('name')?.toString() ?? '').trim()
  const userId = (formData.get('userId')?.toString() ?? '').trim().toLowerCase()
  const expiryDate = formData.get('expiryDate')?.toString() ?? ''
  const notes = (formData.get('notes')?.toString() ?? '').trim() || undefined

  if (!name) return { error: 'Name is required.' }
  if (!userId) return { error: 'User ID is required.' }
  if (!expiryDate) return { error: 'Expiry date is required.' }

  const existing = await getClient(id)
  if (!existing) return { error: 'Client not found.' }

  if (userId !== existing.userId && (await checkUserIdExists(userId, id))) {
    return { error: 'This User ID is already assigned to another client.' }
  }

  // Capture what changed before mutating so audit entries are accurate
  const prevUserId = existing.userId
  const prevExpiry = existing.expiryDate
  const userIdChanged = userId !== prevUserId
  const expiryChanged = expiryDate !== prevExpiry
  const notesChanged = (notes ?? '') !== (existing.notes ?? '')

  // Mutate first — only log if the mutation succeeds
  await updateClient(id, { name, userId, expiryDate, notes })

  if (userIdChanged) {
    await addAuditEntry({ clientId: id, actor: 'admin', action: 'userid_changed', before: prevUserId, after: userId })
  }
  if (expiryChanged) {
    await addAuditEntry({ clientId: id, actor: 'admin', action: 'expiry_changed', before: prevExpiry, after: expiryDate })
  }
  if (notesChanged) {
    await addAuditEntry({ clientId: id, actor: 'admin', action: 'notes_updated' })
  }

  return { success: true }
}

export async function toggleClientStatus(id: string, enabled: boolean): Promise<void> {
  await setClientStatus(id, enabled)
  await addAuditEntry({
    clientId: id,
    actor: 'admin',
    action: enabled ? 'enabled' : 'disabled',
  })
}

export async function removeClient(id: string): Promise<void> {
  await deleteClient(id)
  await addAuditEntry({ clientId: id, actor: 'admin', action: 'removed' })
}

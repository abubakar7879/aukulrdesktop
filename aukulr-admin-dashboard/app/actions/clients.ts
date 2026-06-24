'use server'

import { addClient, updateClient, setClientStatus, deleteClient } from '@/lib/clients'
import { redirect } from 'next/navigation'

export type ClientFormState = { error?: string } | undefined

export async function createClient(
  prevState: ClientFormState,
  formData: FormData,
): Promise<ClientFormState> {
  const name = formData.get('name')?.toString().trim()
  const expiryDate = formData.get('expiryDate')?.toString()

  if (!name) return { error: 'Name is required.' }
  if (!expiryDate) return { error: 'Expiry date is required.' }

  await addClient({ name, expiryDate })
  redirect('/dashboard')
}

export async function editClient(
  id: string,
  prevState: ClientFormState,
  formData: FormData,
): Promise<ClientFormState> {
  const name = formData.get('name')?.toString().trim()
  const expiryDate = formData.get('expiryDate')?.toString()

  if (!name) return { error: 'Name is required.' }
  if (!expiryDate) return { error: 'Expiry date is required.' }

  await updateClient(id, { name, expiryDate })
  redirect('/dashboard')
}

export async function toggleClientStatus(id: string, enabled: boolean) {
  await setClientStatus(id, enabled)
  redirect('/dashboard')
}

export async function removeClient(id: string) {
  await deleteClient(id)
  redirect('/dashboard')
}

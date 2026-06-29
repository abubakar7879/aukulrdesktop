'use server'

import { updateRegistrationStatus } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function approveRegistration(id: string): Promise<void> {
  await updateRegistrationStatus(id, 'approved')
  revalidatePath('/dashboard/registrations')
}

export async function rejectRegistration(id: string): Promise<void> {
  await updateRegistrationStatus(id, 'rejected')
  revalidatePath('/dashboard/registrations')
}

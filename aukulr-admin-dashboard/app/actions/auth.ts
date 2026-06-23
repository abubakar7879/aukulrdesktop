'use server'

import { createSession, deleteSession } from '@/lib/session'
import { redirect } from 'next/navigation'

export type LoginState = { error?: string } | undefined

export async function login(
  prevState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const username = (formData.get('username') as string)?.trim()
  const password = formData.get('password') as string

  if (
    username === process.env.ADMIN_USERNAME &&
    password === process.env.ADMIN_PASSWORD
  ) {
    await createSession()
    redirect('/dashboard')
  }

  return { error: 'Invalid username or password' }
}

export async function logout() {
  await deleteSession()
  redirect('/login')
}

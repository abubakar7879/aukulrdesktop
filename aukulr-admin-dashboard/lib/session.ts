import { SignJWT, jwtVerify } from 'jose'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

const key = new TextEncoder().encode(process.env.SESSION_SECRET)
const SESSION_DURATION_MS = 8 * 60 * 60 * 1000

export async function encrypt(payload: { userId: string; expiresAt: Date }) {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('8h')
    .sign(key)
}

export async function decrypt(session: string | undefined) {
  if (!session) return null
  try {
    const { payload } = await jwtVerify(session, key, { algorithms: ['HS256'] })
    return payload
  } catch {
    return null
  }
}

export async function createSession() {
  const expiresAt = new Date(Date.now() + SESSION_DURATION_MS)
  const session = await encrypt({ userId: 'admin', expiresAt })
  const cookieStore = await cookies()
  cookieStore.set('session', session, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    expires: expiresAt,
    sameSite: 'lax',
    path: '/',
  })
}

export async function deleteSession() {
  const cookieStore = await cookies()
  cookieStore.delete('session')
}

export async function verifySession() {
  const cookieStore = await cookies()
  const cookie = cookieStore.get('session')?.value
  const session = await decrypt(cookie)
  if (!session?.userId) {
    redirect('/login')
  }
  return { isAuth: true }
}

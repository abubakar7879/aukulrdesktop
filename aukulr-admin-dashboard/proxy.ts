import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { decrypt } from '@/lib/session'

export async function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname
  const isProtected = path === '/dashboard' || path.startsWith('/dashboard/')
  const isPublic = path === '/login' || path === '/'

  const cookie = req.cookies.get('session')?.value
  const session = await decrypt(cookie)

  if (isProtected && !session?.userId) {
    return NextResponse.redirect(new URL('/login', req.nextUrl))
  }

  if (isPublic && session?.userId) {
    return NextResponse.redirect(new URL('/dashboard', req.nextUrl))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|.*\\.png$).*)'],
}

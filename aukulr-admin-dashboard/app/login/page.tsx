'use client'

import { useActionState } from 'react'
import { login, type LoginState } from '@/app/actions/auth'

export default function LoginPage() {
  const [state, action, pending] = useActionState<LoginState, FormData>(
    login,
    undefined,
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Aukulr Admin</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to your account</p>
        </div>

        <form action={action} className="space-y-5">
          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {state?.error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {state.error}
            </p>
          )}

          <button
            type="submit"
            disabled={pending}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {pending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

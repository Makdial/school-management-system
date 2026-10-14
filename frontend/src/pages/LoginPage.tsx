import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { GraduationCap, Lock, UserRound } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/Button'
import { Field, Input } from '@/components/ui/Input'

const DEMO = { username: 'schooladmin', password: 'Demo@12345' }

export function LoginPage() {
  const { login, isLoggingIn, loginError, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch {
      // error surfaced through loginError
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between bg-brand-700 p-10 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-white/15">
            <GraduationCap className="size-6" />
          </div>
          <span className="text-lg font-semibold">School Management System</span>
        </div>
        <div className="max-w-md">
          <h1 className="text-3xl font-semibold leading-tight">
            Run your entire school from one place.
          </h1>
          <p className="mt-4 text-brand-100">
            Admissions, students, attendance, examinations, finance, library,
            HR and transport — unified, secure and tenant-isolated.
          </p>
        </div>
        <p className="text-sm text-brand-200">
          © {new Date().getFullYear()} School ERP
        </p>
        <div className="pointer-events-none absolute -right-24 top-1/3 size-72 rounded-full bg-white/5 blur-2xl" />
      </div>

      <div className="flex items-center justify-center bg-slate-50 p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 items-center justify-center rounded-lg bg-brand-600 text-white">
                <GraduationCap className="size-5" />
              </div>
              <span className="text-base font-semibold text-slate-900">
                School ERP
              </span>
            </div>
          </div>

          <h2 className="text-2xl font-semibold text-slate-900">Sign in</h2>
          <p className="mt-1 text-sm text-slate-500">
            Welcome back. Enter your credentials to continue.
          </p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <Field label="Username" htmlFor="username" required>
              <div className="relative">
                <UserRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="username"
                  value={username}
                  autoComplete="username"
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="schooladmin"
                  className="pl-9"
                  required
                />
              </div>
            </Field>

            <Field label="Password" htmlFor="password" required>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  autoComplete="current-password"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  className="pl-9"
                  required
                />
              </div>
            </Field>

            {loginError ? (
              <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {loginError}
              </div>
            ) : null}

            <Button type="submit" size="lg" loading={isLoggingIn} className="w-full">
              Sign in
            </Button>
          </form>

          <button
            type="button"
            onClick={() => {
              setUsername(DEMO.username)
              setPassword(DEMO.password)
            }}
            className="mt-6 w-full rounded-lg border border-dashed border-slate-300 px-3 py-2.5 text-left text-xs text-slate-500 transition hover:border-brand-300 hover:bg-white"
          >
            <span className="font-medium text-slate-600">Demo account</span>
            <br />
            Use <code className="text-brand-600">schooladmin</code> /{' '}
            <code className="text-brand-600">Demo@12345</code> — click to fill.
          </button>
        </div>
      </div>
    </div>
  )
}

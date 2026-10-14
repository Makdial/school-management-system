import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <p className="text-5xl font-semibold text-slate-300">404</p>
      <h1 className="mt-2 text-lg font-semibold text-slate-800">Page not found</h1>
      <p className="mt-1 text-sm text-slate-500">
        The page you are looking for doesn’t exist or has moved.
      </p>
      <Link to="/dashboard" className="mt-5">
        <Button>Back to dashboard</Button>
      </Link>
    </div>
  )
}

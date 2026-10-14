import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react'
import { cn } from '@/lib/utils'

type ToastVariant = 'success' | 'error' | 'info'

interface Toast {
  id: number
  title: string
  description?: string
  variant: ToastVariant
}

interface ToastContextValue {
  toast: (input: {
    title: string
    description?: string
    variant?: ToastVariant
  }) => void
  success: (title: string, description?: string) => void
  error: (title: string, description?: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let counter = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const remove = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback<ToastContextValue['toast']>(
    ({ title, description, variant = 'info' }) => {
      const id = ++counter
      setToasts((current) => [...current, { id, title, description, variant }])
      window.setTimeout(() => remove(id), 4500)
    },
    [remove],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (title, description) => toast({ title, description, variant: 'success' }),
      error: (title, description) => toast({ title, description, variant: 'error' }),
    }),
    [toast],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
        {toasts.map((item) => (
          <ToastCard key={item.id} toast={item} onClose={() => remove(item.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastCard({
  toast,
  onClose,
}: {
  toast: Toast
  onClose: () => void
}) {
  const icons = {
    success: <CheckCircle2 className="size-5 text-emerald-600" />,
    error: <TriangleAlert className="size-5 text-rose-600" />,
    info: <Info className="size-5 text-brand-600" />,
  }
  const border = {
    success: 'border-l-emerald-500',
    error: 'border-l-rose-500',
    info: 'border-l-brand-500',
  }
  return (
    <div
      className={cn(
        'pointer-events-auto flex items-start gap-3 rounded-lg border border-slate-200 border-l-4 bg-white p-3 shadow-lg animate-fade-in',
        border[toast.variant],
      )}
      role="status"
    >
      <div className="mt-0.5">{icons[toast.variant]}</div>
      <div className="flex-1">
        <p className="text-sm font-semibold text-slate-800">{toast.title}</p>
        {toast.description ? (
          <p className="mt-0.5 text-xs text-slate-500">{toast.description}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={onClose}
        className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
        aria-label="Dismiss"
      >
        <X className="size-4" />
      </button>
    </div>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}

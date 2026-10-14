import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Variant =
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'muted'
  | 'brand'

const variants: Record<Variant, string> = {
  default: 'bg-slate-100 text-slate-700',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-rose-100 text-rose-700',
  info: 'bg-sky-100 text-sky-700',
  muted: 'bg-slate-50 text-slate-500',
  brand: 'bg-brand-100 text-brand-700',
}

export function Badge({
  children,
  variant = 'default',
  className,
}: {
  children: ReactNode
  variant?: Variant
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}

const STATUS_VARIANTS: Record<string, Variant> = {
  ACTIVE: 'success',
  INACTIVE: 'muted',
  PENDING: 'warning',
  SUBMITTED: 'info',
  UNDER_REVIEW: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
  ENROLLED: 'brand',
  DRAFT: 'muted',
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  UNPAID: 'danger',
  OVERDUE: 'danger',
  PRESENT: 'success',
  ABSENT: 'danger',
  LATE: 'warning',
  EXCUSED: 'info',
  BORROWED: 'info',
  RETURNED: 'success',
  PUBLISHED: 'success',
  CANCELLED: 'muted',
  COMPLETED: 'success',
  SUSPENDED: 'danger',
  MALE: 'info',
  FEMALE: 'brand',
}

export function statusVariant(value?: string | null): Variant {
  if (!value) return 'muted'
  return STATUS_VARIANTS[String(value).toUpperCase()] ?? 'default'
}

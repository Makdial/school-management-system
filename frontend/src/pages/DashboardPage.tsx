import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  Banknote,
  BookOpen,
  Bus,
  CalendarCheck,
  ClipboardList,
  GraduationCap,
  TrendingUp,
  Users,
} from 'lucide-react'
import { api, apiErrorMessage } from '@/lib/api'
import { formatDate, formatDateTime, formatMoney, humanize } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge, statusVariant } from '@/components/ui/Badge'
import { FullPageSpinner } from '@/components/ui/Spinner'

interface DashboardData {
  school: { id: string; name: string; code: string; currency: string }
  generated_at: string
  current_session: { id: string; name: string } | null
  students: {
    total: number
    active: number
    by_status: Record<string, number>
    by_gender: Record<string, number>
    by_grade: { grade: string; count: number }[]
  }
  academics: {
    grade_levels: number
    sections: number
    subjects: number
    class_subjects: number
  }
  attendance: {
    date: string
    counts: Record<string, number>
    total: number
    rate: number
  }
  admissions: { total: number; by_status: Record<string, number> }
  examinations: {
    total: number
    published: number
    report_cards: number
    published_report_cards: number
  }
  library: {
    books: number
    copies: number
    borrowed: number
    overdue: number
    outstanding_fines: number
  }
  transport: {
    vehicles: number
    active_vehicles: number
    routes: number
    students_assigned: number
  }
  upcoming_events: {
    id: string
    title: string
    event_type: string
    start: string
    location: string
  }[]
  upcoming_holidays: { id: string; name: string; date: string }[]
  finance: {
    currency: string
    invoiced: number
    collected: number
    outstanding: number
    invoices_total: number
    invoices_unpaid: number
    overdue_count: number
    payments_by_method: { method: string; total: number; count: number }[]
  }
  hr: {
    total: number
    active: number
    by_status: Record<string, number>
    on_leave_today: number
    pending_leave_requests: number
  }
}

export function DashboardPage() {
  const dashboard = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () =>
      (await api.get<DashboardData>('/reports/dashboard/')).data,
  })

  if (dashboard.isLoading) return <FullPageSpinner label="Loading dashboard…" />
  if (dashboard.isError)
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        {apiErrorMessage(dashboard.error)}
      </div>
    )

  const data = dashboard.data!
  const currency = data.finance.currency || data.school.currency || 'USD'
  const collectionRate =
    data.finance.invoiced > 0
      ? Math.round((data.finance.collected / data.finance.invoiced) * 100)
      : 0

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {data.school.name} ·{' '}
            {data.current_session ? data.current_session.name : 'No active session'}
          </p>
        </div>
        <p className="text-xs text-slate-400">
          Updated {formatDateTime(data.generated_at)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<GraduationCap className="size-5" />}
          label="Students"
          value={String(data.students.total)}
          hint={`${data.students.active} active`}
          tone="brand"
        />
        <StatCard
          icon={<Users className="size-5" />}
          label="Staff"
          value={String(data.hr.total)}
          hint={`${data.hr.active} active`}
          tone="emerald"
        />
        <StatCard
          icon={<ClipboardList className="size-5" />}
          label="Applications"
          value={String(data.admissions.total)}
          hint={`${data.admissions.by_status.ENROLLED ?? 0} enrolled`}
          tone="sky"
        />
        <StatCard
          icon={<CalendarCheck className="size-5" />}
          label="Attendance today"
          value={data.attendance.total ? `${data.attendance.rate}%` : '—'}
          hint={`${data.attendance.total} marked`}
          tone="amber"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Fee collection</CardTitle>
            <Badge variant="brand">{collectionRate}% collected</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <MoneyStat label="Invoiced" value={formatMoney(data.finance.invoiced, currency)} />
              <MoneyStat label="Collected" value={formatMoney(data.finance.collected, currency)} tone="text-emerald-600" />
              <MoneyStat label="Outstanding" value={formatMoney(data.finance.outstanding, currency)} tone="text-rose-600" />
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-500"
                style={{ width: `${Math.min(100, collectionRate)}%` }}
              />
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-slate-500">
              <span>{data.finance.invoices_total} invoices</span>
              <span>{data.finance.invoices_unpaid} unpaid</span>
              <span className="text-rose-500">{data.finance.overdue_count} overdue</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Attendance today</CardTitle>
            <span className="text-xs text-slate-400">{formatDate(data.attendance.date)}</span>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(data.attendance.counts).length ? (
              Object.entries(data.attendance.counts).map(([status, count]) => (
                <BarRow
                  key={status}
                  label={humanize(status)}
                  value={count}
                  max={Math.max(1, data.attendance.total)}
                  color={statusVariant(status).toString()}
                />
              ))
            ) : (
              <p className="text-sm text-slate-400">No attendance recorded yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Students by grade</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.students.by_grade.map((row) => (
              <BarRow
                key={row.grade}
                label={row.grade}
                value={row.count}
                max={Math.max(1, data.students.total)}
                color="bg-brand-500"
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Admissions pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(data.admissions.by_status).map(([status, count]) => (
              <BarRow
                key={status}
                label={humanize(status)}
                value={count}
                max={Math.max(1, data.admissions.total)}
                color="bg-sky-500"
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Operations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <OpRow icon={<BookOpen className="size-4" />} label="Library books" value={data.library.books} extra={`${data.library.borrowed} borrowed`} />
            <OpRow icon={<Bus className="size-4" />} label="Transport routes" value={data.transport.routes} extra={`${data.transport.students_assigned} students`} />
            <OpRow icon={<TrendingUp className="size-4" />} label="Report cards" value={data.examinations.report_cards} extra={`${data.examinations.published} exams published`} />
            <OpRow icon={<Banknote className="size-4" />} label="Outstanding fines" value={data.library.outstanding_fines} extra={`${data.hr.pending_leave_requests} leave requests`} money currency={currency} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Upcoming events</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-slate-50">
            {data.upcoming_events.length ? (
              data.upcoming_events.map((event) => (
                <div key={event.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{event.title}</p>
                    <p className="text-xs text-slate-400">
                      {formatDateTime(event.start)}
                      {event.location ? ` · ${event.location}` : ''}
                    </p>
                  </div>
                  <Badge variant="info">{humanize(event.event_type)}</Badge>
                </div>
              ))
            ) : (
              <p className="py-2 text-sm text-slate-400">No upcoming events.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Upcoming holidays</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-slate-50">
            {data.upcoming_holidays.length ? (
              data.upcoming_holidays.map((holiday) => (
                <div key={holiday.id} className="flex items-center justify-between py-2.5">
                  <p className="text-sm font-medium text-slate-800">{holiday.name}</p>
                  <span className="text-xs text-slate-400">{formatDate(holiday.date)}</span>
                </div>
              ))
            ) : (
              <p className="py-2 text-sm text-slate-400">No upcoming holidays.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: ReactNode
  label: string
  value: string
  hint: string
  tone: 'brand' | 'emerald' | 'sky' | 'amber'
}) {
  const tones = {
    brand: 'bg-brand-50 text-brand-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    sky: 'bg-sky-50 text-sky-600',
    amber: 'bg-amber-50 text-amber-600',
  }
  return (
    <Card>
      <CardContent className="flex items-center gap-4">
        <div className={`flex size-11 items-center justify-center rounded-lg ${tones[tone]}`}>
          {icon}
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            {label}
          </p>
          <p className="text-2xl font-semibold text-slate-900">{value}</p>
          <p className="text-xs text-slate-400">{hint}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function MoneyStat({
  label,
  value,
  tone = 'text-slate-900',
}: {
  label: string
  value: string
  tone?: string
}) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  )
}

function BarRow({
  label,
  value,
  max,
  color,
}: {
  label: string
  value: number
  max: number
  color: string
}) {
  const width = max > 0 ? Math.round((value / max) * 100) : 0
  const barColor = color.startsWith('bg-') ? color : 'bg-brand-500'
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
        <span>{label}</span>
        <span className="font-medium text-slate-700">{value}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}

function OpRow({
  icon,
  label,
  value,
  extra,
  money,
  currency,
}: {
  icon: ReactNode
  label: string
  value: number
  extra: string
  money?: boolean
  currency?: string
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-slate-500">
        <span className="text-slate-400">{icon}</span>
        {label}
      </span>
      <span className="text-right">
        <span className="block font-medium text-slate-800">
          {money ? formatMoney(value, currency) : value}
        </span>
        <span className="block text-xs text-slate-400">{extra}</span>
      </span>
    </div>
  )
}

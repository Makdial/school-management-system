import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, apiErrorMessage } from '@/lib/api'
import { cn, formatNumber, humanize } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Input'
import { FullPageSpinner } from '@/components/ui/Spinner'
import { Badge } from '@/components/ui/Badge'

const REPORTS = [
  { key: 'attendance', label: 'Attendance', endpoint: '/reports/attendance/' },
  { key: 'enrollment', label: 'Enrollment', endpoint: '/reports/enrollment/' },
  { key: 'academic', label: 'Academic', endpoint: '/reports/academic/' },
  { key: 'finance', label: 'Finance', endpoint: '/reports/finance/' },
  { key: 'hr', label: 'Human Resources', endpoint: '/reports/hr/' },
  { key: 'library', label: 'Library', endpoint: '/reports/library/' },
  { key: 'transport', label: 'Transport', endpoint: '/reports/transport/' },
]

const DATASETS = [
  'students',
  'attendance',
  'staff',
  'invoices',
  'payments',
  'admissions',
  'library',
]

export function ReportsPage() {
  const [active, setActive] = useState(REPORTS[0].key)
  const [dataset, setDataset] = useState(DATASETS[0])
  const [exporting, setExporting] = useState(false)

  const report = REPORTS.find((r) => r.key === active)!

  const query = useQuery({
    queryKey: ['report', active],
    queryFn: async () => (await api.get(report.endpoint)).data as Record<string, unknown>,
  })

  const handleExport = async () => {
    setExporting(true)
    try {
      const response = await api.get('/reports/export/', {
        params: { dataset },
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data as Blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${dataset}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Reports &amp; analytics</h1>
          <p className="text-sm text-slate-500">
            Role-aware summaries scoped to your school.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={dataset}
            onChange={(event) => setDataset(event.target.value)}
            className="w-auto"
          >
            {DATASETS.map((name) => (
              <option key={name} value={name}>
                {humanize(name)}
              </option>
            ))}
          </Select>
          <Button variant="outline" loading={exporting} onClick={handleExport}>
            <Download className="size-4" />
            Export CSV
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-white p-1">
        {REPORTS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setActive(item.key)}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition',
              active === item.key
                ? 'bg-brand-600 text-white'
                : 'text-slate-600 hover:bg-slate-100',
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {query.isLoading ? (
        <FullPageSpinner label="Crunching numbers…" />
      ) : query.isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          {apiErrorMessage(query.error)}
        </div>
      ) : (
        <ReportBody data={query.data ?? {}} />
      )}
    </div>
  )
}

function ReportBody({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {Object.entries(data).map(([key, value]) => (
        <Node key={key} name={key} value={value} />
      ))}
    </div>
  )
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function Node({ name, value }: { name: string; value: unknown }) {
  if (value === null || value === undefined) return null

  if (typeof value === 'number') {
    return (
      <Card>
        <CardContent>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            {humanize(name)}
          </p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">
            {formatNumber(value)}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (typeof value === 'boolean') {
    return (
      <Card>
        <CardContent className="flex items-center justify-between">
          <span className="text-sm text-slate-500">{humanize(name)}</span>
          <Badge variant={value ? 'success' : 'muted'}>{value ? 'Yes' : 'No'}</Badge>
        </CardContent>
      </Card>
    )
  }

  if (typeof value === 'string') {
    return (
      <Card>
        <CardContent className="flex items-center justify-between">
          <span className="text-sm text-slate-500">{humanize(name)}</span>
          <span className="text-sm font-medium text-slate-800">{value}</span>
        </CardContent>
      </Card>
    )
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <Card>
          <CardHeader>
            <CardTitle>{humanize(name)}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-400">No data.</CardContent>
        </Card>
      )
    }
    if (isPlainObject(value[0])) {
      return <TableBlock title={humanize(name)} rows={value as Record<string, unknown>[]} />
    }
    return (
      <Card>
        <CardHeader>
          <CardTitle>{humanize(name)}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          {value.map((v, i) => (
            <div key={i}>{String(v)}</div>
          ))}
        </CardContent>
      </Card>
    )
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value)
    const allNumbers = entries.length > 0 && entries.every(([, v]) => typeof v === 'number')
    if (allNumbers) {
      const max = Math.max(1, ...entries.map(([, v]) => Number(v)))
      return (
        <Card>
          <CardHeader>
            <CardTitle>{humanize(name)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {entries.map(([key, num]) => (
              <div key={key}>
                <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                  <span>{humanize(key)}</span>
                  <span className="font-medium text-slate-700">{formatNumber(Number(num))}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${Math.round((Number(num) / max) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )
    }
    return (
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>{humanize(name)}</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {entries.map(([key, val]) => (
            <div key={key} className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs text-slate-400">{humanize(key)}</p>
              <p className="mt-1 text-sm font-medium text-slate-800">
                {typeof val === 'object'
                  ? isPlainObject(val)
                    ? Object.entries(val)
                        .map(([k, v]) => `${humanize(k)}: ${v}`)
                        .join(' · ')
                    : JSON.stringify(val)
                  : String(val)}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  return null
}

function TableBlock({
  title,
  rows,
}: {
  title: string
  rows: Record<string, unknown>[]
}) {
  const columns = Object.keys(rows[0]).slice(0, 8)
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="text-xs text-slate-400">{rows.length} rows</span>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
              {columns.map((column) => (
                <th key={column} className="px-4 py-2.5 font-medium">
                  {humanize(column)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {rows.map((row, index) => (
              <tr key={index} className="hover:bg-slate-50/70">
                {columns.map((column) => (
                  <td key={column} className="whitespace-nowrap px-4 py-2.5 text-slate-700">
                    {typeof row[column] === 'number'
                      ? formatNumber(row[column] as number)
                      : String(row[column] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

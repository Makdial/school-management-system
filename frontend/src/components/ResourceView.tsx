import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RefreshCw, Search, Trash2 } from 'lucide-react'
import { api, apiErrorMessage } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { cn, formatDate, formatDateTime, formatMoney, formatNumber, humanize } from '@/lib/utils'
import type { ApiRecord, Paginated } from '@/lib/types'
import {
  REF_ENDPOINTS,
  filterableChoiceFields,
  isTextareaField,
  useRefOptions,
  useResourceMeta,
  writableFields,
  type MetaField,
} from '@/lib/resourceMeta'
import type { ColumnConfig, ResourceConfig } from '@/config/resources'
import { Badge, statusVariant } from './ui/Badge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'
import { Field, Input, Select, Textarea } from './ui/Input'
import { Modal } from './ui/Modal'
import { Pagination } from './ui/Pagination'
import { FullPageSpinner } from './ui/Spinner'

const PAGE_SIZE = 20
const CURRENCY = 'USD'
const DEFAULT_HIDDEN = new Set([
  'id',
  'school',
  'user',
  'address',
  'medical_notes',
  'photo',
  'profile_picture',
  'password',
  'data',
  'guardians',
])

function useDebounced<T>(value: T, delay = 350) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}

function autoColumns(fields: Record<string, MetaField>): ColumnConfig[] {
  const columns: ColumnConfig[] = []
  for (const [name, field] of Object.entries(fields)) {
    if (DEFAULT_HIDDEN.has(name)) continue
    if (['nested object', 'file upload', 'image upload'].includes(field.type)) continue
    const type: ColumnConfig['type'] =
      field.type === 'decimal'
        ? 'number'
        : field.type === 'integer'
          ? 'number'
          : field.type === 'date'
            ? 'date'
            : field.type === 'datetime'
              ? 'datetime'
              : field.type === 'boolean'
                ? 'bool'
                : field.type === 'choice'
                  ? 'badge'
                  : 'text'
    columns.push({ key: name, label: field.label || humanize(name), type })
    if (columns.length >= 6) break
  }
  return columns
}

function Cell({ column, record }: { column: ColumnConfig; record: ApiRecord }) {
  const value = record[column.key]
  if (value === null || value === undefined || value === '') {
    return <span className="text-slate-300">—</span>
  }
  switch (column.type) {
    case 'money':
      return <span>{formatMoney(value as number, CURRENCY)}</span>
    case 'number':
      return <span>{formatNumber(value as number)}</span>
    case 'date':
      return <span>{formatDate(String(value))}</span>
    case 'datetime':
      return <span>{formatDateTime(String(value))}</span>
    case 'bool':
      return value ? (
        <Badge variant="success">Yes</Badge>
      ) : (
        <Badge variant="muted">No</Badge>
      )
    case 'badge':
      return (
        <Badge variant={statusVariant(String(value))}>{humanize(String(value))}</Badge>
      )
    default: {
      if (typeof value === 'object') {
        return <span className="text-slate-500">{JSON.stringify(value)}</span>
      }
      return <span>{String(value)}</span>
    }
  }
}

export function ResourceView({ config }: { config: ResourceConfig }) {
  const toast = useToast()
  const queryClient = useQueryClient()
  const meta = useResourceMeta(config.endpoint)

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [ordering, setOrdering] = useState('')
  const [editing, setEditing] = useState<ApiRecord | null>(null)
  const [creating, setCreating] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<ApiRecord | null>(null)

  const debouncedSearch = useDebounced(search)

  const columns = useMemo<ColumnConfig[]>(() => {
    if (config.columns?.length) return config.columns
    if (meta.data) return autoColumns(meta.data.fields)
    return []
  }, [config.columns, meta.data])

  const filterFields = useMemo(
    () => (meta.data ? filterableChoiceFields(meta.data.fields) : []),
    [meta.data],
  )

  const queryKey = ['resource', config.key, page, debouncedSearch, filters, ordering]

  const list = useQuery({
    queryKey,
    queryFn: async () => {
      const { data } = await api.get<Paginated<ApiRecord> | ApiRecord[]>(
        config.endpoint,
        {
          params: {
            page,
            search: debouncedSearch || undefined,
            ordering: ordering || undefined,
            ...filters,
          },
        },
      )
      return Array.isArray(data)
        ? { count: data.length, next: null, previous: null, results: data }
        : data
    },
    placeholderData: (previous) => previous,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['resource', config.key] })

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post(config.endpoint, payload),
    onSuccess: () => {
      toast.success(`${config.title}: record created`)
      setCreating(false)
      void invalidate()
    },
    onError: (error) => toast.error('Could not create record', apiErrorMessage(error)),
  })

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string | number
      payload: Record<string, unknown>
    }) => api.patch(`${config.endpoint}${id}/`, payload),
    onSuccess: () => {
      toast.success(`${config.title}: record updated`)
      setEditing(null)
      void invalidate()
    },
    onError: (error) => toast.error('Could not update record', apiErrorMessage(error)),
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string | number) =>
      api.delete(`${config.endpoint}${id}/`),
    onSuccess: () => {
      toast.success(`${config.title}: record deleted`)
      setConfirmDelete(null)
      void invalidate()
    },
    onError: (error) => toast.error('Could not delete record', apiErrorMessage(error)),
  })

  const rows = list.data?.results ?? []
  const count = list.data?.count ?? 0
  const canWrite = !config.readOnly

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{config.title}</h1>
          <p className="text-sm text-slate-500">
            {config.description ?? `${count} record${count === 1 ? '' : 's'}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => list.refetch()}
            disabled={list.isFetching}
          >
            <RefreshCw className={cn('size-4', list.isFetching && 'animate-spin')} />
            Refresh
          </Button>
          {canWrite ? (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              New
            </Button>
          ) : null}
        </div>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-4 py-3">
          <div className="relative min-w-56 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
              placeholder={`Search ${config.title.toLowerCase()}…`}
              className="pl-9"
            />
          </div>
          {filterFields.map(([name, field]) => (
            <Select
              key={name}
              value={filters[name] ?? ''}
              onChange={(event) => {
                setFilters((prev) => ({ ...prev, [name]: event.target.value }))
                setPage(1)
              }}
              className="w-auto min-w-36"
            >
              <option value="">All {field.label.toLowerCase()}</option>
              {field.choices?.map((choice) => (
                <option key={choice.value} value={choice.value}>
                  {choice.display}
                </option>
              ))}
            </Select>
          ))}
        </div>

        {list.isLoading ? (
          <FullPageSpinner label={`Loading ${config.title.toLowerCase()}…`} />
        ) : list.isError ? (
          <div className="p-8 text-center text-sm text-rose-600">
            {apiErrorMessage(list.error)}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-500">
            No records found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
                  {columns.map((column) => (
                    <th
                      key={column.key}
                      className={cn(
                        'px-4 py-2.5 font-medium',
                        column.align === 'right' && 'text-right',
                      )}
                    >
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-slate-600"
                        onClick={() => {
                          const next =
                            ordering === column.key ? `-${column.key}` : column.key
                          setOrdering(next)
                          setPage(1)
                        }}
                      >
                        {column.label}
                      </button>
                    </th>
                  ))}
                  {canWrite ? (
                    <th className="px-4 py-2.5 text-right font-medium">Actions</th>
                  ) : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {rows.map((record) => (
                  <tr key={String(record.id)} className="hover:bg-slate-50/70">
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className={cn(
                          'whitespace-nowrap px-4 py-2.5 text-slate-700',
                          column.align === 'right' && 'text-right',
                        )}
                      >
                        <Cell column={column} record={record} />
                      </td>
                    ))}
                    {canWrite ? (
                      <td className="whitespace-nowrap px-4 py-2.5 text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Edit"
                            onClick={() => setEditing(record)}
                          >
                            <Pencil className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Delete"
                            onClick={() => setConfirmDelete(record)}
                          >
                            <Trash2 className="size-4 text-rose-500" />
                          </Button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!list.isLoading && !list.isError && rows.length > 0 ? (
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={count}
            onPageChange={setPage}
          />
        ) : null}
      </Card>

      {meta.data ? (
        <>
          <ResourceFormModal
            open={creating}
            title={`New ${config.title.replace(/s$/, '')}`}
            fields={meta.data.fields}
            hidden={config.hidden}
            submitting={createMutation.isPending}
            onClose={() => setCreating(false)}
            onSubmit={(payload) => createMutation.mutate(payload)}
          />
          <ResourceFormModal
            open={Boolean(editing)}
            title={`Edit ${config.title.replace(/s$/, '')}`}
            fields={meta.data.fields}
            hidden={config.hidden}
            initial={editing ?? undefined}
            submitting={updateMutation.isPending}
            onClose={() => setEditing(null)}
            onSubmit={(payload) =>
              editing && updateMutation.mutate({ id: editing.id, payload })
            }
          />
        </>
      ) : null}

      <Modal
        open={Boolean(confirmDelete)}
        onClose={() => setConfirmDelete(null)}
        title="Delete record"
        description="This action cannot be undone."
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending}
              onClick={() =>
                confirmDelete && deleteMutation.mutate(confirmDelete.id)
              }
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          Are you sure you want to delete this record?
        </p>
      </Modal>
    </div>
  )
}

function ResourceFormModal({
  open,
  title,
  fields,
  hidden,
  initial,
  submitting,
  onClose,
  onSubmit,
}: {
  open: boolean
  title: string
  fields: Record<string, MetaField>
  hidden?: string[]
  initial?: ApiRecord
  submitting: boolean
  onClose: () => void
  onSubmit: (payload: Record<string, unknown>) => void
}) {
  const [values, setValues] = useState<Record<string, unknown>>({})

  const entries = useMemo(() => {
    const hiddenSet = new Set([...DEFAULT_HIDDEN, ...(hidden ?? [])])
    return writableFields(fields).filter(
      ([name, field]) =>
        !hiddenSet.has(name) &&
        !['nested object', 'file upload', 'image upload'].includes(field.type),
    )
  }, [fields, hidden, initial])

  useEffect(() => {
    if (!open) return
    const next: Record<string, unknown> = {}
    for (const [name] of entries) {
      const raw = initial?.[name]
      next[name] = raw === null || raw === undefined ? '' : raw
    }
    setValues(next)
  }, [open, initial, entries])

  const setValue = (name: string, value: unknown) =>
    setValues((prev) => ({ ...prev, [name]: value }))

  const handleSubmit = () => {
    const payload: Record<string, unknown> = {}
    for (const [name, field] of entries) {
      const value = values[name]
      if (value === '' || value === null || value === undefined) continue
      if (field.type === 'boolean') {
        payload[name] = value === true || value === 'true'
      } else if (field.type === 'integer' || field.type === 'decimal') {
        const n = Number(value)
        if (!Number.isNaN(n)) payload[name] = n
      } else if (field.type === 'datetime') {
        const d = new Date(String(value))
        payload[name] = Number.isNaN(d.getTime()) ? value : d.toISOString()
      } else {
        payload[name] = value
      }
    }
    onSubmit(payload)
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={submitting} onClick={handleSubmit}>
            Save
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {entries.map(([name, field]) => (
          <FormField
            key={name}
            name={name}
            field={field}
            value={values[name]}
            onChange={(value) => setValue(name, value)}
            className={
              isTextareaField(name) ? 'sm:col-span-2' : undefined
            }
          />
        ))}
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">No editable fields available.</p>
      ) : null}
    </Modal>
  )
}

function FormField({
  name,
  field,
  value,
  onChange,
  className,
}: {
  name: string
  field: MetaField
  value: unknown
  onChange: (value: unknown) => void
  className?: string
}) {
  const refEndpoint = REF_ENDPOINTS[name]
  const refOptions = useRefOptions(field.type === 'field' ? refEndpoint : undefined)
  const text = value === null || value === undefined ? '' : String(value)

  const control = () => {
    if (field.type === 'choice') {
      return (
        <Select value={text} onChange={(event) => onChange(event.target.value)}>
          <option value="">—</option>
          {field.choices?.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.display}
            </option>
          ))}
        </Select>
      )
    }
    if (field.type === 'boolean') {
      return (
        <Select
          value={text === '' ? '' : String(value)}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">—</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </Select>
      )
    }
    if (field.type === 'field') {
      if (refEndpoint && refOptions.data?.length) {
        return (
          <Select value={text} onChange={(event) => onChange(event.target.value)}>
            <option value="">—</option>
            {refOptions.data.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        )
      }
      return (
        <Input
          value={text}
          placeholder="Identifier (UUID)"
          onChange={(event) => onChange(event.target.value)}
        />
      )
    }
    if (isTextareaField(name)) {
      return (
        <Textarea value={text} onChange={(event) => onChange(event.target.value)} />
      )
    }
    if (field.type === 'integer' || field.type === 'decimal') {
      return (
        <Input
          type="number"
          step={field.type === 'decimal' ? '0.01' : '1'}
          value={text}
          onChange={(event) => onChange(event.target.value)}
        />
      )
    }
    if (field.type === 'date') {
      return (
        <Input
          type="date"
          value={text.slice(0, 10)}
          onChange={(event) => onChange(event.target.value)}
        />
      )
    }
    if (field.type === 'datetime') {
      return (
        <Input
          type="datetime-local"
          value={text.slice(0, 16)}
          onChange={(event) => onChange(event.target.value)}
        />
      )
    }
    if (field.type === 'time') {
      return (
        <Input
          type="time"
          value={text.slice(0, 5)}
          onChange={(event) => onChange(event.target.value)}
        />
      )
    }
    if (field.type === 'email') {
      return (
        <Input
          type="email"
          value={text}
          onChange={(event) => onChange(event.target.value)}
        />
      )
    }
    return (
      <Input value={text} onChange={(event) => onChange(event.target.value)} />
    )
  }

  return (
    <Field label={field.label || humanize(name)} required={field.required} className={className}>
      {control()}
      {field.type === 'field' && field.help_text ? (
        <p className="mt-1 text-xs text-slate-400">{field.help_text}</p>
      ) : null}
    </Field>
  )
}

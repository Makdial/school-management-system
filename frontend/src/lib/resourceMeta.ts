import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { ApiRecord } from './types'

export interface MetaChoice {
  value: string
  display: string
}

export interface MetaField {
  type: string
  required: boolean
  read_only: boolean
  label: string
  help_text?: string
  max_length?: number
  choices?: MetaChoice[]
}

export interface ResourceMeta {
  name: string
  description: string
  fields: Record<string, MetaField>
}

/** Map DRF relation field names to the endpoint that lists their options. */
export const REF_ENDPOINTS: Record<string, string> = {
  school: '/schools/',
  user: '/users/',
  student: '/students/',
  guardian: '/guardians/',
  staff: '/staff/',
  teacher: '/staff/',
  class_teacher: '/staff/',
  recipient: '/users/',
  borrower: '/users/',
  current_grade_level: '/grade-levels/',
  grade_level: '/grade-levels/',
  next_level: '/grade-levels/',
  section: '/sections/',
  session: '/sessions/',
  term: '/terms/',
  subject: '/subjects/',
  class_subject: '/class-subjects/',
  department: '/departments/',
  room: '/rooms/',
  period: '/timetable-periods/',
  exam: '/exams/',
  exam_subject: '/exam-subjects/',
  scale: '/grading-scales/',
  fee_structure: '/fee-structures/',
  invoice: '/invoices/',
  payment: '/payments/',
  leave_type: '/leave-types/',
  application: '/admissions/',
  assignment: '/assignments/',
  book: '/books/',
  copy: '/book-copies/',
  category: '/book-categories/',
  route: '/transport-routes/',
  stop: '/transport-stops/',
  vehicle: '/vehicles/',
}

const LABEL_KEYS = [
  'name',
  'full_name',
  'title',
  'label',
  'display_name',
  'code',
  'admission_number',
  'username',
  'number',
  'id',
]

export function recordLabel(record: ApiRecord): string {
  for (const key of LABEL_KEYS) {
    const value = record[key]
    if (value !== undefined && value !== null && value !== '') {
      return String(value)
    }
  }
  return String(record.id)
}

async function fetchMeta(endpoint: string): Promise<ResourceMeta> {
  const { data } = await api.options(endpoint)
  const actions = (data?.actions ?? {}) as Record<string, Record<string, MetaField>>
  const fields = actions.POST ?? actions.PUT ?? actions.GET ?? {}
  return {
    name: data?.name ?? '',
    description: data?.description ?? '',
    fields,
  }
}

export function useResourceMeta(endpoint: string) {
  return useQuery({
    queryKey: ['meta', endpoint],
    queryFn: () => fetchMeta(endpoint),
    staleTime: 10 * 60 * 1000,
  })
}

export function useRefOptions(endpoint?: string) {
  return useQuery({
    queryKey: ['ref-options', endpoint],
    queryFn: async () => {
      const { data } = await api.get(endpoint!, { params: { page: 1 } })
      const rows: ApiRecord[] = Array.isArray(data) ? data : (data?.results ?? [])
      return rows.map((row) => ({ value: String(row.id), label: recordLabel(row) }))
    },
    enabled: Boolean(endpoint),
    staleTime: 5 * 60 * 1000,
  })
}

const TEXTAREA_HINTS = [
  'address',
  'notes',
  'description',
  'medical',
  'remarks',
  'body',
  'content',
  'message',
  'comment',
  'reason',
  'summary',
]

export function isTextareaField(name: string) {
  return TEXTAREA_HINTS.some((hint) => name.includes(hint))
}

/** Fields that can be written (used to build create/update forms). */
export function writableFields(fields: Record<string, MetaField>) {
  return Object.entries(fields).filter(([, f]) => !f.read_only)
}

/** Choice fields usable as list filters. */
export function filterableChoiceFields(fields: Record<string, MetaField>) {
  return Object.entries(fields).filter(
    ([, f]) => f.type === 'choice' && Array.isArray(f.choices) && f.choices.length > 0,
  )
}

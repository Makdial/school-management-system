export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type UserType =
  | 'SUPERADMIN'
  | 'SCHOOL_ADMIN'
  | 'PRINCIPAL'
  | 'TEACHER'
  | 'STUDENT'
  | 'PARENT'
  | 'ACCOUNTANT'
  | 'LIBRARIAN'
  | 'TRANSPORT_MANAGER'
  | 'HR_MANAGER'

export interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  user_type: UserType
  school: string | null
  school_name: string | null
  phone_number: string
  date_of_birth: string | null
  address: string
  profile_picture: string | null
  is_active: boolean
  last_login: string | null
  created_at: string
}

export type RecordValue = string | number | boolean | null | undefined

export interface ApiRecord {
  id: string | number
  [key: string]: unknown
}

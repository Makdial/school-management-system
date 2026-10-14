export type ColumnType =
  | 'text'
  | 'money'
  | 'number'
  | 'date'
  | 'datetime'
  | 'badge'
  | 'bool'

export interface ColumnConfig {
  key: string
  label: string
  type?: ColumnType
  align?: 'left' | 'right'
  hideOnMobile?: boolean
}

export type ResourceGroup =
  | 'Overview'
  | 'Students'
  | 'Academics'
  | 'Admissions'
  | 'Attendance'
  | 'Examinations'
  | 'Finance'
  | 'Library'
  | 'Human Resources'
  | 'Transport'
  | 'Communication'
  | 'Administration'

export interface ResourceConfig {
  key: string
  title: string
  endpoint: string
  group: ResourceGroup
  description?: string
  searchable?: boolean
  readOnly?: boolean
  columns?: ColumnConfig[]
  /** Field names to never show in auto-generated tables/forms. */
  hidden?: string[]
}

export const RESOURCES: ResourceConfig[] = [
  // --- Students -------------------------------------------------------------
  {
    key: 'students',
    title: 'Students',
    endpoint: '/students/',
    group: 'Students',
    description: 'All enrolled learners across the school.',
    searchable: true,
    columns: [
      { key: 'admission_number', label: 'Admission #' },
      { key: 'full_name', label: 'Name' },
      { key: 'gender', label: 'Gender', type: 'badge' },
      { key: 'current_section_name', label: 'Section' },
      { key: 'status', label: 'Status', type: 'badge' },
    ],
  },
  { key: 'guardians', title: 'Guardians', endpoint: '/guardians/', group: 'Students', searchable: true },
  { key: 'student-guardians', title: 'Student Guardians', endpoint: '/student-guardians/', group: 'Students' },
  { key: 'student-documents', title: 'Student Documents', endpoint: '/student-documents/', group: 'Students' },
  {
    key: 'student-status-history',
    title: 'Status History',
    endpoint: '/student-status-history/',
    group: 'Students',
    readOnly: true,
  },

  // --- Academics ------------------------------------------------------------
  { key: 'subjects', title: 'Subjects', endpoint: '/subjects/', group: 'Academics', searchable: true },
  { key: 'class-subjects', title: 'Class Subjects', endpoint: '/class-subjects/', group: 'Academics' },
  { key: 'enrollments', title: 'Enrollments', endpoint: '/enrollments/', group: 'Academics' },
  { key: 'grade-levels', title: 'Grade Levels', endpoint: '/grade-levels/', group: 'Academics' },
  { key: 'sections', title: 'Sections', endpoint: '/sections/', group: 'Academics' },
  { key: 'classrooms', title: 'Classrooms', endpoint: '/classrooms/', group: 'Academics' },
  { key: 'sessions', title: 'Academic Sessions', endpoint: '/sessions/', group: 'Academics' },
  { key: 'terms', title: 'Terms', endpoint: '/terms/', group: 'Academics' },
  { key: 'grading-scales', title: 'Grading Scales', endpoint: '/grading-scales/', group: 'Academics' },
  { key: 'grading-bands', title: 'Grading Bands', endpoint: '/grading-bands/', group: 'Academics' },
  { key: 'rooms', title: 'Rooms', endpoint: '/rooms/', group: 'Academics' },
  { key: 'timetable-periods', title: 'Timetable Periods', endpoint: '/timetable-periods/', group: 'Academics' },
  { key: 'timetable', title: 'Timetable', endpoint: '/timetable/', group: 'Academics' },

  // --- Admissions -----------------------------------------------------------
  { key: 'admissions', title: 'Applications', endpoint: '/admissions/', group: 'Admissions', searchable: true },
  { key: 'admission-documents', title: 'Application Documents', endpoint: '/admission-documents/', group: 'Admissions' },

  // --- Attendance -----------------------------------------------------------
  { key: 'attendance', title: 'Student Attendance', endpoint: '/attendance/', group: 'Attendance' },
  { key: 'staff-attendance', title: 'Staff Attendance', endpoint: '/staff-attendance/', group: 'Attendance' },
  {
    key: 'attendance-corrections',
    title: 'Attendance Corrections',
    endpoint: '/attendance-corrections/',
    group: 'Attendance',
    readOnly: true,
  },

  // --- Examinations ---------------------------------------------------------
  { key: 'exams', title: 'Exams', endpoint: '/exams/', group: 'Examinations' },
  { key: 'exam-subjects', title: 'Exam Subjects', endpoint: '/exam-subjects/', group: 'Examinations' },
  { key: 'marks', title: 'Marks', endpoint: '/marks/', group: 'Examinations' },
  {
    key: 'report-cards',
    title: 'Report Cards',
    endpoint: '/report-cards/',
    group: 'Examinations',
    readOnly: true,
  },

  // --- Finance --------------------------------------------------------------
  { key: 'invoices', title: 'Invoices', endpoint: '/invoices/', group: 'Finance', searchable: true },
  { key: 'invoice-items', title: 'Invoice Items', endpoint: '/invoice-items/', group: 'Finance' },
  { key: 'payments', title: 'Payments', endpoint: '/payments/', group: 'Finance' },
  { key: 'fee-categories', title: 'Fee Categories', endpoint: '/fee-categories/', group: 'Finance' },
  { key: 'fee-structures', title: 'Fee Structures', endpoint: '/fee-structures/', group: 'Finance' },
  { key: 'fee-structure-items', title: 'Fee Structure Items', endpoint: '/fee-structure-items/', group: 'Finance' },
  { key: 'discounts', title: 'Discounts', endpoint: '/discounts/', group: 'Finance' },
  { key: 'refunds', title: 'Refunds', endpoint: '/refunds/', group: 'Finance' },

  // --- Library --------------------------------------------------------------
  { key: 'books', title: 'Books', endpoint: '/books/', group: 'Library', searchable: true },
  { key: 'book-categories', title: 'Book Categories', endpoint: '/book-categories/', group: 'Library' },
  { key: 'book-copies', title: 'Book Copies', endpoint: '/book-copies/', group: 'Library' },
  { key: 'borrowings', title: 'Borrowings', endpoint: '/borrowings/', group: 'Library' },

  // --- HR -------------------------------------------------------------------
  { key: 'staff', title: 'Staff', endpoint: '/staff/', group: 'Human Resources', searchable: true },
  { key: 'departments', title: 'Departments', endpoint: '/departments/', group: 'Human Resources' },
  { key: 'contracts', title: 'Contracts', endpoint: '/contracts/', group: 'Human Resources' },
  { key: 'leave-types', title: 'Leave Types', endpoint: '/leave-types/', group: 'Human Resources' },
  { key: 'leave-requests', title: 'Leave Requests', endpoint: '/leave-requests/', group: 'Human Resources' },

  // --- Transport ------------------------------------------------------------
  { key: 'vehicles', title: 'Vehicles', endpoint: '/vehicles/', group: 'Transport' },
  { key: 'transport-routes', title: 'Routes', endpoint: '/transport-routes/', group: 'Transport' },
  { key: 'transport-stops', title: 'Stops', endpoint: '/transport-stops/', group: 'Transport' },
  { key: 'transport-assignments', title: 'Assignments', endpoint: '/transport-assignments/', group: 'Transport' },
  { key: 'vehicle-maintenance', title: 'Maintenance', endpoint: '/vehicle-maintenance/', group: 'Transport' },

  // --- Communication --------------------------------------------------------
  { key: 'announcements', title: 'Announcements', endpoint: '/announcements/', group: 'Communication' },
  { key: 'events', title: 'School Events', endpoint: '/events/', group: 'Communication' },
  { key: 'holidays', title: 'Holidays', endpoint: '/holidays/', group: 'Communication' },
  { key: 'messages', title: 'Messages', endpoint: '/messages/', group: 'Communication' },
  { key: 'notifications', title: 'Notifications', endpoint: '/notifications/', group: 'Communication' },

  // --- Administration -------------------------------------------------------
  { key: 'users', title: 'Users', endpoint: '/users/', group: 'Administration', searchable: true },
  { key: 'schools', title: 'Schools', endpoint: '/schools/', group: 'Administration', searchable: true },
  { key: 'school-settings', title: 'School Settings', endpoint: '/school-settings/', group: 'Administration' },
  {
    key: 'login-audits',
    title: 'Login Audits',
    endpoint: '/login-audits/',
    group: 'Administration',
    readOnly: true,
  },
  {
    key: 'activity-logs',
    title: 'Activity Logs',
    endpoint: '/activity-logs/',
    group: 'Administration',
    readOnly: true,
  },
  {
    key: 'audit-logs',
    title: 'Audit Logs',
    endpoint: '/audit-logs/',
    group: 'Administration',
    readOnly: true,
  },
]

export const RESOURCE_GROUPS: ResourceGroup[] = [
  'Students',
  'Academics',
  'Admissions',
  'Attendance',
  'Examinations',
  'Finance',
  'Library',
  'Human Resources',
  'Transport',
  'Communication',
  'Administration',
]

export function resourceByKey(key: string) {
  return RESOURCES.find((r) => r.key === key)
}

import {
  BarChart3,
  BookOpen,
  Bus,
  CalendarCheck,
  ClipboardList,
  FileSpreadsheet,
  GraduationCap,
  LayoutDashboard,
  LibraryBig,
  Megaphone,
  Shield,
  Users,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import { RESOURCES, type ResourceGroup } from './resources'
import type { UserType } from '@/lib/types'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  roles?: UserType[]
}

export interface NavSection {
  label: string
  icon: LucideIcon
  items: NavItem[]
  roles?: UserType[]
}

export const GROUP_ICONS: Record<ResourceGroup, LucideIcon> = {
  Overview: LayoutDashboard,
  Students: GraduationCap,
  Academics: BookOpen,
  Admissions: ClipboardList,
  Attendance: CalendarCheck,
  Examinations: FileSpreadsheet,
  Finance: Wallet,
  Library: LibraryBig,
  'Human Resources': Users,
  Transport: Bus,
  Communication: Megaphone,
  Administration: Shield,
}

const GROUP_ROLES: Partial<Record<ResourceGroup, UserType[]>> = {
  Administration: ['SUPERADMIN', 'SCHOOL_ADMIN'],
  Finance: ['SUPERADMIN', 'SCHOOL_ADMIN', 'ACCOUNTANT', 'PRINCIPAL'],
  'Human Resources': ['SUPERADMIN', 'SCHOOL_ADMIN', 'HR_MANAGER', 'PRINCIPAL'],
  Library: ['SUPERADMIN', 'SCHOOL_ADMIN', 'LIBRARIAN', 'PRINCIPAL'],
  Transport: ['SUPERADMIN', 'SCHOOL_ADMIN', 'TRANSPORT_MANAGER', 'PRINCIPAL'],
  Examinations: [
    'SUPERADMIN',
    'SCHOOL_ADMIN',
    'PRINCIPAL',
    'TEACHER',
    'STUDENT',
    'PARENT',
  ],
}

export const PRIMARY_NAV: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Reports', to: '/reports', icon: BarChart3 },
]

export const RESOURCE_NAV: NavSection[] = (() => {
  const groups = new Map<ResourceGroup, NavItem[]>()
  for (const resource of RESOURCES) {
    const items = groups.get(resource.group) ?? []
    items.push({
      label: resource.title,
      to: `/admin/${resource.key}`,
      icon: GROUP_ICONS[resource.group],
    })
    groups.set(resource.group, items)
  }
  return [...groups.entries()].map(([label, items]) => ({
    label,
    icon: GROUP_ICONS[label],
    items,
    roles: GROUP_ROLES[label],
  }))
})()

export function canSee(roles: UserType[] | undefined, userType?: UserType) {
  if (!roles) return true
  if (!userType) return false
  return roles.includes(userType)
}

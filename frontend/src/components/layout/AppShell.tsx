import { useEffect, useState, type ComponentType } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bell,
  Building2,
  ChevronDown,
  LogOut,
  Menu,
  School,
  UserRound,
  X,
} from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { cn, humanize, initials } from '@/lib/utils'
import { canSee, PRIMARY_NAV, RESOURCE_NAV } from '@/config/nav'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'

export function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    Students: true,
  })
  const [menuOpen, setMenuOpen] = useState(false)

  const unread = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: async () =>
      (await api.get<{ unread: number }>('/notifications/unread-count/')).data,
    retry: false,
    refetchInterval: 60_000,
  })

  useEffect(() => {
    setMobileOpen(false)
    setMenuOpen(false)
  }, [location.pathname])

  const sections = RESOURCE_NAV.filter((section) =>
    canSee(section.roles, user?.user_type),
  )

  const sidebar = (
    <div className="flex h-full w-64 flex-col border-r border-slate-200 bg-white">
      <div className="flex h-16 items-center gap-2.5 border-b border-slate-100 px-5">
        <div className="flex size-9 items-center justify-center rounded-lg bg-brand-600 text-white">
          <School className="size-5" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-slate-900">School ERP</p>
          <p className="truncate text-xs text-slate-400">
            {user?.school_name ?? 'All schools'}
          </p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-1">
          {PRIMARY_NAV.map((item) => (
            <SidebarLink key={item.to} to={item.to} icon={item.icon} label={item.label} />
          ))}
        </div>

        {sections.map((section) => {
          const open = openGroups[section.label] ?? false
          const Icon = section.icon
          return (
            <div key={section.label} className="mt-4">
              <button
                type="button"
                onClick={() =>
                  setOpenGroups((prev) => ({ ...prev, [section.label]: !open }))
                }
                className="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400 transition hover:text-slate-600"
              >
                <span className="flex items-center gap-2">
                  <Icon className="size-4" />
                  {section.label}
                </span>
                <ChevronDown
                  className={cn('size-4 transition-transform', open && 'rotate-180')}
                />
              </button>
              {open ? (
                <div className="mt-1 space-y-0.5">
                  {section.items.map((item) => (
                    <SidebarLink
                      key={item.to}
                      to={item.to}
                      label={item.label}
                      indent
                    />
                  ))}
                </div>
              ) : null}
            </div>
          )
        })}
      </nav>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      <aside className="hidden lg:flex">{sidebar}</aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute left-0 top-0 h-full">{sidebar}</div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle navigation"
            >
              {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
            </Button>
            <div className="hidden items-center gap-2 text-sm text-slate-500 sm:flex">
              <Building2 className="size-4 text-slate-400" />
              <span className="font-medium text-slate-700">
                {user?.school_name ?? 'School Management'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate('/admin/notifications')}
              className="relative rounded-md p-2 text-slate-500 transition hover:bg-slate-100"
              aria-label="Notifications"
            >
              <Bell className="size-5" />
              {unread.data?.unread ? (
                <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-semibold text-white">
                  {unread.data.unread > 9 ? '9+' : unread.data.unread}
                </span>
              ) : null}
            </button>

            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((v) => !v)}
                className="flex items-center gap-2 rounded-md border border-slate-200 py-1.5 pl-1.5 pr-2.5 transition hover:bg-slate-50"
              >
                <span className="flex size-7 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
                  {initials(user?.full_name)}
                </span>
                <span className="hidden text-left leading-tight sm:block">
                  <span className="block text-sm font-medium text-slate-800">
                    {user?.full_name}
                  </span>
                  <span className="block text-xs text-slate-400">
                    {humanize(user?.user_type)}
                  </span>
                </span>
                <ChevronDown className="size-4 text-slate-400" />
              </button>

              {menuOpen ? (
                <div className="absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
                  <div className="border-b border-slate-100 px-4 py-3">
                    <p className="text-sm font-medium text-slate-800">
                      {user?.full_name}
                    </p>
                    <p className="truncate text-xs text-slate-400">{user?.email}</p>
                    <Badge variant="brand" className="mt-2">
                      {humanize(user?.user_type)}
                    </Badge>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate('/profile')}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50"
                  >
                    <UserRound className="size-4" />
                    My profile
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      void logout().then(() => navigate('/login'))
                    }}
                    className="flex w-full items-center gap-2 border-t border-slate-100 px-4 py-2.5 text-sm text-rose-600 transition hover:bg-rose-50"
                  >
                    <LogOut className="size-4" />
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function SidebarLink({
  to,
  label,
  icon: Icon,
  indent,
}: {
  to: string
  label: string
  icon?: ComponentType<{ className?: string }>
  indent?: boolean
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition',
          indent && 'pl-9',
          isActive
            ? 'bg-brand-50 text-brand-700'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
        )
      }
    >
      {Icon && !indent ? <Icon className="size-4" /> : null}
      <span className="truncate">{label}</span>
    </NavLink>
  )
}

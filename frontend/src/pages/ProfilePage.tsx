import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { KeyRound, Save } from 'lucide-react'
import { api, apiErrorMessage } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useToast } from '@/lib/toast'
import { humanize, initials } from '@/lib/utils'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Field, Input } from '@/components/ui/Input'

export function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const toast = useToast()

  const [profile, setProfile] = useState({
    first_name: user?.first_name ?? '',
    last_name: user?.last_name ?? '',
    email: user?.email ?? '',
    phone_number: user?.phone_number ?? '',
    date_of_birth: user?.date_of_birth ?? '',
    address: user?.address ?? '',
  })

  const [passwords, setPasswords] = useState({
    old_password: '',
    new_password: '',
  })

  const saveProfile = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.patch('/auth/me/', payload),
    onSuccess: () => {
      toast.success('Profile updated')
      refreshUser()
    },
    onError: (error) => toast.error('Could not update profile', apiErrorMessage(error)),
  })

  const changePassword = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post('/auth/change-password/', payload),
    onSuccess: () => {
      toast.success('Password changed')
      setPasswords({ old_password: '', new_password: '' })
    },
    onError: (error) => toast.error('Could not change password', apiErrorMessage(error)),
  })

  const onSubmitProfile = (event: FormEvent) => {
    event.preventDefault()
    saveProfile.mutate({ ...profile, date_of_birth: profile.date_of_birth || null })
  }

  const onSubmitPassword = (event: FormEvent) => {
    event.preventDefault()
    changePassword.mutate(passwords)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-center gap-4">
        <span className="flex size-14 items-center justify-center rounded-full bg-brand-100 text-lg font-semibold text-brand-700">
          {initials(user?.full_name)}
        </span>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{user?.full_name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="brand">{humanize(user?.user_type)}</Badge>
            <span className="text-sm text-slate-500">{user?.school_name ?? '—'}</span>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmitProfile} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="First name">
              <Input
                value={profile.first_name}
                onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
              />
            </Field>
            <Field label="Last name">
              <Input
                value={profile.last_name}
                onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
              />
            </Field>
            <Field label="Email">
              <Input
                type="email"
                value={profile.email}
                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
              />
            </Field>
            <Field label="Phone">
              <Input
                value={profile.phone_number}
                onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
              />
            </Field>
            <Field label="Date of birth">
              <Input
                type="date"
                value={profile.date_of_birth?.slice(0, 10) ?? ''}
                onChange={(e) => setProfile({ ...profile, date_of_birth: e.target.value })}
              />
            </Field>
            <Field label="Address" className="sm:col-span-2">
              <Input
                value={profile.address}
                onChange={(e) => setProfile({ ...profile, address: e.target.value })}
              />
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" loading={saveProfile.isPending}>
                <Save className="size-4" />
                Save changes
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmitPassword} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Current password" required>
              <Input
                type="password"
                value={passwords.old_password}
                required
                onChange={(e) =>
                  setPasswords({ ...passwords, old_password: e.target.value })
                }
              />
            </Field>
            <Field label="New password" required>
              <Input
                type="password"
                value={passwords.new_password}
                required
                onChange={(e) =>
                  setPasswords({ ...passwords, new_password: e.target.value })
                }
              />
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" variant="secondary" loading={changePassword.isPending}>
                <KeyRound className="size-4" />
                Update password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

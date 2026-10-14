import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage, clearTokens, getAccessToken, getRefreshToken, setTokens } from './api'
import type { User, UserType } from './types'

interface LoginResponse {
  access: string
  refresh: string
  user: User
}

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  isLoggingIn: boolean
  loginError: string | null
  logout: () => Promise<void>
  refreshUser: () => void
  hasRole: (...roles: UserType[]) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: async () => (await api.get<User>('/auth/me/')).data,
    enabled: Boolean(getAccessToken()),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const loginMutation = useMutation({
    mutationFn: async ({
      username,
      password,
    }: {
      username: string
      password: string
    }) => {
      const { data } = await api.post<LoginResponse>('/auth/login/', {
        username,
        password,
      })
      setTokens(data.access, data.refresh)
      return data.user
    },
    onSuccess: (user) => {
      queryClient.setQueryData(['me'], user)
    },
  })

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    try {
      if (refresh) await api.post('/auth/logout/', { refresh })
    } catch {
      // Logout is best-effort; clear locally regardless.
    }
    clearTokens()
    queryClient.clear()
  }, [queryClient])

  const refreshUser = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['me'] })
  }, [queryClient])

  const value = useMemo<AuthContextValue>(() => {
    const user = meQuery.data ?? null
    return {
      user,
      isAuthenticated: Boolean(user),
      isLoading: meQuery.isLoading && Boolean(getAccessToken()),
      login: async (username, password) => {
        await loginMutation.mutateAsync({ username, password })
      },
      isLoggingIn: loginMutation.isPending,
      loginError: loginMutation.isError
        ? apiErrorMessage(loginMutation.error)
        : null,
      logout,
      refreshUser,
      hasRole: (...roles) => (user ? roles.includes(user.user_type) : false),
    }
  }, [meQuery.data, meQuery.isLoading, loginMutation, logout, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'
import i18n from '@/lib/i18n'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  login: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
  updateUser: (updates: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,

      setUser: (user) => {
        if (user?.preferred_language) {
          i18n.changeLanguage(user.preferred_language)
        }
        set({ user, isAuthenticated: !!user })
      },

      setLoading: (isLoading) => set({ isLoading }),

      login: (user, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
        if (user?.preferred_language) {
          i18n.changeLanguage(user.preferred_language)
        }
        set({ user, isAuthenticated: true, isLoading: false })
      },

      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('workspace-storage')
        set({ user: null, isAuthenticated: false, isLoading: false })
      },

      updateUser: (updates) => {
        const currentUser = get().user
        if (currentUser) {
          const updatedUser = { ...currentUser, ...updates }
          if (updates.preferred_language) {
            i18n.changeLanguage(updates.preferred_language)
          }
          set({ user: updatedUser })
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
)

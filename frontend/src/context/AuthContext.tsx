import { createContext, useContext, useEffect, useState, useMemo, type ReactNode } from 'react'
import { syncUser } from '../services/api'

export interface UserProfile {
  name: string
  email: string
  institution?: string
  role?: string
  researchInterests?: string[]
}

interface AuthContextValue {
  user: UserProfile | null
  isAuthenticated: boolean
  displayName: string
  initials: string
  login: (email: string, password?: string, name?: string, institution?: string) => void
  signup: (name: string, email: string, password?: string, institution?: string) => void
  logout: () => void
  updateProfile: (updates: Partial<UserProfile>) => void
}

const STORAGE_KEY = 'lumina_user'

function getInitialUser(): UserProfile | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY) || window.localStorage.getItem('researchmind_user')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed.name === 'string') return parsed
    }
  } catch (err) {
    console.warn('Failed to parse stored user profile:', err)
  }
  return null
}

function deriveNameFromEmail(email: string): string {
  if (!email || !email.includes('@')) return 'Researcher'
  const handle = email.split('@')[0]
  // Convert handle like "john.doe" or "alex_smith" to "John Doe" or "Alex Smith"
  const parts = handle.split(/[._-]+/).filter(Boolean)
  if (parts.length === 0) return 'Researcher'
  return parts.map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(' ')
}

function computeInitials(name: string): string {
  if (!name) return 'RM'
  const tokens = name.trim().split(/\s+/).filter(Boolean)
  if (tokens.length === 1) {
    return tokens[0].slice(0, 2).toUpperCase()
  }
  return (tokens[0][0] + tokens[tokens.length - 1][0]).toUpperCase()
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(() => getInitialUser())

  // Persist user changes to localStorage and SQLite backend database
  useEffect(() => {
    if (user) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
      syncUser({
        email: user.email,
        name: user.name,
        institution: user.institution,
        role: user.role,
      }).catch((err) => console.warn('Could not sync user with backend SQLite:', err))
    } else {
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }, [user])

  const login = (email: string, _password?: string, name?: string, institution?: string) => {
    // If existing user matches, preserve existing details
    const existing = getInitialUser()
    const finalName = name?.trim() || (existing && existing.email.toLowerCase() === email.toLowerCase() ? existing.name : deriveNameFromEmail(email))
    const finalInstitution = institution?.trim() || existing?.institution || 'Research Institute'
    const finalRole = existing?.role || 'Principal Investigator'
    const finalInterests = existing?.researchInterests || ['Machine Learning', 'Scientific RAG', 'Information Retrieval']

    const nextUser: UserProfile = {
      name: finalName,
      email: email.trim(),
      institution: finalInstitution,
      role: finalRole,
      researchInterests: finalInterests,
    }
    setUser(nextUser)
  }

  const signup = (name: string, email: string, _password?: string, institution?: string) => {
    const nextUser: UserProfile = {
      name: name.trim() || deriveNameFromEmail(email),
      email: email.trim(),
      institution: institution?.trim() || 'Academic & Research Institution',
      role: 'Researcher',
      researchInterests: ['Machine Learning', 'Scientific RAG', 'Information Retrieval'],
    }
    setUser(nextUser)
  }

  const logout = () => {
    setUser(null)
  }

  const updateProfile = (updates: Partial<UserProfile>) => {
    setUser((curr) => {
      if (!curr) return null
      return { ...curr, ...updates }
    })
  }

  const displayName = useMemo(() => {
    if (user?.name?.trim()) return user.name.trim()
    if (user?.email) return deriveNameFromEmail(user.email)
    return 'Researcher'
  }, [user])

  const initials = useMemo(() => computeInitials(displayName), [displayName])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      displayName,
      initials,
      login,
      signup,
      logout,
      updateProfile,
    }),
    [user, displayName, initials]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

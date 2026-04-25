import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { api, setToken, clearToken, getToken } from "@/api/client"

interface User {
  id: string
  email: string
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setTokenState] = useState<string | null>(getToken())
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  useEffect(() => {
    if (token) {
      api
        .get("/auth/me")
        .then((res) => setUser(res.data))
        .catch(() => {
          clearToken()
          setTokenState(null)
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [token])

  const login = async (email: string, password: string) => {
    const res = await api.post("/auth/login", { email, password })
    setToken(res.data.access_token)
    setTokenState(res.data.access_token)
    const userRes = await api.get("/auth/me")
    setUser(userRes.data)
  }

  const register = async (email: string, password: string) => {
    const res = await api.post("/auth/register", { email, password })
    setToken(res.data.access_token)
    setTokenState(res.data.access_token)
    const userRes = await api.get("/auth/me")
    setUser(userRes.data)
  }

  const logout = () => {
    clearToken()
    setTokenState(null)
    setUser(null)
    queryClient.clear()
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

import axios from "axios"

const TOKEN_KEY = "flatster_token"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes("/auth/me")) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

import { Navigate } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthContext"
import { LoadingSpinner } from "./LoadingSpinner"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth()

  if (isLoading) return <LoadingSpinner />
  if (!token) return <Navigate to="/login" replace />

  return <>{children}</>
}

import { Link, Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthContext"
import { useFavorites } from "@/api/favorites"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export function Layout() {
  const { user, logout } = useAuth()
  const { data: favorites } = useFavorites()
  const navigate = useNavigate()
  const favCount = favorites?.length ?? 0

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <nav className="flex items-center gap-6">
            <Link to="/projects" className="text-lg font-semibold">
              Flatster
            </Link>
            <Link
              to="/projects"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Projects
            </Link>
            <Link
              to="/compare"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              Compare
              {favCount > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {favCount}
                </Badge>
              )}
            </Link>
          </nav>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                logout()
                navigate("/login")
              }}
            >
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

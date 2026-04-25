import { useState } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "./AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function LoginPage() {
  const { token, login, register } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  if (token) return <Navigate to="/projects" replace />

  const handleSubmit = async (action: "login" | "register") => {
    setError("")
    setLoading(true)
    try {
      if (action === "login") {
        await login(email, password)
      } else {
        if (password.length < 8) {
          setError("Password must be at least 8 characters")
          setLoading(false)
          return
        }
        await register(email, password)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  const form = (action: "login" | "register") => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor={`${action}-email`}>Email</Label>
        <Input
          id={`${action}-email`}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${action}-password`}>Password</Label>
        <Input
          id={`${action}-password`}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={action === "register" ? "Min 8 characters" : ""}
        />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button
        className="w-full"
        disabled={loading}
        onClick={() => handleSubmit(action)}
      >
        {loading ? "Loading..." : action === "login" ? "Login" : "Register"}
      </Button>
    </div>
  )

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center text-2xl">Flatster</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="login" onValueChange={() => setError("")}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">Login</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>
            <TabsContent value="login">{form("login")}</TabsContent>
            <TabsContent value="register">{form("register")}</TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}

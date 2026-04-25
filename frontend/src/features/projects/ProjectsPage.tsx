import { Link } from "react-router-dom"
import { useProjects } from "@/api/projects"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { ProjectCreateDialog } from "./ProjectCreateDialog"
import { formatRelativeTime } from "@/lib/utils"

export function ProjectsPage() {
  const { data: projects, isLoading } = useProjects()

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Projects</h1>
        <ProjectCreateDialog />
      </div>

      {projects?.length === 0 && (
        <p className="text-muted-foreground">
          No projects yet. Create one to start tracking listings.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects?.map((project) => (
          <Link key={project.id} to={`/projects/${project.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{project.name}</CardTitle>
                  <Badge variant={project.is_active ? "default" : "secondary"}>
                    {project.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-2 truncate text-sm text-muted-foreground">
                  {project.scrape_url}
                </p>
                <div className="flex items-center justify-between text-sm">
                  <span>{project.listing_count} listings</span>
                  <span className="text-muted-foreground">
                    {formatRelativeTime(project.last_scraped_at)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useDeleteProject, useTriggerScrape, useUpdateProject, type Project } from "@/api/projects"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { formatRelativeTime } from "@/lib/utils"
import { REGIONS, PROPERTY_TYPES } from "@/lib/constants"

interface Props {
  project: Project
}

export function ProjectSettingsPanel({ project }: Props) {
  const navigate = useNavigate()
  const updateProject = useUpdateProject()
  const deleteProject = useDeleteProject()
  const triggerScrape = useTriggerScrape()
  const [scrapeResult, setScrapeResult] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleScrape = async () => {
    setScrapeResult(null)
    try {
      const result = await triggerScrape.mutateAsync(project.id)
      setScrapeResult(
        `Found ${result.listings_found}: ${result.new} new, ${result.updated} updated, ${result.marked_sold} sold`
      )
    } catch {
      setScrapeResult("Scrape failed")
    }
  }

  const handleDelete = async () => {
    await deleteProject.mutateAsync(project.id)
    navigate("/projects")
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{project.name}</h2>

      <div className="space-y-2 text-sm">
        <div>
          <span className="text-muted-foreground">Region: </span>
          {REGIONS[project.filters.region] || project.filters.region}
        </div>
        <div>
          <span className="text-muted-foreground">Type: </span>
          {PROPERTY_TYPES[project.filters.property_type] || project.filters.property_type}
        </div>
        <div>
          <span className="text-muted-foreground">Transaction: </span>
          {project.filters.transaction}
        </div>
        {project.filters.rooms && (
          <div>
            <span className="text-muted-foreground">Rooms: </span>
            {project.filters.rooms.join(", ")}
          </div>
        )}
        <div>
          <span className="text-muted-foreground">Listings: </span>
          {project.listing_count}
        </div>
        <div>
          <span className="text-muted-foreground">Last scraped: </span>
          {formatRelativeTime(project.last_scraped_at)}
        </div>
      </div>

      <Separator />

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Switch
            checked={project.is_active}
            onCheckedChange={(checked) =>
              updateProject.mutate({ id: project.id, is_active: checked })
            }
          />
          <Label>Active</Label>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            checked={project.ai_scoring_enabled}
            onCheckedChange={(checked) =>
              updateProject.mutate({ id: project.id, ai_scoring_enabled: checked })
            }
          />
          <Label>AI Scoring</Label>
        </div>
      </div>

      <Separator />

      <Button
        className="w-full"
        onClick={handleScrape}
        disabled={triggerScrape.isPending}
      >
        {triggerScrape.isPending ? "Scraping..." : "Scrape Now"}
      </Button>
      {scrapeResult && (
        <p className="text-sm text-muted-foreground">{scrapeResult}</p>
      )}

      <Separator />

      {!confirmDelete ? (
        <Button
          variant="destructive"
          className="w-full"
          onClick={() => setConfirmDelete(true)}
        >
          Delete Project
        </Button>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Are you sure? This deletes all listings.</p>
          <div className="flex gap-2">
            <Button variant="destructive" className="flex-1" onClick={handleDelete}>
              Confirm
            </Button>
            <Button variant="outline" className="flex-1" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

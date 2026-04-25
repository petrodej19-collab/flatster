import { useState } from "react"
import { useParams } from "react-router-dom"
import { useProject } from "@/api/projects"
import { useListings } from "@/api/listings"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { ListingsView } from "@/features/listings/ListingsView"
import { ProjectSettingsPanel } from "./ProjectSettingsPanel"
import { formatPrice, formatRelativeTime } from "@/lib/utils"

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: project, isLoading } = useProject(id!)
  const { data: listingsData } = useListings(id!, { page: 1, per_page: 1 })
  const [showSettings, setShowSettings] = useState(false)

  if (isLoading || !project) return <LoadingSpinner />

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="text-sm text-muted-foreground">
            Last scraped {formatRelativeTime(project.last_scraped_at)}
          </p>
        </div>
        <button
          className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
          onClick={() => setShowSettings(!showSettings)}
        >
          {showSettings ? "Hide settings" : "Settings"}
        </button>
      </div>

      {/* Stats bar */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total listings" value={String(project.listing_count)} />
        <StatCard
          label="AI scoring"
          value={project.ai_scoring_enabled ? "On" : "Off"}
          muted={!project.ai_scoring_enabled}
        />
        <StatCard
          label="Status"
          value={project.is_active ? "Active" : "Paused"}
          muted={!project.is_active}
        />
        <StatCard label="Scrape URL" value={project.scrape_url} truncate />
      </div>

      {/* Settings panel (collapsible) */}
      {showSettings && (
        <div className="mb-6 rounded-lg border bg-card p-4">
          <ProjectSettingsPanel project={project} />
        </div>
      )}

      {/* Listings */}
      <ListingsView projectId={project.id} />
    </div>
  )
}

function StatCard({
  label,
  value,
  muted = false,
  truncate = false,
}: {
  label: string
  value: string
  muted?: boolean
  truncate?: boolean
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-sm font-medium ${muted ? "text-muted-foreground" : ""} ${truncate ? "truncate" : ""}`}>
        {value}
      </p>
    </div>
  )
}

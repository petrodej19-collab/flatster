import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useListings, type ListingFilters, type ListingSummary } from "@/api/listings"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { FavoriteButton } from "./FavoriteButton"
import { formatDate, formatPrice, scoreColor } from "@/lib/utils"

interface Props {
  projectId: string
}

type ViewMode = "grid" | "table"

export function ListingsView({ projectId }: Props) {
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    return (localStorage.getItem(`listings_view_${projectId}`) as ViewMode) || "grid"
  })
  const [filters, setFilters] = useState<ListingFilters>(() => {
    const key = `listings_sort_${projectId}`
    const saved = localStorage.getItem(key)
    if (saved) {
      try {
        const { sort_by, sort_order } = JSON.parse(saved)
        if (sort_by) return { sort_by, sort_order: sort_order || "desc", page: 1, per_page: 25 }
      } catch { /* ignore */ }
    }
    return { sort_by: "first_seen_at", sort_order: "desc", page: 1, per_page: 25 }
  })
  const [previewIdx, setPreviewIdx] = useState<number | null>(null)

  const { data, isLoading, isFetching } = useListings(projectId, filters)
  const items = data?.items ?? []

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (previewIdx === null) return
    if (e.key === "Escape") setPreviewIdx(null)
    if (e.key === "ArrowDown" || e.key === "ArrowRight") {
      e.preventDefault()
      setPreviewIdx((prev) => (prev! < items.length - 1 ? prev! + 1 : 0))
    }
    if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
      e.preventDefault()
      setPreviewIdx((prev) => (prev! > 0 ? prev! - 1 : items.length - 1))
    }
    if (e.key === "Enter") {
      navigate(`/projects/${projectId}/listings/${items[previewIdx].id}`)
    }
  }, [previewIdx, items, navigate, projectId])

  useEffect(() => {
    if (previewIdx !== null) {
      window.addEventListener("keydown", handleKeyDown)
      return () => window.removeEventListener("keydown", handleKeyDown)
    }
  }, [previewIdx, handleKeyDown])

  const handleSort = (column: string) => {
    const sort_order = filters.sort_by === column && filters.sort_order === "asc" ? "desc" : "asc"
    localStorage.setItem(`listings_sort_${projectId}`, JSON.stringify({ sort_by: column, sort_order }))
    setFilters((prev) => ({ ...prev, sort_by: column, sort_order, page: 1 }))
  }

  const toggleView = (mode: ViewMode) => {
    setViewMode(mode)
    localStorage.setItem(`listings_view_${projectId}`, mode)
  }

  const sortIcon = (column: string) => {
    if (filters.sort_by !== column) return ""
    return filters.sort_order === "asc" ? " ↑" : " ↓"
  }

  if (isLoading) return <LoadingSpinner />

  const totalPages = Math.ceil((data?.total ?? 0) / (filters.per_page ?? 25))

  return (
    <div>
      {/* Toolbar */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          className="rounded-md border bg-card px-3 py-2 text-sm"
          value={filters.status || ""}
          onChange={(e) =>
            setFilters((prev) => ({ ...prev, status: e.target.value || undefined, page: 1 }))
          }
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="sold">Sold</option>
          <option value="price_changed">Price changed</option>
        </select>
        <Input
          type="number"
          placeholder="Min price"
          className="w-28"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              min_price: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
        <Input
          type="number"
          placeholder="Max price"
          className="w-28"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              max_price: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
        <Input
          type="number"
          placeholder="Min m²"
          className="w-24"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              min_size: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
        <Input
          type="number"
          placeholder="Max m²"
          className="w-24"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              max_size: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />

        {/* Sort (for grid mode) */}
        {viewMode === "grid" && (
          <select
            className="rounded-md border bg-card px-3 py-2 text-sm"
            value={`${filters.sort_by}:${filters.sort_order}`}
            onChange={(e) => {
              const [sort_by, sort_order] = e.target.value.split(":")
              localStorage.setItem(`listings_sort_${projectId}`, JSON.stringify({ sort_by, sort_order }))
              setFilters((prev) => ({ ...prev, sort_by, sort_order: sort_order as "asc" | "desc", page: 1 }))
            }}
          >
            <option value="first_seen_at:desc">Newest first</option>
            <option value="first_seen_at:asc">Oldest first</option>
            <option value="price:asc">Price: low to high</option>
            <option value="price:desc">Price: high to low</option>
            <option value="price_per_m2:asc">EUR/m²: low to high</option>
            <option value="price_per_m2:desc">EUR/m²: high to low</option>
            <option value="size_m2:desc">Size: largest</option>
            <option value="size_m2:asc">Size: smallest</option>
            <option value="ai_score:desc">AI Score: best</option>
            <option value="basic_score:desc">Score: best</option>
          </select>
        )}

        {/* Export */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const token = localStorage.getItem("flatster_token")
            const url = `/api/projects/${projectId}/listings/export`
            fetch(url, { headers: { Authorization: `Bearer ${token}` } })
              .then(r => r.blob())
              .then(blob => {
                const a = document.createElement("a")
                a.href = URL.createObjectURL(blob)
                a.download = `listings.csv`
                a.click()
                URL.revokeObjectURL(a.href)
              })
          }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export
        </Button>

        {/* View toggle */}
        <div className="ml-auto flex rounded-md border">
          <button
            className={`px-3 py-2 text-sm ${viewMode === "grid" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
            onClick={() => toggleView("grid")}
            title="Grid view"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          </button>
          <button
            className={`px-3 py-2 text-sm ${viewMode === "table" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
            onClick={() => toggleView("table")}
            title="Table view"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className={isFetching ? "opacity-60 transition-opacity" : ""}>
        {viewMode === "grid" ? (
          <ListingsGrid items={items} projectId={projectId} />
        ) : (
          <ListingsTable
            items={items}
            projectId={projectId}
            filters={filters}
            sortIcon={sortIcon}
            handleSort={handleSort}
            previewIdx={previewIdx}
            setPreviewIdx={setPreviewIdx}
          />
        )}
      </div>

      {/* Quick Preview (table mode) */}
      {viewMode === "table" && previewIdx !== null && items[previewIdx] && (
        <QuickPreview
          listing={items[previewIdx]}
          index={previewIdx}
          total={items.length}
          onClose={() => setPreviewIdx(null)}
          onPrev={() => setPreviewIdx((prev) => (prev! > 0 ? prev! - 1 : items.length - 1))}
          onNext={() => setPreviewIdx((prev) => (prev! < items.length - 1 ? prev! + 1 : 0))}
          onOpen={() => navigate(`/projects/${projectId}/listings/${items[previewIdx].id}`)}
        />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {data?.total} listings
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={(filters.page ?? 1) <= 1}
              onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) - 1 }))}
            >
              Previous
            </Button>
            <span className="text-sm">
              {filters.page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={(filters.page ?? 1) >= totalPages}
              onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) + 1 }))}
            >
              Next
            </Button>
            <select
              className="rounded-md border bg-card px-2 py-1 text-sm"
              value={filters.per_page}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, per_page: Number(e.target.value), page: 1 }))
              }
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      )}
    </div>
  )
}


/* ─── Grid View ─── */

function ListingsGrid({ items, projectId }: { items: ListingSummary[]; projectId: string }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="py-12 text-center text-muted-foreground">No listings found</p>
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((listing) => (
        <div
          key={listing.id}
          className="group cursor-pointer overflow-hidden rounded-lg border bg-card transition-all hover:shadow-md"
          onClick={() => navigate(`/projects/${projectId}/listings/${listing.id}`)}
        >
          {/* Image */}
          <div className="relative aspect-[4/3] overflow-hidden bg-muted">
            {listing.images.length > 0 ? (
              <img
                src={listing.images[0]}
                alt={listing.title}
                className="h-full w-full object-cover transition-transform group-hover:scale-105"
                loading="lazy"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No image
              </div>
            )}
            {/* Overlay badges */}
            <div className="absolute left-2 top-2 flex gap-1">
              <StatusBadge status={listing.status} />
            </div>
            <div className="absolute right-2 top-2">
              <div onClick={(e) => e.stopPropagation()}>
                <FavoriteButton listingId={listing.id} />
              </div>
            </div>
            {/* Score pills */}
            <div className="absolute bottom-2 left-2 flex gap-1">
              {listing.ai_score != null && (
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold shadow ${scoreColor(listing.ai_score)}`}>
                  AI {Math.round(listing.ai_score)}
                </span>
              )}
              {listing.basic_score != null && (
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold shadow ${scoreColor(listing.basic_score)}`}>
                  {Math.round(listing.basic_score)}
                </span>
              )}
            </div>
            {listing.images.length > 1 && (
              <span className="absolute bottom-2 right-2 rounded bg-black/60 px-1.5 py-0.5 text-xs text-white">
                {listing.images.length}
              </span>
            )}
          </div>

          {/* Content */}
          <div className="p-3">
            <div className="mb-1 text-lg font-bold">{formatPrice(listing.price)}</div>
            <p className="mb-2 line-clamp-1 text-sm text-muted-foreground">{listing.title}</p>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {listing.size_m2 && <span>{listing.size_m2} m²</span>}
              {listing.rooms && <span>{listing.rooms}</span>}
              {listing.floor && <span>Floor {listing.floor}</span>}
              {listing.year_built && <span>{listing.year_built}</span>}
              {listing.price_per_m2 && (
                <span className="ml-auto font-medium text-foreground">
                  {Math.round(listing.price_per_m2)} EUR/m²
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}


/* ─── Table View ─── */

function ListingsTable({
  items,
  projectId,
  filters,
  sortIcon,
  handleSort,
  previewIdx,
  setPreviewIdx,
}: {
  items: ListingSummary[]
  projectId: string
  filters: ListingFilters
  sortIcon: (col: string) => string
  handleSort: (col: string) => void
  previewIdx: number | null
  setPreviewIdx: (idx: number | null) => void
}) {
  const navigate = useNavigate()

  return (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="w-10 p-2"></th>
            <th className="w-10 p-2"></th>
            <th className="w-16 p-2"></th>
            <th className="p-2 text-left">Title</th>
            <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("price")}>
              Price{sortIcon("price")}
            </th>
            <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("price_per_m2")}>
              EUR/m²{sortIcon("price_per_m2")}
            </th>
            <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("size_m2")}>
              Size{sortIcon("size_m2")}
            </th>
            <th className="p-2 text-center">Rooms</th>
            <th className="p-2 text-center">Floor</th>
            <th className="p-2 text-center">Year</th>
            <th className="cursor-pointer p-2 text-center" onClick={() => handleSort("basic_score")}>
              Score{sortIcon("basic_score")}
            </th>
            <th className="cursor-pointer p-2 text-center" onClick={() => handleSort("ai_score")}>
              AI{sortIcon("ai_score")}
            </th>
            <th className="p-2 text-center">Status</th>
            <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("first_seen_at")}>
              First seen{sortIcon("first_seen_at")}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((listing, idx) => (
            <tr
              key={listing.id}
              className={`cursor-pointer border-b hover:bg-muted/50 ${previewIdx === idx ? "bg-muted" : ""}`}
              onClick={() => navigate(`/projects/${projectId}/listings/${listing.id}`)}
            >
              <td className="p-2" onClick={(e) => e.stopPropagation()}>
                <FavoriteButton listingId={listing.id} />
              </td>
              <td className="p-2">
                <button
                  className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="Quick preview"
                  onClick={(e) => {
                    e.stopPropagation()
                    setPreviewIdx(previewIdx === idx ? null : idx)
                  }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                </button>
              </td>
              <td className="p-2">
                {listing.images[0] ? (
                  <img src={listing.images[0]} alt="" className="h-10 w-14 rounded object-cover" loading="lazy" />
                ) : (
                  <div className="flex h-10 w-14 items-center justify-center rounded bg-muted text-[10px] text-muted-foreground">—</div>
                )}
              </td>
              <td className="max-w-[200px] truncate p-2">{listing.title}</td>
              <td className="p-2 text-right font-medium">{formatPrice(listing.price)}</td>
              <td className="p-2 text-right">
                {listing.price_per_m2 ? Math.round(listing.price_per_m2) : "—"}
              </td>
              <td className="p-2 text-right">
                {listing.size_m2 ? `${listing.size_m2} m²` : "—"}
              </td>
              <td className="p-2 text-center">{listing.rooms || "—"}</td>
              <td className="p-2 text-center">{listing.floor || "—"}</td>
              <td className="p-2 text-center">{listing.year_built || "—"}</td>
              <td className="p-2 text-center">
                {listing.basic_score != null ? (
                  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.basic_score)}`}>
                    {Math.round(listing.basic_score)}
                  </span>
                ) : "—"}
              </td>
              <td className="p-2 text-center">
                {listing.ai_score != null ? (
                  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.ai_score)}`}>
                    {Math.round(listing.ai_score)}
                  </span>
                ) : "—"}
              </td>
              <td className="p-2 text-center">
                <StatusBadge status={listing.status} />
              </td>
              <td className="whitespace-nowrap p-2 text-right text-muted-foreground">
                {listing.first_seen_at ? formatDate(listing.first_seen_at) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


/* ─── Quick Preview (table mode) ─── */

function QuickPreview({
  listing,
  index,
  total,
  onClose,
  onPrev,
  onNext,
  onOpen,
}: {
  listing: ListingSummary
  index: number
  total: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
  onOpen: () => void
}) {
  return (
    <div className="mt-3 rounded-lg border bg-card p-4 shadow-lg">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onPrev}>&#8249;</Button>
          <span className="text-sm text-muted-foreground">{index + 1} / {total}</span>
          <Button variant="outline" size="sm" onClick={onNext}>&#8250;</Button>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onOpen}>Open details</Button>
          <a href={listing.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="sm">View on site</Button>
          </a>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </Button>
        </div>
      </div>
      <div className="flex gap-4">
        <div className="flex shrink-0 gap-2 overflow-x-auto">
          {listing.images.length > 0 ? (
            listing.images.slice(0, 5).map((img, i) => (
              <img key={i} src={img} alt="" className="h-36 w-auto rounded-md object-cover" loading="lazy" />
            ))
          ) : (
            <div className="flex h-36 w-48 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground">No images</div>
          )}
        </div>
        <div className="flex-1 space-y-2">
          <h3 className="font-semibold">{listing.title}</h3>
          {listing.location && <p className="text-sm text-muted-foreground">{listing.location}</p>}
          <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-sm">
            <div><span className="text-muted-foreground">Price:</span> {formatPrice(listing.price)}</div>
            <div><span className="text-muted-foreground">EUR/m²:</span> {listing.price_per_m2 ? Math.round(listing.price_per_m2) : "—"}</div>
            <div><span className="text-muted-foreground">Size:</span> {listing.size_m2 ? `${listing.size_m2} m²` : "—"}</div>
            <div><span className="text-muted-foreground">Rooms:</span> {listing.rooms || "—"}</div>
            <div><span className="text-muted-foreground">Floor:</span> {listing.floor || "—"}</div>
            <div><span className="text-muted-foreground">Year:</span> {listing.year_built || "—"}</div>
          </div>
          <div className="flex items-center gap-3 pt-1">
            {listing.ai_score != null && (
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.ai_score)}`}>AI: {Math.round(listing.ai_score)}</span>
            )}
            {listing.basic_score != null && (
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.basic_score)}`}>Score: {Math.round(listing.basic_score)}</span>
            )}
            <StatusBadge status={listing.status} />
          </div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Arrow keys to navigate, Enter to open, Escape to close</p>
    </div>
  )
}


/* ─── Shared ─── */

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant={
        status === "active" ? "default" : status === "sold" ? "destructive" : "secondary"
      }
    >
      {status}
    </Badge>
  )
}

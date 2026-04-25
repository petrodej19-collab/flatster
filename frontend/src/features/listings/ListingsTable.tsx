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

export function ListingsTable({ projectId }: Props) {
  const navigate = useNavigate()
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

  const sortIcon = (column: string) => {
    if (filters.sort_by !== column) return ""
    return filters.sort_order === "asc" ? " ↑" : " ↓"
  }

  if (isLoading) return <LoadingSpinner />

  const totalPages = Math.ceil((data?.total ?? 0) / (filters.per_page ?? 25))

  return (
    <div>
      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          className="rounded-md border px-3 py-2 text-sm"
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
          className="w-32"
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
          className="w-32"
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
          placeholder="Min size (m²)"
          className="w-32"
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
          placeholder="Max size (m²)"
          className="w-32"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              max_size: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
      </div>

      {/* Table */}
      <div className={`rounded-md border ${isFetching ? "opacity-50" : ""}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="w-10 p-2"></th>
              <th className="w-10 p-2"></th>
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
                <td className="p-2">
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
                <td className="max-w-xs truncate p-2">{listing.title}</td>
                <td className="p-2 text-right">{formatPrice(listing.price)}</td>
                <td className="p-2 text-right">
                  {listing.price_per_m2 ? `${Math.round(listing.price_per_m2)}` : "—"}
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
                  ) : (
                    "—"
                  )}
                </td>
                <td className="p-2 text-center">
                  {listing.ai_score != null ? (
                    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.ai_score)}`}>
                      {Math.round(listing.ai_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="p-2 text-center">
                  <Badge
                    variant={
                      listing.status === "active"
                        ? "default"
                        : listing.status === "sold"
                          ? "destructive"
                          : "secondary"
                    }
                  >
                    {listing.status}
                  </Badge>
                </td>
                <td className="whitespace-nowrap p-2 text-right text-muted-foreground">
                  {listing.first_seen_at ? formatDate(listing.first_seen_at) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Quick Preview */}
      {previewIdx !== null && items[previewIdx] && (
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
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {data?.total} listings total
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
              Page {filters.page} of {totalPages}
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
              className="rounded-md border px-2 py-1 text-sm"
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
          <Button variant="outline" size="sm" onClick={onPrev}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
          </Button>
          <span className="text-sm text-muted-foreground">{index + 1} / {total}</span>
          <Button variant="outline" size="sm" onClick={onNext}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onOpen}>
            Open full details
          </Button>
          <a href={listing.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="sm">
              View on site
            </Button>
          </a>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </Button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Images */}
        <div className="flex shrink-0 gap-2 overflow-x-auto">
          {listing.images.length > 0 ? (
            listing.images.slice(0, 4).map((img, i) => (
              <img
                key={i}
                src={img}
                alt={`Image ${i + 1}`}
                className="h-32 w-auto rounded-md object-cover"
                loading="lazy"
              />
            ))
          ) : (
            <div className="flex h-32 w-44 items-center justify-center rounded-md bg-muted text-sm text-muted-foreground">
              No images
            </div>
          )}
        </div>

        {/* Details */}
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
            {listing.basic_score != null && (
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.basic_score)}`}>
                Score: {Math.round(listing.basic_score)}
              </span>
            )}
            {listing.ai_score != null && (
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.ai_score)}`}>
                AI: {Math.round(listing.ai_score)}
              </span>
            )}
            <Badge
              variant={listing.status === "active" ? "default" : listing.status === "sold" ? "destructive" : "secondary"}
            >
              {listing.status}
            </Badge>
          </div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Arrow keys to navigate, Enter to open, Escape to close</p>
    </div>
  )
}

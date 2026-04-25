import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useListing, useScoreListing } from "@/api/listings"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { FavoriteButton } from "./FavoriteButton"
import { PriceHistoryChart } from "./PriceHistoryChart"
import { formatPrice, formatDate, scoreColor } from "@/lib/utils"

export function ListingDetailPage() {
  const { id, listingId } = useParams<{ id: string; listingId: string }>()
  const navigate = useNavigate()
  const { data: listing, isLoading } = useListing(id!, listingId!)
  const scoreListing = useScoreListing()
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null)
  const [mainImg, setMainImg] = useState(0)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (lightboxIdx === null || !listing) return
    if (e.key === "Escape") setLightboxIdx(null)
    if (e.key === "ArrowRight") setLightboxIdx((prev) => (prev! < listing.images.length - 1 ? prev! + 1 : 0))
    if (e.key === "ArrowLeft") setLightboxIdx((prev) => (prev! > 0 ? prev! - 1 : listing.images.length - 1))
  }, [lightboxIdx, listing])

  useEffect(() => {
    if (lightboxIdx !== null) {
      window.addEventListener("keydown", handleKeyDown)
      return () => window.removeEventListener("keydown", handleKeyDown)
    }
  }, [lightboxIdx, handleKeyDown])

  if (isLoading || !listing) return <LoadingSpinner />

  const analysis = listing.ai_analysis ? (() => {
    try { return JSON.parse(listing.ai_analysis) } catch { return null }
  })() : null

  return (
    <div className="mx-auto max-w-5xl">
      {/* Back + title */}
      <div className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/projects/${id}`)}>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
          Back
        </Button>
        <div className="ml-auto">
          <FavoriteButton listingId={listing.id} />
        </div>
      </div>

      {/* Gallery + Key Info side by side */}
      <div className="mb-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        {/* Gallery */}
        <div className="min-w-0">
          {listing.images.length > 0 ? (
            <>
              <div
                className="cursor-pointer overflow-hidden rounded-lg"
                onClick={() => setLightboxIdx(mainImg)}
              >
                <img
                  src={listing.images[mainImg]}
                  alt={listing.title}
                  className="aspect-[16/10] w-full object-cover transition-transform hover:scale-[1.02]"
                />
              </div>
              {listing.images.length > 1 && (
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                  {listing.images.map((img, i) => (
                    <img
                      key={i}
                      src={img}
                      alt=""
                      className={`h-16 w-24 shrink-0 cursor-pointer rounded object-cover transition-opacity ${
                        i === mainImg ? "ring-2 ring-primary" : "opacity-70 hover:opacity-100"
                      }`}
                      onClick={() => setMainImg(i)}
                      loading="lazy"
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="flex aspect-[16/10] items-center justify-center rounded-lg bg-muted text-muted-foreground">
              No images
            </div>
          )}
        </div>

        {/* Key info card */}
        <div className="min-w-0 space-y-4 overflow-hidden">
          <div>
            <h1 className="text-xl font-bold">{listing.title}</h1>
            {listing.location && (
              <p className="mt-1 text-sm text-muted-foreground">{listing.location}</p>
            )}
          </div>

          <div className="text-3xl font-bold">{formatPrice(listing.price)}</div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <InfoRow label="Price/m²" value={listing.price_per_m2 ? `${Math.round(listing.price_per_m2)} EUR` : null} />
            <InfoRow label="Size" value={listing.size_m2 ? `${listing.size_m2} m²` : null} />
            <InfoRow label="Rooms" value={listing.rooms} />
            <InfoRow label="Floor" value={listing.floor} />
            <InfoRow label="Year built" value={listing.year_built ? String(listing.year_built) : null} />
            <InfoRow label="Renovated" value={listing.year_renovated ? String(listing.year_renovated) : null} />
            <InfoRow label="Energy" value={listing.energy_class} />
            <InfoRow label="Agency" value={listing.agency} />
          </div>

          <div className="flex items-center gap-2">
            <Badge
              variant={listing.status === "active" ? "default" : listing.status === "sold" ? "destructive" : "secondary"}
            >
              {listing.status}
            </Badge>
            <a href={listing.url} target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground underline">
              View original
            </a>
          </div>

          {/* Scores */}
          <div className="flex gap-3 rounded-lg border p-3">
            <ScoreBlock label="Score" score={listing.basic_score} />
            <div className="w-px bg-border" />
            {listing.ai_score != null ? (
              <ScoreBlock label="AI" score={listing.ai_score} />
            ) : listing.description ? (
              <div className="flex flex-1 flex-col items-center justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={scoreListing.isPending}
                  onClick={() => scoreListing.mutate({ projectId: id!, listingId: listingId! })}
                >
                  {scoreListing.isPending ? "Scoring..." : "Score with AI"}
                </Button>
              </div>
            ) : (
              <div className="flex flex-1 items-center justify-center text-xs text-muted-foreground">No description for AI</div>
            )}
          </div>
        </div>
      </div>

      {/* AI Analysis */}
      {analysis && (
        <div className="mb-6 rounded-lg border bg-card p-5">
          <h2 className="mb-3 text-lg font-semibold">AI Analysis</h2>
          <p className="mb-4 text-sm leading-relaxed">{analysis.summary}</p>

          <div className="mb-4 grid gap-4 sm:grid-cols-2">
            <AnalysisCard title="Investment" rating={analysis.investment?.rating} points={analysis.investment?.points} />
            <AnalysisCard title="Livability" rating={analysis.livability?.rating} points={analysis.livability?.points} />
          </div>

          <div className="flex flex-wrap gap-2">
            {analysis.green_flags?.map((f: string, i: number) => (
              <span key={i} className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-800">{f}</span>
            ))}
            {analysis.red_flags?.map((f: string, i: number) => (
              <span key={i} className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-800">{f}</span>
            ))}
          </div>
        </div>
      )}

      {/* Price History */}
      {listing.price_history.length > 1 && (
        <div className="mb-6 rounded-lg border bg-card p-5">
          <h2 className="mb-3 text-lg font-semibold">Price History</h2>
          <PriceHistoryChart history={listing.price_history} />
        </div>
      )}

      {/* Description */}
      {listing.description && (
        <div className="mb-6 rounded-lg border bg-card p-5">
          <h2 className="mb-3 text-lg font-semibold">Description</h2>
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{listing.description}</p>
        </div>
      )}

      {/* Footer meta */}
      <div className="mb-8 flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span>First seen: {formatDate(listing.first_seen_at)}</span>
        <span>Last seen: {formatDate(listing.last_seen_at)}</span>
        {listing.consecutive_misses > 0 && <span>Consecutive misses: {listing.consecutive_misses}</span>}
      </div>

      {/* Lightbox */}
      {lightboxIdx !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85"
          onClick={() => setLightboxIdx(null)}
        >
          <button
            className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/20 px-4 py-3 text-2xl text-white backdrop-blur-sm hover:bg-white/30"
            onClick={(e) => {
              e.stopPropagation()
              setLightboxIdx((prev) => (prev! > 0 ? prev! - 1 : listing.images.length - 1))
            }}
          >
            &#8249;
          </button>
          <img
            src={listing.images[lightboxIdx]}
            alt=""
            className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/20 px-4 py-3 text-2xl text-white backdrop-blur-sm hover:bg-white/30"
            onClick={(e) => {
              e.stopPropagation()
              setLightboxIdx((prev) => (prev! < listing.images.length - 1 ? prev! + 1 : 0))
            }}
          >
            &#8250;
          </button>
          <button
            className="absolute right-4 top-4 rounded-full bg-white/20 px-3 py-1.5 text-lg text-white backdrop-blur-sm hover:bg-white/30"
            onClick={() => setLightboxIdx(null)}
          >
            &#x2715;
          </button>
          <span className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-3 py-1 text-sm text-white">
            {lightboxIdx + 1} / {listing.images.length}
          </span>
        </div>
      )}
    </div>
  )
}


function InfoRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <span className="text-muted-foreground">{label}: </span>
      <span className="font-medium">{value || "—"}</span>
    </div>
  )
}

function ScoreBlock({ label, score }: { label: string; score: number | null }) {
  return (
    <div className="flex flex-1 flex-col items-center">
      <span className="text-xs text-muted-foreground">{label}</span>
      {score != null ? (
        <span className={`mt-1 rounded-lg px-3 py-1 text-2xl font-bold ${scoreColor(score)}`}>
          {Math.round(score)}
        </span>
      ) : (
        <span className="mt-1 text-xl text-muted-foreground">—</span>
      )}
    </div>
  )
}

function AnalysisCard({ title, rating, points }: { title: string; rating?: string; points?: string[] }) {
  return (
    <div className="rounded-md border p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        {rating && (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            rating === "Excellent" ? "bg-green-100 text-green-800" :
            rating === "Good" ? "bg-blue-100 text-blue-800" :
            rating === "Fair" ? "bg-yellow-100 text-yellow-800" :
            "bg-red-100 text-red-800"
          }`}>{rating}</span>
        )}
      </div>
      <ul className="space-y-1 text-xs text-muted-foreground">
        {points?.map((p, i) => (
          <li key={i} className="leading-relaxed">&#8226; {p}</li>
        ))}
      </ul>
    </div>
  )
}

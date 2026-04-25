import { useFavorites } from "@/api/favorites"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { FavoriteButton } from "./FavoriteButton"
import { formatPrice, scoreColor } from "@/lib/utils"

export function ComparisonPage() {
  const { data: favorites, isLoading } = useFavorites()

  if (isLoading) return <LoadingSpinner />

  if (!favorites || favorites.length === 0) {
    return (
      <div className="py-12 text-center">
        <h1 className="mb-2 text-2xl font-bold">Compare Listings</h1>
        <p className="text-muted-foreground">
          No favorites yet. Star listings from any project to compare them here.
        </p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Compare Listings ({favorites.length})</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {favorites.map((listing) => (
          <Card key={listing.id}>
            {listing.thumbnail_url && (
              <img
                src={listing.thumbnail_url}
                alt={listing.title}
                className="h-40 w-full rounded-t-lg object-cover"
              />
            )}
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <CardTitle className="line-clamp-2 text-sm">{listing.title}</CardTitle>
                <FavoriteButton listingId={listing.id} />
              </div>
              {listing.location && (
                <p className="text-xs text-muted-foreground">{listing.location}</p>
              )}
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="text-lg font-bold">{formatPrice(listing.price)}</div>
              <div className="grid grid-cols-2 gap-1 text-xs">
                <span>EUR/m²: {listing.price_per_m2 ? Math.round(listing.price_per_m2) : "—"}</span>
                <span>Size: {listing.size_m2 ? `${listing.size_m2} m²` : "—"}</span>
                <span>Rooms: {listing.rooms || "—"}</span>
                <span>Floor: {listing.floor || "—"}</span>
                <span>Year: {listing.year_built || "—"}</span>
                <span>
                  Score:{" "}
                  {listing.basic_score != null ? (
                    <span className={`rounded px-1 ${scoreColor(listing.basic_score)}`}>
                      {Math.round(listing.basic_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </span>
              </div>
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
              <a
                href={listing.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground underline"
                onClick={(e) => e.stopPropagation()}
              >
                View listing
              </a>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

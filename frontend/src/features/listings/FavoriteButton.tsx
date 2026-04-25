import { Star } from "lucide-react"
import { useFavorites, useToggleFavorite } from "@/api/favorites"
import { Button } from "@/components/ui/button"

export function FavoriteButton({ listingId }: { listingId: string }) {
  const { data: favorites } = useFavorites()
  const toggleFavorite = useToggleFavorite()

  const isFavorited = favorites?.some((f) => f.id === listingId) ?? false

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        toggleFavorite.mutate({ listingId, isFavorited })
      }}
    >
      <Star
        className={`h-4 w-4 ${isFavorited ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
      />
    </Button>
  )
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"
import type { ListingSummary } from "./listings"

export function useFavorites() {
  return useQuery({
    queryKey: ["favorites"],
    queryFn: async () => {
      const res = await api.get<ListingSummary[]>("/favorites")
      return res.data
    },
  })
}

export function useToggleFavorite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      listingId,
      isFavorited,
    }: {
      listingId: string
      isFavorited: boolean
    }) => {
      if (isFavorited) {
        await api.delete(`/favorites/${listingId}`)
      } else {
        await api.post(`/favorites/${listingId}`)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] })
    },
  })
}

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"

export interface ListingSummary {
  id: string
  external_id: string
  url: string
  title: string
  location: string | null
  price: number | null
  price_per_m2: number | null
  size_m2: number | null
  rooms: string | null
  floor: string | null
  year_built: number | null
  status: string
  basic_score: number | null
  ai_score: number | null
  first_seen_at: string | null
  images: string[]
  thumbnail_url: string | null
}

export interface ListingDetail extends ListingSummary {
  description: string | null
  energy_class: string | null
  year_renovated: number | null
  land_size_m2: number | null
  agency: string | null
  ai_score: number | null
  ai_analysis: string | null
  price_history: { price: string; date: string }[]
  consecutive_misses: number
  last_seen_at: string | null
  marked_sold_at: string | null
  created_at: string
}

export interface PaginatedListings {
  items: ListingSummary[]
  total: number
  page: number
  per_page: number
}

export interface ListingFilters {
  status?: string
  min_price?: number
  max_price?: number
  min_size?: number
  max_size?: number
  sort_by?: string
  sort_order?: "asc" | "desc"
  page?: number
  per_page?: number
}

export function useListings(projectId: string, filters: ListingFilters = {}) {
  return useQuery({
    queryKey: ["listings", projectId, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.status) params.set("status", filters.status)
      if (filters.min_price != null) params.set("min_price", String(filters.min_price))
      if (filters.max_price != null) params.set("max_price", String(filters.max_price))
      if (filters.min_size != null) params.set("min_size", String(filters.min_size))
      if (filters.max_size != null) params.set("max_size", String(filters.max_size))
      if (filters.sort_by) params.set("sort_by", filters.sort_by)
      if (filters.sort_order) params.set("sort_order", filters.sort_order)
      if (filters.page) params.set("page", String(filters.page))
      if (filters.per_page) params.set("per_page", String(filters.per_page))

      const res = await api.get<PaginatedListings>(
        `/projects/${projectId}/listings?${params.toString()}`
      )
      return res.data
    },
    enabled: !!projectId,
    placeholderData: keepPreviousData,
  })
}

export function useListing(projectId: string, listingId: string) {
  return useQuery({
    queryKey: ["listing", projectId, listingId],
    queryFn: async () => {
      const res = await api.get<ListingDetail>(
        `/projects/${projectId}/listings/${listingId}`
      )
      return res.data
    },
    enabled: !!projectId && !!listingId,
  })
}

export function useScoreListing() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ projectId, listingId }: { projectId: string; listingId: string }) => {
      const res = await api.post<{ ai_score: number; ai_analysis: string }>(
        `/projects/${projectId}/listings/${listingId}/score`
      )
      return res.data
    },
    onSuccess: (_, { projectId, listingId }) => {
      queryClient.invalidateQueries({ queryKey: ["listing", projectId, listingId] })
    },
  })
}

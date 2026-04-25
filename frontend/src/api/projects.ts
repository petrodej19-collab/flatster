import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"

export interface ProjectFilters {
  transaction: string
  region: string
  sub_region?: string | null
  property_type: string
  rooms?: string[] | null
  price_from?: number | null
  price_to?: number | null
  size_from?: number | null
  size_to?: number | null
  year_from?: number | null
  year_to?: number | null
}

export interface Project {
  id: string
  name: string
  filters: ProjectFilters
  scrape_url: string
  is_active: boolean
  ai_scoring_enabled: boolean
  last_scraped_at: string | null
  created_at: string
  listing_count: number
}

export interface ScrapeResult {
  listings_found: number
  new: number
  updated: number
  marked_sold: number
}

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await api.get<Project[]>("/projects")
      return res.data
    },
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: async () => {
      const res = await api.get<Project>(`/projects/${id}`)
      return res.data
    },
    enabled: !!id,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: { name: string; filters: ProjectFilters }) => {
      const res = await api.post<Project>("/projects", data)
      return res.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: { id: string } & Partial<{ name: string; filters: ProjectFilters; is_active: boolean }>) => {
      const res = await api.patch<Project>(`/projects/${id}`, data)
      return res.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
      queryClient.invalidateQueries({ queryKey: ["projects", data.id] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export function useTriggerScrape() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post<ScrapeResult>(`/projects/${id}/scrape`)
      return res.data
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["projects", id] })
      queryClient.invalidateQueries({ queryKey: ["listings", id] })
    },
  })
}

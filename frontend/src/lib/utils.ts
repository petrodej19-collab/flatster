import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return "N/A"
  return new Intl.NumberFormat("sl-SI", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(price)
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "N/A"
  return new Intl.DateTimeFormat("sl-SI", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date))
}

export function formatRelativeTime(date: string | null | undefined): string {
  if (!date) return "Never"
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffHours < 1) return "Just now"
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(date)
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "bg-gray-100 text-gray-600"
  if (score >= 70) return "bg-green-100 text-green-700"
  if (score >= 40) return "bg-yellow-100 text-yellow-700"
  return "bg-red-100 text-red-700"
}

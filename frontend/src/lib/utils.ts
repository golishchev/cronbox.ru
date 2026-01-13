import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getAssetUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined
  const baseUrl = import.meta.env.VITE_API_URL
  if (baseUrl && !path.startsWith('http')) {
    // Remove /v1 from API URL to get base server URL
    const serverUrl = baseUrl.replace(/\/v1$/, '')
    return `${serverUrl}${path}`
  }
  return path
}

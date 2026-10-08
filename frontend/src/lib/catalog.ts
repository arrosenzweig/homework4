import raw from '../data/products.json'
import type { Product } from '../types'

/**
 * Local catalogue snapshot exported from data/campus_customs.db.
 *
 * The FastAPI backend in `backend/main.py` serves the same shape at
 * GET /api/products. Set VITE_API_URL to read from it instead of this file.
 */
const products = raw as Product[]

const API = import.meta.env.VITE_API_URL as string | undefined

export async function fetchProducts(): Promise<Product[]> {
  if (!API) return products
  try {
    const res = await fetch(`${API}/api/products`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as Product[]
  } catch {
    // Backend not running — fall back to the bundled snapshot.
    return products
  }
}

export function allProducts(): Product[] {
  return products
}

export function getProduct(id: string): Product | undefined {
  return products.find((p) => p.id === id)
}

export function categories(): string[] {
  return [...new Set(products.map((p) => p.category))].sort()
}

export function relatedProducts(product: Product, limit = 4): Product[] {
  return products
    .filter((p) => p.id !== product.id && p.category === product.category)
    .slice(0, limit)
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

export interface CollectionGroup {
  type: string
  names: string[]
}

/** Collections that actually have products, grouped by type, each sorted. */
export function collectionGroups(): CollectionGroup[] {
  const byType = new Map<string, Set<string>>()
  for (const p of products) {
    if (!p.collection || !p.collectionType) continue
    if (!byType.has(p.collectionType)) byType.set(p.collectionType, new Set())
    byType.get(p.collectionType)!.add(p.collection)
  }
  // Residential colleges first: more products, and the more common ask.
  const order = ['Residential College', 'Graduate & Professional School']
  return [...byType.entries()]
    .sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]))
    .map(([type, names]) => ({ type, names: [...names].sort() }))
}

export function productsInCollection(name: string) {
  return products.filter((p) => p.collection === name)
}

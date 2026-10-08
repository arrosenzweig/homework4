import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { Product, Size } from '../types'
import { SIZES } from '../types'

/**
 * The products the agent most recently matched.
 *
 * The chat widget publishes here; <AgentMatches /> on the Home and Products
 * pages subscribes. That is what makes a chat answer show up on the site
 * itself rather than only inside the panel.
 */

/** The card shape the API sends (snake_case, from models.ProductCard). */
export interface ApiProductCard {
  id: string
  name: string
  category: string
  garment_type: string
  description: string
  price: number
  image: string
  colors: string[]
  sizes_in_stock: string[]
  total_stock: number
  in_stock: boolean
  url: string
}

/**
 * Convert an API card into the same `Product` the catalogue grid uses.
 *
 * This adapter is the whole trick behind the "cards still open the detail page"
 * requirement: once an agent match is a Product, it renders through the exact
 * same <ProductCard> component as every other card on the site, so it inherits
 * the same <Link to={`/products/${id}`}> with no second code path to keep in sync.
 *
 * The per-size counts the grid shows are not sent over chat, so stock is
 * reconstructed as present/absent from `sizes_in_stock`. The detail page reads
 * real counts from the catalogue by id, so nothing downstream depends on this.
 */
export function toProduct(card: ApiProductCard): Product {
  const stock = Object.fromEntries(
    SIZES.map((s) => [s, card.sizes_in_stock.includes(s) ? 1 : 0]),
  ) as Record<Size, number>

  return {
    id: card.id,
    name: card.name,
    garmentType: card.garment_type,
    category: card.category,
    description: card.description,
    colors: card.colors,
    tags: [],
    image: card.image,
    price: card.price,
    stock,
    totalStock: card.total_stock,
  }
}

interface AgentResultsValue {
  products: Product[]
  query: string | null
  publish: (cards: ApiProductCard[], query: string) => void
  clear: () => void
}

const AgentResultsContext = createContext<AgentResultsValue | null>(null)

const STORE_KEY = 'cc_agent_matches'

interface Stored {
  products: Product[]
  query: string | null
}

function readStore(): Stored {
  try {
    const raw = sessionStorage.getItem(STORE_KEY)
    if (raw) return JSON.parse(raw) as Stored
  } catch {
    /* unreadable or disabled storage — start empty */
  }
  return { products: [], query: null }
}

export function AgentResultsProvider({ children }: { children: React.ReactNode }) {
  // Seed from sessionStorage so a page refresh does not drop the matches the
  // shopper just asked for. Cleared when the tab closes, which is the right
  // lifetime for "what I was just looking at".
  const initial = readStore()
  const [products, setProducts] = useState<Product[]>(initial.products)
  const [query, setQuery] = useState<string | null>(initial.query)

  useEffect(() => {
    try {
      if (products.length === 0) sessionStorage.removeItem(STORE_KEY)
      else sessionStorage.setItem(STORE_KEY, JSON.stringify({ products, query }))
    } catch {
      /* storage full or disabled — the page still works, it just will not persist */
    }
  }, [products, query])

  const publish = useCallback((cards: ApiProductCard[], q: string) => {
    // An answer with no products (a greeting, a decline) must not wipe the
    // last real result set off the page.
    if (cards.length === 0) return
    setProducts(cards.map(toProduct))
    setQuery(q)
  }, [])

  const clear = useCallback(() => {
    setProducts([])
    setQuery(null)
  }, [])

  const value = useMemo(
    () => ({ products, query, publish, clear }),
    [products, query, publish, clear],
  )

  return <AgentResultsContext.Provider value={value}>{children}</AgentResultsContext.Provider>
}

export function useAgentResults(): AgentResultsValue {
  const ctx = useContext(AgentResultsContext)
  if (!ctx) throw new Error('useAgentResults must be used inside <AgentResultsProvider>')
  return ctx
}

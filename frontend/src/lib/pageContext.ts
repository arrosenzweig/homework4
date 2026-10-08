import { useLocation, useParams } from 'react-router-dom'
import { getProduct, allProducts, categories } from './catalog'
import { buildVocabulary, normalizeQuery } from './searchTerms'

/**
 * What the shopper is looking at, collected from the router and sent with every
 * chat turn so the agent can resolve "this one" without being told.
 *
 * Deliberately carries ids and filters, never prices or stock counts. The agent
 * uses this to work out *which* product is meant and then asks the database for
 * the facts — so a stale page cannot put a wrong number in an answer.
 */
export interface PageContext {
  route: string
  page_type: 'home' | 'products' | 'product_detail' | 'account' | 'other'
  product_id?: string | null
  product_name?: string | null
  category?: string | null
  collection?: string | null
  search_query?: string | null
  visible_product_ids: string[]
}

const MAX_VISIBLE = 12

export function usePageContext(): PageContext {
  const location = useLocation()
  const params = useParams<{ id?: string }>()
  const path = location.pathname

  if (path.startsWith('/products/') && params.id) {
    const product = getProduct(params.id)
    return {
      route: path,
      page_type: 'product_detail',
      product_id: params.id,
      product_name: product?.name ?? null,
      visible_product_ids: [params.id],
    }
  }

  if (path === '/products') {
    const search = new URLSearchParams(location.search)
    const category = search.get('category')
    const known = categories()
    const active = category && known.includes(category) ? category : null
    const q = search.get('q')?.trim() || null
    const sort = search.get('sort')
    const size = search.get('size')
    const collection = search.get('collection')
    const maxPrice = search.get('maxPrice') ? Number(search.get('maxPrice')) : null
    const inStockOnly = search.get('inStock') === '1'

    // Mirrors the grid's own filtering and sorting, so the ids listed here are
    // genuinely the ones on screen, in the order the shopper sees them. That is
    // what makes "the third one" resolvable.
    const all = allProducts()
    const terms = q ? normalizeQuery(q, buildVocabulary(all)) : []
    const filtered = all.filter((p) => {
      if (active && p.category !== active) return false
      if (collection && p.collection !== collection) return false
      if (maxPrice !== null && p.price > maxPrice) return false
      if (size && p.stock[size as keyof typeof p.stock] === 0) return false
      if (inStockOnly && p.totalStock === 0) return false
      if (terms.length === 0) return true
      const haystack = [p.name, p.description, p.category, p.tags.join(' '), p.colors.join(' ')]
        .join(' ')
        .toLowerCase()
      return terms.every((t) => haystack.includes(t))
    })

    if (sort === 'price-asc') filtered.sort((a, b) => a.price - b.price)
    else if (sort === 'price-desc') filtered.sort((a, b) => b.price - a.price)
    else if (sort === 'name') filtered.sort((a, b) => a.name.localeCompare(b.name))

    return {
      route: path + location.search,
      page_type: 'products',
      category: active,
      collection,
      search_query: q,
      visible_product_ids: filtered.slice(0, MAX_VISIBLE).map((p) => p.id),
    }
  }

  if (path === '/') {
    return {
      route: path,
      page_type: 'home',
      visible_product_ids: allProducts()
        .filter((p) => p.totalStock > 0)
        .slice(0, 4)
        .map((p) => p.id),
    }
  }

  if (path === '/login' || path === '/create-account') {
    return { route: path, page_type: 'account', visible_product_ids: [] }
  }

  return { route: path, page_type: 'other', visible_product_ids: [] }
}

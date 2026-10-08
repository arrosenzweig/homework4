import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import AgentMatches from '../components/AgentMatches'
import ProductCard from '../components/ProductCard'
import { allProducts, categories, collectionGroups } from '../lib/catalog'
import { buildVocabulary, normalizeQuery } from '../lib/searchTerms'
import { SIZES, type Size } from '../types'

type Sort = 'featured' | 'price-asc' | 'price-desc' | 'name'

const SORTS: { value: Sort; label: string }[] = [
  { value: 'featured', label: 'Featured' },
  { value: 'price-asc', label: 'Price: low to high' },
  { value: 'price-desc', label: 'Price: high to low' },
  { value: 'name', label: 'Name A–Z' },
]

/**
 * All filter state lives in the URL rather than component state.
 *
 * That makes a filtered view shareable and bookmarkable, survives a refresh,
 * and — the reason it matters here — lets usePageContext() read exactly what
 * the shopper is looking at, so the assistant sees the same filters they do.
 */
export default function Products() {
  const products = allProducts()
  const cats = categories()
  const groups = collectionGroups()
  const [params, setParams] = useSearchParams()

  const active = params.get('category') ?? 'All'
  const query = params.get('q') ?? ''
  const sort = (params.get('sort') as Sort) ?? 'featured'
  const size = params.get('size') as Size | null
  const collection = params.get('collection')
  const maxPrice = params.get('maxPrice') ? Number(params.get('maxPrice')) : null
  const inStockOnly = params.get('inStock') === '1'

  // Built once; the same normalisation the backend applies, so the grid and the
  // assistant agree on what 'grey' or a typo means.
  const vocabulary = useMemo(() => buildVocabulary(products), [products])

  const prices = products.map((p) => p.price)
  const floor = Math.floor(Math.min(...prices))
  const ceiling = Math.ceil(Math.max(...prices))

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      if (v === null || v === '') next.delete(k)
      else next.set(k, v)
    }
    setParams(next)
  }

  const visible = useMemo(() => {
    const terms = query.trim() ? normalizeQuery(query, vocabulary) : []

    const filtered = products.filter((p) => {
      if (active !== 'All' && p.category !== active) return false
      if (collection && p.collection !== collection) return false
      if (maxPrice !== null && p.price > maxPrice) return false
      if (size && p.stock[size] === 0) return false
      if (inStockOnly && p.totalStock === 0) return false
      if (terms.length === 0) return true

      const haystack = [
        p.name,
        p.description,
        p.category,
        p.tags.join(' '),
        p.colors.join(' '),
      ]
        .join(' ')
        .toLowerCase()
      // Every term must appear, so extra words narrow rather than widen.
      return terms.every((t) => haystack.includes(t))
    })

    const sorted = [...filtered]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price)
    else if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price)
    else if (sort === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name))
    return sorted
  }, [products, active, collection, query, vocabulary, sort, size, maxPrice, inStockOnly])

  const filtersOn =
    active !== 'All' ||
    collection !== null ||
    query !== '' ||
    size !== null ||
    maxPrice !== null ||
    inStockOnly

  return (
    <div className="page">
      <AgentMatches />

      <header className="page-head">
        <h1>Products</h1>
        <p className="muted">
          Every piece in the shop, straight from our catalogue. Pick one to see sizes and what we
          have on the shelf.
        </p>
      </header>

      <div className="toolbar">
        <div className="chips">
          {['All', ...cats].map((c) => (
            <button
              key={c}
              onClick={() => update({ category: c === 'All' ? null : c })}
              className={c === active ? 'chip chip-active' : 'chip'}
              aria-pressed={c === active}
            >
              {c}
            </button>
          ))}
        </div>
        <input
          className="search"
          value={query}
          onChange={(e) => update({ q: e.target.value })}
          placeholder="Search by name, color, or team..."
          aria-label="Search products"
        />
      </div>

      <div className="filters">
        <label className="filter">
          <span className="filter-label">Sort</span>
          <select value={sort} onChange={(e) => update({ sort: e.target.value })}>
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>

        <label className="filter filter-wide">
          <span className="filter-label">College or school</span>
          <select
            value={collection ?? ''}
            onChange={(e) => update({ collection: e.target.value || null })}
          >
            <option value="">All of Yale</option>
            {groups.map((g) => (
              <optgroup key={g.type} label={g.type === 'Residential College' ? 'Residential Colleges' : 'Graduate & Professional Schools'}>
                {g.names.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        <label className="filter">
          <span className="filter-label">Size</span>
          <select value={size ?? ''} onChange={(e) => update({ size: e.target.value || null })}>
            <option value="">Any size</option>
            {SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className="filter filter-range">
          <span className="filter-label">
            Max price: <strong>${maxPrice ?? ceiling}</strong>
          </span>
          <input
            type="range"
            min={floor}
            max={ceiling}
            step={1}
            value={maxPrice ?? ceiling}
            onChange={(e) =>
              update({
                maxPrice: Number(e.target.value) >= ceiling ? null : e.target.value,
              })
            }
          />
        </label>

        <label className="filter filter-check">
          <input
            type="checkbox"
            checked={inStockOnly}
            onChange={(e) => update({ inStock: e.target.checked ? '1' : null })}
          />
          <span>In stock only</span>
        </label>

        {filtersOn && (
          <button className="btn btn-ghost btn-sm" onClick={() => setParams({})}>
            Reset
          </button>
        )}
      </div>

      <p className="count" role="status">
        {visible.length} {visible.length === 1 ? 'product' : 'products'}
        {collection && ` for ${collection}`}
        {size && ` available in ${size}`}
        {maxPrice !== null && ` under $${maxPrice + 1}`}
      </p>

      {visible.length === 0 ? (
        <p className="empty">
          {collection
            ? `We don't carry anything for ${collection} with those filters yet.`
            : 'Nothing matched those filters. Try widening the price or clearing the size.'}
        </p>
      ) : (
        <div className="grid grid-3">
          {visible.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  )
}

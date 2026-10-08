import { useEffect, useRef } from 'react'
import ProductCard from './ProductCard'
import { useAgentResults } from '../lib/agentResults'

/**
 * The products the shopping assistant just matched, rendered on the page.
 *
 * Uses <ProductCard>, the same component the catalogue grid uses, so these
 * cards behave identically to every other card on the site — including opening
 * the single-item detail page when clicked.
 */
export default function AgentMatches() {
  const { products, query, clear } = useAgentResults()
  const ref = useRef<HTMLElement>(null)
  const seen = useRef<string>('')

  // Scroll the section into view the first time a given result set appears,
  // so a chat answer visibly lands on the page.
  useEffect(() => {
    const key = products.map((p) => p.id).join(',')
    if (products.length > 0 && key !== seen.current) {
      seen.current = key
      ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [products])

  if (products.length === 0) return null

  return (
    <section className="agent-matches" ref={ref} aria-label="Matches from the shopping assistant">
      <div className="agent-matches-head">
        <div>
          <p className="eyebrow">From your conversation</p>
          <h2>
            {query ? <>Matches for &ldquo;{query}&rdquo;</> : 'Picked by the assistant'}
          </h2>
        </div>
        <button className="btn btn-ghost" onClick={clear}>
          Clear
        </button>
      </div>

      <div className="grid grid-4">
        {products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
    </section>
  )
}

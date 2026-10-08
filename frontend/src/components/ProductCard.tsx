import { Link } from 'react-router-dom'
import type { Product } from '../types'
import { formatPrice } from '../lib/catalog'

export default function ProductCard({ product }: { product: Product }) {
  const soldOut = product.totalStock === 0
  // Honest urgency only: these thresholds read the real inventory rows, so a
  // "Low stock" badge always means the shelf is genuinely thin. Nothing here
  // is manufactured scarcity.
  const sizesLeft = Object.values(product.stock).filter((q) => q > 0).length
  const lowStock = !soldOut && product.totalStock <= 12
  const fewSizes = !soldOut && !lowStock && sizesLeft <= 2

  return (
    <Link to={`/products/${product.id}`} className="card">
      <div className="card-media">
        <img src={product.image} alt={product.name} loading="lazy" />
        {soldOut && <span className="badge badge-out">Sold out</span>}
        {lowStock && <span className="badge badge-low">Low stock</span>}
        {fewSizes && (
          <span className="badge badge-sizes">
            {sizesLeft} size{sizesLeft === 1 ? '' : 's'} left
          </span>
        )}
      </div>
      <div className="card-body">
        <h3 className="card-name">{product.name}</h3>
        <p className="card-type">{product.category}</p>
        <p className="card-desc">{product.description}</p>
        <div className="card-foot">
          <span className="card-price">{formatPrice(product.price)}</span>
          <span className="card-cta">View details &rarr;</span>
        </div>
      </div>
    </Link>
  )
}

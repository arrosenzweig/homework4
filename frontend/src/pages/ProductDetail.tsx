import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getProduct, relatedProducts, formatPrice } from '../lib/catalog'
import { SIZES, type Size } from '../types'

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>()
  const product = id ? getProduct(id) : undefined
  const [size, setSize] = useState<Size | null>(null)

  if (!product) {
    return (
      <div className="page page-narrow">
        <h1>We couldn&rsquo;t find that one</h1>
        <p className="muted">That product isn&rsquo;t in the catalogue.</p>
        <Link to="/products" className="btn btn-primary">
          Back to products
        </Link>
      </div>
    )
  }

  const onHand = size ? product.stock[size] : null
  const soldOut = product.totalStock === 0
  const related = relatedProducts(product)

  return (
    <div className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>
          {product.category}
        </Link>
        <span aria-hidden="true">/</span>
        <span className="crumb-current">{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-media">
          <img src={product.image} alt={product.name} />
        </div>

        <div className="detail-info">
          <p className="eyebrow">{product.garmentType}</p>
          <h1>{product.name}</h1>
          {product.collection && (
            <p className="detail-collection">
              <Link to={`/products?collection=${encodeURIComponent(product.collection)}`}>
                {product.collection}
              </Link>
              <span className="detail-collection-type">{product.collectionType}</span>
            </p>
          )}
          <p className="detail-price">{formatPrice(product.price)}</p>

          <p className="detail-desc">{product.description}</p>

          <div className="field">
            <span className="field-label">Colors</span>
            <div className="chips chips-static">
              {product.colors.map((c) => (
                <span key={c} className="chip chip-plain">
                  {c}
                </span>
              ))}
            </div>
          </div>

          <div className="field">
            <span className="field-label">Size</span>
            <div className="sizes">
              {SIZES.map((s) => {
                const qty = product.stock[s]
                const out = qty === 0
                return (
                  <button
                    key={s}
                    disabled={out}
                    onClick={() => setSize(s)}
                    className={`size ${size === s ? 'size-active' : ''} ${out ? 'size-out' : ''}`}
                    title={out ? `${s} — out of stock` : `${s} — ${qty} in stock`}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="stock-line">
            {soldOut ? (
              <span className="stock stock-none">Sold out in every size</span>
            ) : size === null ? (
              <span className="stock stock-hint">
                Select a size to see what we have on the shelf.
              </span>
            ) : onHand && onHand > 5 ? (
              <span className="stock stock-ok">In stock &mdash; {onHand} available in {size}</span>
            ) : (
              <span className="stock stock-low">Only {onHand} left in {size}</span>
            )}
          </div>

          <button className="btn btn-primary btn-lg btn-block" disabled={!size || soldOut}>
            {soldOut ? 'Sold out' : size ? `Add ${size} to bag` : 'Select a size'}
          </button>

          <table className="stock-table">
            <caption>Stock by size</caption>
            <thead>
              <tr>
                {SIZES.map((s) => (
                  <th key={s} scope="col">
                    {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                {SIZES.map((s) => (
                  <td key={s} className={product.stock[s] === 0 ? 'zero' : undefined}>
                    {product.stock[s]}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>

          <div className="field">
            <span className="field-label">Tags</span>
            <p className="tags">{product.tags.join(' · ')}</p>
          </div>
        </div>
      </div>

      {related.length > 0 && (
        <section className="section">
          <h2>More {product.category.toLowerCase()}</h2>
          <div className="grid grid-4">
            {related.map((p) => (
              <Link key={p.id} to={`/products/${p.id}`} className="card">
                <div className="card-media">
                  <img src={p.image} alt={p.name} loading="lazy" />
                </div>
                <div className="card-body">
                  <h3 className="card-name">{p.name}</h3>
                  <span className="card-price">{formatPrice(p.price)}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

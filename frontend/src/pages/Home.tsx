import { Link } from 'react-router-dom'
import AgentMatches from '../components/AgentMatches'
import { allProducts, formatPrice, collectionGroups } from '../lib/catalog'

/*
 * Copy on this page is drawn from yalebulldogblue.com (Yale Bulldog Blue by
 * Campus Customs): the taglines, category language and store details are the
 * shop's own wording.
 */
export default function Home() {
  const products = allProducts()
  const featured = products.filter((p) => p.totalStock > 0).slice(0, 4)
  const groups = collectionGroups()

  return (
    <div className="page">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Officially Licensed Merchandise</p>
          <h1>Shop Bulldog Blue</h1>
          <p className="lede">Casual comfort, classic Bulldog pride.</p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-primary btn-lg">
              Shop all {products.length} products
            </Link>
            <Link to="/about" className="btn btn-ghost btn-lg">
              Our story
            </Link>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="hero-tile tile-y">Y</div>
          <div className="hero-tile tile-text">
            <span>Big Pride,</span>
            <span>Big Yale</span>
          </div>
        </div>
      </section>

      <AgentMatches />

      <section className="strip">
        <div>
          <strong>Add a touch of Bulldog pride</strong>
          <p>Yale Official Licensed apparel, printed and embroidered in New Haven.</p>
        </div>
        <div>
          <strong>Shop comfy layers</strong>
          <p>Crewnecks, hoodies, quarter-zips and jackets for every season on campus.</p>
        </div>
        <div>
          <strong>Come visit us!</strong>
          <p>57 Broadway, New Haven CT, 06511 &mdash; right across from campus.</p>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Long sleeves we love</h2>
          <Link to="/products" className="link-more">
            View all &rarr;
          </Link>
        </div>
        <div className="grid grid-4">
          {featured.map((p) => (
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

      <section className="section">
        <h2>Top it off!</h2>
        <p className="muted">Shop by garment.</p>
        <div className="chips">
          {['Crewnecks', 'Hoodies', 'T-Shirts', 'Quarter-Zips', 'Jackets', 'Long Sleeves'].map(
            (c) => (
              <Link key={c} to={`/products?category=${encodeURIComponent(c)}`} className="chip">
                {c}
              </Link>
            ),
          )}
        </div>
      </section>

      {groups.map((g) => (
        <section className="section" key={g.type}>
          <h2>
            {g.type === 'Residential College'
              ? 'Shop your residential college'
              : 'Graduate & professional schools'}
          </h2>
          <p className="muted">
            {g.type === 'Residential College'
              ? 'Crewnecks, quarter-zips and tees for the colleges we stock.'
              : 'Gear for the schools across campus.'}
          </p>
          <div className="chips">
            {g.names.map((n) => (
              <Link
                key={n}
                to={`/products?collection=${encodeURIComponent(n)}`}
                className="chip chip-collection"
              >
                {n}
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

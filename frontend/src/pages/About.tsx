import { Link } from 'react-router-dom'

/*
 * Copy on this page is drawn from yalebulldogblue.com and Campus Customs'
 * own published description of the business (family-run since 1975, 57
 * Broadway, co-owners Joel and Jeremy Cobden).
 */
export default function About() {
  return (
    <div className="page page-narrow">
      <p className="eyebrow">Yale Bulldog Blue by Campus Customs</p>
      <h1>Come visit us!</h1>

      <p className="lede">
        Campus Customs is a family-run company in New Haven, right across from Yale University.
        We have been in business since 1975, when we opened as a memorabilia shop.
      </p>

      <p>
        Since then we have grown well past the storefront. Today we handle large-scale screen
        printing, embroidery, graphic design, and complete event merchandise services &mdash;
        alongside the Officially Licensed Yale apparel you will find on these pages.
      </p>

      <p>
        Co-owners Joel and Jeremy Cobden carry forward their father&rsquo;s tradition of
        exceptional customer service and ethical business practices. That is the part of the
        business that has not changed since 1975.
      </p>

      <div className="about-grid">
        <div className="about-fact">
          <strong>Since</strong>
          <span>1975</span>
        </div>
        <div className="about-fact">
          <strong>Find us</strong>
          <span>
            57 Broadway
            <br />
            New Haven, CT 06511
          </span>
        </div>
        <div className="about-fact">
          <strong>Licensing</strong>
          <span>Yale Official Licensed</span>
        </div>
      </div>

      <h2>What we make</h2>
      <p>
        Add a touch of Bulldog pride: crewnecks, hoodies, quarter-zips, jackets and tees for the
        residential colleges, 20+ varsity teams, the graduate and professional schools, and the
        relatives who cheer from the stands. Casual comfort, classic Bulldog pride.
      </p>

      <p>
        <Link to="/products" className="btn btn-primary">
          Shop the collection
        </Link>
      </p>

      <p className="source-note">
        Store history, location and brand language on this page come from{' '}
        <a href="https://yalebulldogblue.com" target="_blank" rel="noreferrer">
          yalebulldogblue.com
        </a>{' '}
        and Campus Customs&rsquo; published business description.
      </p>
    </div>
  )
}

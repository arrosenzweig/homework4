import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { upcomingEvents, formatEventDate } from '../data/athletics'

const STORE_KEY = 'cc_ticker_hidden'

/**
 * A scrolling strip of upcoming Yale Athletics home events, fixed to the
 * bottom of every page.
 *
 * Each event is a button, not decoration: clicking opens the catalogue
 * filtered to gear for that sport. The animation pauses on hover and on
 * keyboard focus so the items can actually be read and clicked, and the whole
 * strip respects prefers-reduced-motion.
 */
export default function AthleticsTicker() {
  const navigate = useNavigate()
  const [hidden, setHidden] = useState(false)
  const events = upcomingEvents()

  useEffect(() => {
    try {
      setHidden(sessionStorage.getItem(STORE_KEY) === '1')
    } catch {
      /* storage unavailable */
    }
  }, [])

  useEffect(() => {
    document.body.classList.toggle('has-ticker', !hidden && events.length > 0)
    return () => document.body.classList.remove('has-ticker')
  }, [hidden, events.length])

  if (hidden || events.length === 0) return null

  function dismiss() {
    setHidden(true)
    try {
      sessionStorage.setItem(STORE_KEY, '1')
    } catch {
      /* storage unavailable */
    }
  }

  // Rendered twice so the strip can loop seamlessly; the copy is hidden from
  // assistive tech so events are not announced twice.
  const row = (ariaHidden: boolean) => (
    <ul className="ticker-track" aria-hidden={ariaHidden || undefined}>
      {events.map((e, i) => (
        <li key={`${e.date}-${e.sport}-${i}`}>
          <button
            className="ticker-item"
            onClick={() => navigate(`/products?q=${encodeURIComponent(e.shop)}`)}
            tabIndex={ariaHidden ? -1 : 0}
          >
            <span className="ticker-date">{formatEventDate(e.date)}</span>
            <span className="ticker-sport">{e.sport}</span>
            <span className="ticker-vs">{e.home ? 'vs' : 'at'}</span>
            <span className="ticker-opp">{e.opponent}</span>
            {e.home && <span className="ticker-home">Home</span>}
          </button>
        </li>
      ))}
    </ul>
  )

  return (
    <aside className="ticker" aria-label="Upcoming Yale Athletics events">
      <span className="ticker-label" aria-hidden="true">
        Bulldogs
      </span>

      <div className="ticker-viewport">
        {row(false)}
        {row(true)}
      </div>

      <button className="ticker-dismiss" onClick={dismiss} aria-label="Hide the athletics schedule">
        &times;
      </button>
    </aside>
  )
}

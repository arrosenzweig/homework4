import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAgentResults, type ApiProductCard } from '../lib/agentResults'
import { useAuth } from '../lib/auth'
import { usePageContext } from '../lib/pageContext'

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

interface Turn {
  role: 'user' | 'assistant'
  content: string
  products?: ApiProductCard[]
}

const GREETING: Turn = {
  role: 'assistant',
  content:
    "Hi! I'm the Bulldog Blue shopping assistant. Ask me about sizes, stock, or what to get your Yale grad.",
}

const SUGGESTIONS = ['What hoodies do you have?', 'Something warm under $60', 'Gifts for a Yale dad']

export default function ChatWidget() {
  const { publish } = useAgentResults()
  const { user } = useAuth()
  const page = usePageContext()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [restored, setRestored] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const fabRef = useRef<HTMLButtonElement>(null)
  const [announcement, setAnnouncement] = useState('')

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns, open, pending])

  // Escape closes the panel, the convention for any dismissable overlay.
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  // Move focus into the panel when it opens and back to the launcher when it
  // closes, so a keyboard user is never left with focus on a hidden element.
  useEffect(() => {
    if (open) inputRef.current?.focus()
    else fabRef.current?.focus()
  }, [open])

  // Restore the saved conversation when a signed-in shopper returns, and drop it
  // again on logout so the next person at this browser starts clean.
  useEffect(() => {
    if (!user) {
      setTurns([GREETING])
      setRestored(false)
      return
    }
    if (restored) return

    const token = localStorage.getItem('cc_token')
    if (!token) return

    fetch(`${API}/api/chat/history`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('history unavailable'))))
      .then((data: { turns: Turn[]; saved: boolean }) => {
        if (data.turns.length > 0) setTurns([GREETING, ...data.turns])
      })
      .catch(() => undefined)
      .finally(() => setRestored(true))
  }, [user, restored])

  async function clearConversation() {
    const token = localStorage.getItem('cc_token')
    setTurns([GREETING])
    setAnnouncement('Conversation cleared.')
    if (user && token) {
      await fetch(`${API}/api/chat/history`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => undefined)
    }
  }

  async function send(text: string) {
    const message = text.trim()
    if (!message || pending) return

    // Send prior turns so the agent can resolve "it" and "that one".
    const history = turns
      .filter((t) => t !== GREETING)
      .map((t) => ({ role: t.role, content: t.content }))

    setTurns((t) => [...t, { role: 'user', content: message }])
    setDraft('')
    setPending(true)

    try {
      const token = localStorage.getItem('cc_token')
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Sent when signed in, so the server knows who to greet and whose
          // history to record. Absent for guests, who chat without being saved.
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message, history, page }),
      })
      if (!res.ok) {
        let detail = 'failed'
        try {
          const body = await res.json()
          if (typeof body?.detail === 'string') detail = body.detail
        } catch {
          /* no JSON body */
        }
        throw new Error(detail)
      }
      const data = (await res.json()) as { reply: string; products: ApiProductCard[] }
      setTurns((t) => [
        ...t,
        { role: 'assistant', content: data.reply, products: data.products },
      ])
      setAnnouncement(
        data.products.length > 0
          ? `${data.reply} Showing ${data.products.length} products.`
          : data.reply,
      )
      // Hand the structured matches to the page so they render as full
      // product cards in the catalogue layout, not just inside this panel.
      publish(data.products, message)
    } catch (err) {
      // Surface the server's own explanation when it gave one — a rate-limit or
      // timeout message is far more useful than a generic failure.
      const text =
        err instanceof Error && err.message !== 'failed'
          ? err.message
          : "I can't reach the shop's assistant right now. Make sure the backend is running, then try again."
      setTurns((t) => [...t, { role: 'assistant', content: text }])
      setAnnouncement(text)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="chat-root">
      {open && (
        <section
          className="chat-panel"
          role="dialog"
          aria-modal="false"
          aria-label="Shopping assistant"
        >
          <header className="chat-head">
            <div>
              <strong>Bulldog Blue Assistant</strong>
              <span className="chat-status">
                {user
                  ? `Saved to your account, ${user.firstName ?? user.name.split(' ')[0]}`
                  : 'Ask about products, sizes, or stock'}
              </span>
            </div>
            <div className="chat-actions">
              {turns.length > 1 && (
                <button
                  className="chat-clear"
                  onClick={clearConversation}
                  title={user ? 'Clear and delete saved history' : 'Clear this conversation'}
                >
                  Clear
                </button>
              )}
              <button className="chat-x" onClick={() => setOpen(false)} aria-label="Close chat">
                &times;
              </button>
            </div>
          </header>

          {/* Replies are announced here rather than on the log itself, so a
              screen reader reads the new message once instead of re-reading
              the whole thread on every update. */}
          <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
            {announcement}
          </p>

          <div className="chat-log" ref={scrollRef} role="log" aria-label="Conversation">
            {turns.map((t, i) => (
              <div key={i} className="turn">
                <div className={`bubble bubble-${t.role}`}>{t.content}</div>

                {t.products && t.products.length > 0 && (
                  <div className="chat-cards">
                    {t.products.map((p) => (
                      <Link
                        key={p.id}
                        to={p.url || `/products/${p.id}`}
                        className="chat-card"
                        onClick={() => setOpen(false)}
                      >
                        <img src={p.image} alt={p.name} loading="lazy" />
                        <div className="chat-card-body">
                          <strong>{p.name}</strong>
                          <span className="chat-card-price">${p.price.toFixed(2)}</span>
                          <span className="chat-card-sizes">
                            {p.sizes_in_stock.length > 0
                              ? p.sizes_in_stock.join(' · ')
                              : 'Sold out'}
                          </span>
                        </div>
                      </Link>
                    ))}

                    <button
                      className="chat-see-all"
                      onClick={() => {
                        setOpen(false)
                        navigate('/products')
                      }}
                    >
                      See these on the page &rarr;
                    </button>
                  </div>
                )}
              </div>
            ))}

            {!user && turns.length > 1 && (
              <p className="chat-guest-note">
                You are chatting as a guest, so this conversation is not saved.{' '}
                <Link to="/login" onClick={() => setOpen(false)}>
                  Log in
                </Link>{' '}
                to keep it.
              </p>
            )}

            {turns.length === 1 && (
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)} disabled={pending}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            {pending && (
              <div className="bubble bubble-assistant typing" aria-label="Assistant is typing">
                <span />
                <span />
                <span />
              </div>
            )}
          </div>

          <form
            className="chat-form"
            onSubmit={(e) => {
              e.preventDefault()
              send(draft)
            }}
          >
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="What hoodies do you have?"
              aria-label="Message"
            />
            <button type="submit" className="btn btn-primary" disabled={!draft.trim() || pending}>
              Send
            </button>
          </form>
        </section>
      )}

      <button
        ref={fabRef}
        className="chat-fab"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close shopping assistant' : 'Open shopping assistant'}
      >
        {open ? '✕' : 'Chat with us'}
      </button>
    </div>
  )
}

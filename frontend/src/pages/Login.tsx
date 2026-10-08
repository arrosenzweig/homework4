import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

export default function Login() {
  const { login, user, logout } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not log in.')
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="page page-form">
        <h1>You are logged in</h1>
        <p className="muted">
          Signed in as <strong>{user.email}</strong>.
        </p>
        <button className="btn btn-primary btn-lg btn-block" onClick={() => logout()}>
          Log out
        </button>
      </div>
    )
  }

  return (
    <div className="page page-form">
      <h1>Log in</h1>
      <p className="muted">
        Pick up where you left off &mdash; your saved sizes and past conversations with our
        shopping assistant.
      </p>

      <form onSubmit={submit} className="form">
        <label className="field">
          <span className="field-label">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@yale.edu"
            autoComplete="email"
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy}>
          {busy ? 'Checking…' : 'Log in'}
        </button>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </form>

      <p className="muted">
        New here? <Link to="/create-account">Create an account</Link>.
      </p>

      <p className="demo-hint">
        <strong>Test account</strong>
        <code>test@campuscustoms.yale.edu</code>
        <code>password</code>
      </p>
    </div>
  )
}

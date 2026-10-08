import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const EMPTY = {
  firstName: '',
  lastName: '',
  email: '',
  password: '',
  confirmPassword: '',
}

export default function CreateAccount() {
  const { signup, user, logout } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function set(key: keyof typeof EMPTY) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }))
  }

  const mismatch =
    form.confirmPassword.length > 0 && form.password !== form.confirmPassword

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (form.password !== form.confirmPassword) {
      setError('Those passwords do not match.')
      return
    }

    setBusy(true)
    try {
      await signup(form)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="page page-form">
        <h1>You already have an account</h1>
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
      <h1>Create an account</h1>
      <p className="muted">
        Save your sizes once and skip the guesswork next time. We will also keep your chat history
        with the shopping assistant.
      </p>

      <form onSubmit={submit} className="form">
        <div className="form-row">
          <label className="field">
            <span className="field-label">First name</span>
            <input
              value={form.firstName}
              onChange={set('firstName')}
              autoComplete="given-name"
              required
            />
          </label>
          <label className="field">
            <span className="field-label">Last name</span>
            <input
              value={form.lastName}
              onChange={set('lastName')}
              autoComplete="family-name"
              required
            />
          </label>
        </div>

        <label className="field">
          <span className="field-label">Email</span>
          <input
            type="email"
            value={form.email}
            onChange={set('email')}
            placeholder="you@yale.edu"
            autoComplete="email"
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Password</span>
          <input
            type="password"
            value={form.password}
            onChange={set('password')}
            autoComplete="new-password"
            minLength={8}
            required
          />
          <span className="field-hint">At least 8 characters.</span>
        </label>

        <label className="field">
          <span className="field-label">Confirm password</span>
          <input
            type="password"
            value={form.confirmPassword}
            onChange={set('confirmPassword')}
            autoComplete="new-password"
            required
            aria-invalid={mismatch}
          />
          {mismatch && <span className="field-hint field-hint-bad">Passwords do not match.</span>}
        </label>

        <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={busy}>
          {busy ? 'Creating…' : 'Create account'}
        </button>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </form>

      <p className="muted">
        Already have one? <Link to="/login">Log in</Link>.
      </p>
    </div>
  )
}

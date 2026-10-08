import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function signOut() {
    await logout()
    navigate('/')
  }

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            Y
          </span>
          <span className="brand-text">
            <strong>Yale Bulldog Blue</strong>
            <em>by Campus Customs</em>
          </span>
        </Link>

        <nav className="nav-links" aria-label="Main">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="nav-auth">
          {user ? (
            <>
              <span className="nav-user">
                Hi, {user.firstName ?? user.name.split(' ')[0]}
              </span>
              <button className="btn btn-ghost" onClick={signOut}>
                Log Out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="btn btn-ghost">
                Log In
              </NavLink>
              <NavLink to="/create-account" className="btn btn-primary">
                Create Account
              </NavLink>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

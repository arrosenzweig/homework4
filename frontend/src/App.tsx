import { Routes, Route, Link } from 'react-router-dom'
import NavBar from './components/NavBar'
import ChatWidget from './components/ChatWidget'
import AthleticsTicker from './components/AthleticsTicker'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import CreateAccount from './pages/CreateAccount'

export default function App() {
  return (
    <>
      <NavBar />

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route
            path="*"
            element={
              <div className="page page-narrow">
                <h1>Page not found</h1>
                <Link to="/" className="btn btn-primary">
                  Back home
                </Link>
              </div>
            }
          />
        </Routes>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div>
            <strong>Yale Bulldog Blue by Campus Customs</strong>
            <p>57 Broadway, New Haven CT, 06511</p>
            <p className="tiny">Officially Licensed Merchandise &middot; Yale Official Licensed</p>
          </div>
          <nav className="footer-links" aria-label="Footer">
            <Link to="/products">Products</Link>
            <Link to="/about">About Us</Link>
            <Link to="/login">Log In</Link>
            <Link to="/create-account">Create Account</Link>
          </nav>
        </div>
        <p className="tiny footer-note">
          Coursework demo for AI Foundations HW 4. Brand wording on the Home and About Us pages is
          drawn from yalebulldogblue.com.
        </p>
      </footer>

      <ChatWidget />
      <AthleticsTicker />
    </>
  )
}

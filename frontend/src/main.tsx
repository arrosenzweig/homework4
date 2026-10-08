import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AgentResultsProvider } from './lib/agentResults'
import { AuthProvider } from './lib/auth'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <AgentResultsProvider>
          <App />
        </AgentResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)

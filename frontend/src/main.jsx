import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppWithAuth from './App_with_auth.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppWithAuth />
  </StrictMode>,
)

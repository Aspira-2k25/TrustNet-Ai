import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ResultLanguageProvider } from './components/ResultLanguageProvider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ResultLanguageProvider><App /></ResultLanguageProvider>
  </StrictMode>,
)

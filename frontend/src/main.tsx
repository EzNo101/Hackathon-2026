import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { EquilibriumProvider } from './state/EquilibriumContext'
import './index.css'

// Vstupní bod aplikace. Provider drží sdílený stav výboje, času a režimu.
const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Chybí kořenový element #root v index.html.')
}

createRoot(rootElement).render(
  <StrictMode>
    <EquilibriumProvider>
      <App />
    </EquilibriumProvider>
  </StrictMode>,
)

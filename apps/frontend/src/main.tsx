import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MotionConfig } from 'motion/react'
import './index.css'
import './i18n/config'
import App from './App.tsx'

// reducedMotion="user": con "reducir movimiento" activo se eliminan los desplazamientos
// y escalados, y se conservan los cambios de opacidad.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
  </StrictMode>,
)

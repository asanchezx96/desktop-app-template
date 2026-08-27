import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { installLocalAuthFetchInterceptor, initLocalAuth } from './localAuth'
import { ErrorBoundary } from './components/ErrorBoundary'

// Instala el interceptor de fetch que inyecta el token de autenticación
// local (X-Local-Auth-Token) en cada llamada al backend FastAPI local, y
// obtiene ese token una vez desde /api/bootstrap/token antes de renderizar
// la app, para evitar llamadas iniciales sin autenticar.
installLocalAuthFetchInterceptor()

initLocalAuth().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </React.StrictMode>,
  )
})

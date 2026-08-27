import { LayoutTemplate } from 'lucide-react'
import { AppHeader } from '../components/AppHeader'
import { useTheme } from '../hooks/useTheme'

// Página de inicio del template. Sustitúyela por la pantalla real de tu
// aplicación: el resto de la infraestructura (ventana nativa, backend
// FastAPI, autenticación local, WebSocket, bandeja del sistema) ya está
// lista y no depende de lo que haya aquí.
export function DashboardPage() {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="h-screen flex flex-col bg-bg overflow-hidden select-none font-sans text-text">
      <AppHeader theme={theme} toggleTheme={toggleTheme} />

      <div className="flex-1 overflow-y-auto flex items-center justify-center p-8">
        <div className="max-w-md text-center space-y-4">
          <div className="mx-auto w-14 h-14 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
            <LayoutTemplate className="w-6 h-6 text-accent" />
          </div>
          <h1 className="text-lg font-bold tracking-tight">Desktop App Template</h1>
          <p className="text-sm text-text/60 leading-relaxed">
            La ventana nativa, el backend FastAPI local y la bandeja del sistema ya
            están funcionando. Empieza a construir tu aplicación editando{' '}
            <code className="px-1.5 py-0.5 rounded-sm bg-panel border border-border text-[12px] font-mono">
              src/frontend/src/pages/DashboardPage.jsx
            </code>
            .
          </p>
        </div>
      </div>
    </div>
  )
}

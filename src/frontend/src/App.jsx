import { DashboardPage } from './pages/DashboardPage'

// La app es una sola pantalla local. No hay rutas ni sesión que proteger,
// así que se monta la pantalla principal directamente.
export default function App() {
  return <DashboardPage />
}

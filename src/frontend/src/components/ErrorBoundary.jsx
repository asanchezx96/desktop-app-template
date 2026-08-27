import { Component } from 'react'

// Sin esto, un error de render no controlado deja la ventana de la app en
// blanco sin ningún mensaje. React solo detecta errores de render a través
// de un class component con getDerivedStateFromError/componentDidCatch.
export class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('💥 UI ERROR:', error, errorInfo)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
          <h1 className="text-lg font-semibold">Algo salió mal</h1>
          <p className="max-w-md text-sm text-gray-500">
            Ocurrió un error inesperado en la interfaz. Puedes intentar
            recargar la aplicación; si el problema persiste, contacta a soporte.
          </p>
          <button
            className="rounded-sm bg-black px-5 py-2 text-sm font-medium text-white hover:bg-black/90"
            onClick={() => window.location.reload()}
          >
            Recargar
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

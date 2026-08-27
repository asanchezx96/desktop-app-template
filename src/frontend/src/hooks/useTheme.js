import { useEffect, useState } from 'react'

const STORAGE_KEY = 'vite-ui-theme'

/**
 * Tema claro/oscuro de la aplicación.
 *
 * Aplica la clase al elemento raíz —de donde cuelgan las variables de color de
 * index.css— y recuerda la elección en localStorage. Sustituye al contexto
 * global anterior: es el único estado que la interfaz necesita compartir.
 */
export function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem(STORAGE_KEY) || 'light')

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const toggleTheme = () => setTheme(prev => (prev === 'light' ? 'dark' : 'light'))

  return { theme, setTheme, toggleTheme }
}

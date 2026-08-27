import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { MoreHorizontal } from 'lucide-react'

const MENU_WIDTH = 230

/**
 * Menú desplegable de acciones secundarias.
 *
 * Se dibuja con un portal y `position: fixed` porque el contenedor de la tabla
 * recorta su contenido (overflow-hidden) y un menú absoluto quedaría cortado en
 * las últimas filas.
 *
 * `items` acepta `null`/`false` para poder condicionar entradas en línea, y
 * `{ separator: true }` para agrupar.
 */
export function ActionMenu({ items, label, title = 'Más acciones', className = '' }) {
  const [open, setOpen] = useState(false)
  const [coords, setCoords] = useState(null)
  const btnRef = useRef(null)
  const menuRef = useRef(null)

  const entries = items.filter(Boolean)

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return
    const rect = btnRef.current.getBoundingClientRect()
    const height = menuRef.current?.offsetHeight || 0
    const below = rect.bottom + 6
    // Si no cabe debajo, se abre hacia arriba en lugar de salirse de la ventana.
    const top = below + height > window.innerHeight - 8 ? Math.max(8, rect.top - height - 6) : below
    const left = Math.min(window.innerWidth - MENU_WIDTH - 8, Math.max(8, rect.right - MENU_WIDTH))
    setCoords({ top, left })
  }, [open, entries.length])

  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    const onDown = e => {
      if (menuRef.current?.contains(e.target) || btnRef.current?.contains(e.target)) return
      setOpen(false)
    }
    const onKey = e => { if (e.key === 'Escape') setOpen(false) }

    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    // En captura: el scroll ocurre en el contenedor de la tabla, no en window.
    window.addEventListener('scroll', close, true)
    window.addEventListener('resize', close)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('resize', close)
    }
  }, [open])

  return (
    <>
      <button
        ref={btnRef}
        onClick={() => setOpen(o => !o)}
        title={title}
        aria-haspopup="menu"
        aria-expanded={open}
        className={className || `inline-flex items-center justify-center gap-1.5 h-8 rounded-md border transition-colors ${
          label ? 'px-3 text-xs font-semibold' : 'w-8'
        } ${
          open
            ? 'border-accent/40 bg-accent/10 text-accent'
            : 'border-border bg-panel text-text/60 hover:text-text hover:bg-border/50'
        }`}
      >
        {label}
        <MoreHorizontal className="w-4 h-4" />
      </button>

      {open && createPortal(
        <div
          ref={menuRef}
          role="menu"
          style={{ top: coords?.top ?? -9999, left: coords?.left ?? -9999, width: MENU_WIDTH, opacity: coords ? 1 : 0 }}
          className="menu-panel fixed z-[95] py-1 bg-panel border border-border rounded-lg shadow-xl shadow-black/20 dark:shadow-black/50"
        >
          {entries.map((item, i) => item.separator ? (
            <div key={i} className="h-px bg-border my-1" />
          ) : (
            <button
              key={i}
              role="menuitem"
              disabled={item.disabled}
              onClick={() => { setOpen(false); item.onClick?.() }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs text-left transition-colors ${
                item.disabled
                  ? 'text-text/30 cursor-not-allowed'
                  : item.tone === 'danger'
                    ? 'text-rose-500 hover:bg-rose-500/10'
                    : 'text-text/80 hover:text-text hover:bg-bg'
              }`}
            >
              {item.icon && <item.icon className="w-3.5 h-3.5 shrink-0" />}
              <span className="flex-1 truncate">{item.label}</span>
              {item.hint && <span className="text-[10px] text-text/35 shrink-0">{item.hint}</span>}
            </button>
          ))}
        </div>,
        document.body
      )}
    </>
  )
}

import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

// Paletas por intención. El acento vive en el icono y en el botón de acción;
// el resto del diálogo se queda en los tokens neutros del tema.
const TONES = {
  default: {
    icon: 'bg-accent/10 border-accent/25 text-accent',
    confirm: 'bg-accent text-bg hover:bg-accent2 focus-visible:ring-accent/40',
  },
  danger: {
    icon: 'bg-rose-500/10 border-rose-500/25 text-rose-500',
    confirm: 'bg-rose-600 text-white hover:bg-rose-500 focus-visible:ring-rose-500/40',
  },
  warning: {
    icon: 'bg-amber-500/10 border-amber-500/25 text-amber-500',
    confirm: 'bg-amber-600 text-white hover:bg-amber-500 focus-visible:ring-amber-500/40',
  },
}

/**
 * Diálogo de confirmación modal. Sustituye a window.confirm, que en el webview
 * embebido se dibuja como una alerta del navegador ("localhost:5099 dice…").
 *
 * Se controla desde fuera: `open` lo muestra y `onCancel`/`onConfirm` lo cierran.
 */
export function ConfirmDialog({
  open,
  tone = 'default',
  icon: Icon,
  title,
  subtitle,
  children,
  detail,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  onConfirm,
  onCancel,
}) {
  const confirmRef = useRef(null)
  const lastFocused = useRef(null)
  // Los callbacks llegan como funciones nuevas en cada render; guardarlos en una
  // ref mantiene el efecto atado solo a `open`, que si no se remontaría en cada
  // repintado del dashboard (cada 3 s) robando el foco.
  const handlers = useRef({ onConfirm, onCancel })
  handlers.current = { onConfirm, onCancel }

  useEffect(() => {
    if (!open) return

    // Se guarda el elemento que abrió el diálogo para devolverle el foco al
    // cerrar: si no, el foco cae al <body> y se pierde la navegación por teclado.
    lastFocused.current = document.activeElement
    confirmRef.current?.focus()

    const onKey = e => {
      if (e.key === 'Escape') {
        e.preventDefault()
        handlers.current.onCancel?.()
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handlers.current.onConfirm?.()
      }
    }

    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      lastFocused.current?.focus?.()
    }
  }, [open])

  if (!open) return null

  const palette = TONES[tone] || TONES.default

  return (
    <div
      className="dialog-overlay fixed inset-0 z-[90] flex items-center justify-center p-6 bg-black/40 dark:bg-black/60 backdrop-blur-[3px]"
      onMouseDown={e => { if (e.target === e.currentTarget) onCancel?.() }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="dialog-panel w-full max-w-md bg-panel border border-border rounded-xl overflow-hidden shadow-2xl shadow-black/25 dark:shadow-black/60"
      >
        <header className="flex items-start gap-3 px-5 py-4">
          {Icon && (
            <div className={`shrink-0 mt-0.5 p-2 rounded-lg border ${palette.icon}`}>
              <Icon className="w-4 h-4" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h2 className="text-[15px] font-bold tracking-tight text-text leading-tight">{title}</h2>
            {subtitle && (
              <p className="mt-0.5 text-[11px] text-text/50 font-mono truncate">{subtitle}</p>
            )}
          </div>
          <button
            onClick={onCancel}
            aria-label="Cerrar"
            className="shrink-0 -mr-1 -mt-1 inline-flex items-center justify-center w-7 h-7 rounded-md text-text/40 hover:text-text hover:bg-bg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        {/* Separador pedido: banda gris de 3px, no un borde de 1px */}
        <div className="h-[3px] w-full bg-zinc-200 dark:bg-zinc-700" />

        <div className="px-5 py-4">
          <div className="text-[13px] leading-relaxed text-text/75">{children}</div>

          {detail && (
            <p className="mt-3 px-3 py-2 rounded-md bg-bg border border-border text-[11px] leading-relaxed text-text/55">
              {detail}
            </p>
          )}

          <div className="flex justify-end gap-2 mt-5">
            <button
              onClick={onCancel}
              className="px-4 py-2 rounded-md border border-border bg-bg text-xs font-semibold text-text/70 hover:text-text hover:bg-border/50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              {cancelLabel}
            </button>
            <button
              ref={confirmRef}
              onClick={onConfirm}
              className={`px-4 py-2 rounded-md text-xs font-bold transition-colors focus:outline-none focus-visible:ring-2 ${palette.confirm}`}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

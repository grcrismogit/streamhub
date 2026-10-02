// Componentes de interfaz pequeños y reutilizables.
// Regla: usar el elemento HTML con significado (p, section, progress, dialog...)
// y recurrir a <div> solo cuando ningún elemento semántico encaja.
import { useEffect, useRef, type MouseEvent, type ReactNode } from 'react'
import { initials } from '../lib/format'

export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  // Color estable derivado del nombre
  const hue = [...name].reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 360
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, fontSize: size * 0.4, background: `hsl(${hue} 55% 42%)` }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  )
}

/** Indicador de carga: un único <p role="status">; el círculo se dibuja con CSS (::before). */
export function Spinner({ label = 'Cargando…' }: { label?: string }) {
  return (
    <p className="spinner" role="status">
      <span className="sr-only">{label}</span>
    </p>
  )
}

export function Alert({ children, tone = 'error' }: { children: ReactNode; tone?: 'error' | 'success' }) {
  return (
    <p className={`alert alert-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      {children}
    </p>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <section className="empty" aria-label={title}>
      <svg viewBox="0 0 24 24" width="40" height="40" aria-hidden="true">
        <path
          fill="currentColor"
          d="M4 5h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm6 3.5v7l6-3.5-6-3.5Z"
        />
      </svg>
      <h2>{title}</h2>
      {children}
    </section>
  )
}

/** Barra de progreso con el elemento nativo <progress> (accesible sin ARIA extra). */
export function ProgressBar({ value, label = 'Progreso de subida' }: { value: number; label?: string }) {
  return (
    <label className="progress">
      <span className="sr-only">{label}</span>
      <progress value={value} max={100} />
      <output aria-hidden="true">{value}%</output>
    </label>
  )
}

/** Diálogo modal basado en <dialog> nativo: foco atrapado, Esc y fondo (::backdrop) incluidos. */
export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  // Cerrar al hacer clic en el fondo: el evento llega al propio <dialog> y
  // las coordenadas quedan fuera de su rectángulo.
  function onBackdropClick(e: MouseEvent<HTMLDialogElement>) {
    if (e.target !== e.currentTarget) return
    const r = e.currentTarget.getBoundingClientRect()
    const outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom
    if (outside) onClose()
  }

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClick={onBackdropClick}
    >
      <header className="modal-header">
        <h2 id="modal-title">{title}</h2>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">
          ✕
        </button>
      </header>
      {open && children}
    </dialog>
  )
}

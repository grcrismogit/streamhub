import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { api, ApiError, type Video } from '../api'
import { useAuth } from '../auth/AuthContext'
import { EditVideoForm } from '../components/EditVideoForm'
import { VideoUploadForm } from '../components/VideoUploadForm'
import { Alert, Avatar, EmptyState, Modal, Spinner } from '../components/ui'
import { formatDate, formatViews, timeAgo } from '../lib/format'

export default function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const location = useLocation()

  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Video | null>(null)
  const [deleting, setDeleting] = useState<Video | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  // Carga inicial: mis videos + datos frescos del usuario (conteo, nombre).
  const userId = user?.id
  useEffect(() => {
    if (userId === undefined) return
    const controller = new AbortController()
    // Trae TODOS los videos del usuario, de 50 en 50 (límite por página de la API).
    async function loadAll(): Promise<Video[]> {
      const all: Video[] = []
      for (;;) {
        const page = await api.listVideos({ user_id: userId, limit: 50, offset: all.length }, controller.signal)
        all.push(...page.items)
        if (page.items.length === 0 || all.length >= page.total) return all
      }
    }
    loadAll()
      .then(setVideos)
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err instanceof ApiError ? err.message : 'No se pudieron cargar tus videos')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    refreshUser().catch(() => undefined)
    return () => controller.abort()
  }, [userId, refreshUser])

  // Si llega con #upload (botón "Publicar" del encabezado), hacer scroll al formulario.
  useEffect(() => {
    if (location.hash === '#upload') document.getElementById('upload')?.scrollIntoView({ behavior: 'smooth' })
  }, [location.hash])

  if (!user) return null

  async function confirmDelete() {
    if (!deleting) return
    setDeleteBusy(true)
    try {
      await api.deleteVideo(deleting.id)
      setVideos((prev) => prev.filter((v) => v.id !== deleting.id))
      await refreshUser().catch(() => undefined) // actualiza el contador de videos
      setNotice(`Se eliminó “${deleting.title}”.`)
      setDeleting(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar el video')
      setDeleting(null)
    } finally {
      setDeleteBusy(false)
    }
  }

  const totalViews = videos.reduce((acc, v) => acc + v.views, 0)

  return (
    <section className="page profile" aria-labelledby="profile-name">
      <header className="profile-card">
        <Avatar name={user.name} size={88} />
        {/* <hgroup> agrupa el título con sus subtítulos sin un <div> extra. */}
        <hgroup>
          <h1 id="profile-name">{user.name}</h1>
          <p className="muted">{user.email}</p>
          <p className="muted small">Miembro desde {formatDate(user.created_at)}</p>
        </hgroup>
        <dl className="stats">
          {/* En HTML5, <div> es el único agrupador válido de pares <dt>/<dd>. */}
          <div>
            <dt>Videos publicados</dt>
            <dd>{user.video_count}</dd>
          </div>
          <div>
            <dt>Vistas totales</dt>
            <dd>{loading ? '—' : totalViews.toLocaleString('es')}</dd>
          </div>
        </dl>
      </header>

      <section id="upload" className="panel" aria-labelledby="upload-title">
        <h2 id="upload-title">Publicar un video</h2>
        <VideoUploadForm
          onUploaded={(v) => {
            setVideos((prev) => [v, ...prev])
            void refreshUser()
          }}
        />
      </section>

      <section className="panel" aria-labelledby="my-videos-title">
        <h2 id="my-videos-title">Mis videos</h2>
        {notice && <Alert tone="success">{notice}</Alert>}
        {error && <Alert>{error}</Alert>}

        {loading ? (
          <Spinner />
        ) : videos.length === 0 ? (
          <EmptyState title="Todavía no has publicado videos">
            <p className="muted">Usa el formulario de arriba para subir el primero.</p>
          </EmptyState>
        ) : (
          <ul className="my-videos">
            {/* Cada <li> es un grid: miniatura · textos · acciones, sin envoltorios. */}
            {videos.map((v) => (
              <li key={v.id} className="my-video">
                <Link to={`/watch/${v.id}`} className="thumb small-thumb" tabIndex={-1} aria-hidden="true">
                  <img src={v.thumbnail_url} alt="" loading="lazy" />
                </Link>
                <h3 className="video-title">
                  <Link to={`/watch/${v.id}`}>{v.title}</Link>
                </h3>
                <p className="muted small my-video-meta">
                  {formatViews(v.views)} · publicado {timeAgo(v.created_at)}
                </p>
                {v.description && <p className="muted small clamp-2 my-video-desc">{v.description}</p>}
                <menu className="my-video-actions" aria-label={`Acciones para ${v.title}`}>
                  <li>
                    <button type="button" className="btn btn-ghost" onClick={() => setEditing(v)}>
                      Editar
                    </button>
                  </li>
                  <li>
                    <button type="button" className="btn btn-danger" onClick={() => setDeleting(v)}>
                      Eliminar
                    </button>
                  </li>
                </menu>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Modal open={editing !== null} title="Editar video" onClose={() => setEditing(null)}>
        {editing && (
          <EditVideoForm
            video={editing}
            onCancel={() => setEditing(null)}
            onSaved={(updated) => {
              setVideos((prev) => prev.map((v) => (v.id === updated.id ? updated : v)))
              setNotice(`Se actualizó “${updated.title}”.`)
              setEditing(null)
            }}
          />
        )}
      </Modal>

      <Modal open={deleting !== null} title="Eliminar video" onClose={() => !deleteBusy && setDeleting(null)}>
        {deleting && (
          <>
            <p>
              ¿Seguro que quieres eliminar <strong>“{deleting.title}”</strong>? Se borrarán el video, la miniatura y
              todos sus comentarios. Esta acción no se puede deshacer.
            </p>
            <footer className="row-end">
              <button type="button" className="btn btn-ghost" onClick={() => setDeleting(null)} disabled={deleteBusy}>
                Cancelar
              </button>
              <button type="button" className="btn btn-danger" onClick={confirmDelete} disabled={deleteBusy}>
                {deleteBusy ? 'Eliminando…' : 'Sí, eliminar'}
              </button>
            </footer>
          </>
        )}
      </Modal>
    </section>
  )
}

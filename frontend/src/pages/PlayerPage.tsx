import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { api, ApiError, type Comment, type Video } from '../api'
import { useAuth } from '../auth/AuthContext'
import { VideoCard, VideoCardSkeleton } from '../components/VideoCard'
import { Alert, Avatar, EmptyState, Spinner } from '../components/ui'
import { formatDate, formatViews, timeAgo } from '../lib/format'

export default function PlayerPage() {
  const { id } = useParams()
  const videoId = Number(id)
  // La `key` garantiza un estado limpio al navegar de un video a otro (recomendados).
  return <Player key={videoId} videoId={videoId} />
}

function Player({ videoId }: { videoId: number }) {
  const { user } = useAuth()
  const validId = Number.isInteger(videoId) && videoId > 0

  const [video, setVideo] = useState<Video | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [recommended, setRecommended] = useState<Video[] | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'notfound' | 'error'>('loading')
  const [expanded, setExpanded] = useState(false)

  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [commentError, setCommentError] = useState<string | null>(null)

  // Se cuenta UNA vista por visita (evita el doble montaje de StrictMode en desarrollo).
  const viewCounted = useRef(false)

  useEffect(() => {
    if (!validId) return
    const controller = new AbortController()
    const { signal } = controller
    window.scrollTo({ top: 0 })

    api
      .getVideo(videoId, signal)
      .then((v) => {
        setVideo(v)
        setStatus('ready')
        if (!viewCounted.current) {
          viewCounted.current = true
          api
            .registerView(videoId)
            .then(({ views }) => setVideo((cur) => (cur ? { ...cur, views } : cur)))
            .catch(() => undefined) // no es crítico
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        setStatus(err instanceof ApiError && err.status === 404 ? 'notfound' : 'error')
      })

    // Comentarios y recomendados se cargan en paralelo.
    api
      .listComments(videoId, signal)
      .then(setComments)
      .catch(() => undefined)
    api
      .recommended(videoId, signal)
      .then(setRecommended)
      .catch((err) => {
        if (err.name !== 'AbortError') setRecommended([])
      })

    return () => controller.abort()
  }, [videoId, validId])

  async function onComment(e: FormEvent) {
    e.preventDefault()
    const content = draft.trim()
    if (!content) return
    setSending(true)
    setCommentError(null)
    try {
      const created = await api.createComment(videoId, content)
      setComments((prev) => [created, ...prev])
      setDraft('')
    } catch (err) {
      setCommentError(err instanceof ApiError ? err.message : 'No se pudo publicar el comentario')
    } finally {
      setSending(false)
    }
  }

  if (!validId || status === 'notfound') {
    return (
      <EmptyState title="Video no encontrado">
        <p className="muted">Puede que haya sido eliminado.</p>
        <Link to="/" className="btn btn-primary">
          Volver al inicio
        </Link>
      </EmptyState>
    )
  }

  if (status === 'error') return <Alert>No se pudo cargar el video. Intenta recargar la página.</Alert>

  return (
    <section className="page watch" aria-label="Reproductor">
      {status === 'loading' || !video ? (
        <article className="watch-main" aria-busy="true">
          <Spinner label="Cargando video…" />
        </article>
      ) : (
        <article className="watch-main" aria-labelledby="video-title">
          <video
            className="player"
            src={video.video_url}
            poster={video.thumbnail_url}
            controls
            playsInline
            preload="metadata"
          >
            Tu navegador no soporta la reproducción de video.
          </video>

          <h1 id="video-title" className="watch-title">
            {video.title}
          </h1>

          <p className="owner">
            <Avatar name={video.owner.name} size={40} />
            <strong>{video.owner.name}</strong>
            {user?.id === video.user_id && (
              <Link to="/profile" className="small link">
                Gestionar mis videos
              </Link>
            )}
          </p>

          <section className="description-box" aria-label="Descripción">
            <p className="strong">
              {formatViews(video.views)} · <time dateTime={video.created_at}>{formatDate(video.created_at)}</time>
            </p>
            {video.description ? (
              <>
                <p className={expanded ? 'description' : 'description clamp'}>{video.description}</p>
                {video.description.length > 180 && (
                  <button
                    type="button"
                    className="link-btn"
                    aria-expanded={expanded}
                    onClick={() => setExpanded((x) => !x)}
                  >
                    {expanded ? 'Mostrar menos' : 'Mostrar más'}
                  </button>
                )}
              </>
            ) : (
              <p className="muted">Sin descripción.</p>
            )}
          </section>

          <section className="comments" aria-labelledby="comments-title">
            <h2 id="comments-title">
              {comments.length} {comments.length === 1 ? 'comentario' : 'comentarios'}
            </h2>

            {user ? (
              // Grid: avatar en la 1.ª columna; textarea, error y pie en la 2.ª.
              <form className="comment-form" onSubmit={onComment}>
                <Avatar name={user.name} size={36} />
                <textarea
                  placeholder="Escribe un comentario…"
                  aria-label="Escribe un comentario"
                  rows={2}
                  maxLength={1000}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                />
                {commentError && <Alert>{commentError}</Alert>}
                <footer className="row-end">
                  <small className="muted">{draft.length}/1000</small>
                  <button type="submit" className="btn btn-primary" disabled={sending || !draft.trim()}>
                    {sending ? 'Publicando…' : 'Comentar'}
                  </button>
                </footer>
              </form>
            ) : (
              <p className="muted">
                <Link to="/login" state={{ from: `/watch/${videoId}` }} className="link">
                  Inicia sesión
                </Link>{' '}
                para comentar.
              </p>
            )}

            <ol className="comment-list">
              {comments.map((c) => (
                <li key={c.id} className="comment">
                  <Avatar name={c.author.name} size={36} />
                  <p className="comment-head">
                    <strong>{c.author.name}</strong>{' '}
                    <time className="muted" dateTime={c.created_at}>
                      {timeAgo(c.created_at)}
                    </time>
                  </p>
                  <p className="comment-text">{c.content}</p>
                </li>
              ))}
            </ol>
          </section>
        </article>
      )}

      <aside className="watch-side" aria-labelledby="rec-title">
        <h2 id="rec-title" className="side-title">
          Videos recomendados
        </h2>
        {recommended === null ? (
          Array.from({ length: 4 }, (_, i) => <VideoCardSkeleton key={i} compact />)
        ) : recommended.length === 0 ? (
          <p className="muted">No hay más videos por ahora.</p>
        ) : (
          recommended.map((v) => <VideoCard key={v.id} video={v} compact />)
        )}
      </aside>
    </section>
  )
}

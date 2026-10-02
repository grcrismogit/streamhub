import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { api, ApiError, type Video, type VideoSort } from '../api'
import { VideoCard, VideoCardSkeleton } from '../components/VideoCard'
import { Alert, EmptyState } from '../components/ui'

const PAGE_SIZE = 12

export default function HomePage() {
  const [params] = useSearchParams()
  const q = params.get('q') ?? ''
  const sort: VideoSort = params.get('sort') === 'popular' ? 'popular' : 'recent'
  // La `key` reinicia el estado del catálogo cada vez que cambia la búsqueda u orden.
  return <Catalog key={`${q}|${sort}`} q={q} sort={sort} />
}

/** URL del catálogo conservando la búsqueda actual (el orden es navegación: usa enlaces). */
function sortHref(q: string, sort: VideoSort): string {
  const p = new URLSearchParams()
  if (q) p.set('q', q)
  if (sort === 'popular') p.set('sort', 'popular')
  const qs = p.toString()
  return qs ? `/?${qs}` : '/'
}

function Catalog({ q, sort }: { q: string; sort: VideoSort }) {
  const [videos, setVideos] = useState<Video[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // AbortController cancela la petición si el usuario cambia de filtro o de página.
  useEffect(() => {
    const controller = new AbortController()
    api
      .listVideos({ q, sort, limit: PAGE_SIZE, offset: 0 }, controller.signal)
      .then((page) => {
        setVideos(page.items)
        setTotal(page.total)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err instanceof ApiError ? err.message : 'Error al cargar videos')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [q, sort])

  async function loadMore() {
    setLoadingMore(true)
    try {
      const page = await api.listVideos({ q, sort, limit: PAGE_SIZE, offset: videos.length })
      setVideos((prev) => [...prev, ...page.items])
      setTotal(page.total)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar más videos')
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <section className="page" aria-labelledby="catalog-title">
      <header className="page-head">
        <h1 id="catalog-title">{q ? `Resultados para “${q}”` : 'Explorar videos'}</h1>
        <nav className="chips" aria-label="Ordenar videos">
          <Link to={sortHref(q, 'recent')} className="chip" aria-current={sort === 'recent' ? 'page' : undefined}>
            Recientes
          </Link>
          <Link to={sortHref(q, 'popular')} className="chip" aria-current={sort === 'popular' ? 'page' : undefined}>
            Más vistos
          </Link>
        </nav>
      </header>

      {error && <Alert>{error}</Alert>}

      {loading ? (
        <section className="video-grid" aria-busy="true" aria-label="Cargando videos">
          {Array.from({ length: 8 }, (_, i) => (
            <VideoCardSkeleton key={i} />
          ))}
        </section>
      ) : videos.length === 0 && !error ? (
        <EmptyState title={q ? 'No encontramos videos' : 'Aún no hay videos'}>
          <p className="muted">{q ? 'Prueba con otras palabras.' : '¡Sé el primero en publicar uno desde tu perfil!'}</p>
        </EmptyState>
      ) : (
        <>
          <p className="muted small">
            {total} {total === 1 ? 'video' : 'videos'}
          </p>
          <section className="video-grid" aria-label="Videos">
            {videos.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </section>
          {videos.length < total && (
            <button type="button" className="btn btn-ghost load-more" onClick={loadMore} disabled={loadingMore}>
              {loadingMore ? 'Cargando…' : 'Cargar más'}
            </button>
          )}
        </>
      )}
    </section>
  )
}

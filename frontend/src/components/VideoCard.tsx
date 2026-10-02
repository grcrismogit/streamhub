import { Link } from 'react-router'
import type { Video } from '../api'
import { formatDate, formatShortDate, formatViews } from '../lib/format'
import { Avatar } from './ui'

/**
 * Tarjeta de video. Un solo <article> organizado con CSS Grid
 * (miniatura · avatar · título · autor · vistas/fecha), sin contenedores extra.
 */
export function VideoCard({ video, compact = false }: { video: Video; compact?: boolean }) {
  return (
    <article className={compact ? 'video-card compact' : 'video-card'}>
      {/* El enlace de la miniatura es redundante con el del título: se oculta a lectores y al tabulador. */}
      <Link to={`/watch/${video.id}`} className="thumb" tabIndex={-1} aria-hidden="true">
        <img src={video.thumbnail_url} alt="" loading="lazy" decoding="async" />
      </Link>
      {!compact && <Avatar name={video.owner.name} size={36} />}
      <h3 className="video-title">
        <Link to={`/watch/${video.id}`}>{video.title}</Link>
      </h3>
      <p className="video-owner">{video.owner.name}</p>
      <p className="video-stats">
        {formatViews(video.views)} · <time dateTime={video.created_at} title={`Publicado el ${formatDate(video.created_at)}`}>
          {formatShortDate(video.created_at)}
        </time>
      </p>
    </article>
  )
}

export function VideoCardSkeleton({ compact = false }: { compact?: boolean }) {
  return (
    <article className={compact ? 'video-card compact skeleton' : 'video-card skeleton'} aria-hidden="true">
      <span className="thumb" />
      <span className="line video-title" />
      <span className="line short video-owner" />
    </article>
  )
}

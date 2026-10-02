import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from './ui'

export function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') ?? '')

  function onSearch(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    navigate(q ? `/?q=${encodeURIComponent(q)}` : '/')
  }

  return (
    <header className="topbar">
      <Link to="/" className="brand" aria-label="StreamHub, ir al inicio">
        <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
          <rect width="32" height="32" rx="8" fill="var(--accent)" />
          <path d="M12 9.5v13l11-6.5z" fill="#fff" />
        </svg>
        <span>StreamHub</span>
      </Link>

      <form className="search" role="search" onSubmit={onSearch}>
        <input
          type="search"
          placeholder="Buscar videos"
          aria-label="Buscar videos"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={100}
        />
        <button type="submit" aria-label="Buscar">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              fill="currentColor"
              d="M10 2a8 8 0 0 1 6.32 12.9l5.39 5.4-1.41 1.4-5.4-5.38A8 8 0 1 1 10 2Zm0 2a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z"
            />
          </svg>
        </button>
      </form>

      <nav className="topbar-actions">
        {user ? (
          <>
            <Link to="/profile#upload" className="btn btn-ghost hide-sm">
              + Publicar
            </Link>
            <Link to="/profile" className="user-chip" title="Mi perfil">
              <Avatar name={user.name} size={32} />
              <span className="hide-sm">{user.name.split(' ')[0]}</span>
            </Link>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              Salir
            </button>
          </>
        ) : (
          <Link to="/login" className="btn btn-primary">
            Iniciar sesión
          </Link>
        )}
      </nav>
    </header>
  )
}

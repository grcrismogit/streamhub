import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router'
import { ApiError } from '../api'
import { useAuth } from '../auth/AuthContext'
import { Alert } from '../components/ui'

type Mode = 'login' | 'register'

export default function AuthPage() {
  const { login, register, isAuthenticated } = useAuth()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Con sesión iniciada (incluido justo después de entrar o registrarse) se vuelve a donde iba.
  if (isAuthenticated) return <Navigate to={from} replace />

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (mode === 'register' && name.trim().length < 2) return setError('El nombre debe tener al menos 2 caracteres.')
    if (password.length < 8) return setError('La contraseña debe tener al menos 8 caracteres.')

    setLoading(true)
    try {
      if (mode === 'login') await login(email.trim(), password)
      else await register(name.trim(), email.trim(), password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Ocurrió un error inesperado.')
      setLoading(false)
    }
  }

  return (
    <section className="auth-page" aria-labelledby="auth-title">
      <article className="auth-card">
        <header className="auth-brand">
          <svg viewBox="0 0 32 32" width="40" height="40" aria-hidden="true">
            <rect width="32" height="32" rx="8" fill="var(--accent)" />
            <path d="M12 9.5v13l11-6.5z" fill="#fff" />
          </svg>
          <h1 id="auth-title">{mode === 'login' ? 'Bienvenido de nuevo' : 'Crea tu cuenta'}</h1>
          <p className="muted">
            {mode === 'login' ? 'Inicia sesión para publicar y comentar.' : 'Únete y comparte tus videos.'}
          </p>
        </header>

        <nav className="tabs" role="tablist" aria-label="Tipo de acceso">
          <button
            type="button"
            role="tab"
            id="tab-login"
            aria-controls="auth-form"
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'tab active' : 'tab'}
            onClick={() => switchMode('login')}
          >
            Iniciar sesión
          </button>
          <button
            type="button"
            role="tab"
            id="tab-register"
            aria-controls="auth-form"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'tab active' : 'tab'}
            onClick={() => switchMode('register')}
          >
            Registrarse
          </button>
        </nav>

        <form
          id="auth-form"
          role="tabpanel"
          aria-labelledby={mode === 'login' ? 'tab-login' : 'tab-register'}
          onSubmit={onSubmit}
          className="form"
        >
          {mode === 'register' && (
            <label className="field">
              <span>Nombre</span>
              <input
                type="text"
                autoComplete="name"
                required
                minLength={2}
                maxLength={80}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label className="field">
            <span>Correo electrónico</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Contraseña</span>
            <input
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {mode === 'register' && <small className="muted">Mínimo 8 caracteres.</small>}
          </label>

          {error && <Alert>{error}</Alert>}

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Procesando…' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
          </button>
        </form>
      </article>
    </section>
  )
}

import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router'
import { Header } from './components/Header'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Spinner } from './components/ui'

// Code-splitting: cada página se descarga solo cuando se visita.
const AuthPage = lazy(() => import('./pages/AuthPage'))
const HomePage = lazy(() => import('./pages/HomePage'))
const PlayerPage = lazy(() => import('./pages/PlayerPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))

export default function App() {
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const showHeader = pathname !== '/login'

  return (
    <>
      <a href="#content" className="skip-link">
        Saltar al contenido
      </a>
      {/* key: el buscador se sincroniza con ?q= al navegar (p. ej. al volver al inicio) */}
      {showHeader && <Header key={params.get('q') ?? ''} />}
      {/* Un único <main> para toda la app; cada página es una <section> dentro. */}
      <main id="content" tabIndex={-1}>
        <Suspense fallback={<Spinner />}>
          <Routes>
            {/* Página 1 */}
            <Route path="/login" element={<AuthPage />} />
            {/* Página 2 */}
            <Route path="/" element={<HomePage />} />
            {/* Página 3 */}
            <Route path="/watch/:id" element={<PlayerPage />} />
            {/* Página 4 */}
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </>
  )
}

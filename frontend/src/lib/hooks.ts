import { useEffect, useMemo } from 'react'

/**
 * URL temporal (blob:) para previsualizar un File local; se libera al cambiar o desmontar.
 * Nota: en desarrollo, StrictMode ejecuta useMemo dos veces; en producción se crea una sola URL.
 */
export function useObjectUrl(file: File | null): string | null {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])
  return url
}

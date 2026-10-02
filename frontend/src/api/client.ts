// Cliente HTTP mínimo sobre fetch: base URL, token, errores tipados.

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

let authToken: string | null = null
let onUnauthorized: (() => void) | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

/** Se llama cuando la API responde 401 (token vencido o inválido). */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

/** Convierte el `detail` de FastAPI (string o lista de errores 422) en un mensaje legible. */
function extractMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((d: { loc?: (string | number)[]; msg?: string }) => {
          const field = d.loc?.filter((p) => p !== 'body').join('.')
          return field ? `${field}: ${d.msg}` : d.msg
        })
        .join(' · ')
    }
  }
  return fallback
}

function handleError(status: number, body: unknown, hadToken: boolean): never {
  if (status === 401 && hadToken) onUnauthorized?.()
  const fallback =
    status === 413
      ? 'El archivo supera el tamaño máximo permitido (video: 100 MB, miniatura: 5 MB).'
      : status >= 500
        ? 'El servidor no está disponible. Intenta de nuevo en un momento.'
        : `Error ${status}`
  throw new ApiError(status, extractMessage(body, fallback))
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: BodyInit | object
  query?: Record<string, string | number | undefined | null>
  signal?: AbortSignal
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = new URL(API_URL + path)
  for (const [k, v] of Object.entries(opts.query ?? {})) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
  }

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  let body: BodyInit | undefined
  if (opts.body instanceof FormData || opts.body instanceof URLSearchParams) {
    body = opts.body // el navegador pone el Content-Type correcto
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  let res: Response
  try {
    res = await fetch(url, { method: opts.method ?? 'GET', headers, body, signal: opts.signal })
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err
    throw new ApiError(0, 'No se pudo conectar con la API. Revisa tu conexión.')
  }

  if (res.status === 204) return undefined as T
  const data: unknown = await res.json().catch(() => null)
  if (!res.ok) handleError(res.status, data, Boolean(authToken))
  return data as T
}

/**
 * Subida multipart con progreso. fetch() aún no expone progreso de subida,
 * por eso aquí se usa XMLHttpRequest.
 */
export function uploadWithProgress<T>(
  path: string,
  method: 'POST' | 'PUT',
  form: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open(method, API_URL + path)
    xhr.responseType = 'json'
    xhr.setRequestHeader('Accept', 'application/json')
    if (authToken) xhr.setRequestHeader('Authorization', `Bearer ${authToken}`)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response as T)
      else {
        try {
          handleError(xhr.status, xhr.response, Boolean(authToken))
        } catch (err) {
          reject(err)
        }
      }
    }
    xhr.onerror = () => reject(new ApiError(0, 'Se perdió la conexión durante la subida.'))
    xhr.send(form)
  })
}

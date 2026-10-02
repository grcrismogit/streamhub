// Un único lugar con todas las llamadas a la API.
import { request, uploadWithProgress } from './client'
import type { Comment, PublicUser, TokenResponse, User, Video, VideoPage, VideoSort } from './types'

export * from './client'
export type * from './types'

// ---------- Usuarios / Auth ----------
export const api = {
  register: (data: { name: string; email: string; password: string }) =>
    request<User>('/users', { method: 'POST', body: data }),

  login: (email: string, password: string) =>
    request<TokenResponse>('/login', {
      method: 'POST',
      // OAuth2 password flow: application/x-www-form-urlencoded con "username"
      body: new URLSearchParams({ username: email, password }),
    }),

  me: () => request<User>('/users/me'),
  getUser: (id: number) => request<PublicUser>(`/users/${id}`),

  // ---------- Videos ----------
  listVideos: (
    params: { q?: string; user_id?: number; sort?: VideoSort; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) => request<VideoPage>('/videos', { query: params, signal }),

  getVideo: (id: number, signal?: AbortSignal) => request<Video>(`/videos/${id}`, { signal }),

  recommended: (id: number, signal?: AbortSignal) =>
    request<Video[]>(`/videos/${id}/recommended`, { query: { limit: 8 }, signal }),

  registerView: (id: number) =>
    request<{ id: number; views: number }>(`/videos/${id}/view`, { method: 'POST' }),

  createVideo: (form: FormData, onProgress?: (p: number) => void) =>
    uploadWithProgress<Video>('/videos', 'POST', form, onProgress),

  updateVideo: (id: number, form: FormData, onProgress?: (p: number) => void) =>
    uploadWithProgress<Video>(`/videos/${id}`, 'PUT', form, onProgress),

  deleteVideo: (id: number) => request<void>(`/videos/${id}`, { method: 'DELETE' }),

  // ---------- Comentarios ----------
  listComments: (videoId: number, signal?: AbortSignal) =>
    request<Comment[]>(`/videos/${videoId}/comments`, { signal }),

  createComment: (videoId: number, content: string) =>
    request<Comment>(`/videos/${videoId}/comments`, { method: 'POST', body: { content } }),
}

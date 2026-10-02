// Tipos que reflejan los esquemas de la API (FastAPI / Pydantic).

export interface User {
  id: number
  name: string
  email: string
  created_at: string
  video_count: number
}

export interface PublicUser {
  id: number
  name: string
  created_at: string
  video_count: number
}

export interface Owner {
  id: number
  name: string
}

export interface Video {
  id: number
  title: string
  description: string
  video_url: string
  thumbnail_url: string
  views: number
  user_id: number
  owner: Owner
  created_at: string
  updated_at: string
}

export interface VideoPage {
  items: Video[]
  total: number
  limit: number
  offset: number
}

export interface Comment {
  id: number
  content: string
  user_id: number
  video_id: number
  created_at: string
  author: Owner
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export type VideoSort = 'recent' | 'popular'

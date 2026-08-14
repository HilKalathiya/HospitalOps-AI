/**
 * HospitalOps AI — API client foundation.
 *
 * Provides a base fetch wrapper configured for the backend API.
 * In future chunks this will be expanded with authentication headers,
 * request retry logic, and typed response helpers.
 */

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

interface RequestOptions<TBody = unknown> {
  method?: HttpMethod
  body?: TBody
  headers?: Record<string, string>
  signal?: AbortSignal
}

interface ApiError {
  error: string
  message: string
  detail: unknown | null
}

export class ApiClientError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly apiError: ApiError,
  ) {
    super(apiError.message)
    this.name = 'ApiClientError'
  }
}

let _accessToken: string | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
}

/**
 * Base request function. All API calls should go through this.
 */
async function request<TResponse>(
  path: string,
  options: RequestOptions = {},
  isRetry = false,
): Promise<TResponse> {
  const { method = 'GET', body, headers = {}, signal } = options

  const mergedHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...headers,
  }

  if (_accessToken) {
    mergedHeaders['Authorization'] = `Bearer ${_accessToken}`
  }

  // Include credentials so the HttpOnly refresh token cookie is sent
  let response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    signal,
    headers: mergedHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })

  // Handle automatic token refresh if we get a 401
  if (response.status === 401 && !isRetry && path !== '/auth/login' && path !== '/auth/refresh') {
    try {
      // Attempt to refresh the session
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        credentials: 'include',
      })

      if (refreshResponse.ok) {
        const { access_token } = await refreshResponse.json()
        setAccessToken(access_token)
        
        // Retry the original request
        mergedHeaders['Authorization'] = `Bearer ${access_token}`
        response = await fetch(`${API_BASE_URL}${path}`, {
          method,
          signal,
          headers: mergedHeaders,
          body: body !== undefined ? JSON.stringify(body) : undefined,
          credentials: 'include',
        })
      } else {
        // Refresh failed, clear token
        setAccessToken(null)
      }
    } catch {
      setAccessToken(null)
    }
  }

  if (!response.ok) {
    let apiError: ApiError
    try {
      apiError = (await response.json()) as ApiError
    } catch {
      apiError = {
        error: 'UNKNOWN_ERROR',
        message: `HTTP ${response.status}: ${response.statusText}`,
        detail: null,
      }
    }
    throw new ApiClientError(response.status, apiError)
  }

  return response.json() as Promise<TResponse>
}

// ── Convenience methods ───────────────────────────────────────────────────────

export const apiClient = {
  get: <TResponse>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'GET' }),

  post: <TResponse, TBody = unknown>(path: string, body?: TBody, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'POST', body }),

  put: <TResponse, TBody = unknown>(path: string, body?: TBody, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'PUT', body }),

  patch: <TResponse, TBody = unknown>(path: string, body?: TBody, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'PATCH', body }),

  delete: <TResponse>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<TResponse>(path, { ...options, method: 'DELETE' }),
}

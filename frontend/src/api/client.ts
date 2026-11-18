import { useAuthStore } from '../store/auth';
import type { ApiErrorDetail, BaseResponse, TokenPairResponse, UnpackedResponse } from '../types/api';

export class ApiError extends Error {
  statusCode: number;
  errors: ApiErrorDetail[];
  data?: unknown;
  response?: {
    status: number;
    data: unknown;
  };

  constructor(statusCode: number, errors: ApiErrorDetail[] = [], message?: string, data?: unknown) {
    const defaultMsg = errors.length > 0
      ? errors.map((e) => e.detail || e.message || e.msg || JSON.stringify(e)).join(', ')
      : `API Error with status ${statusCode}`;
    super(message || defaultMsg);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errors = errors;
    this.data = data;
    this.response = {
      status: statusCode,
      data,
    };
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function executeTokenRefresh(): Promise<string | null> {
  const currentRefreshToken = useAuthStore.getState().refreshToken;
  const currentPath = `${window.location.pathname}${window.location.search}`;
  const redirectTarget = `/login?redirect=${encodeURIComponent(currentPath)}`;

  if (!currentRefreshToken) {
    useAuthStore.getState().logout();
    if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
      window.location.href = redirectTarget;
    }
    return null;
  }

  try {
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ refresh_token: currentRefreshToken }),
    });

    const data = (await response.json()) as BaseResponse<TokenPairResponse>;

    if (!response.ok || (data.errors && data.errors.length > 0) || !data.body?.access_token) {
      throw new Error('Failed to refresh token');
    }

    useAuthStore.getState().setTokens(data.body.access_token, data.body.refresh_token);
    return data.body.access_token;
  } catch (err) {
    useAuthStore.getState().logout();
    if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
      window.location.href = redirectTarget;
    }
    return null;
  } finally {
    refreshPromise = null;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<UnpackedResponse<T>> {
  const normalizedPath = path.startsWith('/')
    ? path
    : `/api/v1/${path}`;

  const fullPath = normalizedPath.startsWith('/api')
    ? normalizedPath
    : `/api/v1${normalizedPath}`;

  const headers = new Headers(options.headers || {});

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  const { accessToken } = useAuthStore.getState();
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(fullPath, {
      ...options,
      headers,
    });
  } catch (networkError) {
    throw new ApiError(0, [{ message: 'Сетевая ошибка или сервер недоступен' }], (networkError as Error).message);
  }

  const isAuthEndpoint =
    fullPath.includes('/auth/login') ||
    fullPath.includes('/auth/register') ||
    fullPath.includes('/auth/refresh') ||
    fullPath.includes('/auth/verification-code');

  // Handle 401 with Single-flight refresh token queue
  if (response.status === 401 && !isAuthEndpoint) {
    if (!refreshPromise) {
      refreshPromise = executeTokenRefresh();
    }

    const newAccessToken = await refreshPromise;
    if (!newAccessToken) {
      throw new ApiError(401, [{ message: 'Сессия истекла. Пожалуйста, войдите снова.' }]);
    }

    // Replay request with new access token
    headers.set('Authorization', `Bearer ${newAccessToken}`);
    try {
      response = await fetch(fullPath, {
        ...options,
        headers,
      });
    } catch (networkError) {
      throw new ApiError(0, [{ message: 'Сетевая ошибка при повторе запроса' }], (networkError as Error).message);
    }
  }

  let json: BaseResponse<T>;
  try {
    json = await response.json();
  } catch {
    if (!response.ok) {
      throw new ApiError(response.status, [{ message: response.statusText || 'Неизвестная ошибка сервера' }]);
    }
    // Return empty payload if not JSON
    return {
      data: null as unknown as T,
      statusCode: response.status,
    };
  }

  const isErrorStatus = response.status >= 400 || (json.status_code && json.status_code >= 400);
  const hasErrors = Array.isArray(json.errors) && json.errors.length > 0;

  if (isErrorStatus || hasErrors) {
    const primaryError = json.errors?.[0];
    const rawDetail =
      (primaryError && typeof primaryError === 'object' && (primaryError.detail || primaryError.message || primaryError.msg)) ||
      (json as unknown as { detail?: string }).detail;

    const extractedMessage =
      typeof rawDetail === 'string' && rawDetail.trim()
        ? rawDetail.trim()
        : rawDetail
        ? JSON.stringify(rawDetail)
        : `API Error ${json.status_code || response.status}`;

    throw new ApiError(
      json.status_code || response.status,
      json.errors || [],
      extractedMessage,
      json
    );
  }

  return {
    data: json.body,
    metadata: json.metadata,
    statusCode: json.status_code || response.status,
  };
}

import { apiFetch } from './client';
import type {
  CartItemRequest,
  CartResponse,
  CategoryResponse,
  CreateReviewRequest,
  LoginRequest,
  ProductDetailResponse,
  ProductResponse,
  RegisterRequest,
  RegisterResponse,
  ReviewResponse,
  SearchResultResponse,
  SendEmailCodeRequest,
  TokenPairResponse,
  UpdatePersonalRequest,
  UserPersonalResponse,
  UserProfileResponse,
  UserResponse,
  VerificationInitResponse,
  VerifyCodeRequest,
} from '../types/api';

export const authApi = {
  login: (data: LoginRequest) =>
    apiFetch<TokenPairResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  register: (data: RegisterRequest) =>
    apiFetch<RegisterResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  verifyCode: (data: VerifyCodeRequest) =>
    apiFetch<UserResponse>('/api/v1/auth/verification-code', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  sendEmailCode: (data: SendEmailCodeRequest) =>
    apiFetch<VerificationInitResponse>('/api/v1/auth/email/send-code', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  logout: () =>
    apiFetch<null>('/api/v1/auth/logout', {
      method: 'POST',
    }),

  getMe: () =>
    apiFetch<UserProfileResponse>('/api/v1/users/me', {
      method: 'GET',
    }),
};

export const usersApi = {
  updatePersonal: (data: UpdatePersonalRequest) =>
    apiFetch<UserPersonalResponse>('/api/v1/users/me/personal', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};

export const categoriesApi = {
  list: () => apiFetch<CategoryResponse[]>('/api/v1/categories', { method: 'GET' }),
};

export interface ProductListParams {
  category_id?: string;
  min_price?: number | string;
  max_price?: number | string;
  search?: string;
  limit?: number;
  offset?: number;
}

export const productsApi = {
  list: (params: ProductListParams = {}) => {
    const sp = new URLSearchParams();
    if (params.category_id) sp.set('category_id', params.category_id);
    if (params.min_price !== undefined && params.min_price !== '') sp.set('min_price', String(params.min_price));
    if (params.max_price !== undefined && params.max_price !== '') sp.set('max_price', String(params.max_price));
    if (params.search) sp.set('search', params.search);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));

    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<ProductResponse[]>(`/api/v1/products${query}`, { method: 'GET' });
  },

  getBySlug: (slug: string) =>
    apiFetch<ProductDetailResponse>(`/api/v1/products/${slug}`, { method: 'GET' }),

  getReviews: (productId: string, limit = 20, offset = 0) =>
    apiFetch<ReviewResponse[]>(
      `/api/v1/products/${productId}/reviews?limit=${limit}&offset=${offset}`,
      { method: 'GET' }
    ),

  createReview: (productId: string, data: CreateReviewRequest) =>
    apiFetch<ReviewResponse>(`/api/v1/products/${productId}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export const searchApi = {
  search: (q: string, limit = 10) => {
    const sp = new URLSearchParams({ q, limit: String(limit) });
    return apiFetch<SearchResultResponse>(`/api/v1/search?${sp.toString()}`, {
      method: 'GET',
    });
  },
};

export const favoritesApi = {
  list: () => apiFetch<ProductResponse[]>('/api/v1/favorites', { method: 'GET' }),

  add: (productId: string) =>
    apiFetch<unknown>(`/api/v1/favorites/${productId}`, { method: 'POST' }),

  remove: (productId: string) =>
    apiFetch<null>(`/api/v1/favorites/${productId}`, { method: 'DELETE' }),
};

export const cartApi = {
  get: () => apiFetch<CartResponse>('/api/v1/cart', { method: 'GET' }),

  updateItem: (variantId: string, quantity: number) => {
    const body: CartItemRequest = { quantity };
    return apiFetch<Record<string, boolean>>(`/api/v1/cart/items/${variantId}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  removeItem: (variantId: string) =>
    apiFetch<Record<string, boolean>>(`/api/v1/cart/items/${variantId}`, {
      method: 'DELETE',
    }),

  clear: () =>
    apiFetch<Record<string, boolean>>('/api/v1/cart', {
      method: 'DELETE',
    }),
};

import { apiFetch } from './client';
import { notificationsApi } from './notifications';
import { moderationApi } from './moderation';
import { brandsApi } from './brands';
import type {
  CartItemRequest,
  CartResponse,
  CategoryResponse,
  CreateReviewRequest,
  LoginRequest,
  OrderResponse,
  OrderStatus,
  ProductCreateRequest,
  ProductUpdateRequest,
  ProductVariantCreateRequest,
  ProductVariantUpdateRequest,
  ProductVariantResponse,
  ProductDetailResponse,
  ProductImageResponse,
  ProductResponse,
  RegisterRequest,
  RegisterResponse,
  RefreshTokenRequest,
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
  CreateAddressRequest,
  UserAddressResponse,
} from '../types/api';

export { notificationsApi, moderationApi, brandsApi };

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

  refresh: (data: RefreshTokenRequest) =>
    apiFetch<TokenPairResponse>('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify(data),
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

export const addressesApi = {
  list: () =>
    apiFetch<UserAddressResponse[]>('/api/v1/users/me/addresses', { method: 'GET' }),

  create: (data: CreateAddressRequest) =>
    apiFetch<UserAddressResponse>('/api/v1/users/me/addresses', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  setDefault: (addressId: string) =>
    apiFetch<UserAddressResponse>(`/api/v1/users/me/addresses/${addressId}/default`, {
      method: 'PATCH',
    }),

  delete: (addressId: string) =>
    apiFetch<null>(`/api/v1/users/me/addresses/${addressId}`, {
      method: 'DELETE',
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
  size?: string;
  color?: string;
  is_limited?: boolean;
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
    if (params.size) sp.set('size', params.size);
    if (params.color) sp.set('color', params.color);
    if (params.is_limited !== undefined) sp.set('is_limited', String(params.is_limited));
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

  create: (data: ProductCreateRequest) =>
    apiFetch<ProductResponse>('/api/v1/products', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (productId: string, data: ProductUpdateRequest) =>
    apiFetch<ProductResponse>(`/api/v1/products/${productId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (productId: string) =>
    apiFetch<null>(`/api/v1/products/${productId}`, {
      method: 'DELETE',
    }),

  uploadImage: (productId: string, formData: FormData) =>
    apiFetch<ProductImageResponse>(`/api/v1/products/${productId}/images/upload`, {
      method: 'POST',
      body: formData,
    }),

  deleteImage: (productId: string, imageId: string) =>
    apiFetch<null>(`/api/v1/products/${productId}/images/${imageId}`, {
      method: 'DELETE',
    }),

  createVariant: (productId: string, data: ProductVariantCreateRequest) =>
    apiFetch<ProductVariantResponse>(`/api/v1/products/${productId}/variants`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateVariant: (variantId: string, data: ProductVariantUpdateRequest) =>
    apiFetch<ProductVariantResponse>(`/api/v1/variants/${variantId}`, {
      method: 'PATCH',
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

export const ordersApi = {
  list: (params: { status?: OrderStatus; limit?: number; offset?: number } = {}) => {
    const sp = new URLSearchParams();
    if (params.status) sp.set('status', params.status);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<OrderResponse[]>(`/api/v1/orders${query}`, { method: 'GET' });
  },

  getById: (orderId: string) =>
    apiFetch<OrderResponse>(`/api/v1/orders/${orderId}`, { method: 'GET' }),

  cancel: (orderId: string) =>
    apiFetch<OrderResponse>(`/api/v1/orders/${orderId}/cancel`, { method: 'POST' }),
};

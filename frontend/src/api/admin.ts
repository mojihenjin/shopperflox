import { apiFetch } from './client';
import type {
  AdminBanUserRequest,
  AdminBrandResponse,
  AdminCategoryCreateRequest,
  AdminCategoryUpdateRequest,
  AdminReviewResponse,
  AdminUserBanResponse,
  AdminUserResponse,
  AdminUserUpdateRequest,
  CategoryResponse,
  ProductResponse,
} from '../types/api';

export interface AdminListUsersParams {
  search?: string;
  status?: 'all' | 'active' | 'banned' | 'unbanned' | 'deleted';
  verified_profile?: boolean;
  sort_by?: 'created_at' | 'login';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface AdminListBrandsParams {
  search?: string;
  moderation_status?: string;
  is_verified?: boolean;
  include_deleted?: boolean;
  sort_by?: 'created_at' | 'name' | 'views_count' | 'orders_count';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface AdminListCategoriesParams {
  search?: string;
  sort_by?: 'sort_order' | 'created_at' | 'name';
  sort_order?: 'asc' | 'desc';
}

export interface AdminListProductsParams {
  search?: string;
  moderation_status?: string;
  is_hidden?: number;
  is_limited?: boolean;
  sort_by?: 'created_at' | 'base_price' | 'views_count' | 'orders_count' | 'title';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface AdminListReviewsParams {
  search?: string;
  rating?: number;
  sort_by?: 'created_at' | 'rating';
  sort_order?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export const adminApi = {
  // --- USERS ---
  listUsers: (params: AdminListUsersParams = {}) => {
    const sp = new URLSearchParams();
    if (params.search) sp.set('search', params.search);
    if (params.status && params.status !== 'all') sp.set('status', params.status);
    if (params.verified_profile !== undefined) sp.set('verified_profile', String(params.verified_profile));
    if (params.sort_by) sp.set('sort_by', params.sort_by);
    if (params.sort_order) sp.set('sort_order', params.sort_order);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<AdminUserResponse[]>(`/api/v1/admin/users${q}`, { method: 'GET' });
  },

  updateUser: (userId: string, data: AdminUserUpdateRequest) =>
    apiFetch<AdminUserResponse>(`/api/v1/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteUser: (userId: string) =>
    apiFetch<null>(`/api/v1/admin/users/${userId}`, { method: 'DELETE' }),

  banUser: (userId: string, data: AdminBanUserRequest) =>
    apiFetch<AdminUserBanResponse>(`/api/v1/admin/users/${userId}/ban`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  unbanUser: (userId: string) =>
    apiFetch<AdminUserBanResponse>(`/api/v1/admin/users/${userId}/unban`, {
      method: 'POST',
    }),

  resetPassword: (userId: string) =>
    apiFetch<unknown>(`/api/v1/admin/users/${userId}/reset-password`, {
      method: 'POST',
    }),

  // --- BRANDS ---
  listBrands: (params: AdminListBrandsParams = {}) => {
    const sp = new URLSearchParams();
    if (params.search) sp.set('search', params.search);
    if (params.moderation_status) sp.set('moderation_status', params.moderation_status);
    if (params.is_verified !== undefined) sp.set('is_verified', String(params.is_verified));
    if (params.include_deleted !== undefined) sp.set('include_deleted', String(params.include_deleted));
    if (params.sort_by) sp.set('sort_by', params.sort_by);
    if (params.sort_order) sp.set('sort_order', params.sort_order);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<AdminBrandResponse[]>(`/api/v1/admin/brands${q}`, { method: 'GET' });
  },

  remoderateBrand: (brandId: string) =>
    apiFetch<AdminBrandResponse>(`/api/v1/admin/brands/${brandId}/remoderate`, {
      method: 'POST',
    }),

  hideAllBrandProducts: (brandId: string) =>
    apiFetch<unknown>(`/api/v1/admin/brands/${brandId}/hide-all-products`, {
      method: 'POST',
    }),

  // --- CATEGORIES ---
  listCategories: (params: AdminListCategoriesParams = {}) => {
    const sp = new URLSearchParams();
    if (params.search) sp.set('search', params.search);
    if (params.sort_by) sp.set('sort_by', params.sort_by);
    if (params.sort_order) sp.set('sort_order', params.sort_order);
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<CategoryResponse[]>(`/api/v1/admin/categories${q}`, { method: 'GET' });
  },

  createCategory: (data: AdminCategoryCreateRequest) =>
    apiFetch<CategoryResponse>('/api/v1/admin/categories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateCategory: (categoryId: string, data: AdminCategoryUpdateRequest) =>
    apiFetch<CategoryResponse>(`/api/v1/admin/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteCategory: (categoryId: string) =>
    apiFetch<null>(`/api/v1/admin/categories/${categoryId}`, { method: 'DELETE' }),

  // --- PRODUCTS ---
  listProducts: (params: AdminListProductsParams = {}) => {
    const sp = new URLSearchParams();
    if (params.search) sp.set('search', params.search);
    if (params.moderation_status) sp.set('moderation_status', params.moderation_status);
    if (params.is_hidden !== undefined) sp.set('is_hidden', String(params.is_hidden));
    if (params.is_limited !== undefined) sp.set('is_limited', String(params.is_limited));
    if (params.sort_by) sp.set('sort_by', params.sort_by);
    if (params.sort_order) sp.set('sort_order', params.sort_order);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<ProductResponse[]>(`/api/v1/admin/products${q}`, { method: 'GET' });
  },

  remoderateProduct: (productId: string) =>
    apiFetch<ProductResponse>(`/api/v1/admin/products/${productId}/remoderate`, {
      method: 'POST',
    }),

  // --- REVIEWS ---
  listReviews: (params: AdminListReviewsParams = {}) => {
    const sp = new URLSearchParams();
    if (params.search) sp.set('search', params.search);
    if (params.rating !== undefined) sp.set('rating', String(params.rating));
    if (params.sort_by) sp.set('sort_by', params.sort_by);
    if (params.sort_order) sp.set('sort_order', params.sort_order);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const q = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<AdminReviewResponse[]>(`/api/v1/admin/reviews${q}`, { method: 'GET' });
  },

  deleteReview: (reviewId: string) =>
    apiFetch<null>(`/api/v1/admin/reviews/${reviewId}`, { method: 'DELETE' }),
};

import { apiFetch } from './client';
import type {
  AddBrandMemberRequest,
  BrandCreateRequest,
  BrandMemberResponse,
  BrandResponse,
  BrandUpdateRequest,
  MyBrandResponse,
  RemoveMemberResponse,
} from '../types/api';

export interface BrandListParams {
  limit?: number;
  offset?: number;
}

export const brandsApi = {
  list: (params: BrandListParams = {}) => {
    const sp = new URLSearchParams();
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<BrandResponse[]>(`/api/v1/brands${query}`, { method: 'GET' });
  },

  my: () => apiFetch<MyBrandResponse[]>('/api/v1/brands/my', { method: 'GET' }),

  getBySlug: (slug: string) =>
    apiFetch<BrandResponse>(`/api/v1/brands/${encodeURIComponent(slug)}`, { method: 'GET' }),

  create: (data: BrandCreateRequest) =>
    apiFetch<BrandResponse>('/api/v1/brands', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (brandId: string, data: BrandUpdateRequest) =>
    apiFetch<BrandResponse>(`/api/v1/brands/${brandId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  uploadLogo: (brandId: string, formData: FormData) =>
    apiFetch<BrandResponse>(`/api/v1/brands/${brandId}/logo`, {
      method: 'POST',
      body: formData,
    }),

  delete: (brandId: string) =>
    apiFetch<BrandResponse>(`/api/v1/brands/${brandId}`, {
      method: 'DELETE',
    }),

  listMembers: (brandId: string) =>
    apiFetch<BrandMemberResponse[]>(`/api/v1/brands/${brandId}/members`, {
      method: 'GET',
    }),

  addMember: (brandId: string, data: AddBrandMemberRequest) =>
    apiFetch<BrandMemberResponse>(`/api/v1/brands/${brandId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  removeMember: (brandId: string, userId: string) =>
    apiFetch<RemoveMemberResponse>(`/api/v1/brands/${brandId}/members/${userId}`, {
      method: 'DELETE',
    }),
};

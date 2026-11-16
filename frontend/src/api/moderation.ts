import { apiFetch } from './client';
import type {
  ProductResponse,
  PendingCountResponse,
  RejectProductRequest,
  ModerationRequestType,
} from '../types/api';

export interface ListPendingProductsParams {
  request_type?: ModerationRequestType;
  limit?: number;
  offset?: number;
}

export const moderationApi = {
  list: (params: ListPendingProductsParams = {}) => {
    const sp = new URLSearchParams();
    if (params.request_type) sp.set('request_type', params.request_type);
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<ProductResponse[]>(`/api/v1/moderation/products${query}`, {
      method: 'GET',
    });
  },

  getPendingCount: () =>
    apiFetch<PendingCountResponse>('/api/v1/moderation/products/pending-count', {
      method: 'GET',
    }),

  approve: (productId: string) =>
    apiFetch<ProductResponse>(`/api/v1/moderation/products/${productId}/approve`, {
      method: 'POST',
    }),

  reject: (productId: string, data: RejectProductRequest = {}) =>
    apiFetch<ProductResponse>(`/api/v1/moderation/products/${productId}/reject`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

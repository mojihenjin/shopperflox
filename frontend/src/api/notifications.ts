import { apiFetch } from './client';
import type {
  NotificationResponse,
  UnreadCountResponse,
  ReadAllNotificationsResponse,
} from '../types/api';

export type {
  NotificationResponse,
  UnreadCountResponse,
  ReadAllNotificationsResponse,
};

export interface ListNotificationsParams {
  limit?: number;
  offset?: number;
}

export const notificationsApi = {
  list: (params: ListNotificationsParams = {}) => {
    const sp = new URLSearchParams();
    if (params.limit !== undefined) sp.set('limit', String(params.limit));
    if (params.offset !== undefined) sp.set('offset', String(params.offset));
    const query = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch<NotificationResponse[]>(`/api/v1/notifications${query}`, {
      method: 'GET',
    });
  },

  getUnreadCount: () =>
    apiFetch<UnreadCountResponse>('/api/v1/notifications/unread-count', {
      method: 'GET',
    }),

  markAsRead: (notificationId: string) =>
    apiFetch<NotificationResponse>(`/api/v1/notifications/${notificationId}/read`, {
      method: 'PATCH',
    }),

  markAllAsRead: () =>
    apiFetch<ReadAllNotificationsResponse>('/api/v1/notifications/read-all', {
      method: 'POST',
    }),
};

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsApi } from '../api/notifications';
import { formatDateTime } from '../utils/format';
import type { NotificationResponse } from '../types/api';

interface NotificationsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationsDrawer({ isOpen, onClose }: NotificationsDrawerProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent body scrolling when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Fetch notifications
  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list({ limit: 50 }),
    enabled: isOpen,
    staleTime: 10 * 1000,
  });

  const notifications = notificationsData?.data || [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  // Mark all as read mutation
  const markAllMutation = useMutation({
    mutationFn: () => notificationsApi.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadNotificationsCount'] });
    },
  });

  // Mark single as read mutation
  const markSingleMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unreadNotificationsCount'] });
    },
  });

  const handleLinkClick = (item: NotificationResponse) => {
    if (!item.is_read) {
      markSingleMutation.mutate(item.id);
    }
    onClose();
    if (item.link) {
      if (item.link.startsWith('/')) {
        navigate(item.link);
      } else {
        window.location.href = item.link;
      }
    }
  };

  const handleMarkAsRead = (e: React.MouseEvent, item: NotificationResponse) => {
    e.stopPropagation();
    if (!item.is_read) {
      markSingleMutation.mutate(item.id);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-[#3F2021]/40 transition-opacity"
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <aside
        className="fixed inset-y-0 right-0 max-w-full flex pl-10"
        aria-label="Панель уведомлений"
      >
        <div className="w-screen max-w-md bg-[#F2E9DB] border-l border-[#3F2021]/20 flex flex-col h-full rounded-none">
          {/* Header */}
          <div className="p-5 md:p-6 border-b border-[#3F2021]/20 flex items-center justify-between gap-4 bg-[#F2E9DB]">
            <div className="flex items-baseline gap-2">
              <h2 className="font-serif text-xl sm:text-2xl uppercase tracking-wider text-[#3F2021]">
                УВЕДОМЛЕНИЯ
              </h2>
              {unreadCount > 0 && (
                <span className="text-[11px] font-mono font-bold text-[#3F2021]">
                  ({unreadCount})
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={() => markAllMutation.mutate()}
                  disabled={markAllMutation.isPending}
                  className="text-[10px] font-sans font-semibold uppercase tracking-wider px-2.5 py-1 border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors rounded-none disabled:opacity-50"
                >
                  {markAllMutation.isPending ? 'ОБНОВЛЕНИЕ...' : 'ПРОЧИТАТЬ ВСЕ'}
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                aria-label="Закрыть уведомления"
                className="text-2xl leading-none font-sans text-[#3F2021] hover:opacity-60 transition-opacity px-1"
              >
                ×
              </button>
            </div>
          </div>

          {/* Notifications List */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-3.5 scrollbar-none">
            {isLoading ? (
              <div className="py-20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( ЗАГРУЗКА УВЕДОМЛЕНИЙ... )
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-20 text-center border border-[#3F2021]/20 p-6 rounded-none">
                <div className="font-serif text-lg uppercase tracking-wider text-[#3F2021]">
                  НЕТ УВЕДОМЛЕНИЙ
                </div>
                <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                  Здесь будут появляться сообщения об изменении статусов ваших заказов и доставки
                </p>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => !item.is_read && markSingleMutation.mutate(item.id)}
                  className={`p-4 transition-all rounded-none ${
                    !item.is_read
                      ? 'border-l-4 border-[#3F2021] bg-[#FFFFFF] border-t border-r border-b border-[#3F2021]/15 cursor-pointer'
                      : 'border border-[#3F2021]/15 bg-[#F2E9DB]/60 opacity-80'
                  }`}
                >
                  {/* Top row: Title & Date */}
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-serif text-sm font-semibold uppercase tracking-wider text-[#3F2021]">
                      {item.title}
                    </span>
                    <span className="font-mono text-[10px] text-[#3F2021]/60 whitespace-nowrap">
                      {formatDateTime(item.created_at)}
                    </span>
                  </div>

                  {/* Body Text */}
                  <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/80 leading-relaxed mt-2 whitespace-pre-line">
                    {item.body}
                  </p>

                  {/* Bottom row: Link and read status action */}
                  <div className="mt-3 flex items-center justify-between gap-2 pt-2 border-t border-[#3F2021]/10">
                    {item.link ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLinkClick(item);
                        }}
                        className="inline-flex items-center gap-1 text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] hover:underline underline-offset-4"
                      >
                        ПЕРЕЙТИ К ДЕТАЛЯМ ↗
                      </button>
                    ) : (
                      <span className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/40">
                        SHOPPERFLOX
                      </span>
                    )}

                    {!item.is_read && (
                      <button
                        type="button"
                        onClick={(e) => handleMarkAsRead(e, item)}
                        className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60 hover:text-[#3F2021] underline underline-offset-2"
                      >
                        ПРОЧИТАНО
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

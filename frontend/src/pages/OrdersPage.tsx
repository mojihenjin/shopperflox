import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ordersApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { formatDate, formatPrice } from '../utils/format';
import type { OrderStatus } from '../types/api';

const STATUS_LABELS: Record<OrderStatus, { text: string; bg: string; color: string }> = {
  pending_payment: { text: 'ОЖИДАЕТ ОПЛАТЫ', bg: 'bg-[#3F2021]/10', color: 'text-[#3F2021]' },
  paid: { text: 'ОПЛАЧЕН', bg: 'bg-[#3F2021]/15', color: 'text-[#3F2021]' },
  processing: { text: 'В ОБРАБОТКЕ', bg: 'bg-[#3F2021]/20', color: 'text-[#3F2021]' },
  shipped: { text: 'В ПУТИ / ОТПРАВЛЕН', bg: 'bg-[#3F2021]', color: 'text-[#F2E9DB]' },
  delivered: { text: 'ДОСТАВЛЕН', bg: 'bg-[#3F2021]', color: 'text-[#F2E9DB]' },
  cancelled: { text: 'ОТМЕНЁН', bg: 'bg-[#FF8562]/20', color: 'text-[#3F2021]' },
  refunded: { text: 'ВОЗВРАТ СРЕДСТВ', bg: 'bg-[#FF8562]/20', color: 'text-[#3F2021]' },
};

export function OrdersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuthStore();
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  const { data: ordersData, isLoading, error } = useQuery({
    queryKey: ['orders'],
    queryFn: () => ordersApi.list({ limit: 50 }),
    enabled: isAuthenticated,
  });

  const orders = ordersData?.data || [];

  const handleCopyPostCode = async (postCode: string) => {
    try {
      await navigator.clipboard.writeText(postCode);
      setCopiedCode(postCode);
      setTimeout(() => {
        setCopiedCode(null);
      }, 2500);
    } catch {
      // Fallback
      setCopiedCode(postCode);
      setTimeout(() => {
        setCopiedCode(null);
      }, 2500);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex flex-col items-center justify-center px-4 py-24 text-center">
        <h1 className="font-serif text-3xl md:text-4xl uppercase tracking-wider text-[#3F2021]">
          ИСТОРИЯ ЗАКАЗОВ
        </h1>
        <p className="mt-3 text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 max-w-md">
          Для просмотра ваших заказов и отслеживания отправлений необходимо войти в личный кабинет.
        </p>
        <button
          type="button"
          onClick={() => navigate(loginRedirectUrl, { state: { from: location } })}
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-8 py-3.5 text-xs font-sans uppercase tracking-widest transition-colors rounded-none"
        >
          ВОЙТИ В АККАУНТ ↗
        </button>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#F2E9DB] min-h-screen py-10 md:py-16">
      <div className="w-full max-w-none px-4 md:px-8 space-y-10">
        {/* Header */}
        <div className="border-b border-[#3F2021]/20 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
              ( ЛИЧНЫЙ КАБИНЕТ )
            </span>
            <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021] mt-1">
              ВАШИ ЗАКАЗЫ
            </h1>
          </div>
          <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
            ВСЕГО ЗАКАЗОВ: {orders.length}
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
            ( ЗАГРУЗКА ИСТОРИИ ЗАКАЗОВ... )
          </div>
        ) : error ? (
          <div className="py-16 text-center border border-[#3F2021]/20 p-8 rounded-none">
            <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
              НЕ УДАЛОСЬ ЗАГРУЗИТЬ ЗАКАЗЫ
            </div>
            <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
              Произошла ошибка при получении данных. Попробуйте обновить страницу позже.
            </p>
          </div>
        ) : orders.length === 0 ? (
          <div className="py-20 text-center border border-[#3F2021]/20 p-8 rounded-none bg-[#F2E9DB]">
            <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
              У ВАС ПОКА НЕТ ОФОРМЛЕННЫХ ЗАКАЗОВ
            </div>
            <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-lg mx-auto">
              После оформления покупки здесь будут отображаться статус заказа, история изменений и информация для отслеживания отправления.
            </p>
            <Link
              to="/catalog"
              className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-8 py-3 text-xs font-sans uppercase tracking-wider transition-colors rounded-none"
            >
              ПЕРЕЙТИ В КАТАЛОГ ↗
            </Link>
          </div>
        ) : (
          <div className="space-y-8">
            {orders.map((order) => {
              const statusInfo = STATUS_LABELS[order.status] || {
                text: order.status,
                bg: 'bg-[#3F2021]/15',
                color: 'text-[#3F2021]',
              };
              const items = order.items || [];
              const orderShortId = order.id.slice(0, 8).toUpperCase();

              return (
                <div
                  key={order.id}
                  className="border border-[#3F2021]/30 bg-[#F2E9DB] rounded-none divide-y divide-[#3F2021]/15"
                >
                  {/* Order Card Header */}
                  <div className="p-4 sm:p-6 flex flex-wrap items-center justify-between gap-4 bg-[#F2E9DB]">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm sm:text-base font-bold text-[#3F2021] tracking-wider">
                          ЗАКАЗ #{orderShortId}
                        </span>
                        <span
                          className={`px-2.5 py-0.5 text-[10px] font-sans uppercase tracking-widest font-semibold rounded-none ${statusInfo.bg} ${statusInfo.color}`}
                        >
                          {statusInfo.text}
                        </span>
                      </div>
                      <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
                        ОФОРМЛЕН: {formatDate(order.created_at)}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
                        ИТОГО К ОПЛАТЕ:
                      </div>
                      <div className="font-serif text-xl sm:text-2xl font-bold text-[#3F2021]">
                        {formatPrice(order.total_amount)}
                      </div>
                    </div>
                  </div>

                  {/* Post-Code Block (if present) */}
                  {order.post_code && (
                    <div className="p-4 sm:p-6 bg-[#FFFFFF] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                        <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
                          ПОЧТОВЫЙ КОД / ТРЕКИНГ:
                        </span>
                        <span className="font-mono text-xs sm:text-sm font-bold text-[#3F2021] tracking-wider bg-[#F2E9DB] px-3 py-1 border border-[#3F2021]/20 select-all">
                          POST-CODE: {order.post_code}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleCopyPostCode(order.post_code!)}
                        className="self-start sm:self-auto px-4 py-1.5 text-xs font-sans font-semibold uppercase tracking-wider border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors rounded-none whitespace-nowrap"
                      >
                        {copiedCode === order.post_code ? 'СКОПИРОВАНО ✓' : 'СКОПИРОВАТЬ'}
                      </button>
                    </div>
                  )}

                  {/* Tracking Number (if present and distinct from post_code) */}
                  {order.tracking_number && order.tracking_number !== order.post_code && (
                    <div className="px-4 sm:px-6 py-3 bg-[#F2E9DB]/60 flex items-center justify-between text-xs font-sans uppercase tracking-wider text-[#3F2021]/80">
                      <span>ТРЕК-НОМЕР СЛУЖБЫ ДОСТАВКИ:</span>
                      <span className="font-mono font-semibold text-[#3F2021]">{order.tracking_number}</span>
                    </div>
                  )}

                  {/* Items List */}
                  <div className="p-4 sm:p-6 space-y-4">
                    <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
                      ( СОСТАВ ЗАКАЗА — {items.length} ПОЗИЦИЙ )
                    </div>

                    <div className="divide-y divide-[#3F2021]/10">
                      {items.map((item) => {
                        const canLeaveReview = order.status === 'delivered';

                        return (
                          <div
                            key={item.id}
                            className="py-4 first:pt-0 last:pb-0 flex flex-col md:flex-row md:items-center justify-between gap-4"
                          >
                            {/* Product Info */}
                            <div className="space-y-1.5 flex-1">
                              <div>
                                {item.product_slug ? (
                                  <Link
                                    to={`/products/${item.product_slug}`}
                                    className="font-serif text-base sm:text-lg text-[#3F2021] hover:underline underline-offset-4 uppercase tracking-wide inline-block"
                                  >
                                    {item.title_snapshot} ↗
                                  </Link>
                                ) : (
                                  <span className="font-serif text-base sm:text-lg text-[#3F2021] uppercase tracking-wide">
                                    {item.title_snapshot}
                                  </span>
                                )}
                              </div>

                              <div className="flex flex-wrap items-center gap-3 text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
                                {item.color_snapshot && (
                                  <span>ЦВЕТ: <strong className="text-[#3F2021]">{item.color_snapshot}</strong></span>
                                )}
                                {item.size_snapshot && (
                                  <>
                                    <span>·</span>
                                    <span>РАЗМЕР: <strong className="text-[#3F2021]">{item.size_snapshot}</strong></span>
                                  </>
                                )}
                                {item.sku_snapshot && (
                                  <>
                                    <span>·</span>
                                    <span className="font-mono">АРТИКУЛ: {item.sku_snapshot}</span>
                                  </>
                                )}
                              </div>

                              <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]">
                                {item.quantity} шт. × {formatPrice(item.unit_price)} ={' '}
                                <strong className="font-semibold">{formatPrice(Number(item.unit_price) * item.quantity)}</strong>
                              </div>
                            </div>

                            {/* Review Action */}
                            <div className="flex-shrink-0 self-start md:self-center">
                              {canLeaveReview ? (
                                item.product_slug ? (
                                  <Link
                                    to={`/products/${item.product_slug}#reviews`}
                                    className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none whitespace-nowrap inline-block"
                                  >
                                    ОСТАВИТЬ ОТЗЫВ ↗
                                  </Link>
                                ) : (
                                  <span className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/50">
                                    ( ТОВАР НЕДОСТУПЕН )
                                  </span>
                                )
                              ) : (
                                <span className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/50 bg-[#3F2021]/5 px-3 py-1.5 border border-[#3F2021]/15 inline-block">
                                  ( ОТЗЫВ ДОСТУПЕН ПОСЛЕ ПОЛУЧЕНИЯ )
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

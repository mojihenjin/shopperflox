import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ordersApi } from '../api/endpoints';
import { formatPrice, formatDate } from '../utils/format';
import { formatApiError } from '../utils/errorMapper';
import type { ApiError } from '../api/client';

export function DebugPayPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [payError, setPayError] = useState<string | null>(null);

  const { data: orderData, isLoading, error } = useQuery({
    queryKey: ['orderDetail', orderId],
    queryFn: () => ordersApi.getById(orderId!),
    enabled: Boolean(orderId),
  });

  const order = orderData?.data;

  const debugPayMutation = useMutation({
    mutationFn: () => ordersApi.debugPay(orderId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['profileOrders'] });
      queryClient.invalidateQueries({ queryKey: ['orderDetail', orderId] });
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      navigate('/profile');
    },
    onError: (err: ApiError) => {
      setPayError(formatApiError(err, 'ОШИБКА ВЫПОЛНЕНИЯ ТЕСТОВОЙ ОПЛАТЫ'));
    },
  });

  if (isLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ПОЛУЧЕНИЕ ДАННЫХ ЗАКАЗА ДЛЯ ОПЛАТЫ... )
        </div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex flex-col items-center justify-center py-20 px-4 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          ЗАКАЗ НЕ НАЙДЕН
        </h1>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md">
          Не удалось найти информацию о заказе с идентификатором {orderId}.
        </p>
        <Link
          to="/profile"
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-8 py-3 text-xs font-sans uppercase tracking-wider transition-colors rounded-none"
        >
          ВЕРНУТЬСЯ В ПРОФИЛЬ ↗
        </Link>
      </div>
    );
  }

  const items = order.items || [];

  return (
    <div className="w-full bg-[#F2E9DB] min-h-screen py-12 md:py-20 px-4 md:px-8">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Header */}
        <div className="border-b border-[#3F2021]/20 pb-6">
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block mb-1">
            ( РЕЖИМ РАЗРАБОТКИ И ОТЛАДКИ )
          </span>
          <h1 className="font-serif text-3xl md:text-4xl uppercase tracking-wider text-[#3F2021]">
            ТЕСТОВАЯ ОПЛАТА (DEBUG MODE)
          </h1>
        </div>

        {payError && (
          <div className="p-4 bg-red-100 text-red-900 border border-red-300 text-xs font-sans rounded-none">
            {payError}
          </div>
        )}

        {/* Order Details Card */}
        <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 space-y-6 rounded-none">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
            <div>
              <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60 block">
                НОМЕР ЗАКАЗА
              </span>
              <span className="font-mono text-base font-bold text-[#3F2021] tracking-wider">
                ЗАКАЗ #{order.id.slice(0, 8).toUpperCase()}
              </span>
              <span className="text-[10px] font-mono text-[#3F2021]/50 block">
                ID: {order.id}
              </span>
            </div>

            <div className="text-right">
              <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60 block">
                СУММА К ОПЛАТЕ
              </span>
              <span className="font-serif text-2xl font-bold text-[#3F2021]">
                {formatPrice(order.total_amount)}
              </span>
            </div>
          </div>

          {/* Delivery & Recipient Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-sans">
            <div>
              <span className="text-[10px] uppercase text-[#3F2021]/60 block font-semibold">
                ПОЛУЧАТЕЛЬ
              </span>
              <span className="font-semibold uppercase text-[#3F2021]">
                {order.recipient_firstname} {order.recipient_lastname || ''} {order.recipient_middlename || ''}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase text-[#3F2021]/60 block font-semibold">
                СПОСОБ ДОСТАВКИ
              </span>
              <span className="text-[#3F2021]">
                {order.delivery_type === 'post_office' || order.post_office_id
                  ? 'ПОЧТОВОЕ ОТДЕЛЕНИЕ'
                  : order.shipping_city
                  ? `АДРЕС: Г. ${order.shipping_city}, ${order.shipping_house || ''}`
                  : 'ДОСТАВКА ПО АДРЕСУ'}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase text-[#3F2021]/60 block font-semibold">
                ДАТА СОЗДАНИЯ
              </span>
              <span className="font-mono text-[#3F2021]">
                {formatDate(order.created_at)}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase text-[#3F2021]/60 block font-semibold">
                ТЕКУЩИЙ СТАТУС
              </span>
              <span className="font-semibold uppercase text-[#3F2021]">
                {order.status}
              </span>
            </div>
          </div>

          {/* Items Summary */}
          {items.length > 0 && (
            <div className="border-t border-[#3F2021]/15 pt-4 space-y-2">
              <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60 font-semibold block">
                СОСТАВ ЗАКАЗА ({items.length} ПОЗИЦИЙ):
              </span>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {items.map((it) => (
                  <div key={it.id} className="flex justify-between text-xs font-sans text-[#3F2021]">
                    <span>
                      {it.title_snapshot} ({it.quantity} шт.)
                    </span>
                    <span className="font-mono font-bold">
                      {formatPrice(Number(it.unit_price) * it.quantity)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Button */}
          <div className="border-t border-[#3F2021]/15 pt-6 space-y-3">
            <button
              type="button"
              disabled={debugPayMutation.isPending}
              onClick={() => debugPayMutation.mutate()}
              className="w-full bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] py-4 text-xs font-sans uppercase tracking-widest font-semibold transition-colors cursor-pointer rounded-none disabled:opacity-50 text-center"
            >
              {debugPayMutation.isPending ? 'ОБРАБОТКА ТЕСТОВОГО ПЛАТЕЖА...' : 'ОПЛАТИТЬ (DEBUG) ↗'}
            </button>

            <div className="text-center">
              <Link
                to="/profile"
                className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 hover:text-[#3F2021] underline underline-offset-4"
              >
                ОТМЕНИТЬ И ВЕРНУТЬСЯ В ПРОФИЛЬ
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DebugPayPage;

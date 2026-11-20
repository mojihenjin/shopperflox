import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { analyticsApi, queueApi } from '../api/endpoints';
import { formatPrice, formatDate, formatImageUrl } from '../utils/format';
import { formatApiError } from '../utils/errorMapper';
import type {
  FulfillmentStatus,
  QueueItemResponse,
  QueueItemUpdateRequest,
} from '../types/api';
import type { ApiError } from '../api/client';

export interface QueueAndAnalyticsViewProps {
  brandId?: string | null;
  brandName?: string | null;
  className?: string;
}

const STATUS_FILTERS: { key: FulfillmentStatus | 'ALL'; label: string }[] = [
  { key: 'ALL', label: 'ВСЕ' },
  { key: 'pending', label: 'ОЖИДАЕТ' },
  { key: 'packing', label: 'ПАКУЕТСЯ' },
  { key: 'handed_to_post', label: 'ОТПРАВЛЕНО НА ПОЧТУ' },
  { key: 'in_transit', label: 'В ПОЧТОВОЙ СЛУЖБЕ' },
  { key: 'delivered', label: 'ПОЛУЧЕНО' },
  { key: 'returning', label: 'В ОБРАТНОЙ ОТПРАВКЕ' },
  { key: 'returned', label: 'ВОЗВРАЩЕНО' },
];

const STATUS_LABELS: Record<FulfillmentStatus, string> = {
  awaiting_payment: 'ОЖИДАЕТ ОПЛАТЫ',
  pending: 'ОЖИДАЕТ',
  packing: 'ПАКУЕТСЯ',
  handed_to_post: 'ОТПРАВЛЕНО НА ПОЧТУ',
  in_transit: 'В ПОЧТОВОЙ СЛУЖБЕ',
  delivered: 'ПОЛУЧЕНО',
  returning: 'В ОБРАТНОЙ ОТПРАВКЕ',
  returned: 'ВОЗВРАЩЕНО',
  cancelled: 'ОТМЕНЁН',
};

function getStatusBadgeStyle(status: FulfillmentStatus): string {
  switch (status) {
    case 'awaiting_payment':
      return 'border border-[#3F2021]/20 bg-[#3F2021]/5 text-[#3F2021]';
    case 'pending':
      return 'border border-[#FF8562] bg-[#FF8562]/10 text-[#3F2021]';
    case 'packing':
      return 'border border-[#7594B3] bg-[#7594B3]/15 text-[#3F2021]';
    case 'handed_to_post':
      return 'border border-[#3F2021]/30 bg-[#F2E9DB] text-[#3F2021]';
    case 'in_transit':
      return 'border border-[#3F2021] bg-[#3F2021]/10 text-[#3F2021]';
    case 'delivered':
      return 'bg-[#3F2021] text-[#F2E9DB] border border-[#3F2021]';
    case 'returning':
      return 'border border-[#FF8562] bg-[#FF8562]/15 text-[#3F2021] font-semibold';
    case 'returned':
      return 'border border-[#3F2021]/40 bg-[#3F2021]/20 text-[#3F2021] font-semibold';
    case 'cancelled':
      return 'border border-[#FF8562]/50 bg-[#FF8562]/20 text-[#3F2021]';
    default:
      return 'border border-[#3F2021]/30 text-[#3F2021]';
  }
}

function formatRevenueMap(revenue: Record<string, string> | undefined): string {
  if (!revenue || Object.keys(revenue).length === 0) return '0 ₽';
  const parts: string[] = [];
  if (revenue.RUB) parts.push(`${formatPrice(revenue.RUB)}`);
  if (revenue.USD) parts.push(`$ ${Number(revenue.USD).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  if (revenue.EUR) parts.push(`€ ${Number(revenue.EUR).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  if (revenue.CNY) parts.push(`¥ ${Number(revenue.CNY).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  return parts.length > 0 ? parts.join(' · ') : '0 ₽';
}

export function QueueAndAnalyticsView({
  brandId,
  brandName,
  className = '',
}: QueueAndAnalyticsViewProps) {
  const queryClient = useQueryClient();
  const [activeStatusFilter, setActiveStatusFilter] = useState<FulfillmentStatus | 'ALL'>('ALL');
  const [expandedProductIds, setExpandedProductIds] = useState<Record<string, boolean>>({});
  const [postCodeInputs, setPostCodeInputs] = useState<Record<string, string>>({});
  const [actionFeedback, setActionFeedback] = useState<{ id: string; msg: string; isError?: boolean } | null>(null);

  // --- 1. Analytics Query ---
  const {
    data: analyticsData,
    isLoading: isAnalyticsLoading,
    error: analyticsError,
  } = useQuery({
    queryKey: ['analytics', brandId || 'my'],
    queryFn: () => (brandId ? analyticsApi.getByBrand(brandId) : analyticsApi.getMy()),
  });

  const analytics = analyticsData?.data;

  // --- 2. Queue Query ---
  const selectedStatusParam = activeStatusFilter === 'ALL' ? undefined : activeStatusFilter;

  const {
    data: queueData,
    isLoading: isQueueLoading,
    error: queueError,
  } = useQuery({
    queryKey: ['queue', brandId || 'my', activeStatusFilter],
    queryFn: () =>
      brandId
        ? queueApi.getByBrand(brandId, selectedStatusParam)
        : queueApi.getMy(selectedStatusParam),
  });

  const queueItems: QueueItemResponse[] = queueData?.data || [];

  // Count items per status
  const queueCountQuery = useQuery({
    queryKey: ['queueAllCounts', brandId || 'my'],
    queryFn: () => (brandId ? queueApi.getByBrand(brandId) : queueApi.getMy()),
  });
  const allQueueItems: QueueItemResponse[] = queueCountQuery.data?.data || [];

  const statusCounts = STATUS_FILTERS.reduce(
    (acc, f) => {
      if (f.key === 'ALL') {
        acc[f.key] = allQueueItems.length;
      } else {
        acc[f.key] = allQueueItems.filter((item) => item.fulfillment_status === f.key).length;
      }
      return acc;
    },
    {} as Record<string, number>
  );

  // --- 3. Mutations ---
  const updateQueueItemMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: QueueItemUpdateRequest }) =>
      queueApi.updateItem(id, data),
    onSuccess: (_res, vars) => {
      setActionFeedback({
        id: vars.id,
        msg: '✓ ДАННЫЕ УСПЕШНО СОХРАНЕНЫ',
      });
      setTimeout(() => setActionFeedback(null), 3500);
      queryClient.invalidateQueries({ queryKey: ['queue', brandId || 'my'] });
      queryClient.invalidateQueries({ queryKey: ['queueAllCounts', brandId || 'my'] });
    },
    onError: (err: ApiError, vars) => {
      setActionFeedback({
        id: vars.id,
        msg: formatApiError(err, 'ОШИБКА ОБНОВЛЕНИЯ СТАТУСА'),
        isError: true,
      });
      setTimeout(() => setActionFeedback(null), 5000);
    },
  });

  const handleStatusChange = (itemId: string, newStatus: string) => {
    updateQueueItemMutation.mutate({
      id: itemId,
      data: { fulfillment_status: newStatus as FulfillmentStatus },
    });
  };

  const handleSavePostCode = (itemId: string) => {
    const code = postCodeInputs[itemId] !== undefined
      ? postCodeInputs[itemId]
      : (queueItems.find((q) => q.id === itemId)?.post_code || '');
    updateQueueItemMutation.mutate({
      id: itemId,
      data: { post_code: code.trim() || null },
    });
  };

  const toggleProductExpand = (productId: string) => {
    setExpandedProductIds((prev) => ({
      ...prev,
      [productId]: !prev[productId],
    }));
  };

  return (
    <div className={`space-y-12 ${className}`}>
      {/* ---------------- SECTION 1: ANALYTICS ---------------- */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[#3F2021]/15 pb-3">
          <div>
            <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
              ( РАЗДЕЛ I )
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl uppercase tracking-wider text-[#3F2021]">
              СТАТИСТИКА ПРОДАЖ {brandName ? `· ${brandName}` : '· SELF-WORKED'}
            </h2>
          </div>
          <span className="text-xs font-mono uppercase text-[#3F2021]/60">
            {brandId ? `БРЕНД ID: ${brandId.slice(0, 8)}` : 'ЛИЧНЫЕ ВЫПУСКИ АВТОРА'}
          </span>
        </div>

        {isAnalyticsLoading ? (
          <div className="p-10 bg-[#FFFFFF] border border-[#3F2021] text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
            ( ЗАГРУЗКА АНАЛИТИКИ ПРОДАЖ... )
          </div>
        ) : analyticsError ? (
          <div className="p-6 bg-[#FFFFFF] border border-red-700/30 text-center text-xs font-sans uppercase tracking-wider text-red-700">
            {formatApiError(analyticsError, 'НЕ УДАЛОСЬ ЗАГРУЗИТЬ СТАТИСТИКУ ПРОДАЖ')}
          </div>
        ) : (
          <div className="space-y-6">
            {/* 4 Overview Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Total Views */}
              <div className="bg-[#FFFFFF] border border-[#3F2021] p-5 space-y-2">
                <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                  ОБЩИЕ ПРОСМОТРЫ КАТАЛОГА
                </span>
                <div className="font-serif text-3xl sm:text-4xl font-bold text-[#3F2021]">
                  {(analytics?.total_views || 0).toLocaleString('ru-RU')}
                </div>
                <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
                  ПРОСМОТРОВ КАРТОЧЕК ИЗДЕЛИЙ
                </div>
              </div>

              {/* Total Units Sold */}
              <div className="bg-[#FFFFFF] border border-[#3F2021] p-5 space-y-2">
                <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                  ПРОДАНО ЕДИНИЦ (ШТ.)
                </span>
                <div className="font-serif text-3xl sm:text-4xl font-bold text-[#3F2021]">
                  {(analytics?.total_units_sold || 0).toLocaleString('ru-RU')}
                </div>
                <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
                  ВЫКУПЛЕННЫХ И ОПЛАЧЕННЫХ ПОЗИЦИЙ
                </div>
              </div>

              {/* Total Revenue Breakdown */}
              <div className="bg-[#FFFFFF] border border-[#3F2021] p-5 space-y-2 sm:col-span-2 lg:col-span-1">
                <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                  ОБЩАЯ ВЫРУЧКА ПО ВАЛЮТАМ
                </span>
                <div className="font-serif text-2xl sm:text-3xl font-bold text-[#3F2021] truncate">
                  {formatRevenueMap(analytics?.total_revenue)}
                </div>
                <div className="text-[11px] font-mono uppercase tracking-wider text-[#3F2021]/70">
                  {analytics?.total_revenue?.RUB ? `₽: ${formatPrice(analytics.total_revenue.RUB)}` : '₽: 0 ₽'}
                  {analytics?.total_revenue?.USD ? ` · $: $${analytics.total_revenue.USD}` : ''}
                  {analytics?.total_revenue?.EUR ? ` · €: €${analytics.total_revenue.EUR}` : ''}
                  {analytics?.total_revenue?.CNY ? ` · ¥: ¥${analytics.total_revenue.CNY}` : ''}
                </div>
              </div>
            </div>

            {/* Product & Variant Breakdown Table */}
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#3F2021]/15 pb-3">
                <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                  ( ДЕТАЛИЗАЦИЯ ПО ТОВАРАМ И ВАРИАЦИЯМ )
                </span>
                <span className="text-xs font-mono uppercase text-[#3F2021]/60">
                  [{analytics?.products?.length || 0} МОДЕЛЕЙ]
                </span>
              </div>

              {!analytics?.products || analytics.products.length === 0 ? (
                <div className="py-8 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                  ( ДАННЫЕ О ПРОДАЖАХ ПОКА ОТСУТСТВУЮТ )
                </div>
              ) : (
                <div className="space-y-4">
                  {analytics.products.map((p) => {
                    const isExpanded = Boolean(expandedProductIds[p.product_id]);
                    const variantsCount = p.variants?.length || 0;

                    return (
                      <div
                        key={p.product_id}
                        className="border border-[#3F2021]/20 bg-[#F2E9DB]/20 rounded-none overflow-hidden"
                      >
                        {/* Product Row */}
                        <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#FFFFFF]">
                          <div className="space-y-1">
                            <Link
                              to={`/products/${p.slug}`}
                              className="font-serif text-base font-bold uppercase tracking-wider text-[#3F2021] hover:underline flex items-center gap-1.5"
                            >
                              <span>{p.title}</span>
                              <span className="text-xs font-sans">↗</span>
                            </Link>
                            <div className="text-[11px] font-mono text-[#3F2021]/60">
                              SLUG: {p.slug}
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-4 sm:gap-6 text-xs font-sans uppercase">
                            <div>
                              <span className="text-[10px] text-[#3F2021]/60 block font-semibold">
                                ПРОСМОТРЫ
                              </span>
                              <span className="font-mono font-bold text-[#3F2021]">
                                {(p.views_count || 0).toLocaleString('ru-RU')}
                              </span>
                            </div>

                            <div>
                              <span className="text-[10px] text-[#3F2021]/60 block font-semibold">
                                ПРОДАНО
                              </span>
                              <span className="font-mono font-bold text-[#3F2021]">
                                {(p.units_sold || 0).toLocaleString('ru-RU')} ШТ.
                              </span>
                            </div>

                            <div>
                              <span className="text-[10px] text-[#3F2021]/60 block font-semibold">
                                ВЫРУЧКА
                              </span>
                              <span className="font-mono font-bold text-[#3F2021]">
                                {formatRevenueMap(p.revenue)}
                              </span>
                            </div>

                            {variantsCount > 0 && (
                              <button
                                type="button"
                                onClick={() => toggleProductExpand(p.product_id)}
                                className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3 py-1.5 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none self-start md:self-auto"
                              >
                                {isExpanded ? '[-] СВЕРНУТЬ' : `[+] ВАРИАЦИИ (${variantsCount})`}
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Variants Sub-table */}
                        {isExpanded && p.variants && p.variants.length > 0 && (
                          <div className="p-4 border-t border-[#3F2021]/15 bg-[#F2E9DB]/30 overflow-x-auto">
                            <table className="w-full text-left text-xs font-sans uppercase border-collapse">
                              <thead>
                                <tr className="border-b border-[#3F2021]/20 text-[10px] font-semibold tracking-wider text-[#3F2021]/70">
                                  <th className="py-2 pr-4">АРТИКУЛ (SKU)</th>
                                  <th className="py-2 px-4">ЦВЕТ</th>
                                  <th className="py-2 px-4">РАЗМЕР</th>
                                  <th className="py-2 px-4">ОСТАТОК</th>
                                  <th className="py-2 px-4">ПРОДАНО</th>
                                  <th className="py-2 pl-4 text-right">ВЫРУЧКА</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-[#3F2021]/10">
                                {p.variants.map((v) => (
                                  <tr key={v.variant_id} className="hover:bg-[#FFFFFF]/60">
                                    <td className="py-2.5 pr-4 font-mono font-bold text-[#3F2021]">
                                      {v.sku}
                                    </td>
                                    <td className="py-2.5 px-4 text-[#3F2021]/80">
                                      {v.color || '—'}
                                    </td>
                                    <td className="py-2.5 px-4 text-[#3F2021]/80">
                                      {v.size || '—'}
                                    </td>
                                    <td className="py-2.5 px-4 font-mono text-[#3F2021]">
                                      {v.stock_quantity ?? 0} ШТ.
                                    </td>
                                    <td className="py-2.5 px-4 font-mono font-bold text-[#3F2021]">
                                      {v.units_sold ?? 0} ШТ.
                                    </td>
                                    <td className="py-2.5 pl-4 text-right font-mono font-bold text-[#3F2021]">
                                      {formatRevenueMap(v.revenue)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ---------------- SECTION 2: FULFILLMENT QUEUE ---------------- */}
      <section className="space-y-6 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[#3F2021]/15 pb-3">
          <div>
            <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
              ( РАЗДЕЛ II )
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl uppercase tracking-wider text-[#3F2021]">
              ОЧЕРЕДЬ СБОРКИ И ОТПРАВКИ
            </h2>
          </div>
          <span className="text-xs font-mono uppercase text-[#3F2021]/60">
            ВСЕГО В ОЧЕРЕДИ: {allQueueItems.length} ЕД.
          </span>
        </div>

        {/* Filter Bar with Badge Counts */}
        <div className="flex flex-wrap items-center gap-1.5 border border-[#3F2021]/30 p-2 bg-[#FFFFFF]">
          {STATUS_FILTERS.map((f) => {
            const isActive = activeStatusFilter === f.key;
            const count = statusCounts[f.key] || 0;

            return (
              <button
                key={f.key}
                type="button"
                onClick={() => setActiveStatusFilter(f.key)}
                className={`px-3 py-1.5 text-xs font-sans uppercase tracking-wider transition-colors cursor-pointer rounded-none flex items-center gap-2 ${
                  isActive
                    ? 'bg-[#3F2021] text-[#F2E9DB] font-bold'
                    : 'bg-[#F2E9DB]/50 text-[#3F2021] hover:bg-[#3F2021]/10 font-semibold'
                }`}
              >
                <span>{f.label}</span>
                <span
                  className={`px-1.5 py-0.2 text-[10px] font-mono leading-tight ${
                    isActive ? 'bg-[#F2E9DB] text-[#3F2021]' : 'bg-[#3F2021]/10 text-[#3F2021]'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Queue Items List */}
        {isQueueLoading ? (
          <div className="p-12 bg-[#FFFFFF] border border-[#3F2021] text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
            ( ЗАГРУЗКА ОЧЕРЕДИ ОТПРАВКИ... )
          </div>
        ) : queueError ? (
          <div className="p-6 bg-[#FFFFFF] border border-red-700/30 text-center text-xs font-sans uppercase tracking-wider text-red-700">
            {formatApiError(queueError, 'НЕ УДАЛОСЬ ЗАГРУЗИТЬ ОЧЕРЕДЬ ОТПРАВКИ')}
          </div>
        ) : queueItems.length === 0 ? (
          <div className="p-12 bg-[#FFFFFF] border border-[#3F2021] text-center space-y-2 rounded-none">
            <span className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60 block">
              ( НЕТ ПОЗИЦИЙ В ВЫБРАННОМ СТАТУСЕ )
            </span>
            <h3 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
              ОЧЕРЕДЬ ПУСТА
            </h3>
            <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-sm mx-auto">
              Новые оплаченные заказы покупателей появятся в этом списке автоматически.
            </p>
          </div>
        ) : (
          <div className="space-y-5">
            {queueItems.map((item) => {
              const currentPostCode =
                postCodeInputs[item.id] !== undefined
                  ? postCodeInputs[item.id]
                  : (item.post_code || '');

              const isUpdatingThis =
                updateQueueItemMutation.isPending &&
                updateQueueItemMutation.variables?.id === item.id;

              const feedback = actionFeedback?.id === item.id ? actionFeedback : null;

              return (
                <div
                  key={item.id}
                  className="bg-[#FFFFFF] border border-[#3F2021] p-5 sm:p-6 space-y-5 rounded-none"
                >
                  {/* Card Header: Order ID + Date + Status */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#3F2021]/15 pb-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#3F2021]">
                        ЗАКАЗ #{item.order_id.slice(0, 8).toUpperCase()}
                      </span>
                      <span className="text-[#3F2021]/40">·</span>
                      <span className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
                        ОФОРМЛЕН: {formatDate(item.created_at)}
                      </span>
                      {item.updated_at && item.updated_at !== item.created_at && (
                        <>
                          <span className="text-[#3F2021]/40">·</span>
                          <span className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/50">
                            ОБНОВЛЁН: {formatDate(item.updated_at)}
                          </span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-1 text-[11px] font-sans font-bold uppercase tracking-wider ${getStatusBadgeStyle(
                          item.fulfillment_status
                        )}`}
                      >
                        {STATUS_LABELS[item.fulfillment_status] || item.fulfillment_status}
                      </span>
                    </div>
                  </div>

                  {/* 4 Information Blocks */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pt-1">
                    {/* 1. Product & Photo */}
                    <div className="space-y-2">
                      <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                        1. ИЗДЕЛИЕ И СУММА
                      </span>
                      <div className="flex items-start gap-3">
                        {item.product.image_url ? (
                          <img
                            src={formatImageUrl(item.product.image_url, item.product.title)}
                            alt={item.product.title}
                            className="aspect-[2/3] w-20 object-cover border border-[#3F2021] bg-[#F2E9DB] rounded-none shrink-0"
                          />
                        ) : (
                          <div className="aspect-[2/3] w-20 border border-[#3F2021] bg-[#F2E9DB] flex items-center justify-center font-serif text-xl font-bold text-[#3F2021] shrink-0 select-none">
                            {(item.product.title[0] || 'P').toUpperCase()}
                          </div>
                        )}
                        <div className="space-y-1">
                          <Link
                            to={`/products/${item.product.slug}`}
                            className="font-serif text-sm font-bold uppercase tracking-wider text-[#3F2021] hover:underline line-clamp-2"
                          >
                            {item.product.title} ↗
                          </Link>
                          <div className="font-mono text-xs font-bold text-[#3F2021]">
                            {item.quantity} шт. × {formatPrice(item.unit_price)}
                          </div>
                          <div className="text-[11px] font-mono text-[#3F2021]/60 uppercase">
                            ВАЛЮТА: {item.currency}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 2. Variation & Size */}
                    <div className="space-y-2">
                      <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                        2. ВАРИАЦИЯ И РАЗМЕР
                      </span>
                      <div className="space-y-1 text-xs font-sans uppercase">
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">АРТИКУЛ (SKU)</span>
                          <span className="font-mono font-bold text-[#3F2021]">
                            {item.variant.sku}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">ЦВЕТ</span>
                          <span className="font-semibold text-[#3F2021]">
                            {item.variant.color || 'НЕ УКАЗАН'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">РАЗМЕР</span>
                          <span className="font-semibold text-[#3F2021]">
                            {item.variant.size || 'ONE SIZE'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">КОЛИЧЕСТВО К ОТПРАВКЕ</span>
                          <span className="font-mono font-bold text-[#3F2021]">
                            {item.quantity} ШТ.
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 3. Shipping Address */}
                    <div className="space-y-2">
                      <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                        3. АДРЕС ОТПРАВКИ
                      </span>
                      <div className="space-y-1 text-xs font-sans uppercase">
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">ПОЧТОВЫЙ ИНДЕКС</span>
                          <span className="font-mono font-bold text-[#3F2021]">
                            {item.shipping_address?.postal_code || '—'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">ГОРОД / НАСЕЛЁННЫЙ ПУНКТ</span>
                          <span className="font-semibold text-[#3F2021]">
                            {item.shipping_address?.city || 'НЕ УКАЗАН'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-[#3F2021]/60 block">УЛИЦА, ДОМ, КВАРТИРА</span>
                          <span className="text-[#3F2021] leading-relaxed">
                            {item.shipping_address?.street || 'НЕ УКАЗАН'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 4. Customer Info */}
                    <div className="space-y-2">
                      <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                        4. ПОЛУЧАТЕЛЬ
                      </span>
                      <div className="space-y-1 text-xs font-sans">
                        <div>
                          <span className="text-[10px] uppercase text-[#3F2021]/60 block">ФИО ПОЛУЧАТЕЛЯ</span>
                          <span className="font-semibold uppercase text-[#3F2021]">
                            {item.customer.firstname || item.customer.lastname
                              ? `${item.customer.firstname || ''} ${item.customer.lastname || ''}`.trim()
                              : 'НЕ УКАЗАНО'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase text-[#3F2021]/60 block">ПРОФИЛЬ ПОКУПАТЕЛЯ</span>
                          <Link
                            to={`/users/${item.customer.login}`}
                            className="font-mono font-bold text-[#3F2021] hover:underline"
                          >
                            @{item.customer.login} ↗
                          </Link>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase text-[#3F2021]/60 block">КОНТАКТНЫЙ ТЕЛЕФОН</span>
                          <span className="font-mono text-[#3F2021]">
                            {item.customer.phone_number || 'Не указан'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase text-[#3F2021]/60 block">ЭЛЕКТРОННАЯ ПОЧТА</span>
                          <span className="text-[#3F2021] truncate block">
                            {item.customer.email || 'Не указана'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Feedback Banner */}
                  {feedback && (
                    <div
                      className={`p-2.5 text-xs font-sans uppercase tracking-wider text-center font-semibold rounded-none ${
                        feedback.isError
                          ? 'bg-red-700 text-[#F2E9DB]'
                          : 'bg-[#3F2021] text-[#F2E9DB]'
                      }`}
                    >
                      {feedback.msg}
                    </div>
                  )}

                  {/* Controls Row: Status Select + Post Code Input + Tracking URL */}
                  <div className="pt-3 border-t border-[#3F2021]/15 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 bg-[#F2E9DB]/20 p-3.5">
                    {/* Status Select */}
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                      <label className="text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] whitespace-nowrap">
                        ИЗМЕНИТЬ СТАТУС:
                      </label>
                      <select
                        value={item.fulfillment_status}
                        disabled={isUpdatingThis}
                        onChange={(e) => handleStatusChange(item.id, e.target.value)}
                        className="bg-[#FFFFFF] border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none cursor-pointer disabled:opacity-50"
                      >
                        <option value="pending">1. ОЖИДАЕТ</option>
                        <option value="packing">2. ПАКУЕТСЯ</option>
                        <option value="handed_to_post">3. ОТПРАВЛЕНО НА ПОЧТУ</option>
                        <option value="in_transit">4. В ПОЧТОВОЙ СЛУЖБЕ</option>
                        <option value="delivered">5. ПОЛУЧЕНО</option>
                        <option value="returning">6. В ОБРАТНОЙ ОТПРАВКЕ</option>
                        <option value="returned">7. ВОЗВРАЩЕНО</option>
                      </select>
                    </div>

                    {/* Post Code Input & Save */}
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                      <label className="text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] whitespace-nowrap">
                        ТРЕК-КОД (POST_CODE):
                      </label>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="text"
                          placeholder="ТРЕК-НОМЕР ПОСЫЛКИ..."
                          value={currentPostCode}
                          disabled={isUpdatingThis}
                          onChange={(e) =>
                            setPostCodeInputs((prev) => ({
                              ...prev,
                              [item.id]: e.target.value,
                            }))
                          }
                          className="bg-[#FFFFFF] border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-1.5 text-xs font-mono tracking-wider text-[#3F2021] outline-none rounded-none w-48 sm:w-56 disabled:opacity-50"
                        />
                        <button
                          type="button"
                          disabled={isUpdatingThis}
                          onClick={() => handleSavePostCode(item.id)}
                          className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none disabled:opacity-50 whitespace-nowrap"
                        >
                          {isUpdatingThis ? '...' : 'СОХРАНИТЬ ↗'}
                        </button>
                      </div>
                    </div>

                    {/* Tracking Link (if available) */}
                    {item.tracking_url && (
                      <a
                        href={item.tracking_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none inline-flex items-center justify-center gap-1.5 whitespace-nowrap text-center"
                      >
                        <span>ОТСЛЕДИТЬ ПОСЫЛКУ</span>
                        <span>↗</span>
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

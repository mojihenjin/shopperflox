import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { adminApi } from '../../api/admin';
import { productsApi } from '../../api/endpoints';
import { formatDate, formatImageUrl, formatPrice } from '../../utils/format';
import type { ProductResponse } from '../../types/api';
import type { ApiError } from '../../api/client';

const PAGE_SIZE = 20;

interface AdminProductsTabProps {
  onFeedback: (msg: string) => void;
}

export function AdminProductsTab({ onFeedback }: AdminProductsTabProps) {
  const queryClient = useQueryClient();

  // Filters & Sorting state
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [moderationFilter, setModerationFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [hiddenFilter, setHiddenFilter] = useState<'all' | '0' | '1' | '2'>('all');
  const [isLimitedFilter, setIsLimitedFilter] = useState(false);
  const [sortBy, setSortBy] = useState<'created_at' | 'base_price' | 'views_count' | 'orders_count' | 'title'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);

  // Delete Confirm State
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Fetch Products
  const { data: productsData, isLoading, error } = useQuery({
    queryKey: [
      'adminProducts',
      searchQuery,
      moderationFilter,
      hiddenFilter,
      isLimitedFilter,
      sortBy,
      sortOrder,
      page,
    ],
    queryFn: () =>
      adminApi.listProducts({
        search: searchQuery.trim() || undefined,
        moderation_status: moderationFilter === 'all' ? undefined : moderationFilter,
        is_hidden: hiddenFilter === 'all' ? undefined : parseInt(hiddenFilter, 10),
        is_limited: isLimitedFilter ? true : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
  });

  const products = productsData?.data || [];

  // Visibility Switcher Mutation
  const updateVisibilityMutation = useMutation({
    mutationFn: ({ productId, isHidden }: { productId: string; isHidden: 0 | 1 | 2 }) =>
      productsApi.update(productId, { is_hidden: isHidden }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminProducts'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      onFeedback('Видимость товара обновлена');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка обновления видимости товара');
    },
  });

  // Remoderate Mutation
  const remoderateMutation = useMutation({
    mutationFn: (productId: string) => adminApi.remoderateProduct(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminProducts'] });
      queryClient.invalidateQueries({ queryKey: ['moderationProducts'] });
      onFeedback('Товар отправлен на переодобрение модераторами (pending)');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка отправки товара на переодобрение');
    },
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (productId: string) => productsApi.delete(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminProducts'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setConfirmDeleteId(null);
      onFeedback('Товар успешно удалён');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка удаления товара');
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Control / Filter Bar */}
      <div className="bg-[#FFFFFF] border border-[#3F2021] p-4 sm:p-6 space-y-4 rounded-none">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-lg">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="ПОИСК ПО НАЗВАНИЮ, БРЕНДУ ИЛИ SKU..."
              className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
            />
            <button
              type="submit"
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold whitespace-nowrap transition-colors rounded-none"
            >
              ИСКАТЬ ↗
            </button>
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  setSearchQuery('');
                  setPage(1);
                }}
                className="text-xs text-[#3F2021]/60 hover:text-[#3F2021] px-2 font-mono"
              >
                ×
              </button>
            )}
          </form>

          {/* Create Product Link */}
          <Link
            to="/creator/products/new"
            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none whitespace-nowrap inline-block text-center"
          >
            + СОЗДАТЬ ТОВАР ↗
          </Link>
        </div>

        {/* Filters and Sorting */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Moderation Status */}
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 mr-1 select-none">
                МОДЕРАЦИЯ:
              </span>
              {(
                [
                  { id: 'all', label: 'ВСЕ' },
                  { id: 'pending', label: 'PENDING' },
                  { id: 'approved', label: 'APPROVED' },
                  { id: 'rejected', label: 'REJECTED' },
                ] as const
              ).map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => {
                    setModerationFilter(m.id);
                    setPage(1);
                  }}
                  className={`px-2 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                    moderationFilter === m.id
                      ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                      : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            {/* Visibility Filter */}
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 mr-1 select-none">
                ВИДИМОСТЬ:
              </span>
              {(
                [
                  { id: 'all', label: 'ВСЕ' },
                  { id: '0', label: '0 (ОТКРЫТ)' },
                  { id: '1', label: '1 (ПО ССЫЛКЕ)' },
                  { id: '2', label: '2 (СКРЫТ)' },
                ] as const
              ).map((h) => (
                <button
                  key={h.id}
                  type="button"
                  onClick={() => {
                    setHiddenFilter(h.id);
                    setPage(1);
                  }}
                  className={`px-2 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                    hiddenFilter === h.id
                      ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                      : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>

            {/* Limited checkbox */}
            <label className="flex items-center gap-1.5 cursor-pointer select-none text-xs font-sans uppercase tracking-wider text-[#3F2021]">
              <input
                type="checkbox"
                checked={isLimitedFilter}
                onChange={(e) => {
                  setIsLimitedFilter(e.target.checked);
                  setPage(1);
                }}
                className="w-4 h-4 rounded-none accent-[#3F2021] border-[#3F2021]"
              />
              <span>ТОЛЬКО LIMITED</span>
            </label>
          </div>

          {/* Sorting */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 select-none">
              СОРТИРОВКА:
            </span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as 'created_at' | 'base_price' | 'views_count' | 'orders_count' | 'title');
                setPage(1);
              }}
              className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
            >
              <option value="created_at">ДАТЕ СОЗДАНИЯ</option>
              <option value="views_count">ПРОСМОТРАМ</option>
              <option value="orders_count">ЗАКАЗАМ</option>
              <option value="base_price">ЦЕНЕ</option>
              <option value="title">НАЗВАНИЮ</option>
            </select>

            <button
              type="button"
              onClick={() => {
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                setPage(1);
              }}
              className="border border-[#3F2021]/30 hover:border-[#3F2021] bg-[#F2E9DB]/20 px-3 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold transition-colors rounded-none"
            >
              {sortOrder === 'desc' ? '↓ УБЫВ.' : '↑ ВОЗР.'}
            </button>
          </div>
        </div>
      </div>

      {/* Products List */}
      {isLoading ? (
        <div className="py-20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 bg-[#FFFFFF] border border-[#3F2021]/20">
          ( ЗАГРУЗКА ТОВАРОВ... )
        </div>
      ) : error ? (
        <div className="p-8 text-center border border-[#3F2021]/20 bg-[#FFFFFF]">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ОШИБКА ЗАГРУЗКИ ТОВАРОВ
          </div>
        </div>
      ) : products.length === 0 ? (
        <div className="p-12 text-center border border-[#3F2021]/20 bg-[#FFFFFF] space-y-2">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ТОВАРЫ НЕ НАЙДЕНЫ
          </div>
          <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            Попробуйте изменить поисковый запрос или фильтры
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((prod: ProductResponse) => {
            const isDeleting = confirmDeleteId === prod.id;
            const mainImg = prod.images?.[0]?.url;

            return (
              <div
                key={prod.id}
                className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4 sm:p-5 space-y-3.5 rounded-none"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    {/* Thumbnail */}
                    <Link
                      to={`/products/${prod.slug}`}
                      className="shrink-0 w-14 h-20 bg-[#E5E5E5] border border-[#3F2021]/20 overflow-hidden group block"
                    >
                      <img
                        src={formatImageUrl(mainImg, prod.title)}
                        alt={prod.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    </Link>

                    {/* Details */}
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Link
                          to={`/products/${prod.slug}`}
                          className="font-serif text-lg uppercase font-bold text-[#3F2021] hover:underline"
                        >
                          {prod.title}
                        </Link>
                        {prod.brand && (
                          <span className="font-sans text-xs uppercase font-semibold text-[#3F2021]/70">
                            [{prod.brand}]
                          </span>
                        )}
                        {prod.is_limited && (
                          <span className="bg-[#3F2021] text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase tracking-wider font-bold">
                            LIMITED
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 text-[10px] font-sans uppercase font-semibold ${
                            prod.moderation_status === 'approved'
                              ? 'bg-emerald-800 text-[#FFFFFF]'
                              : prod.moderation_status === 'pending'
                              ? 'bg-[#3F2021] text-[#F2E9DB]'
                              : 'bg-red-800 text-[#FFFFFF]'
                          }`}
                        >
                          {prod.moderation_status || 'PENDING'}
                        </span>
                      </div>

                      <div className="text-xs font-mono text-[#3F2021]/80 flex items-center gap-3 flex-wrap">
                        <span className="font-bold text-[#3F2021]">
                          {formatPrice(prod.base_price)}
                        </span>
                        <span>·</span>
                        <span>ПРОСМОТРЫ: {prod.views_count ?? 0}</span>
                        <span>·</span>
                        <span>ЗАКАЗЫ: {prod.orders_count ?? 0}</span>
                        <span>·</span>
                        <span>ВАРИАЦИЙ: {prod.variants?.length ?? 0}</span>
                        <span>·</span>
                        <span>СОЗДАН: {formatDate(prod.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right actions */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                    {/* 3-position visibility switcher */}
                    <div className="flex items-center border border-[#3F2021]/30 bg-[#FFFFFF] p-0.5 rounded-none">
                      <span className="text-[9px] font-sans uppercase tracking-wider text-[#3F2021]/70 px-1.5 select-none font-semibold">
                        ВИДИМОСТЬ:
                      </span>
                      {([0, 1, 2] as const).map((lvl) => (
                        <button
                          key={lvl}
                          type="button"
                          disabled={updateVisibilityMutation.isPending}
                          onClick={() =>
                            updateVisibilityMutation.mutate({
                              productId: prod.id,
                              isHidden: lvl,
                            })
                          }
                          className={`px-2 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                            (prod.is_hidden ?? 0) === lvl
                              ? 'bg-[#3F2021] text-[#F2E9DB]'
                              : 'text-[#3F2021]/70 hover:text-[#3F2021]'
                          }`}
                        >
                          {lvl === 0 ? '0 (ОТКРЫТ)' : lvl === 1 ? '1 (ССЫЛКА)' : '2 (СКРЫТ)'}
                        </button>
                      ))}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={remoderateMutation.isPending}
                        onClick={() => remoderateMutation.mutate(prod.id)}
                        className="border border-[#3F2021]/40 text-[#3F2021] hover:border-[#3F2021] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors rounded-none whitespace-nowrap"
                      >
                        НА ПЕРЕОДОБРЕНИЕ
                      </button>

                      <Link
                        to={`/creator/products/${prod.slug}/edit`}
                        className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3 py-1 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors rounded-none whitespace-nowrap"
                      >
                        ИЗМЕНИТЬ ↗
                      </Link>

                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(isDeleting ? null : prod.id)}
                        className="text-red-700 hover:text-red-900 text-xs px-2 font-mono uppercase"
                      >
                        УДАЛИТЬ ×
                      </button>
                    </div>
                  </div>
                </div>

                {/* Inline Delete Confirmation */}
                {isDeleting && (
                  <div className="p-3 bg-red-100 border border-red-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs font-sans uppercase text-red-900 font-bold">
                      ВНИМАНИЕ: Безвозвратно удалить товар «{prod.title}»?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(prod.id)}
                        className="bg-red-700 text-[#FFFFFF] px-3 py-1 text-xs font-sans uppercase font-bold"
                      >
                        {deleteMutation.isPending ? 'УДАЛЕНИЕ...' : 'ПОДТВЕРДИТЬ УДАЛЕНИЕ'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021] px-2"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-[#3F2021]/20 pt-4">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
          className="border border-[#3F2021] px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors"
        >
          ← ПРЕДЫДУЩАЯ
        </button>
        <span className="text-xs font-mono uppercase text-[#3F2021]/70">
          СТРАНИЦА {page}
        </span>
        <button
          type="button"
          disabled={products.length < PAGE_SIZE}
          onClick={() => setPage(page + 1)}
          className="border border-[#3F2021] px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors"
        >
          СЛЕДУЮЩАЯ →
        </button>
      </div>
    </div>
  );
}

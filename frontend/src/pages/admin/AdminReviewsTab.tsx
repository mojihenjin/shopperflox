import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { adminApi } from '../../api/admin';
import { formatDate } from '../../utils/format';
import { formatApiError } from '../../utils/errorMapper';
import type { AdminReviewResponse } from '../../types/api';
import type { ApiError } from '../../api/client';

const PAGE_SIZE = 20;

const FIT_LABELS: Record<string, string> = {
  true_to_size: 'ИДЁТ В РАЗМЕР',
  runs_small: 'МАЛОМЕРИТ',
  runs_large: 'БОЛЬШЕМЕРИТ',
};

interface AdminReviewsTabProps {
  onFeedback: (msg: string) => void;
}

export function AdminReviewsTab({ onFeedback }: AdminReviewsTabProps) {
  const queryClient = useQueryClient();

  // Filters & Sorting state
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [ratingFilter, setRatingFilter] = useState<number | 'all'>('all');
  const [sortBy, setSortBy] = useState<'created_at' | 'rating'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);

  // Delete Confirm State
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Fetch Reviews
  const { data: reviewsData, isLoading, error } = useQuery({
    queryKey: [
      'adminReviews',
      searchQuery,
      ratingFilter,
      sortBy,
      sortOrder,
      page,
    ],
    queryFn: () =>
      adminApi.listReviews({
        search: searchQuery.trim() || undefined,
        rating: ratingFilter === 'all' ? undefined : ratingFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
  });

  const reviews = reviewsData?.data || [];

  // Delete Review Mutation
  const deleteMutation = useMutation({
    mutationFn: (reviewId: string) => adminApi.deleteReview(reviewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminReviews'] });
      setConfirmDeleteId(null);
      onFeedback('Отзыв успешно удалён');
    },
    onError: (err: ApiError) => {
      onFeedback(formatApiError(err, 'ОШИБКА УДАЛЕНИЯ ОТЗЫВА'));
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
              placeholder="ПОИСК ПО КОММЕНТАРИЮ, АВТОРУ ИЛИ ТОВАРУ..."
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

          {/* Sorting */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 select-none">
              СОРТИРОВКА:
            </span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as 'created_at' | 'rating');
                setPage(1);
              }}
              className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
            >
              <option value="created_at">ДАТЕ СОЗДАНИЯ</option>
              <option value="rating">ОЦЕНКЕ</option>
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

        {/* Rating Filter Bar */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 mr-1 select-none">
            ОЦЕНКА:
          </span>
          <button
            type="button"
            onClick={() => {
              setRatingFilter('all');
              setPage(1);
            }}
            className={`px-3 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
              ratingFilter === 'all'
                ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
            }`}
          >
            ВСЕ
          </button>
          {[5, 4, 3, 2, 1].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => {
                setRatingFilter(r);
                setPage(1);
              }}
              className={`px-3 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                ratingFilter === r
                  ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                  : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
              }`}
            >
              {r} ★
            </button>
          ))}
        </div>
      </div>

      {/* Reviews List */}
      {isLoading ? (
        <div className="py-20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 bg-[#FFFFFF] border border-[#3F2021]/20">
          ( ЗАГРУЗКА ОТЗЫВОВ... )
        </div>
      ) : error ? (
        <div className="p-8 text-center border border-[#3F2021]/20 bg-[#FFFFFF]">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ОШИБКА ЗАГРУЗКИ ОТЗЫВОВ
          </div>
        </div>
      ) : reviews.length === 0 ? (
        <div className="p-12 text-center border border-[#3F2021]/20 bg-[#FFFFFF] space-y-2">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ОТЗЫВЫ НЕ НАЙДЕНЫ
          </div>
          <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            Попробуйте изменить поисковый запрос или фильтр по оценке
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((rev: AdminReviewResponse) => {
            const isDeleting = confirmDeleteId === rev.id;

            return (
              <div
                key={rev.id}
                className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4 sm:p-5 space-y-3 rounded-none"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3F2021]/15 pb-2.5">
                  <div className="flex items-center gap-3 flex-wrap">
                    {/* Stars */}
                    <div className="flex items-center gap-1 font-mono text-sm text-[#3F2021] font-bold">
                      <span className="text-base text-[#3F2021]">
                        {'★'.repeat(rev.rating)}
                        {'☆'.repeat(5 - rev.rating)}
                      </span>
                      <span>({rev.rating} / 5)</span>
                    </div>

                    {/* Fit Feedback */}
                    {rev.fit_feedback && (
                      <span className="bg-[#3F2021]/10 text-[#3F2021] px-2 py-0.5 text-[10px] font-sans font-semibold uppercase tracking-wider">
                        {FIT_LABELS[rev.fit_feedback] || rev.fit_feedback}
                      </span>
                    )}

                    {/* Author */}
                    <span className="font-mono text-xs font-bold text-[#3F2021]">
                      @{rev.user_login}
                    </span>

                    {/* Published status */}
                    {!rev.is_published && (
                      <span className="bg-red-100 text-red-800 px-2 py-0.5 text-[10px] font-mono uppercase font-bold">
                        НЕ ОПУБЛИКОВАН
                      </span>
                    )}
                  </div>

                  {/* Date */}
                  <div className="text-[11px] font-mono text-[#3F2021]/60">
                    {formatDate(rev.created_at)}
                  </div>
                </div>

                {/* Target Product */}
                <div className="flex items-center gap-2 text-xs font-sans uppercase">
                  <span className="text-[#3F2021]/60 select-none">ТОВАР:</span>
                  <Link
                    to={`/products/${rev.product_slug}`}
                    className="font-serif font-bold text-[#3F2021] hover:underline"
                  >
                    {rev.product_title} ↗
                  </Link>
                </div>

                {/* Comment Text */}
                <p className="text-xs font-sans text-[#3F2021] uppercase leading-relaxed whitespace-pre-line bg-[#F2E9DB]/20 p-3 border border-[#3F2021]/10">
                  {rev.comment ? rev.comment : <span className="text-[#3F2021]/40">(БЕЗ ТЕКСТОВОГО КОММЕНТАРИЯ)</span>}
                </p>

                {/* Footer Action */}
                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteId(isDeleting ? null : rev.id)}
                    className="text-red-700 hover:text-red-900 text-xs font-sans uppercase tracking-wider font-semibold underline underline-offset-4"
                  >
                    УДАЛИТЬ ОТЗЫВ ×
                  </button>
                </div>

                {/* Inline Delete Confirmation */}
                {isDeleting && (
                  <div className="p-3 bg-red-100 border border-red-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs font-sans uppercase text-red-900 font-bold">
                      ВНИМАНИЕ: Безвозвратно удалить отзыв пользователя @{rev.user_login}?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(rev.id)}
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
          disabled={reviews.length < PAGE_SIZE}
          onClick={() => setPage(page + 1)}
          className="border border-[#3F2021] px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors"
        >
          СЛЕДУЮЩАЯ →
        </button>
      </div>
    </div>
  );
}

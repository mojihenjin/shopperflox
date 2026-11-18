import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { brandsApi } from '../../api/brands';
import { formatDate, formatImageUrl } from '../../utils/format';
import type { AdminBrandResponse, BrandMemberResponse } from '../../types/api';
import type { ApiError } from '../../api/client';

const PAGE_SIZE = 20;

interface AdminBrandsTabProps {
  onFeedback: (msg: string) => void;
}

export function AdminBrandsTab({ onFeedback }: AdminBrandsTabProps) {
  const queryClient = useQueryClient();

  // Filters & Sorting state
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [moderationFilter, setModerationFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [verifiedFilter, setVerifiedFilter] = useState<'all' | 'verified' | 'unverified'>('all');
  const [includeDeleted, setIncludeDeleted] = useState(true);
  const [sortBy, setSortBy] = useState<'created_at' | 'name' | 'views_count' | 'orders_count'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);

  // New Brand Form State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [brandNameInput, setBrandNameInput] = useState('');
  const [brandHisUrlInput, setBrandHisUrlInput] = useState('');
  const [brandLogoFile, setBrandLogoFile] = useState<File | null>(null);

  // Expanded Members Brand ID
  const [expandedBrandId, setExpandedBrandId] = useState<string | null>(null);

  // Add Member State
  const [newMemberLogin, setNewMemberLogin] = useState('');
  const [newMemberRole, setNewMemberRole] = useState<'representative' | 'moderator'>('representative');

  // Confirmation States
  const [confirmHideBrandId, setConfirmHideBrandId] = useState<string | null>(null);
  const [confirmDeleteBrandId, setConfirmDeleteBrandId] = useState<string | null>(null);

  // Fetch Brands
  const { data: brandsData, isLoading, error } = useQuery({
    queryKey: [
      'adminBrands',
      searchQuery,
      moderationFilter,
      verifiedFilter,
      includeDeleted,
      sortBy,
      sortOrder,
      page,
    ],
    queryFn: () =>
      adminApi.listBrands({
        search: searchQuery.trim() || undefined,
        moderation_status: moderationFilter === 'all' ? undefined : moderationFilter,
        is_verified:
          verifiedFilter === 'all'
            ? undefined
            : verifiedFilter === 'verified',
        include_deleted: includeDeleted,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
  });

  const brands = brandsData?.data || [];

  // Create Brand Mutation
  const createBrandMutation = useMutation({
    mutationFn: async () => {
      if (!brandNameInput.trim()) throw new Error('Укажите название бренда');
      const res = await brandsApi.create({
        name: brandNameInput.trim(),
        his_url: brandHisUrlInput.trim() || undefined,
      });

      if (brandLogoFile && res.data?.id) {
        const formData = new FormData();
        formData.append('file', brandLogoFile);
        await brandsApi.uploadLogo(res.data.id, formData);
      }
      return res.data;
    },
    onSuccess: (newBrand) => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      setIsCreateOpen(false);
      setBrandNameInput('');
      setBrandHisUrlInput('');
      setBrandLogoFile(null);
      onFeedback(`Бренд «${newBrand?.name}» успешно создан`);
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка создания бренда');
    },
  });

  // Verify Mutation
  const verifyMutation = useMutation({
    mutationFn: ({ brandId, isVerified }: { brandId: string; isVerified: boolean }) =>
      brandsApi.verify(brandId, isVerified),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      onFeedback('Статус верификации бренда обновлён');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка изменения верификации бренда');
    },
  });

  // Remoderate Mutation
  const remoderateMutation = useMutation({
    mutationFn: (brandId: string) => adminApi.remoderateBrand(brandId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      onFeedback('Бренд отправлен на переодобрение (статус изменён на pending)');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка отправки бренда на переодобрение');
    },
  });

  // Hide All Products Mutation
  const hideAllProductsMutation = useMutation({
    mutationFn: (brandId: string) => adminApi.hideAllBrandProducts(brandId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      queryClient.invalidateQueries({ queryKey: ['adminProducts'] });
      setConfirmHideBrandId(null);
      onFeedback('Все товары бренда успешно переведены в скрытый статус (is_hidden = 2)');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка скрытия товаров бренда');
    },
  });

  // Delete Brand Mutation
  const deleteBrandMutation = useMutation({
    mutationFn: (brandId: string) => brandsApi.delete(brandId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      setConfirmDeleteBrandId(null);
      onFeedback('Бренд успешно удалён');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка удаления бренда');
    },
  });

  // Add / Update Member Mutation
  const addMemberMutation = useMutation({
    mutationFn: ({
      brandId,
      login,
      role,
    }: {
      brandId: string;
      login: string;
      role: 'representative' | 'moderator';
    }) => brandsApi.addMember(brandId, { login, role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      setNewMemberLogin('');
      onFeedback('Участник бренда успешно добавлен / роль обновлена');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка добавления участника');
    },
  });

  // Remove Member Mutation
  const removeMemberMutation = useMutation({
    mutationFn: ({ brandId, userId }: { brandId: string; userId: string }) =>
      brandsApi.removeMember(brandId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBrands'] });
      onFeedback('Участник исключён из команды бренда');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка исключения участника');
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
              placeholder="ПОИСК БРЕНДА ПО НАЗВАНИЮ ИЛИ SLUG..."
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

          {/* Action: Create Brand */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCreateOpen(!isCreateOpen)}
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none whitespace-nowrap"
            >
              {isCreateOpen ? 'ОТМЕНА ×' : '+ СОЗДАТЬ БРЕНД'}
            </button>
          </div>
        </div>

        {/* Filter Badges & Sorting */}
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
                  className={`px-2.5 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                    moderationFilter === m.id
                      ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                      : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>

            {/* Verification */}
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 mr-1 select-none">
                ВЕРИФ:
              </span>
              {(
                [
                  { id: 'all', label: 'ВСЕ' },
                  { id: 'verified', label: 'ВЕРИФИЦИРОВАННЫЕ' },
                  { id: 'unverified', label: 'НЕ ВЕРИФ' },
                ] as const
              ).map((v) => (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => {
                    setVerifiedFilter(v.id);
                    setPage(1);
                  }}
                  className={`px-2.5 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                    verifiedFilter === v.id
                      ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                      : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>

            {/* Include Deleted Checkbox */}
            <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-sans uppercase tracking-wider text-[#3F2021]">
              <input
                type="checkbox"
                checked={includeDeleted}
                onChange={(e) => {
                  setIncludeDeleted(e.target.checked);
                  setPage(1);
                }}
                className="w-4 h-4 rounded-none accent-[#3F2021] border-[#3F2021]"
              />
              <span>ПОКАЗЫВАТЬ УДАЛЁННЫЕ</span>
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
                setSortBy(e.target.value as 'created_at' | 'name' | 'views_count' | 'orders_count');
                setPage(1);
              }}
              className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
            >
              <option value="created_at">ДАТЕ СОЗДАНИЯ</option>
              <option value="views_count">ПРОСМОТРАМ</option>
              <option value="orders_count">ЗАКАЗАМ</option>
              <option value="name">НАЗВАНИЮ</option>
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

      {/* Inline Create Brand Form */}
      {isCreateOpen && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createBrandMutation.mutate();
          }}
          className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-4 rounded-none"
        >
          <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
            ( СОЗДАНИЕ НОВОГО БРЕНДА )
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                НАЗВАНИЕ БРЕНДА (NAME) *
              </label>
              <input
                type="text"
                required
                placeholder="VORTEX APPAREL"
                value={brandNameInput}
                onChange={(e) => setBrandNameInput(e.target.value)}
                className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                ССЫЛКА НА РЕСУРС (HISURL)
              </label>
              <input
                type="url"
                placeholder="HTTPS://BRAND.COM"
                value={brandHisUrlInput}
                onChange={(e) => setBrandHisUrlInput(e.target.value)}
                className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                ЛОГОТИП БРЕНДА (ОПЦИОНАЛЬНО)
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setBrandLogoFile(e.target.files?.[0] || null)}
                className="w-full text-xs font-sans file:mr-3 file:py-1.5 file:px-3 file:border-0 file:text-xs file:font-sans file:uppercase file:bg-[#3F2021] file:text-[#F2E9DB] file:cursor-pointer text-[#3F2021]"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={createBrandMutation.isPending}
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2 text-xs font-sans uppercase tracking-wider font-semibold disabled:opacity-50 transition-colors"
            >
              {createBrandMutation.isPending ? 'СОЗДАНИЕ...' : 'СОЗДАТЬ БРЕНД ↗'}
            </button>
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 hover:text-[#3F2021] px-2"
            >
              ОТМЕНА
            </button>
          </div>
        </form>
      )}

      {/* Brands List */}
      {isLoading ? (
        <div className="py-20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 bg-[#FFFFFF] border border-[#3F2021]/20">
          ( ЗАГРУЗКА БРЕНДОВ... )
        </div>
      ) : error ? (
        <div className="p-8 text-center border border-[#3F2021]/20 bg-[#FFFFFF]">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ОШИБКА ЗАГРУЗКИ БРЕНДОВ
          </div>
        </div>
      ) : brands.length === 0 ? (
        <div className="p-12 text-center border border-[#3F2021]/20 bg-[#FFFFFF] space-y-2">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            БРЕНДЫ НЕ НАЙДЕНЫ
          </div>
          <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            Попробуйте изменить поисковый запрос или фильтры
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {brands.map((brand: AdminBrandResponse) => {
            const isExpanded = expandedBrandId === brand.id;
            const isConfirmHide = confirmHideBrandId === brand.id;
            const isConfirmDelete = confirmDeleteBrandId === brand.id;
            const members = brand.members || [];

            return (
              <div
                key={brand.id}
                className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4 sm:p-5 space-y-4 rounded-none"
              >
                {/* Brand Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
                  <div className="flex items-center gap-4">
                    {brand.logo_url ? (
                      <img
                        src={formatImageUrl(brand.logo_url, brand.name)}
                        alt={brand.name}
                        className="w-14 h-14 object-cover border border-[#3F2021] rounded-none shrink-0"
                      />
                    ) : (
                      <div className="w-14 h-14 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-center font-serif text-xl font-bold text-[#3F2021] rounded-none shrink-0 select-none">
                        {brand.name.slice(0, 2).toUpperCase()}
                      </div>
                    )}

                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-serif text-xl uppercase tracking-wider text-[#3F2021] font-bold">
                          {brand.name}
                        </span>
                        <span className="font-mono text-xs text-[#3F2021]/60">
                          /{brand.slug}
                        </span>

                        {brand.is_verified && (
                          <span
                            className="w-4 h-4 rounded-full bg-[#3F2021] text-[#F2E9DB] inline-flex items-center justify-center text-[10px] font-bold select-none leading-none shrink-0"
                            title="Бренд верифицирован"
                          >
                            ✓
                          </span>
                        )}

                        <span
                          className={`px-2 py-0.5 text-[10px] font-sans uppercase font-semibold ${
                            brand.moderation_status === 'approved'
                              ? 'bg-emerald-800 text-[#FFFFFF]'
                              : brand.moderation_status === 'pending'
                              ? 'bg-[#3F2021] text-[#F2E9DB]'
                              : 'bg-red-800 text-[#FFFFFF]'
                          }`}
                        >
                          {brand.moderation_status || 'PENDING'}
                        </span>

                        {brand.is_deleted && (
                          <span className="bg-red-100 text-red-800 border border-red-800/40 px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider">
                            УДАЛЁН
                          </span>
                        )}
                      </div>

                      <div className="text-[11px] font-mono text-[#3F2021]/70 flex items-center gap-3 flex-wrap">
                        <span>ПРОСМОТРЫ: {brand.views_count ?? 0}</span>
                        <span>·</span>
                        <span>ЗАКАЗЫ: {brand.orders_count ?? 0}</span>
                        <span>·</span>
                        <span>СОЗДАН: {formatDate(brand.created_at)}</span>
                        {brand.his_url && (
                          <>
                            <span>·</span>
                            <a
                              href={brand.his_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[#3F2021] hover:underline uppercase font-sans font-semibold"
                            >
                              HISURL ↗
                            </a>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions buttons */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => setExpandedBrandId(isExpanded ? null : brand.id)}
                      className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-3 py-1 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors rounded-none"
                    >
                      {isExpanded ? 'ЗАКРЫТЬ СОСТАВ ×' : `УЧАСТНИКИ (${members.length}) ↓`}
                    </button>

                    <button
                      type="button"
                      disabled={verifyMutation.isPending}
                      onClick={() =>
                        verifyMutation.mutate({
                          brandId: brand.id,
                          isVerified: !brand.is_verified,
                        })
                      }
                      className="border border-[#3F2021]/40 text-[#3F2021] hover:border-[#3F2021] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors rounded-none"
                    >
                      {brand.is_verified ? 'СНЯТЬ ВЕРИФ' : 'ВЕРИФИЦИРОВАТЬ ✓'}
                    </button>

                    <button
                      type="button"
                      disabled={remoderateMutation.isPending}
                      onClick={() => remoderateMutation.mutate(brand.id)}
                      className="border border-[#3F2021]/40 text-[#3F2021] hover:border-[#3F2021] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors rounded-none"
                    >
                      НА ПЕРЕОДОБРЕНИЕ
                    </button>

                    <button
                      type="button"
                      onClick={() => setConfirmHideBrandId(isConfirmHide ? null : brand.id)}
                      className="border border-[#FF8562] text-red-900 bg-[#FF8562]/10 hover:bg-[#FF8562] hover:text-[#FFFFFF] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors rounded-none"
                    >
                      СКРЫТЬ ВСЕ ТОВАРЫ
                    </button>

                    <button
                      type="button"
                      onClick={() => setConfirmDeleteBrandId(isConfirmDelete ? null : brand.id)}
                      className="text-red-700 hover:text-red-900 text-xs px-2 font-mono uppercase"
                    >
                      УДАЛИТЬ ×
                    </button>
                  </div>
                </div>

                {/* Inline Confirmation: Hide all products */}
                {isConfirmHide && (
                  <div className="p-3.5 bg-red-50 border border-red-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs font-sans uppercase text-red-900 font-semibold">
                      ВНИМАНИЕ: Скрыть все товары бренда «{brand.name}» из общего каталога?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={hideAllProductsMutation.isPending}
                        onClick={() => hideAllProductsMutation.mutate(brand.id)}
                        className="bg-red-700 text-[#FFFFFF] px-3 py-1 text-xs font-sans uppercase font-bold"
                      >
                        {hideAllProductsMutation.isPending ? 'СКРЫТИЕ...' : 'ДА, СКРЫТЬ ВСЕ'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmHideBrandId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021] px-2"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}

                {/* Inline Confirmation: Delete brand */}
                {isConfirmDelete && (
                  <div className="p-3.5 bg-red-100 border border-red-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs font-sans uppercase text-red-900 font-bold">
                      ВНИМАНИЕ: Безвозвратно удалить бренд «{brand.name}» и снять товары с продажи?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={deleteBrandMutation.isPending}
                        onClick={() => deleteBrandMutation.mutate(brand.id)}
                        className="bg-red-700 text-[#FFFFFF] px-3 py-1 text-xs font-sans uppercase font-bold"
                      >
                        {deleteBrandMutation.isPending ? 'УДАЛЕНИЕ...' : 'ПОДТВЕРДИТЬ УДАЛЕНИЕ'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteBrandId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021] px-2"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}

                {/* Expanded Members Panel */}
                {isExpanded && (
                  <div className="p-4 bg-[#F2E9DB]/40 border border-[#3F2021]/20 space-y-4">
                    <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-2">
                      <span className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                        ( КОМАНДА БРЕНДА «{brand.name}» )
                      </span>
                      <span className="text-[10px] font-mono text-[#3F2021]/60">
                        {members.length} УЧАСТНИКОВ
                      </span>
                    </div>

                    {/* Member rows */}
                    {members.length === 0 ? (
                      <div className="text-xs font-sans uppercase text-[#3F2021]/60 py-2">
                        ( В бренде пока нет участников )
                      </div>
                    ) : (
                      <div className="divide-y divide-[#3F2021]/10 border border-[#3F2021]/15 bg-[#FFFFFF]">
                        {members.map((member: BrandMemberResponse) => (
                          <div
                            key={member.user_id}
                            className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-xs font-bold text-[#3F2021]">
                                @{member.user_login || member.user_id.slice(0, 8)}
                              </span>
                              <span className="bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[10px] font-mono uppercase">
                                {member.role}
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              {/* Switch Role Button */}
                              <button
                                type="button"
                                disabled={addMemberMutation.isPending}
                                onClick={() => {
                                  if (!member.user_login) return;
                                  const nextRole =
                                    member.role === 'representative'
                                      ? 'moderator'
                                      : 'representative';
                                  addMemberMutation.mutate({
                                    brandId: brand.id,
                                    login: member.user_login,
                                    role: nextRole,
                                  });
                                }}
                                className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021] underline underline-offset-2 hover:opacity-75"
                              >
                                СМЕНИТЬ НА {member.role === 'representative' ? 'MODERATOR' : 'REPRESENTATIVE'}
                              </button>

                              {/* Remove Member Button */}
                              <button
                                type="button"
                                disabled={removeMemberMutation.isPending}
                                onClick={() =>
                                  removeMemberMutation.mutate({
                                    brandId: brand.id,
                                    userId: member.user_id,
                                  })
                                }
                                className="text-[10px] font-sans uppercase tracking-wider text-red-700 hover:text-red-900 underline underline-offset-2 ml-2"
                              >
                                ИСКЛЮЧИТЬ ×
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add Member inline form */}
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (!newMemberLogin.trim()) return;
                        addMemberMutation.mutate({
                          brandId: brand.id,
                          login: newMemberLogin.trim(),
                          role: newMemberRole,
                        });
                      }}
                      className="flex flex-col sm:flex-row sm:items-center gap-2 pt-2 border-t border-[#3F2021]/15"
                    >
                      <input
                        type="text"
                        required
                        placeholder="@LOGIN ПОЛЬЗОВАТЕЛЯ..."
                        value={newMemberLogin}
                        onChange={(e) => setNewMemberLogin(e.target.value)}
                        className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-mono text-[#3F2021] outline-none"
                      />
                      <select
                        value={newMemberRole}
                        onChange={(e) =>
                          setNewMemberRole(e.target.value as 'representative' | 'moderator')
                        }
                        className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase text-[#3F2021] outline-none"
                      >
                        <option value="representative">REPRESENTATIVE</option>
                        <option value="moderator">MODERATOR</option>
                      </select>
                      <button
                        type="submit"
                        disabled={addMemberMutation.isPending || !newMemberLogin.trim()}
                        className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
                      >
                        + ДОБАВИТЬ В КОМАНДУ
                      </button>
                    </form>
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
          disabled={brands.length < PAGE_SIZE}
          onClick={() => setPage(page + 1)}
          className="border border-[#3F2021] px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors"
        >
          СЛЕДУЮЩАЯ →
        </button>
      </div>
    </div>
  );
}

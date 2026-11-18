import { useState, useMemo } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { moderationApi, categoriesApi, productsApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { formatImageUrl, formatPrice, formatDate } from '../utils/format';
import type { ProductResponse, ModerationRequestType, BrandResponse } from '../types/api';
import type { ApiError } from '../api/client';

interface RequestCardProps {
  product: ProductResponse;
  categoryName?: string;
  onActionSuccess: (message: string) => void;
}

function ModerationRequestCard({ product, categoryName, onActionSuccess }: RequestCardProps) {
  const queryClient = useQueryClient();
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState(0);
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  // Fetch full details (images and variants) for this product
  const { data: detailData } = useQuery({
    queryKey: ['product', product.slug],
    queryFn: () => productsApi.getBySlug(product.slug),
    staleTime: 60 * 1000,
  });

  const detail = detailData?.data;
  const images = detail?.images || [];
  const variants = detail?.variants || [];

  const totalPhotos = images.length;
  const currentPhotoNumber = totalPhotos > 0 ? selectedPhotoIndex + 1 : 0;
  const photoCounter = `${String(currentPhotoNumber).padStart(2, '0')} / ${String(Math.max(1, totalPhotos)).padStart(2, '0')}`;
  const currentPhotoUrl = images[selectedPhotoIndex]?.url;

  // Approve Mutation
  const approveMutation = useMutation({
    mutationFn: () => moderationApi.approve(product.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderationProducts'] });
      queryClient.invalidateQueries({ queryKey: ['moderationPendingCount'] });
      queryClient.invalidateQueries({ queryKey: ['product', product.slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      onActionSuccess(`ЗАЯВКА НА ТОВАР «${product.title}» ОДОБРЕНА ✓`);
    },
    onError: (err: ApiError) => {
      onActionSuccess(err.message || 'Ошибка при одобрении товара');
    },
  });

  // Reject Mutation
  const rejectMutation = useMutation({
    mutationFn: () => moderationApi.reject(product.id, { reason: rejectReason.trim() || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderationProducts'] });
      queryClient.invalidateQueries({ queryKey: ['moderationPendingCount'] });
      queryClient.invalidateQueries({ queryKey: ['product', product.slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setIsRejectOpen(false);
      onActionSuccess(`ЗАЯВКА НА ТОВАР «${product.title}» ОТКЛОНЕНА`);
    },
    onError: (err: ApiError) => {
      onActionSuccess(err.message || 'Ошибка при отклонении товара');
    },
  });

  const handlePrevPhoto = () => {
    if (totalPhotos <= 1) return;
    setSelectedPhotoIndex((prev) => (prev - 1 + totalPhotos) % totalPhotos);
  };

  const handleNextPhoto = () => {
    if (totalPhotos <= 1) return;
    setSelectedPhotoIndex((prev) => (prev + 1) % totalPhotos);
  };

  const rubText = formatPrice(product.base_price);
  const usdText = product.price_usd ? `$ ${product.price_usd}` : 'НЕ УКАЗАНО';
  const eurText = product.price_eur ? `€ ${product.price_eur}` : 'НЕ УКАЗАНО';

  const hasSpecs = Boolean(
    product.material ||
    product.density ||
    product.composition ||
    product.print_method ||
    product.note
  );

  return (
    <div className="border border-[#3F2021]/30 bg-[#F2E9DB] rounded-none p-5 sm:p-7 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
        {/* LEFT: 2:3 Photo Preview with gallery switcher */}
        <div className="lg:col-span-4 space-y-2">
          <div className="relative aspect-[2/3] w-full bg-[#E5E5E5] border border-[#3F2021]/20 overflow-hidden rounded-none select-none">
            {currentPhotoUrl ? (
              <img
                src={formatImageUrl(currentPhotoUrl, product.title)}
                alt={product.title}
                className="w-full h-full object-cover rounded-none"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/50 p-4 text-center">
                ( НЕТ ЗАГРУЖЕННЫХ ФОТО )
              </div>
            )}

            {/* Gallery Navigation Arrows */}
            {totalPhotos > 1 && (
              <>
                <button
                  type="button"
                  onClick={handlePrevPhoto}
                  className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-[#F2E9DB]/90 text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] border border-[#3F2021]/30 flex items-center justify-center font-serif text-base transition-colors rounded-none"
                >
                  ←
                </button>
                <button
                  type="button"
                  onClick={handleNextPhoto}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-[#F2E9DB]/90 text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] border border-[#3F2021]/30 flex items-center justify-center font-serif text-base transition-colors rounded-none"
                >
                  →
                </button>
              </>
            )}

            {/* Monospace frame counter */}
            {totalPhotos > 0 && (
              <div className="absolute bottom-2 right-2 bg-[#3F2021]/80 text-[#F2E9DB] px-2 py-0.5 text-[10px] font-mono tracking-widest rounded-none">
                {photoCounter}
              </div>
            )}
          </div>

          {/* Filmstrip thumbnails if multiple photos */}
          {totalPhotos > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
              {images.map((img, idx) => (
                <button
                  key={img.id || idx}
                  type="button"
                  onClick={() => setSelectedPhotoIndex(idx)}
                  className={`relative w-12 h-16 flex-shrink-0 border transition-all rounded-none ${
                    selectedPhotoIndex === idx
                      ? 'border-[#3F2021] ring-1 ring-[#3F2021]'
                      : 'border-[#3F2021]/30 opacity-70 hover:opacity-100'
                  }`}
                >
                  <img
                    src={formatImageUrl(img.url, product.title)}
                    alt={product.title}
                    className="w-full h-full object-cover rounded-none"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT: Product Details & Moderation Decisions */}
        <div className="lg:col-span-8 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            {/* Header: Request Type Badge & Category */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#3F2021]/15 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                {product.request_type === 'EDIT' ? (
                  <span className="border border-[#3F2021] text-[#3F2021] bg-[#F2E9DB] px-3 py-1 text-xs font-sans font-bold uppercase tracking-widest rounded-none">
                    EDIT (ИЗМЕНЕНИЯ)
                  </span>
                ) : (
                  <span className="bg-[#3F2021] text-[#F2E9DB] px-3 py-1 text-xs font-sans font-bold uppercase tracking-widest rounded-none">
                    CREATE (НОВЫЙ ТОВАР)
                  </span>
                )}

                {categoryName && (
                  <span className="text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70">
                    КАТЕГОРИЯ: <strong className="text-[#3F2021]">{categoryName}</strong>
                  </span>
                )}
              </div>

              <span className="text-[10px] font-mono uppercase tracking-wider text-[#3F2021]/60">
                ПОДАНО: {formatDate(product.created_at)}
              </span>
            </div>

            {/* Title & Brand */}
            <div>
              <div className="flex flex-wrap items-center gap-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                {product.is_self_worked && (
                  <span className="bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[9px] font-semibold tracking-widest rounded-none">
                    ( self-worked )
                  </span>
                )}
                {product.is_limited && (
                  <span className="bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[9px] font-semibold tracking-widest rounded-none">
                    ( LIMITED )
                  </span>
                )}
                <span>[ {product.brand || 'НЕ УКАЗАНО'} ]</span>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
                <h3 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  {product.title}
                </h3>
                <Link
                  to={`/products/${product.slug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-sans uppercase tracking-wider text-[#3F2021] hover:underline underline-offset-4 whitespace-nowrap"
                >
                  ОТКРЫТЬ КАРТОЧКУ ↗
                </Link>
              </div>
            </div>

            {/* Price Row */}
            <div className="text-xs font-mono uppercase tracking-wider text-[#3F2021]/80 border-b border-[#3F2021]/15 pb-3">
              ₽: <strong className="text-[#3F2021] font-bold text-sm">{rubText}</strong> · $: {usdText} · €: {eurText}
            </div>

            {/* Description */}
            {product.description && (
              <div className="space-y-1">
                <div className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                  ( ОПИСАНИЕ )
                </div>
                <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021] leading-relaxed whitespace-pre-line bg-[#FFFFFF] p-3 border border-[#3F2021]/15 rounded-none">
                  {product.description}
                </p>
              </div>
            )}

            {/* Characteristics Table */}
            {hasSpecs && (
              <div className="border border-[#3F2021]/20 bg-[#FFFFFF] p-3.5 space-y-2 rounded-none">
                <div className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
                  ( ХАРАКТЕРИСТИКИ )
                </div>
                <div className="divide-y divide-[#3F2021]/10 text-xs font-sans">
                  {product.material && (
                    <div className="flex justify-between py-1.5 gap-4">
                      <span className="text-[#3F2021]/60 uppercase">МАТЕРИАЛ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">{product.material}</span>
                    </div>
                  )}
                  {product.density && (
                    <div className="flex justify-between py-1.5 gap-4">
                      <span className="text-[#3F2021]/60 uppercase">ПЛОТНОСТЬ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">{product.density}</span>
                    </div>
                  )}
                  {product.composition && (
                    <div className="flex justify-between py-1.5 gap-4">
                      <span className="text-[#3F2021]/60 uppercase">СОСТАВ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">{product.composition}</span>
                    </div>
                  )}
                  {product.print_method && (
                    <div className="flex justify-between py-1.5 gap-4">
                      <span className="text-[#3F2021]/60 uppercase">НАНЕСЕНИЕ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">{product.print_method}</span>
                    </div>
                  )}
                  {product.note && (
                    <div className="py-1.5 space-y-0.5">
                      <span className="text-[#3F2021]/60 uppercase block">ПРИМЕЧАНИЕ:</span>
                      <p className="text-[#3F2021] uppercase text-[11px] leading-relaxed">{product.note}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Variants (Colors, Sizes, Stock) */}
            {variants.length > 0 && (
              <div className="space-y-1.5">
                <div className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
                  ( ВАРИАНТЫ И ОСТАТКИ НА СКЛАДЕ — {variants.length} SKU )
                </div>
                <div className="flex flex-wrap gap-2">
                  {variants.map((v) => (
                    <div
                      key={v.id}
                      className="border border-[#3F2021]/30 bg-[#FFFFFF] px-2.5 py-1.5 text-xs font-sans rounded-none"
                    >
                      <div className="flex items-center gap-1.5 font-semibold text-[#3F2021] uppercase">
                        {v.color_hex && (
                          <span
                            className="w-2.5 h-2.5 inline-block border border-[#3F2021]/40 rounded-none"
                            style={{ backgroundColor: v.color_hex }}
                          />
                        )}
                        <span>{v.color_name || v.color || 'Цвет'}</span>
                        <span>·</span>
                        <span>{v.size || 'ONE'}</span>
                      </div>
                      <div className="text-[10px] font-mono text-[#3F2021]/70 mt-0.5">
                        {v.sku} · ОСТАТОК: {v.stock_quantity ?? 0} ШТ.
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Decision Block */}
          <div className="pt-4 border-t border-[#3F2021]/20 space-y-3">
            {!isRejectOpen ? (
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  disabled={approveMutation.isPending || rejectMutation.isPending}
                  onClick={() => approveMutation.mutate()}
                  className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-3 text-xs font-sans font-semibold uppercase tracking-wider transition-colors disabled:opacity-50 rounded-none"
                >
                  {approveMutation.isPending ? 'ОДОБРЕНИЕ...' : 'ОДОБРИТЬ ✓'}
                </button>

                <button
                  type="button"
                  disabled={approveMutation.isPending || rejectMutation.isPending}
                  onClick={() => setIsRejectOpen(true)}
                  className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-6 py-3 text-xs font-sans font-semibold uppercase tracking-wider transition-colors disabled:opacity-50 rounded-none"
                >
                  ОТКЛОНИТЬ ×
                </button>
              </div>
            ) : (
              <div className="border border-[#3F2021] p-4 bg-[#FFFFFF] space-y-3 rounded-none">
                <div className="text-xs font-sans uppercase tracking-wider font-semibold text-[#3F2021]">
                  ОТКЛОНЕНИЕ ЗАЯВКИ
                </div>
                <textarea
                  rows={3}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Причина отклонения (необязательно, будет показана автору)..."
                  className="w-full bg-[#F2E9DB] border border-[#3F2021]/30 focus:border-[#3F2021] p-2.5 text-xs font-sans tracking-wider outline-none text-[#3F2021] resize-none rounded-none"
                />
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    disabled={rejectMutation.isPending}
                    onClick={() => rejectMutation.mutate()}
                    className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors disabled:opacity-50 rounded-none"
                  >
                    {rejectMutation.isPending ? 'ОТКЛОНЕНИЕ...' : 'ПОДТВЕРДИТЬ ОТКЛОНЕНИЕ'}
                  </button>
                  <button
                    type="button"
                    disabled={rejectMutation.isPending}
                    onClick={() => setIsRejectOpen(false)}
                    className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-5 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none"
                  >
                    ОТМЕНА
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface BrandCardProps {
  brand: BrandResponse;
  onActionSuccess: (msg: string) => void;
}

function BrandModerationCard({ brand, onActionSuccess }: BrandCardProps) {
  const queryClient = useQueryClient();
  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const approveMutation = useMutation({
    mutationFn: () => moderationApi.approveBrand(brand.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderationBrands'] });
      queryClient.invalidateQueries({ queryKey: ['moderationPendingBrandsCount'] });
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      onActionSuccess(`БРЕНД «${brand.name}» ОДОБРЕН ✓`);
    },
    onError: (err: ApiError) => {
      onActionSuccess(err.message || 'Ошибка при одобрении бренда');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () =>
      moderationApi.rejectBrand(brand.id, { reason: rejectReason.trim() || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderationBrands'] });
      queryClient.invalidateQueries({ queryKey: ['moderationPendingBrandsCount'] });
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      setIsRejectOpen(false);
      onActionSuccess(`ЗАЯВКА НА БРЕНД «${brand.name}» ОТКЛОНЕНА`);
    },
    onError: (err: ApiError) => {
      onActionSuccess(err.message || 'Ошибка при отклонении бренда');
    },
  });

  return (
    <div className="border border-[#3F2021]/30 bg-[#F2E9DB] rounded-none p-5 sm:p-7 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
        <div className="flex items-center gap-4">
          {brand.logo_url ? (
            <img
              src={formatImageUrl(brand.logo_url, brand.name)}
              alt={brand.name}
              className="w-16 h-16 object-cover border border-[#3F2021] rounded-none shrink-0"
            />
          ) : (
            <div className="w-16 h-16 bg-[#FFFFFF] border border-[#3F2021] flex items-center justify-center font-serif text-xl font-bold text-[#3F2021] rounded-none shrink-0 select-none">
              {brand.name.slice(0, 2).toUpperCase()}
            </div>
          )}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                {brand.name}
              </h2>
              <span className="font-mono text-xs text-[#3F2021]/60">
                /{brand.slug}
              </span>
            </div>
            <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mt-1 flex items-center gap-3 flex-wrap">
              <span>ID: {brand.id.slice(0, 8)}...</span>
              <span>·</span>
              <span>ДАТА: {brand.created_at ? formatDate(brand.created_at) : 'НЕДАВНО'}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {brand.his_url && (
            <a
              href={brand.his_url}
              target="_blank"
              rel="noopener noreferrer"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-3.5 py-1.5 text-xs font-sans uppercase tracking-wider transition-colors rounded-none font-semibold"
            >
              HISURL ↗
            </a>
          )}
          <span className="bg-[#3F2021] text-[#F2E9DB] px-2.5 py-1 text-[10px] font-sans uppercase tracking-widest font-semibold rounded-none">
            PENDING
          </span>
        </div>
      </div>

      {/* Moderation Actions */}
      <div className="pt-2 border-t border-[#3F2021]/15 space-y-4">
        {!isRejectOpen ? (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate()}
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none disabled:opacity-50 cursor-pointer"
            >
              {approveMutation.isPending ? 'ОДОБРЕНИЕ...' : 'ОДОБРИТЬ БРЕНД ✓'}
            </button>
            <button
              type="button"
              onClick={() => setIsRejectOpen(true)}
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-5 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none cursor-pointer"
            >
              ОТКЛОНИТЬ ЗАЯВКУ ×
            </button>
          </div>
        ) : (
          <div className="p-4 bg-[#FFFFFF] border border-[#3F2021] space-y-3 rounded-none">
            <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
              ( УКАЖИТЕ ПРИЧИНУ ОТКЛОНЕНИЯ БРЕНДА )
            </div>
            <textarea
              rows={2}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Например: Некорректный логотип или недостоверный ресурс бренда..."
              className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] p-2.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                disabled={rejectMutation.isPending}
                onClick={() => rejectMutation.mutate()}
                className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none disabled:opacity-50 cursor-pointer"
              >
                {rejectMutation.isPending ? 'ОТКЛОНЕНИЕ...' : 'ПОДТВЕРДИТЬ ОТКЛОНЕНИЕ'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsRejectOpen(false);
                  setRejectReason('');
                }}
                className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2 text-xs font-sans uppercase tracking-wider transition-colors rounded-none cursor-pointer"
              >
                ОТМЕНА
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function ModerationRequestsPage() {
  const { isAuthenticated, user: authUser } = useAuthStore();
  const [mainSection, setMainSection] = useState<'PRODUCTS' | 'BRANDS'>('PRODUCTS');
  const [activeTab, setActiveTab] = useState<'ALL' | 'CREATE' | 'EDIT'>('ALL');
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);

  const currentUser = authUser;
  const permissions = currentUser?.global_permissions || [];
  const canModerate = permissions.includes('*') || permissions.includes('mod:approve_manager');

  // Categories list
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
  });

  const categoryMap = useMemo(() => {
    const map = new Map<string, string>();
    (categoriesData?.data || []).forEach((c) => {
      map.set(c.id, c.name);
    });
    return map;
  }, [categoriesData]);

  // Pending Count for Products
  const { data: pendingCountData } = useQuery({
    queryKey: ['moderationPendingCount'],
    queryFn: () => moderationApi.getPendingCount(),
    enabled: isAuthenticated && canModerate,
    refetchInterval: 30000,
  });

  const totalPending = pendingCountData?.data?.pending_count ?? 0;

  // Pending Count for Brands
  const { data: pendingBrandsCountData } = useQuery({
    queryKey: ['moderationPendingBrandsCount'],
    queryFn: () => moderationApi.getPendingBrandsCount(),
    enabled: isAuthenticated && canModerate,
    refetchInterval: 30000,
  });

  const totalPendingBrands = pendingBrandsCountData?.data?.pending_count ?? 0;

  // Requests query for Products
  const requestTypeFilter: ModerationRequestType | undefined =
    activeTab === 'ALL' ? undefined : activeTab;

  const {
    data: requestsData,
    isLoading: isRequestsLoading,
    error: productsError,
  } = useQuery({
    queryKey: ['moderationProducts', requestTypeFilter],
    queryFn: () => moderationApi.list({ request_type: requestTypeFilter, limit: 50 }),
    enabled: isAuthenticated && canModerate && mainSection === 'PRODUCTS',
  });

  const products = requestsData?.data || [];

  // Requests query for Brands
  const {
    data: brandsData,
    isLoading: isBrandsLoading,
    error: brandsError,
  } = useQuery({
    queryKey: ['moderationBrands'],
    queryFn: () => moderationApi.listBrands({ limit: 50 }),
    enabled: isAuthenticated && canModerate && mainSection === 'BRANDS',
  });

  const pendingBrands = brandsData?.data || [];

  if (!isAuthenticated) {
    return <Navigate to="/login?redirect=%2Fmoderation%2Frequests" replace />;
  }

  if (!canModerate) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex flex-col items-center justify-center px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          ДОСТУП ОГРАНИЧЕН
        </h1>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md">
          Раздел модерации заявок доступен только администраторам и модераторам каталога с правом mod:approve_manager.
        </p>
        <Link
          to="/"
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-8 py-3 text-xs font-sans uppercase tracking-wider transition-colors rounded-none"
        >
          НА ГЛАВНУЮ ↗
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#F2E9DB] min-h-screen py-10 md:py-16">
      <div className="w-full max-w-none px-4 md:px-8 space-y-8">
        {/* Header */}
        <div className="border-b border-[#3F2021]/20 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
              ( ЦЕНТР МОДЕРАЦИИ КАТАЛОГА )
            </span>
            <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021] mt-1">
              ЗАЯВКИ НА РАЗМЕЩЕНИЕ
            </h1>
          </div>
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#3F2021]">
            {totalPending} ОЖИДАЮТ ПРОВЕРКИ
          </div>
        </div>

        {/* Notices */}
        {feedbackNotice && (
          <div className="p-4 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-wider text-center rounded-none">
            {feedbackNotice}
          </div>
        )}

        {/* Top-Level Section Switcher: Products vs Brands */}
        <div className="flex border-b border-[#3F2021]/20 gap-4">
          <button
            type="button"
            onClick={() => setMainSection('PRODUCTS')}
            className={`pb-3 px-1 text-sm sm:text-base font-serif uppercase tracking-wider transition-all border-b-2 ${
              mainSection === 'PRODUCTS'
                ? 'border-[#3F2021] text-[#3F2021] font-bold'
                : 'border-transparent text-[#3F2021]/50 hover:text-[#3F2021]'
            }`}
          >
            ТОВАРЫ ({totalPending})
          </button>
          <button
            type="button"
            onClick={() => setMainSection('BRANDS')}
            className={`pb-3 px-1 text-sm sm:text-base font-serif uppercase tracking-wider transition-all border-b-2 ${
              mainSection === 'BRANDS'
                ? 'border-[#3F2021] text-[#3F2021] font-bold'
                : 'border-transparent text-[#3F2021]/50 hover:text-[#3F2021]'
            }`}
          >
            БРЕНДЫ ({totalPendingBrands})
          </button>
        </div>

        {mainSection === 'PRODUCTS' ? (
          <>
            {/* Filter Tabs for Products */}
            <div className="flex border-b border-[#3F2021]/20 gap-2">
              <button
                type="button"
                onClick={() => setActiveTab('ALL')}
                className={`px-5 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                  activeTab === 'ALL'
                    ? 'bg-[#3F2021] text-[#F2E9DB] border-b-2 border-[#3F2021]'
                    : 'text-[#3F2021]/70 hover:text-[#3F2021] hover:bg-[#3F2021]/5'
                }`}
              >
                ВСЕ
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('CREATE')}
                className={`px-5 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                  activeTab === 'CREATE'
                    ? 'bg-[#3F2021] text-[#F2E9DB] border-b-2 border-[#3F2021]'
                    : 'text-[#3F2021]/70 hover:text-[#3F2021] hover:bg-[#3F2021]/5'
                }`}
              >
                CREATE (НОВЫЕ)
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('EDIT')}
                className={`px-5 py-2.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                  activeTab === 'EDIT'
                    ? 'bg-[#3F2021] text-[#F2E9DB] border-b-2 border-[#3F2021]'
                    : 'text-[#3F2021]/70 hover:text-[#3F2021] hover:bg-[#3F2021]/5'
                }`}
              >
                EDIT (ИЗМЕНЕНИЯ)
              </button>
            </div>

            {/* Products Content */}
            {isRequestsLoading ? (
              <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( ЗАГРУЗКА ЗАЯВОК НА МОДЕРАЦИЮ... )
              </div>
            ) : productsError ? (
              <div className="py-16 text-center border border-[#3F2021]/20 p-8 rounded-none">
                <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  НЕ УДАЛОСЬ ЗАГРУЗИТЬ СПИСОК ЗАЯВОК
                </div>
                <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                  Попробуйте обновить страницу или проверить соединение с сервером.
                </p>
              </div>
            ) : products.length === 0 ? (
              <div className="py-20 text-center border border-[#3F2021]/20 p-8 rounded-none bg-[#F2E9DB]">
                <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  НЕТ ОЖИДАЮЩИХ ЗАЯВОК НА ТОВАРЫ
                </div>
                <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md mx-auto">
                  Все заявки на добавление и редактирование товаров в выбранной категории обработаны.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {products.map((prod) => (
                  <ModerationRequestCard
                    key={prod.id}
                    product={prod}
                    categoryName={categoryMap.get(prod.category_id)}
                    onActionSuccess={(msg) => {
                      setFeedbackNotice(msg);
                      setTimeout(() => setFeedbackNotice(null), 4000);
                    }}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          /* Brands Moderation Section */
          <>
            {isBrandsLoading ? (
              <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( ЗАГРУЗКА ЗАЯВОК НА БРЕНДЫ... )
              </div>
            ) : brandsError ? (
              <div className="py-16 text-center border border-[#3F2021]/20 p-8 rounded-none">
                <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  НЕ УДАЛОСЬ ЗАГРУЗИТЬ СПИСОК БРЕНДОВ
                </div>
                <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                  Попробуйте обновить страницу или проверить соединение с сервером.
                </p>
              </div>
            ) : pendingBrands.length === 0 ? (
              <div className="py-20 text-center border border-[#3F2021]/20 p-8 rounded-none bg-[#F2E9DB]">
                <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  НЕТ ОЖИДАЮЩИХ ЗАЯВОК НА БРЕНДЫ
                </div>
                <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md mx-auto">
                  Все заявки на регистрацию брендов успешно обработаны модераторами.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {pendingBrands.map((brand) => (
                  <BrandModerationCard
                    key={brand.id}
                    brand={brand}
                    onActionSuccess={(msg) => {
                      setFeedbackNotice(msg);
                      setTimeout(() => setFeedbackNotice(null), 4000);
                    }}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

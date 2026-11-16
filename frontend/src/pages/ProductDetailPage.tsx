import { useState, useMemo, useEffect } from 'react';
import { useParams, Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, cartApi, favoritesApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { formatImageUrl, formatPrice, formatDate } from '../utils/format';
import type { FitFeedback, ProductVariantResponse } from '../types/api';
import type { ApiError } from '../api/client';

export function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAuthenticated, user: authUser } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  // --- STATE HOOKS (Strictly top-level) ---
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [selectedColor, setSelectedColor] = useState<string | null>(null);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Review Form States
  const [reviewRating, setReviewRating] = useState<number>(5);
  const [reviewComment, setReviewComment] = useState('');
  const [reviewFit, setReviewFit] = useState<FitFeedback>('true_to_size');
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSuccess, setReviewSuccess] = useState<string | null>(null);

  // --- DATA FETCHING HOOKS (Strictly top-level) ---
  // 1. Product Detail
  const {
    data: productData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['product', slug],
    queryFn: () => productsApi.getBySlug(slug || ''),
    enabled: Boolean(slug),
  });

  const detail = productData?.data;
  const product = detail?.product;
  const variants = useMemo(() => detail?.variants || [], [detail?.variants]);
  const images = useMemo(() => detail?.images || [], [detail?.images]);

  // 2. Current User Profile (for role and permissions check)
  const currentUser = authUser;

  // 3. Product Reviews
  const { data: reviewsData } = useQuery({
    queryKey: ['reviews', product?.id],
    queryFn: () => productsApi.getReviews(product?.id || ''),
    enabled: Boolean(product?.id),
  });

  const reviews = useMemo(() => reviewsData?.data || [], [reviewsData?.data]);

  // 4. Favorites
  const { data: favoritesData } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => favoritesApi.list(),
    enabled: isAuthenticated,
  });

  const isFavorite = useMemo(() => {
    if (!product?.id) return false;
    return (favoritesData?.data || []).some((p) => p.id === product.id);
  }, [favoritesData, product?.id]);

  // --- COMPUTED COLOR & VARIANT STATE (Strictly top-level) ---
  // Unique available colors extracted from variants and images
  const availableColors = useMemo(() => {
    const colorMap = new Map<string, { name: string; hex?: string | null }>();
    variants.forEach((v) => {
      const name = (v.color_name || v.color || '').trim();
      if (name && !colorMap.has(name.toLowerCase())) {
        colorMap.set(name.toLowerCase(), { name, hex: v.color_hex });
      }
    });
    images.forEach((img) => {
      const name = (img.color || '').trim();
      if (name && !colorMap.has(name.toLowerCase())) {
        colorMap.set(name.toLowerCase(), { name });
      }
    });
    return Array.from(colorMap.values());
  }, [variants, images]);

  // Filtered images based on selected color (fallback to all images)
  const filteredImages = useMemo(() => {
    if (!selectedColor) return images;
    const matching = images.filter(
      (img) => img.color && img.color.trim().toLowerCase() === selectedColor.trim().toLowerCase()
    );
    return matching.length > 0 ? matching : images;
  }, [images, selectedColor]);

  // Filtered variants based on selected color (for sizes)
  const availableSizesForColor = useMemo(() => {
    if (!selectedColor) {
      return variants.filter((v) => Boolean(v.size));
    }
    const matching = variants.filter(
      (v) =>
        ((v.color_name && v.color_name.trim().toLowerCase() === selectedColor.trim().toLowerCase()) ||
         (v.color && v.color.trim().toLowerCase() === selectedColor.trim().toLowerCase())) &&
        Boolean(v.size)
    );
    return matching.length > 0 ? matching : variants.filter((v) => Boolean(v.size));
  }, [variants, selectedColor]);

  // Active / selected variant
  const activeVariant = useMemo<ProductVariantResponse | null>(() => {
    if (!variants || variants.length === 0) return null;
    if (selectedVariantId) {
      const found = variants.find((v) => v.id === selectedVariantId);
      if (found) return found;
    }
    if (availableSizesForColor.length > 0) {
      return availableSizesForColor[0];
    }
    return variants[0] || null;
  }, [variants, selectedVariantId, availableSizesForColor]);

  // Permissions calculation
  const permissions = useMemo(() => {
    if (!currentUser || !product) {
      return { isCreator: false, isSuperAdmin: false, hasBrandAccess: false, canUpdate: false, canDelete: false };
    }
    const isCreator = Boolean(product.creator_id && currentUser.id === product.creator_id);
    const globalPermissions = currentUser.global_permissions || [];
    const isSuperAdmin = globalPermissions.includes('*');
    const hasBrandAccess = Boolean(
      product.brand &&
      (globalPermissions.some((p) => p.toLowerCase() === `brand:${product.brand!.toLowerCase()}`) ||
       globalPermissions.includes('brand:*'))
    );
    const canUpdate = isCreator || isSuperAdmin || hasBrandAccess || globalPermissions.includes('mod:update');
    const canDelete = isCreator || isSuperAdmin || hasBrandAccess || globalPermissions.includes('mod:delete');

    return { isCreator, isSuperAdmin, hasBrandAccess, canUpdate, canDelete };
  }, [currentUser, product]);

  // --- EFFECT HOOKS (Strictly top-level) ---
  // 1. Auto-select initial color when product data loads
  useEffect(() => {
    if (availableColors.length > 0 && !selectedColor) {
      setSelectedColor(availableColors[0].name);
    }
  }, [availableColors, selectedColor]);

  // 2. Auto-synchronize variant when available sizes change
  useEffect(() => {
    if (availableSizesForColor.length > 0) {
      const currentValid = availableSizesForColor.some((v) => v.id === selectedVariantId);
      if (!currentValid) {
        const inStock = availableSizesForColor.find((v) => (v.stock_quantity ?? 0) > 0);
        setSelectedVariantId((inStock || availableSizesForColor[0]).id);
      }
    } else if (variants.length > 0 && !selectedVariantId) {
      setSelectedVariantId(variants[0].id);
    }
  }, [availableSizesForColor, selectedVariantId, variants]);

  // 3. Reset image index when selected color changes
  useEffect(() => {
    setSelectedImageIndex(0);
  }, [selectedColor]);

  // 4. Keyboard navigation for gallery (ArrowLeft / ArrowRight)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (filteredImages.length <= 1) return;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setSelectedImageIndex((prev) => (prev - 1 + filteredImages.length) % filteredImages.length);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setSelectedImageIndex((prev) => (prev + 1) % filteredImages.length);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredImages.length]);

  // 5. Scroll to #reviews if present in URL
  useEffect(() => {
    if (location.hash === '#reviews') {
      const timer = setTimeout(() => {
        const el = document.getElementById('reviews');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth' });
        }
      }, 350);
      return () => clearTimeout(timer);
    }
  }, [location.hash, isLoading]);

  // --- MUTATION HOOKS (Strictly top-level) ---
  // Update Visibility Mutation (0 = Open, 1 = Link only, 2 = Hidden)
  const updateVisibilityMutation = useMutation({
    mutationFn: async (newHidden: 0 | 1 | 2) => {
      if (!product?.id) return;
      return productsApi.update(product.id, {
        is_hidden: newHidden,
        is_published: newHidden !== 2,
      });
    },
    onSuccess: (res) => {
      queryClient.setQueryData(['product', slug], (old: { data?: { product?: typeof product } } | undefined) => {
        if (!old || !old.data || !old.data.product) return old;
        return {
          ...old,
          data: {
            ...old.data,
            product: {
              ...old.data.product,
              is_hidden: res?.data?.is_hidden,
              is_published: res?.data?.is_published,
            },
          },
        };
      });
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      const hiddenVal = res?.data?.is_hidden ?? 0;
      setFeedbackNotice(
        hiddenVal === 0
          ? 'УРОВЕНЬ ВИДИМОСТИ: ОТКРЫТ ВСЕМ'
          : hiddenVal === 1
          ? 'УРОВЕНЬ ВИДИМОСТИ: ТОЛЬКО ПО ПРЯМОЙ ССЫЛКЕ'
          : 'УРОВЕНЬ ВИДИМОСТИ: ПОЛНОСТЬЮ СКРЫТ'
      );
      setTimeout(() => setFeedbackNotice(null), 3500);
    },
    onError: (err: ApiError) => {
      setFeedbackNotice(err.message || 'Не удалось обновить видимость товара');
      setTimeout(() => setFeedbackNotice(null), 3500);
    },
  });

  // Delete Product Mutation
  const deleteProductMutation = useMutation({
    mutationFn: async () => {
      if (!product?.id) return;
      return productsApi.delete(product.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      navigate('/');
    },
    onError: (err: ApiError) => {
      setFeedbackNotice(err.message || 'Ошибка при удалении товара');
      setShowDeleteConfirm(false);
      setTimeout(() => setFeedbackNotice(null), 3500);
    },
  });

  // Toggle favorite mutation
  const toggleFavoriteMutation = useMutation({
    mutationFn: async () => {
      if (!isAuthenticated) {
        navigate(loginRedirectUrl, { state: { from: location } });
        return;
      }
      if (!product?.id) return;
      if (isFavorite) {
        await favoritesApi.remove(product.id);
      } else {
        await favoritesApi.add(product.id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
  });

  // Add to cart mutation
  const addToCartMutation = useMutation({
    mutationFn: async () => {
      if (!isAuthenticated) {
        navigate(loginRedirectUrl, { state: { from: location } });
        return;
      }
      if (!activeVariant) return;
      await cartApi.updateItem(activeVariant.id, quantity);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      setFeedbackNotice('ТОВАР УСПЕШНО ДОБАВЛЕН В КОРЗИНУ');
      setTimeout(() => setFeedbackNotice(null), 3500);
    },
    onError: (err: ApiError) => {
      setFeedbackNotice(err.message || 'Ошибка при добавлении в корзину');
      setTimeout(() => setFeedbackNotice(null), 3500);
    },
  });

  // Create review mutation
  const createReviewMutation = useMutation({
    mutationFn: async () => {
      if (!isAuthenticated) {
        navigate(loginRedirectUrl, { state: { from: location } });
        return;
      }
      if (!product?.id) return;
      await productsApi.createReview(product.id, {
        rating: reviewRating,
        comment: reviewComment.trim() || null,
        fit_feedback: reviewFit,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews', product?.id] });
      setReviewSuccess('СПАСИБО ЗА ВАШ ОТЗЫВ!');
      setReviewComment('');
      setReviewError(null);
      setTimeout(() => setReviewSuccess(null), 4000);
    },
    onError: (err: ApiError) => {
      setReviewError(err.message || 'Не удалось отправить отзыв');
    },
  });

  // --- CONDITIONAL EARLY RETURNS (Strictly below all hooks) ---
  if (isLoading) {
    return (
      <div className="w-full min-h-[60vh] bg-[#F2E9DB] flex items-center justify-center py-32 px-4 text-center">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ЗАГРУЗКА ИНФОРМАЦИИ О МОДЕЛИ... )
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="w-full min-h-[60vh] bg-[#F2E9DB] flex flex-col items-center justify-center py-24 px-4 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          МОДЕЛЬ НЕ НАЙДЕНА
        </h1>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
          Возможно, товар был перемещён в архив или ссылка устарела.
        </p>
        <div className="mt-3 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
          СЛУЖБА ПОДДЕРЖКИ:{' '}
          <span className="text-[#3F2021] font-semibold">
            support@shopper.flox
          </span>
        </div>
        <Link
          to="/catalog"
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-[#2B1516] transition-colors rounded-none"
        >
          ВЕРНУТЬСЯ В КАТАЛОГ ↗
        </Link>
      </div>
    );
  }

  // --- PRESENTATION HELPERS ---
  const activeImage = filteredImages[selectedImageIndex] || filteredImages[0] || null;
  const totalImagesCount = filteredImages.length;
  const currentImageNumber = totalImagesCount > 0 ? selectedImageIndex + 1 : 0;
  const formattedCounter = `${String(currentImageNumber).padStart(2, '0')} / ${String(Math.max(1, totalImagesCount)).padStart(2, '0')}`;

  const effectivePriceRub = activeVariant?.price_override || product.base_price;
  const rubPriceText = formatPrice(effectivePriceRub);
  const usdPriceText = product.price_usd
    ? `$ ${Number(product.price_usd).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : 'НЕ УКАЗАНО';
  const eurPriceText = product.price_eur
    ? `€ ${Number(product.price_eur).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : 'НЕ УКАЗАНО';

  const stockQuantity = activeVariant?.stock_quantity ?? 0;
  const totalStockAcrossAllVariants = variants.reduce((sum, v) => sum + (v.stock_quantity ?? 0), 0);
  const isOutOfStock = variants.length > 0 ? (activeVariant !== null ? stockQuantity === 0 : totalStockAcrossAllVariants === 0) : false;

  const handlePrevImage = () => {
    if (totalImagesCount <= 1) return;
    setSelectedImageIndex((prev) => (prev - 1 + totalImagesCount) % totalImagesCount);
  };

  const handleNextImage = () => {
    if (totalImagesCount <= 1) return;
    setSelectedImageIndex((prev) => (prev + 1) % totalImagesCount);
  };

  const handleReviewSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    createReviewMutation.mutate();
  };

  return (
    <div className="w-full bg-[#F2E9DB]">
      {/* Breadcrumbs */}
      <div className="border-b border-[#3F2021]/15 py-3">
        <div className="w-full max-w-none px-4 md:px-8 flex items-center gap-2 text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
          <Link to="/catalog" className="hover:text-[#3F2021]">
            КАТАЛОГ
          </Link>
          <span>/</span>
          {product.brand && (
            <>
              <span>{product.brand}</span>
              <span>/</span>
            </>
          )}
          <span className="text-[#3F2021] font-medium truncate">{product.title || 'НЕ УКАЗАНО'}</span>
        </div>
      </div>

      <div className="w-full max-w-none px-4 md:px-8 py-8 md:py-14">
        {feedbackNotice && (
          <div className="mb-8 p-3.5 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-widest text-center rounded-none">
            {feedbackNotice}
          </div>
        )}

        {/* MAIN TWO-COLUMN SECTION */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
          {/* LEFT COLUMN: Large Photo Gallery (7 columns on desktop) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            {/* Gallery Header / Color info indicator */}
            <div className="flex items-center justify-between text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70">
              <div>
                {selectedColor ? (
                  <span>ЦВЕТ: <strong className="text-[#3F2021]">{selectedColor}</strong> ({totalImagesCount} ФОТО)</span>
                ) : (
                  <span>ГАЛЕРЕЯ МОДЕЛИ</span>
                )}
              </div>
              <div className="font-mono text-xs font-semibold text-[#3F2021]">
                {formattedCounter}
              </div>
            </div>

            {/* Main Stage Image (2:3 aspect ratio, bg-[#E5E5E5], rounded-none) */}
            <div className="relative aspect-[2/3] w-full bg-[#E5E5E5] border border-[#3F2021]/20 overflow-hidden rounded-none select-none">
              {activeImage ? (
                <img
                  src={formatImageUrl(activeImage.url, product.title)}
                  alt={activeImage.alt_text || product.title}
                  className="w-full h-full object-cover rounded-none"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/50">
                  ( НЕТ ФОТОГРАФИИ )
                </div>
              )}

              {/* Overlaid Navigation Arrows */}
              {totalImagesCount > 1 && (
                <>
                  <button
                    type="button"
                    onClick={handlePrevImage}
                    aria-label="Предыдущее фото"
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-[#F2E9DB]/90 text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] border border-[#3F2021]/30 flex items-center justify-center font-serif text-lg transition-colors rounded-none"
                  >
                    ←
                  </button>
                  <button
                    type="button"
                    onClick={handleNextImage}
                    aria-label="Следующее фото"
                    className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-[#F2E9DB]/90 text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] border border-[#3F2021]/30 flex items-center justify-center font-serif text-lg transition-colors rounded-none"
                  >
                    →
                  </button>
                </>
              )}

              {/* Overlay Monospace Counter in bottom-right corner */}
              <div className="absolute bottom-3 right-3 bg-[#3F2021]/80 text-[#F2E9DB] px-2.5 py-1 text-[11px] font-mono tracking-widest rounded-none">
                {formattedCounter}
              </div>
            </div>

            {/* Thumbnails Filmstrip below the main image */}
            {totalImagesCount > 1 && (
              <div className="flex gap-2.5 overflow-x-auto pb-2 scrollbar-none">
                {filteredImages.map((img, idx) => (
                  <button
                    key={img.id || idx}
                    type="button"
                    onClick={() => setSelectedImageIndex(idx)}
                    className={`relative w-16 h-24 sm:w-20 sm:h-28 flex-shrink-0 border transition-all rounded-none ${
                      selectedImageIndex === idx
                        ? 'border-[#3F2021] ring-2 ring-[#3F2021]'
                        : 'border-[#3F2021]/30 opacity-70 hover:opacity-100'
                    }`}
                  >
                    <img
                      src={formatImageUrl(img.url, product.title)}
                      alt={img.alt_text || product.title}
                      className="w-full h-full object-cover rounded-none"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Information, Variant Picker, Characteristics, Actions (5 columns) */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
            <div className="space-y-6">
              {/* Moderation Status Banner (for author and moderators) */}
              {permissions.canUpdate && product.moderation_status === 'pending' && (
                <div className="border border-[#3F2021]/30 bg-[#F2E9DB] p-2.5 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021] font-semibold">
                  ( НА МОДЕРАЦИИ · ТИП: {product.request_type || 'CREATE'} )
                </div>
              )}
              {permissions.canUpdate && product.moderation_status === 'rejected' && (
                <div className="border border-[#FF8562] bg-[#FF8562]/10 p-3 text-center text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold space-y-1">
                  <div>( ОТКЛОНЕНО: {product.rejection_reason || 'Причина не указана'} )</div>
                  <div>
                    <Link
                      to={`/creator/products/${product.slug}/edit`}
                      className="underline underline-offset-4 font-bold hover:opacity-80 inline-block mt-0.5"
                    >
                      ИСПРАВИТЬ И ОТПРАВИТЬ ЗАНОВО ↗
                    </Link>
                  </div>
                </div>
              )}

              {/* Visibility Banner (for author and moderators) */}
              {permissions.canUpdate && product.is_hidden === 1 && (
                <div className="border border-[#3F2021]/30 bg-[#F2E9DB] p-2 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021] font-semibold">
                  ( ДОСТУПЕН ТОЛЬКО ПО ПРЯМОЙ ССЫЛКЕ )
                </div>
              )}
              {permissions.canUpdate && product.is_hidden === 2 && (
                <div className="border border-[#FF8562] bg-[#FF8562]/10 p-2 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021] font-semibold">
                  ( ТОВАР СКРЫТ ОТ ПОКУПАТЕЛЕЙ )
                </div>
              )}

              {/* Mandatory Field 1: Brand / (self-worked) / (LIMITED) */}
              <div className="flex flex-wrap items-center gap-2">
                {product.is_self_worked && (
                  <span className="bg-[#3F2021] text-[#F2E9DB] px-2.5 py-0.5 text-[10px] font-sans uppercase tracking-widest font-semibold rounded-none">
                    ( self-worked )
                  </span>
                )}
                {product.is_limited && (
                  <span className="bg-[#3F2021] text-[#F2E9DB] px-2.5 py-0.5 text-[10px] font-sans uppercase tracking-widest font-semibold rounded-none">
                    ( LIMITED )
                  </span>
                )}
                <span className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
                  [ {product.brand || 'НЕ УКАЗАНО'} ]
                </span>
              </div>

              {/* Mandatory Field 2: Title */}
              <h1 className="font-serif text-3xl sm:text-4xl uppercase tracking-wider text-[#3F2021] leading-snug">
                {product.title || 'НЕ УКАЗАНО'}
              </h1>

              {/* Mandatory Field 3: Price in RUB, USD, EUR */}
              <div className="space-y-2 border-b border-[#3F2021]/15 pb-4">
                <div className="font-serif text-3xl font-bold text-[#3F2021]">
                  {rubPriceText}
                </div>
                <div className="text-xs font-mono uppercase tracking-wider text-[#3F2021]/80">
                  ₽: {rubPriceText} · $: {usdPriceText} · €: {eurPriceText}
                </div>
              </div>

              {/* Mandatory Field 4: Colors (interactive or "Цвет: НЕ УКАЗАНО") */}
              <div className="space-y-2">
                <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                  ЦВЕТ: {selectedColor || 'НЕ УКАЗАНО'}
                </div>
                {availableColors.length === 0 ? (
                  <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                    Цвет: НЕ УКАЗАНО
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {availableColors.map((c) => {
                      const isSelected = selectedColor?.trim().toLowerCase() === c.name.trim().toLowerCase();
                      return (
                        <button
                          key={c.name}
                          type="button"
                          onClick={() => setSelectedColor(c.name)}
                          className={`px-3 py-1.5 text-xs font-sans uppercase tracking-wider border transition-colors flex items-center gap-2 rounded-none ${
                            isSelected
                              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                              : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021] bg-[#F2E9DB]'
                          }`}
                        >
                          {c.hex && (
                            <span
                              className="w-3 h-3 inline-block border border-current rounded-none"
                              style={{ backgroundColor: c.hex }}
                            />
                          )}
                          <span>{c.name}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Mandatory Field 5: Sizes with stock count */}
              <div className="space-y-2">
                <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                  РАЗМЕР: {activeVariant?.size || 'НЕ УКАЗАНО'}
                </div>
                {availableSizesForColor.length === 0 ? (
                  <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                    Размеры: НЕ УКАЗАНО
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {availableSizesForColor.map((v) => {
                      const isSelected = activeVariant?.id === v.id;
                      const stock = v.stock_quantity ?? 0;
                      const stockLabel = stock > 0 ? `${stock} шт.` : '0 шт. — нет';
                      const noStock = stock === 0;

                      return (
                        <button
                          key={v.id}
                          type="button"
                          onClick={() => setSelectedVariantId(v.id)}
                          className={`px-3 py-2 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                            isSelected
                              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                              : noStock
                              ? 'border-[#3F2021]/20 text-[#3F2021]/40 bg-[#3F2021]/5'
                              : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021] bg-[#F2E9DB]'
                          }`}
                        >
                          {v.size} ({stockLabel})
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Mandatory Field 6: Description */}
              <div className="space-y-1.5 pt-2 border-t border-[#3F2021]/15">
                <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
                  ( ОПИСАНИЕ )
                </div>
                <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021] leading-relaxed whitespace-pre-line">
                  {product.description || 'НЕ УКАЗАНО'}
                </p>
              </div>

              {/* Characteristics: Mandatory Material + Optional Density/Composition/Print/Note */}
              <div className="border border-[#3F2021]/20 bg-[#F2E9DB] p-4 space-y-3 rounded-none">
                <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                  ( ХАРАКТЕРИСТИКИ ИЗДЕЛИЯ )
                </div>
                <div className="divide-y divide-[#3F2021]/15 text-xs font-sans">
                  {/* Mandatory Material */}
                  <div className="flex justify-between py-2 gap-4">
                    <span className="text-[#3F2021]/60 uppercase tracking-wider">МАТЕРИАЛ:</span>
                    <span className="font-semibold text-[#3F2021] uppercase text-right">
                      {product.material || 'НЕ УКАЗАНО'}
                    </span>
                  </div>

                  {/* Optional: Density */}
                  {product.density && (
                    <div className="flex justify-between py-2 gap-4">
                      <span className="text-[#3F2021]/60 uppercase tracking-wider">ПЛОТНОСТЬ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">
                        {product.density}
                      </span>
                    </div>
                  )}

                  {/* Optional: Composition */}
                  {product.composition && (
                    <div className="flex justify-between py-2 gap-4">
                      <span className="text-[#3F2021]/60 uppercase tracking-wider">СОСТАВ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">
                        {product.composition}
                      </span>
                    </div>
                  )}

                  {/* Optional: Print Method */}
                  {product.print_method && (
                    <div className="flex justify-between py-2 gap-4">
                      <span className="text-[#3F2021]/60 uppercase tracking-wider">НАНЕСЕНИЕ:</span>
                      <span className="font-semibold text-[#3F2021] uppercase text-right">
                        {product.print_method}
                      </span>
                    </div>
                  )}

                  {/* Optional: Note */}
                  {product.note && (
                    <div className="py-2 space-y-1">
                      <span className="text-[#3F2021]/60 uppercase tracking-wider block">ПРИМЕЧАНИЕ:</span>
                      <p className="text-[#3F2021] uppercase leading-relaxed text-[11px]">
                        {product.note}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Control Panel: Immediately under characteristics for creator, brand or moderator */}
              {(permissions.canUpdate || permissions.canDelete) && (
                <div className="border border-[#3F2021]/30 bg-[#F2E9DB] p-4 space-y-3.5 rounded-none">
                  <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-2">
                    <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                      ( УПРАВЛЕНИЕ ТОВАРОМ )
                    </span>
                    <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70">
                      СТАТУС: <strong className="text-[#3F2021]">
                        {(product.is_hidden ?? 0) === 0
                          ? 'ОТКРЫТ ВСЕМ'
                          : product.is_hidden === 1
                          ? 'ТОЛЬКО ПО ССЫЛКЕ'
                          : 'ПОЛНОСТЬЮ СКРЫТ'}
                      </strong>
                    </span>
                  </div>

                  {!showDeleteConfirm ? (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                      {/* Left: 3-position visibility switcher */}
                      {permissions.canUpdate && (
                        <div className="flex items-center border border-[#3F2021]/30 bg-[#FFFFFF] p-0.5 rounded-none">
                          <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/80 px-2 select-none">
                            ВИДИМОСТЬ:
                          </span>
                          <button
                            type="button"
                            disabled={updateVisibilityMutation.isPending}
                            onClick={() => updateVisibilityMutation.mutate(0)}
                            className={`px-2.5 py-1 text-[10px] font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                              (product.is_hidden ?? 0) === 0
                                ? 'bg-[#3F2021] text-[#F2E9DB]'
                                : 'text-[#3F2021]/70 hover:text-[#3F2021] hover:bg-[#3F2021]/10'
                            }`}
                          >
                            ОТКРЫТ
                          </button>
                          <button
                            type="button"
                            disabled={updateVisibilityMutation.isPending}
                            onClick={() => updateVisibilityMutation.mutate(1)}
                            className={`px-2.5 py-1 text-[10px] font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                              product.is_hidden === 1
                                ? 'bg-[#3F2021] text-[#F2E9DB]'
                                : 'text-[#3F2021]/70 hover:text-[#3F2021] hover:bg-[#3F2021]/10'
                            }`}
                          >
                            ПО ССЫЛКЕ
                          </button>
                          <button
                            type="button"
                            disabled={updateVisibilityMutation.isPending}
                            onClick={() => updateVisibilityMutation.mutate(2)}
                            className={`px-2.5 py-1 text-[10px] font-sans font-semibold uppercase tracking-wider transition-colors rounded-none ${
                              product.is_hidden === 2
                                ? 'bg-[#3F2021] text-[#F2E9DB]'
                                : 'text-[#3F2021]/70 hover:text-[#3F2021] hover:bg-[#3F2021]/10'
                            }`}
                          >
                            СКРЫТ
                          </button>
                        </div>
                      )}

                      {/* Right: Edit & Delete buttons */}
                      <div className="flex items-center gap-2">
                        {permissions.canUpdate && (
                          <Link
                            to={`/creator/products/${product.slug}/edit`}
                            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3.5 py-1.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none inline-block whitespace-nowrap"
                          >
                            ИЗМЕНИТЬ ↗
                          </Link>
                        )}

                        {permissions.canDelete && (
                          <button
                            type="button"
                            onClick={() => setShowDeleteConfirm(true)}
                            className="border border-[#3F2021]/60 text-[#3F2021]/80 hover:bg-[#3F2021] hover:text-[#F2E9DB] px-3.5 py-1.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none whitespace-nowrap"
                          >
                            УДАЛИТЬ
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    /* Inline confirmation for deletion (NO browser window.confirm) */
                    <div className="border border-[#3F2021] p-3 bg-[#FFFFFF] space-y-3 rounded-none">
                      <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                        ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ЭТОТ ТОВАР? ДЕЙСТВИЕ НЕОБРАТИМО.
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          disabled={deleteProductMutation.isPending}
                          onClick={() => deleteProductMutation.mutate()}
                          className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none disabled:opacity-50"
                        >
                          {deleteProductMutation.isPending ? 'УДАЛЕНИЕ...' : 'ПОДТВЕРДИТЬ УДАЛЕНИЕ'}
                        </button>
                        <button
                          type="button"
                          disabled={deleteProductMutation.isPending}
                          onClick={() => setShowDeleteConfirm(false)}
                          className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none"
                        >
                          ОТМЕНА
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Customer Actions: Quantity, In-stock, Add to Cart, Favorites */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-sans uppercase tracking-wider text-[#3F2021]">
                      КОЛИЧЕСТВО:
                    </span>
                    <div className="flex items-center border border-[#3F2021]">
                      <button
                        type="button"
                        onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                        disabled={quantity <= 1 || isOutOfStock}
                        className="px-3 py-1 text-sm font-sans hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors disabled:opacity-30 rounded-none"
                      >
                        −
                      </button>
                      <span className="px-4 py-1 text-xs font-mono font-bold text-[#3F2021]">
                        {quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => setQuantity((q) => q + 1)}
                        disabled={isOutOfStock}
                        className="px-3 py-1 text-sm font-sans hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors disabled:opacity-30 rounded-none"
                      >
                        +
                      </button>
                    </div>
                  </div>

                  <div>
                    {isOutOfStock ? (
                      <span className="text-xs font-sans uppercase tracking-wider font-semibold text-[#FF8562]">
                        {product.is_limited
                          ? 'ЛИМИТИРОВАННЫЙ ТИРАЖ · РАСПРОДАНО'
                          : 'НЕТ В НАЛИЧИИ · ОЖИДАЕТСЯ ПОПОЛНЕНИЕ'}
                      </span>
                    ) : (
                      <span className="text-xs font-sans uppercase tracking-wider font-semibold text-[#3F2021]/80">
                        В НАЛИЧИИ ({stockQuantity})
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                  <button
                    type="button"
                    disabled={isOutOfStock || addToCartMutation.isPending}
                    onClick={() => addToCartMutation.mutate()}
                    className="flex-1 bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] py-4 px-6 text-xs font-sans font-semibold uppercase tracking-[0.08em] transition-colors disabled:opacity-40 rounded-none"
                  >
                    {addToCartMutation.isPending
                      ? 'ДОБАВЛЕНИЕ...'
                      : isOutOfStock
                      ? product.is_limited
                        ? 'ЛИМИТИРОВАННЫЙ ТИРАЖ · РАСПРОДАНО'
                        : 'НЕТ В НАЛИЧИИ · ОЖИДАЕТСЯ ПОПОЛНЕНИЕ'
                      : 'В КОРЗИНУ ↗'}
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleFavoriteMutation.mutate()}
                    className="border border-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] py-4 px-6 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none"
                  >
                    {isFavorite ? '♥ В ИЗБРАННОМ' : '♡ В ИЗБРАННОЕ'}
                  </button>
                </div>
              </div>
            </div>

            {/* Editorial Features Guarantee */}
            <div className="border-t border-[#3F2021]/20 pt-6 space-y-2 text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
              <div>✓ ПРЕМИАЛЬНЫЕ МАТЕРИАЛЫ И ВЫСОКОКАЧЕСТВЕННАЯ ФУРНИТУРА</div>
              <div>✓ ОРИГИНАЛЬНАЯ КОМПЛЕКТАЦИЯ И ФИРМЕННАЯ УПАКОВКА</div>
              <div>✓ ГАРАНТИЯ КАЧЕСТВА SHOPPERFLOX — 12 МЕСЯЦЕВ</div>
            </div>
          </div>
        </div>

        {/* REVIEWS SECTION BELOW TWO-COLUMN BLOCK */}
        <section id="reviews" className="mt-20 pt-12 border-t border-[#3F2021]/20">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                ( ОТЗЫВЫ И ВПЕЧАТЛЕНИЯ )
              </span>
              <h2 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021] mt-1">
                ОТЗЫВЫ ПОКУПАТЕЛЕЙ
              </h2>
            </div>
            <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
              ВСЕГО ОТЗЫВОВ: {reviews.length}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
            {/* Reviews List (7 columns) */}
            <div className="lg:col-span-7 space-y-6">
              {reviews.length === 0 ? (
                <div className="p-8 border border-[#3F2021]/20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 rounded-none">
                  ( У ЭТОЙ МОДЕЛИ ЕЩЕ НЕТ ОТЗЫВОВ. СТАНЬТЕ ПЕРВЫМ! )
                </div>
              ) : (
                reviews.map((rev) => (
                  <div key={rev.id} className="p-5 border border-[#3F2021]/20 bg-[#F2E9DB] space-y-3 rounded-none">
                    <div className="flex items-center justify-between text-xs font-sans">
                      <div className="flex items-center gap-2">
                        <span className="font-serif font-bold text-[#3F2021] tracking-wider">
                          {'★'.repeat(rev.rating)}{'☆'.repeat(5 - rev.rating)}
                        </span>
                        <span className="font-semibold text-[#3F2021]">({rev.rating}/5)</span>
                      </div>
                      <span className="text-[#3F2021]/60 text-[11px]">{formatDate(rev.created_at)}</span>
                    </div>

                    {rev.fit_feedback && (
                      <div className="inline-block bg-[#3F2021]/10 text-[#3F2021] px-2 py-0.5 text-[10px] font-sans uppercase tracking-widest rounded-none">
                        ПОСАДКА: {rev.fit_feedback === 'true_to_size' ? 'В РАЗМЕР' : rev.fit_feedback === 'runs_small' ? 'МАЛОМЕРИТ' : 'БОЛЬШЕМЕРИТ'}
                      </div>
                    )}

                    {rev.comment && (
                      <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021] leading-relaxed">
                        {rev.comment}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Review Form (5 columns) */}
            <div className="lg:col-span-5">
              <div className="border border-[#3F2021] p-6 bg-[#F2E9DB] rounded-none">
                <h3 className="font-serif text-xl uppercase tracking-wider text-[#3F2021] mb-4">
                  ОСТАВИТЬ ОТЗЫВ
                </h3>

                {!isAuthenticated ? (
                  <div className="space-y-4 text-center py-6">
                    <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
                      Чтобы поделиться впечатлениями о покупке, необходимо войти в аккаунт
                    </p>
                    <Link
                      to={loginRedirectUrl}
                      state={{ from: location }}
                      className="inline-block bg-[#3F2021] text-[#F2E9DB] px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-[#2B1516] transition-colors rounded-none"
                    >
                      ВОЙТИ В АККАУНТ ↗
                    </Link>
                  </div>
                ) : (
                  <form onSubmit={handleReviewSubmit} className="space-y-4">
                    {reviewSuccess && (
                      <div className="p-3 bg-[#3F2021] text-[#F2E9DB] text-xs uppercase tracking-wider text-center rounded-none">
                        {reviewSuccess}
                      </div>
                    )}

                    {reviewError && (
                      <div className="p-3 border border-[#3F2021] bg-[#FF8562]/10 text-[#3F2021] text-xs uppercase tracking-wider rounded-none">
                        {reviewError}
                      </div>
                    )}

                    {/* Rating Selector */}
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                        ОЦЕНКА *
                      </label>
                      <div className="flex gap-2">
                        {[1, 2, 3, 4, 5].map((val) => (
                          <button
                            key={val}
                            type="button"
                            onClick={() => setReviewRating(val)}
                            className={`flex-1 py-1.5 border text-xs font-sans font-semibold transition-colors rounded-none ${
                              reviewRating >= val
                                ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021]'
                                : 'border-[#3F2021]/30 text-[#3F2021]'
                            }`}
                          >
                            ★ {val}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Fit Feedback */}
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                        СООТВЕТСТВИЕ РАЗМЕРУ
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {(['runs_small', 'true_to_size', 'runs_large'] as FitFeedback[]).map((fit) => (
                          <button
                            key={fit}
                            type="button"
                            onClick={() => setReviewFit(fit)}
                            className={`py-1.5 px-1 border text-[10px] font-sans uppercase tracking-wider transition-colors rounded-none ${
                              reviewFit === fit
                                ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                                : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                            }`}
                          >
                            {fit === 'runs_small' ? 'МАЛОМЕРИТ' : fit === 'true_to_size' ? 'В РАЗМЕР' : 'БОЛЬШЕМЕРИТ'}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Comment */}
                    <div>
                      <label
                        htmlFor="rev-comment"
                        className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5"
                      >
                        КОММЕНТАРИЙ
                      </label>
                      <textarea
                        id="rev-comment"
                        rows={4}
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        placeholder="ПОДЕЛИТЕСЬ ВАШИМИ ВПЕЧАТЛЕНИЯМИ О ПОСАДКЕ И МАТЕРИАЛАХ..."
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-2.5 text-xs font-sans uppercase tracking-wider outline-none text-[#3F2021] resize-none rounded-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={createReviewMutation.isPending}
                      className="w-full bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] py-3 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50 rounded-none"
                    >
                      {createReviewMutation.isPending ? 'ОТПРАВКА...' : 'ОПУБЛИКОВАТЬ ОТЗЫВ ↗'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

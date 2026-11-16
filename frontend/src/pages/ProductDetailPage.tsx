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
  const { isAuthenticated } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [selectedVariant, setSelectedVariant] = useState<ProductVariantResponse | null>(null);
  const [selectedCurrency, setSelectedCurrency] = useState<'RUB' | 'USD' | 'EUR'>('RUB');
  const [quantity, setQuantity] = useState(1);
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);

  // Review Form States
  const [reviewRating, setReviewRating] = useState<number>(5);
  const [reviewComment, setReviewComment] = useState('');
  const [reviewFit, setReviewFit] = useState<FitFeedback>('true_to_size');
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewSuccess, setReviewSuccess] = useState<string | null>(null);

  // Fetch product detail
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
  const variants = detail?.variants || [];
  const images = detail?.images || [];

  // Automatically select first variant when product loads
  useEffect(() => {
    if (variants.length > 0 && !selectedVariant) {
      setSelectedVariant(variants[0]);
    }
  }, [variants, selectedVariant]);

  // Fetch reviews for this product
  const { data: reviewsData } = useQuery({
    queryKey: ['reviews', product?.id],
    queryFn: () => productsApi.getReviews(product?.id || ''),
    enabled: Boolean(product?.id),
  });

  const reviews = reviewsData?.data || [];

  // Fetch favorites
  const { data: favoritesData } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => favoritesApi.list(),
    enabled: isAuthenticated,
  });

  const isFavorite = useMemo(() => {
    if (!product?.id) return false;
    return (favoritesData?.data || []).some((p) => p.id === product.id);
  }, [favoritesData, product?.id]);

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
      if (!selectedVariant) return;
      await cartApi.updateItem(selectedVariant.id, quantity);
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

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-4 py-32 text-center text-xs font-sans uppercase tracking-widest text-sf-muted">
        ( ЗАГРУЗКА ИНФОРМАЦИИ О МОДЕЛИ... )
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-[600px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-sf-dark">
          МОДЕЛЬ НЕ НАЙДЕНА
        </h1>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-sf-muted">
          Возможно, товар был перемещён в архив или ссылка устарела.
        </p>
        <div className="mt-3 text-xs font-sans uppercase tracking-wider text-sf-muted">
          СЛУЖБА ПОДДЕРЖКИ:{' '}
          <a href="mailto:support@shopper.flox" className="text-sf-dark underline underline-offset-4">
            support@shopper.flox
          </a>
        </div>
        <Link
          to="/"
          className="mt-6 inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
        >
          ВЕРНУТЬСЯ В КАТАЛОГ ↗
        </Link>
      </div>
    );
  }

  // Selected color resolution & Gallery filtering
  const selectedColor = selectedVariant?.color_name || selectedVariant?.color || null;

  const filteredImages = useMemo(() => {
    if (!selectedColor) return images;
    const matching = images.filter(
      (img) => img.color && img.color.trim().toLowerCase() === selectedColor.trim().toLowerCase()
    );
    return matching.length > 0 ? matching : images;
  }, [images, selectedColor]);

  // Reset image index when color changes
  useEffect(() => {
    setSelectedImageIndex(0);
  }, [selectedColor]);

  const activeImage = filteredImages[selectedImageIndex]?.url || null;
  const currentPrice = selectedVariant?.price_override || product.base_price;
  const inStock = selectedVariant ? (selectedVariant.stock_quantity ?? 0) > 0 : true;

  const hasMultiCurrency = Boolean(product.price_usd || product.price_eur);
  let displayedPriceText = formatPrice(currentPrice);
  if (selectedCurrency === 'USD' && product.price_usd) {
    displayedPriceText = `$ ${Number(product.price_usd).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  } else if (selectedCurrency === 'EUR' && product.price_eur) {
    displayedPriceText = `€ ${Number(product.price_eur).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  }

  const hasSpecs = Boolean(
    product.material ||
    product.density ||
    product.composition ||
    product.print_method ||
    product.note
  );

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
      <div className="border-b border-sf-dark/15 py-3">
        <div className="w-full max-w-none px-4 md:px-8 flex items-center gap-2 text-[11px] font-sans uppercase tracking-wider text-sf-muted">
          <Link to="/catalog" className="hover:text-sf-dark">
            КАТАЛОГ
          </Link>
          <span>/</span>
          {product.brand && (
            <>
              <span>{product.brand}</span>
              <span>/</span>
            </>
          )}
          <span className="text-sf-dark font-medium truncate">{product.title}</span>
        </div>
      </div>

      <div className="w-full max-w-none px-4 md:px-8 py-10 md:py-16">
        {feedbackNotice && (
          <div className="mb-8 p-3.5 bg-sf-dark text-sf-cream text-xs font-sans uppercase tracking-widest text-center">
            {feedbackNotice}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14">
          {/* LEFT: 2:3 Portrait Gallery (7 cols on desktop) */}
          <div className="lg:col-span-7 flex flex-col md:flex-row gap-4">
            {/* Thumbnails */}
            {filteredImages.length > 1 && (
              <div className="flex md:flex-col gap-2 order-2 md:order-1 overflow-x-auto md:overflow-y-auto max-h-[640px] scrollbar-none">
                {filteredImages.map((img, idx) => (
                  <button
                    key={img.id}
                    type="button"
                    onClick={() => setSelectedImageIndex(idx)}
                    className={`relative w-16 h-24 md:w-20 md:h-28 flex-shrink-0 border transition-all ${
                      selectedImageIndex === idx
                        ? 'border-sf-dark ring-1 ring-sf-dark'
                        : 'border-sf-dark/25 opacity-70 hover:opacity-100'
                    }`}
                  >
                    <img
                      src={formatImageUrl(img.url, product.title)}
                      alt={img.alt_text || product.title}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}

            {/* Main Stage Image (2:3 aspect ratio) */}
            <div className="flex-1 order-1 md:order-2 space-y-2">
              {selectedColor && filteredImages.length < images.length && (
                <div className="text-[11px] font-sans uppercase tracking-wider text-sf-muted">
                  ( ЦВЕТ: {selectedColor} — {filteredImages.length} ИЗ {images.length} ФОТО )
                </div>
              )}
              <div className="relative aspect-[2/3] w-full bg-[#E5DBCB] border border-sf-dark/20 overflow-hidden">
                <img
                  src={formatImageUrl(activeImage, product.title)}
                  alt={product.title}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>

          {/* RIGHT: Product Details & Variant Picker (5 cols) */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-8">
            <div className="space-y-6">
              {/* Brand and self-worked badge */}
              <div className="flex flex-wrap items-center gap-2">
                {product.brand && (
                  <div className="text-[12px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
                    [ {product.brand} ]
                  </div>
                )}
                {product.is_self_worked && (
                  <span className="bg-[#3F2021] text-[#F2E9DB] px-2.5 py-0.5 text-[10px] font-sans uppercase tracking-widest font-semibold">
                    SELF-WORKED
                  </span>
                )}
              </div>

              <h1 className="font-serif text-3xl sm:text-4xl uppercase tracking-wider text-sf-dark leading-snug">
                {product.title}
              </h1>

              {/* Price Row with Currency Switcher */}
              <div className="flex flex-wrap items-baseline justify-between gap-4 border-b border-sf-dark/15 pb-4">
                <div className="flex items-baseline gap-4">
                  <span className="font-sans text-2xl font-bold text-sf-black">
                    {displayedPriceText}
                  </span>
                  {selectedVariant?.price_override && selectedCurrency === 'RUB' && (
                    <span className="text-xs font-sans uppercase tracking-wider text-sf-muted line-through">
                      {formatPrice(product.base_price)}
                    </span>
                  )}
                </div>

                {hasMultiCurrency && (
                  <div className="flex items-center gap-1 border border-sf-dark/25 p-0.5 bg-[#FFFFFF]">
                    <button
                      type="button"
                      onClick={() => setSelectedCurrency('RUB')}
                      className={`px-2 py-0.5 text-[11px] font-sans font-semibold transition-colors ${
                        selectedCurrency === 'RUB'
                          ? 'bg-[#3F2021] text-[#F2E9DB]'
                          : 'text-[#3F2021]/70 hover:text-[#3F2021]'
                      }`}
                    >
                      ₽ RUB
                    </button>
                    {product.price_usd && (
                      <button
                        type="button"
                        onClick={() => setSelectedCurrency('USD')}
                        className={`px-2 py-0.5 text-[11px] font-sans font-semibold transition-colors ${
                          selectedCurrency === 'USD'
                            ? 'bg-[#3F2021] text-[#F2E9DB]'
                            : 'text-[#3F2021]/70 hover:text-[#3F2021]'
                        }`}
                      >
                        $ USD
                      </button>
                    )}
                    {product.price_eur && (
                      <button
                        type="button"
                        onClick={() => setSelectedCurrency('EUR')}
                        className={`px-2 py-0.5 text-[11px] font-sans font-semibold transition-colors ${
                          selectedCurrency === 'EUR'
                            ? 'bg-[#3F2021] text-[#F2E9DB]'
                            : 'text-[#3F2021]/70 hover:text-[#3F2021]'
                        }`}
                      >
                        € EUR
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* SKU & Availability Badge */}
              <div className="flex items-center gap-3 text-xs font-sans uppercase tracking-wider border-b border-sf-dark/15 pb-4">
                <span className="text-sf-muted">АРТИКУЛ / SKU:</span>
                <span className="font-mono font-semibold text-sf-dark">
                  {selectedVariant?.sku || 'НЕ ВЫБРАН'}
                </span>
                <span className="ml-auto">
                  {inStock ? (
                    <span className="text-emerald-800 font-semibold">
                      В НАЛИЧИИ ({selectedVariant?.stock_quantity ?? 'МНОГО'})
                    </span>
                  ) : (
                    <span className="text-sf-coral font-semibold">НЕТ В НАЛИЧИИ</span>
                  )}
                </span>
              </div>

              {/* Description */}
              {product.description && (
                <div className="text-xs font-sans uppercase tracking-wider text-sf-dark/80 leading-relaxed">
                  {product.description}
                </div>
              )}

              {/* Characteristics Table */}
              {hasSpecs && (
                <div className="border border-sf-dark/20 bg-sf-cream/40 p-5 space-y-3">
                  <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-dark">
                    ( ХАРАКТЕРИСТИКИ ИЗДЕЛИЯ )
                  </div>
                  <div className="divide-y divide-sf-dark/15 text-xs font-sans">
                    {product.material && (
                      <div className="flex justify-between py-2 gap-4">
                        <span className="text-sf-muted uppercase tracking-wider">МАТЕРИАЛ:</span>
                        <span className="font-semibold text-sf-dark uppercase text-right">{product.material}</span>
                      </div>
                    )}
                    {product.density && (
                      <div className="flex justify-between py-2 gap-4">
                        <span className="text-sf-muted uppercase tracking-wider">ПЛОТНОСТЬ:</span>
                        <span className="font-semibold text-sf-dark uppercase text-right">{product.density}</span>
                      </div>
                    )}
                    {product.composition && (
                      <div className="flex justify-between py-2 gap-4">
                        <span className="text-sf-muted uppercase tracking-wider">СОСТАВ:</span>
                        <span className="font-semibold text-sf-dark uppercase text-right">{product.composition}</span>
                      </div>
                    )}
                    {product.print_method && (
                      <div className="flex justify-between py-2 gap-4">
                        <span className="text-sf-muted uppercase tracking-wider">НАНЕСЕНИЕ:</span>
                        <span className="font-semibold text-sf-dark uppercase text-right">{product.print_method}</span>
                      </div>
                    )}
                    {product.note && (
                      <div className="py-2 space-y-1">
                        <span className="text-sf-muted uppercase tracking-wider block">ПРИМЕЧАНИЕ:</span>
                        <p className="text-sf-dark uppercase leading-relaxed text-[11px]">{product.note}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Variant Picker (Color & Size) */}
              {variants.length > 0 && (
                <div className="space-y-4 pt-2">
                  <div className="text-xs font-sans font-semibold uppercase tracking-wider text-sf-dark">
                    ВЫБЕРИТЕ ВАРИАНТ МОДЕЛИ:
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {variants.map((v) => {
                      const isSelected = selectedVariant?.id === v.id;
                      return (
                        <button
                          key={v.id}
                          type="button"
                          onClick={() => setSelectedVariant(v)}
                          className={`p-3 text-left border transition-colors flex flex-col justify-between ${
                            isSelected
                              ? 'bg-sf-dark text-sf-cream border-sf-dark'
                              : 'bg-[#F2E9DB] text-sf-dark border-sf-dark/30 hover:border-sf-dark'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs font-semibold uppercase">
                            <span>{v.color_name}</span>
                            {v.color_hex && (
                              <span
                                className="w-3.5 h-3.5 border border-sf-cream/40 inline-block"
                                style={{ backgroundColor: v.color_hex }}
                              />
                            )}
                          </div>
                          <div className="mt-2 flex items-center justify-between text-[11px] opacity-80">
                            <span>РАЗМЕР: {v.size}</span>
                            <span>{formatPrice(v.price_override || product.base_price)}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Quantity selector & Actions */}
              <div className="space-y-3 pt-4">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-sans uppercase tracking-wider text-sf-dark">
                    КОЛИЧЕСТВО:
                  </span>
                  <div className="flex items-center border border-sf-dark">
                    <button
                      type="button"
                      onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                      disabled={quantity <= 1}
                      className="px-3 py-1 text-sm font-sans hover:bg-sf-dark hover:text-sf-cream transition-colors disabled:opacity-40"
                    >
                      −
                    </button>
                    <span className="px-4 py-1 text-xs font-mono font-bold text-sf-dark">
                      {quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => setQuantity((q) => q + 1)}
                      className="px-3 py-1 text-sm font-sans hover:bg-sf-dark hover:text-sf-cream transition-colors"
                    >
                      +
                    </button>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-2">
                  <button
                    type="button"
                    disabled={!inStock || addToCartMutation.isPending}
                    onClick={() => addToCartMutation.mutate()}
                    className="flex-1 bg-sf-dark text-sf-cream hover:bg-sf-black py-3.5 px-6 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-40"
                  >
                    {addToCartMutation.isPending ? 'ДОБАВЛЕНИЕ...' : 'ДОБАВИТЬ В КОРЗИНУ ↗'}
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleFavoriteMutation.mutate()}
                    className="border border-sf-dark hover:bg-sf-dark hover:text-sf-cream py-3.5 px-6 text-xs font-sans font-semibold uppercase tracking-wider transition-colors"
                  >
                    {isFavorite ? '♥ В ИЗБРАННОМ' : '♡ В ИЗБРАННОЕ'}
                  </button>
                </div>
              </div>
            </div>

            {/* Editorial Features Guarantee */}
            <div className="border-t border-sf-dark/20 pt-6 space-y-2 text-[11px] font-sans uppercase tracking-wider text-sf-muted">
              <div>✓ ПРЕМИАЛЬНЫЕ МАТЕРИАЛЫ И ВЫСОКОКАЧЕСТВЕННАЯ ФУРНИТУРА</div>
              <div>✓ ОРИГИНАЛЬНАЯ КОМПЛЕКТАЦИЯ И ФИРМЕННАЯ УПАКОВКА</div>
              <div>✓ ГАРАНТИЯ КАЧЕСТВА SHOPPERFLOX — 12 МЕСЯЦЕВ</div>
            </div>
          </div>
        </div>

        {/* REVIEWS SECTION */}
        <section className="mt-20 pt-12 border-t border-sf-dark/20">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
                ( ОТЗЫВЫ И ВПЕЧАТЛЕНИЯ )
              </span>
              <h2 className="font-serif text-3xl uppercase tracking-wider text-sf-dark mt-1">
                ОТЗЫВЫ ПОКУПАТЕЛЕЙ
              </h2>
            </div>
            <div className="text-xs font-sans uppercase tracking-wider text-sf-muted">
              ВСЕГО ОТЗЫВОВ: {reviews.length}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
            {/* Reviews List (7 cols) */}
            <div className="lg:col-span-7 space-y-6">
              {reviews.length === 0 ? (
                <div className="p-8 border border-sf-dark/20 text-center text-xs font-sans uppercase tracking-widest text-sf-muted">
                  ( У ЭТОЙ МОДЕЛИ ЕЩЕ НЕТ ОТЗЫВОВ. СТАНЬТЕ ПЕРВЫМ! )
                </div>
              ) : (
                reviews.map((rev) => (
                  <div key={rev.id} className="p-5 border border-sf-dark/20 bg-sf-cream/40 space-y-3">
                    <div className="flex items-center justify-between text-xs font-sans">
                      <div className="flex items-center gap-2">
                        <span className="font-serif font-bold text-sf-dark tracking-wider">
                          {'★'.repeat(rev.rating)}{'☆'.repeat(5 - rev.rating)}
                        </span>
                        <span className="font-semibold text-sf-dark">({rev.rating}/5)</span>
                      </div>
                      <span className="text-sf-muted text-[11px]">{formatDate(rev.created_at)}</span>
                    </div>

                    {rev.fit_feedback && (
                      <div className="inline-block bg-sf-dark/10 text-sf-dark px-2 py-0.5 text-[10px] font-sans uppercase tracking-widest">
                        ПОСАДКА: {rev.fit_feedback === 'true_to_size' ? 'В РАЗМЕР' : rev.fit_feedback === 'runs_small' ? 'МАЛОМЕРИТ' : 'БОЛЬШЕМЕРИТ'}
                      </div>
                    )}

                    {rev.comment && (
                      <p className="text-xs font-sans uppercase tracking-wider text-sf-dark leading-relaxed">
                        {rev.comment}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Review Form (5 cols) */}
            <div className="lg:col-span-5">
              <div className="border border-sf-dark p-6 bg-[#F2E9DB]">
                <h3 className="font-serif text-xl uppercase tracking-wider text-sf-dark mb-4">
                  ОСТАВИТЬ ОТЗЫВ
                </h3>

                {!isAuthenticated ? (
                  <div className="space-y-4 text-center py-6">
                    <p className="text-xs font-sans uppercase tracking-wider text-sf-muted">
                      Чтобы поделиться впечатлениями о покупке, необходимо войти в аккаунт
                    </p>
                    <Link
                      to={loginRedirectUrl}
                      state={{ from: location }}
                      className="inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-sf-black transition-colors"
                    >
                      ВОЙТИ В АККАУНТ ↗
                    </Link>
                  </div>
                ) : (
                  <form onSubmit={handleReviewSubmit} className="space-y-4">
                    {reviewSuccess && (
                      <div className="p-3 bg-sf-dark text-sf-cream text-xs uppercase tracking-wider">
                        {reviewSuccess}
                      </div>
                    )}

                    {reviewError && (
                      <div className="p-3 border border-sf-dark bg-sf-dark/5 text-sf-dark text-xs uppercase tracking-wider">
                        {reviewError}
                      </div>
                    )}

                    {/* Rating Selector */}
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5">
                        ОЦЕНКА *
                      </label>
                      <div className="flex gap-2">
                        {[1, 2, 3, 4, 5].map((val) => (
                          <button
                            key={val}
                            type="button"
                            onClick={() => setReviewRating(val)}
                            className={`flex-1 py-1.5 border text-xs font-sans font-semibold transition-colors ${
                              reviewRating >= val
                                ? 'bg-sf-dark text-sf-cream border-sf-dark'
                                : 'border-sf-dark/30 text-sf-dark'
                            }`}
                          >
                            ★ {val}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Fit Feedback */}
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5">
                        СООТВЕТСТВИЕ РАЗМЕРУ
                      </label>
                      <div className="grid grid-cols-3 gap-2">
                        {(['runs_small', 'true_to_size', 'runs_large'] as FitFeedback[]).map((fit) => (
                          <button
                            key={fit}
                            type="button"
                            onClick={() => setReviewFit(fit)}
                            className={`py-1.5 px-1 border text-[10px] font-sans uppercase tracking-wider transition-colors ${
                              reviewFit === fit
                                ? 'bg-sf-dark text-sf-cream border-sf-dark font-semibold'
                                : 'border-sf-dark/30 text-sf-dark hover:border-sf-dark'
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
                        className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
                      >
                        КОММЕНТАРИЙ
                      </label>
                      <textarea
                        id="rev-comment"
                        rows={4}
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        placeholder="ПОДЕЛИТЕСЬ ВАШИМИ ВПЕЧАТЛЕНИЯМИ О ПОСАДКЕ И МАТЕРИАЛАХ..."
                        className="w-full bg-[#F2E9DB] border border-sf-dark/30 focus:border-sf-dark p-2.5 text-xs font-sans uppercase tracking-wider outline-none text-sf-black resize-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={createReviewMutation.isPending}
                      className="w-full bg-sf-dark text-sf-cream hover:bg-sf-black py-3 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50"
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

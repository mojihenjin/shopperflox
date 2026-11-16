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
      <div className="max-w-[1280px] mx-auto px-4 py-32 text-center text-xs font-sans uppercase tracking-widest text-amov-muted">
        ( ЗАГРУЗКА ИНФОРМАЦИИ О МОДЕЛИ... )
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-[600px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-amov-dark">
          МОДЕЛЬ НЕ НАЙДЕНА
        </h1>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-amov-muted">
          Возможно, товар был перемещён в архив или ссылка устарела.
        </p>
        <Link
          to="/"
          className="mt-6 inline-block bg-amov-dark text-amov-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
        >
          ВЕРНУТЬСЯ В КАТАЛОГ ↗
        </Link>
      </div>
    );
  }

  const activeImage = images[selectedImageIndex]?.url || null;
  const currentPrice = selectedVariant?.price_override || product.base_price;
  const inStock = selectedVariant ? (selectedVariant.stock_quantity ?? 0) > 0 : true;

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
      <div className="border-b border-amov-dark/15 py-3">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 flex items-center gap-2 text-[11px] font-sans uppercase tracking-wider text-amov-muted">
          <Link to="/" className="hover:text-amov-dark">
            КАТАЛОГ
          </Link>
          <span>/</span>
          {product.brand && (
            <>
              <span>{product.brand}</span>
              <span>/</span>
            </>
          )}
          <span className="text-amov-dark font-medium truncate">{product.title}</span>
        </div>
      </div>

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-10 md:py-16">
        {feedbackNotice && (
          <div className="mb-8 p-3.5 bg-amov-dark text-amov-cream text-xs font-sans uppercase tracking-widest text-center">
            {feedbackNotice}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14">
          {/* LEFT: 2:3 Portrait Gallery (7 cols on desktop) */}
          <div className="lg:col-span-7 flex flex-col md:flex-row gap-4">
            {/* Thumbnails */}
            {images.length > 1 && (
              <div className="flex md:flex-col gap-2 order-2 md:order-1 overflow-x-auto md:overflow-y-auto max-h-[640px] scrollbar-none">
                {images.map((img, idx) => (
                  <button
                    key={img.id}
                    type="button"
                    onClick={() => setSelectedImageIndex(idx)}
                    className={`relative w-16 h-24 md:w-20 md:h-28 flex-shrink-0 border transition-all ${
                      selectedImageIndex === idx
                        ? 'border-amov-dark ring-1 ring-amov-dark'
                        : 'border-amov-dark/25 opacity-70 hover:opacity-100'
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
            <div className="flex-1 order-1 md:order-2">
              <div className="relative aspect-[2/3] w-full bg-[#E5DBCB] border border-amov-dark/20 overflow-hidden">
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
              {product.brand && (
                <div className="text-[12px] font-sans font-semibold uppercase tracking-widest text-amov-muted">
                  [ {product.brand} ]
                </div>
              )}

              <h1 className="font-serif text-3xl sm:text-4xl uppercase tracking-wider text-amov-dark leading-snug">
                {product.title}
              </h1>

              <div className="flex items-baseline gap-4">
                <span className="font-sans text-2xl font-bold text-amov-black">
                  {formatPrice(currentPrice)}
                </span>
                {selectedVariant?.price_override && (
                  <span className="text-xs font-sans uppercase tracking-wider text-amov-muted line-through">
                    {formatPrice(product.base_price)}
                  </span>
                )}
              </div>

              {/* SKU & Availability Badge */}
              <div className="flex items-center gap-3 text-xs font-sans uppercase tracking-wider border-y border-amov-dark/15 py-3">
                <span className="text-amov-muted">АРТИКУЛ / SKU:</span>
                <span className="font-mono font-semibold text-amov-dark">
                  {selectedVariant?.sku || 'НЕ ВЫБРАН'}
                </span>
                <span className="ml-auto">
                  {inStock ? (
                    <span className="text-emerald-800 font-semibold">
                      В НАЛИЧИИ ({selectedVariant?.stock_quantity ?? 'МНОГО'})
                    </span>
                  ) : (
                    <span className="text-amov-coral font-semibold">НЕТ В НАЛИЧИИ</span>
                  )}
                </span>
              </div>

              {/* Description */}
              {product.description && (
                <div className="text-xs font-sans uppercase tracking-wider text-amov-dark/80 leading-relaxed">
                  {product.description}
                </div>
              )}

              {/* Variant Picker (Color & Size) */}
              {variants.length > 0 && (
                <div className="space-y-4 pt-2">
                  <div className="text-xs font-sans font-semibold uppercase tracking-wider text-amov-dark">
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
                              ? 'bg-amov-dark text-amov-cream border-amov-dark'
                              : 'bg-[#F2E9DB] text-amov-dark border-amov-dark/30 hover:border-amov-dark'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs font-semibold uppercase">
                            <span>{v.color_name}</span>
                            {v.color_hex && (
                              <span
                                className="w-3.5 h-3.5 border border-amov-cream/40 inline-block"
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
                  <span className="text-xs font-sans uppercase tracking-wider text-amov-dark">
                    КОЛИЧЕСТВО:
                  </span>
                  <div className="flex items-center border border-amov-dark">
                    <button
                      type="button"
                      onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                      disabled={quantity <= 1}
                      className="px-3 py-1 text-sm font-sans hover:bg-amov-dark hover:text-amov-cream transition-colors disabled:opacity-40"
                    >
                      −
                    </button>
                    <span className="px-4 py-1 text-xs font-mono font-bold text-amov-dark">
                      {quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => setQuantity((q) => q + 1)}
                      className="px-3 py-1 text-sm font-sans hover:bg-amov-dark hover:text-amov-cream transition-colors"
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
                    className="flex-1 bg-amov-dark text-amov-cream hover:bg-amov-black py-3.5 px-6 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-40"
                  >
                    {addToCartMutation.isPending ? 'ДОБАВЛЕНИЕ...' : 'ДОБАВИТЬ В КОРЗИНУ ↗'}
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleFavoriteMutation.mutate()}
                    className="border border-amov-dark hover:bg-amov-dark hover:text-amov-cream py-3.5 px-6 text-xs font-sans font-semibold uppercase tracking-wider transition-colors"
                  >
                    {isFavorite ? '♥ В ИЗБРАННОМ' : '♡ В ИЗБРАННОЕ'}
                  </button>
                </div>
              </div>
            </div>

            {/* Editorial Features Guarantee */}
            <div className="border-t border-amov-dark/20 pt-6 space-y-2 text-[11px] font-sans uppercase tracking-wider text-amov-muted">
              <div>✓ ОРИГИНАЛЬНАЯ КОМПЛЕКТАЦИЯ: ФУТЛЯР + САЛФЕТКА ИЗ МИКРОФИБРЫ</div>
              <div>✓ БЕСПЛАТНАЯ ПРИМЕРКА ПРИ ДОСТАВКЕ КУРЬЕРОМ</div>
              <div>✓ ГАРАНТИЯ КАЧЕСТВА AMÓV — 12 МЕСЯЦЕВ</div>
            </div>
          </div>
        </div>

        {/* REVIEWS SECTION */}
        <section className="mt-20 pt-12 border-t border-amov-dark/20">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-amov-muted">
                ( ОТЗЫВЫ И ВПЕЧАТЛЕНИЯ )
              </span>
              <h2 className="font-serif text-3xl uppercase tracking-wider text-amov-dark mt-1">
                ОТЗЫВЫ ПОКУПАТЕЛЕЙ
              </h2>
            </div>
            <div className="text-xs font-sans uppercase tracking-wider text-amov-muted">
              ВСЕГО ОТЗЫВОВ: {reviews.length}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
            {/* Reviews List (7 cols) */}
            <div className="lg:col-span-7 space-y-6">
              {reviews.length === 0 ? (
                <div className="p-8 border border-amov-dark/20 text-center text-xs font-sans uppercase tracking-widest text-amov-muted">
                  ( У ЭТОЙ МОДЕЛИ ЕЩЕ НЕТ ОТЗЫВОВ. СТАНЬТЕ ПЕРВЫМ! )
                </div>
              ) : (
                reviews.map((rev) => (
                  <div key={rev.id} className="p-5 border border-amov-dark/20 bg-amov-cream/40 space-y-3">
                    <div className="flex items-center justify-between text-xs font-sans">
                      <div className="flex items-center gap-2">
                        <span className="font-serif font-bold text-amov-dark tracking-wider">
                          {'★'.repeat(rev.rating)}{'☆'.repeat(5 - rev.rating)}
                        </span>
                        <span className="font-semibold text-amov-dark">({rev.rating}/5)</span>
                      </div>
                      <span className="text-amov-muted text-[11px]">{formatDate(rev.created_at)}</span>
                    </div>

                    {rev.fit_feedback && (
                      <div className="inline-block bg-amov-dark/10 text-amov-dark px-2 py-0.5 text-[10px] font-sans uppercase tracking-widest">
                        ПОСАДКА: {rev.fit_feedback === 'true_to_size' ? 'В РАЗМЕР' : rev.fit_feedback === 'runs_small' ? 'МАЛОМЕРИТ' : 'БОЛЬШЕМЕРИТ'}
                      </div>
                    )}

                    {rev.comment && (
                      <p className="text-xs font-sans uppercase tracking-wider text-amov-dark leading-relaxed">
                        {rev.comment}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Review Form (5 cols) */}
            <div className="lg:col-span-5">
              <div className="border border-amov-dark p-6 bg-[#F2E9DB]">
                <h3 className="font-serif text-xl uppercase tracking-wider text-amov-dark mb-4">
                  ОСТАВИТЬ ОТЗЫВ
                </h3>

                {!isAuthenticated ? (
                  <div className="space-y-4 text-center py-6">
                    <p className="text-xs font-sans uppercase tracking-wider text-amov-muted">
                      Чтобы поделиться впечатлениями о покупке, необходимо войти в аккаунт
                    </p>
                    <Link
                      to={loginRedirectUrl}
                      state={{ from: location }}
                      className="inline-block bg-amov-dark text-amov-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-amov-black transition-colors"
                    >
                      ВОЙТИ В АККАУНТ ↗
                    </Link>
                  </div>
                ) : (
                  <form onSubmit={handleReviewSubmit} className="space-y-4">
                    {reviewSuccess && (
                      <div className="p-3 bg-amov-dark text-amov-cream text-xs uppercase tracking-wider">
                        {reviewSuccess}
                      </div>
                    )}

                    {reviewError && (
                      <div className="p-3 border border-amov-dark bg-amov-dark/5 text-amov-dark text-xs uppercase tracking-wider">
                        {reviewError}
                      </div>
                    )}

                    {/* Rating Selector */}
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-amov-dark mb-1.5">
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
                                ? 'bg-amov-dark text-amov-cream border-amov-dark'
                                : 'border-amov-dark/30 text-amov-dark'
                            }`}
                          >
                            ★ {val}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Fit Feedback */}
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-amov-dark mb-1.5">
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
                                ? 'bg-amov-dark text-amov-cream border-amov-dark font-semibold'
                                : 'border-amov-dark/30 text-amov-dark hover:border-amov-dark'
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
                        className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-amov-dark mb-1.5"
                      >
                        КОММЕНТАРИЙ
                      </label>
                      <textarea
                        id="rev-comment"
                        rows={4}
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        placeholder="ПОДЕЛИТЕСЬ ВАШИМИ ВПЕЧАТЛЕНИЯМИ О ПОСАДКЕ И МАТЕРИАЛАХ..."
                        className="w-full bg-[#F2E9DB] border border-amov-dark/30 focus:border-amov-dark p-2.5 text-xs font-sans uppercase tracking-wider outline-none text-amov-black resize-none"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={createReviewMutation.isPending}
                      className="w-full bg-amov-dark text-amov-cream hover:bg-amov-black py-3 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50"
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

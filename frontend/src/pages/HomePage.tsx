import { useState, useMemo, useEffect } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, categoriesApi, favoritesApi } from '../api/endpoints';
import { ProductCard } from '../components/ProductCard';
import { useAuthStore } from '../store/auth';

const PAGE_SIZE = 12;

export function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  const categoryIdParam = searchParams.get('category_id') || '';
  const searchParam = searchParams.get('search') || '';
  const minPriceParam = searchParams.get('min_price') || '';
  const maxPriceParam = searchParams.get('max_price') || '';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const offset = (Math.max(1, pageParam) - 1) * PAGE_SIZE;

  // Local filter states for input forms
  const [minPriceInput, setMinPriceInput] = useState(minPriceParam);
  const [maxPriceInput, setMaxPriceInput] = useState(maxPriceParam);

  useEffect(() => {
    setMinPriceInput(minPriceParam);
    setMaxPriceInput(maxPriceParam);
  }, [minPriceParam, maxPriceParam]);

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
  });

  // Fetch products
  const { data: productsData, isLoading: isProductsLoading } = useQuery({
    queryKey: ['products', categoryIdParam, searchParam, minPriceParam, maxPriceParam, offset],
    queryFn: () =>
      productsApi.list({
        category_id: categoryIdParam || undefined,
        search: searchParam || undefined,
        min_price: minPriceParam || undefined,
        max_price: maxPriceParam || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  });

  // Fetch favorites
  const { data: favoritesData } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => favoritesApi.list(),
    enabled: isAuthenticated,
  });

  const favoriteIds = useMemo(() => {
    return new Set((favoritesData?.data || []).map((p) => p.id));
  }, [favoritesData]);

  // Favorite toggle mutation
  const toggleFavoriteMutation = useMutation({
    mutationFn: async (productId: string) => {
      if (!isAuthenticated) {
        navigate(loginRedirectUrl, { state: { from: location } });
        return;
      }
      if (favoriteIds.has(productId)) {
        await favoritesApi.remove(productId);
      } else {
        await favoritesApi.add(productId);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
  });

  const handleCategorySelect = (id: string) => {
    const next = new URLSearchParams(searchParams);
    if (id) {
      next.set('category_id', id);
    } else {
      next.delete('category_id');
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const handlePriceFilterApply = (e: React.FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams(searchParams);
    if (minPriceInput) next.set('min_price', minPriceInput);
    else next.delete('min_price');

    if (maxPriceInput) next.set('max_price', maxPriceInput);
    else next.delete('max_price');

    next.set('page', '1');
    setSearchParams(next);
  };

  const handleResetFilters = () => {
    setMinPriceInput('');
    setMaxPriceInput('');
    setSearchParams({});
  };

  const totalProducts = productsData?.metadata?.total ?? (productsData?.data?.length || 0);
  const totalPages = Math.ceil(totalProducts / PAGE_SIZE) || 1;
  const products = productsData?.data || [];
  const categories = categoriesData?.data || [];

  const handlePageChange = (newPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(newPage));
    setSearchParams(next);
    const catalogElement = document.getElementById('catalog');
    if (catalogElement) {
      catalogElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="w-full">
      {/* 1. HERO SECTION: Full Bleed #3F2021 (Dark Chocolate) */}
      <section className="relative w-full bg-amov-dark text-amov-cream overflow-hidden">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[580px] lg:min-h-[680px]">
            {/* Left Column: Editorial Typography */}
            <div className="flex flex-col justify-between py-12 lg:py-20 pr-0 lg:pr-12">
              <div className="space-y-6">
                <div className="text-[12px] font-sans font-medium uppercase tracking-widest text-amov-cream/80">
                  AMOV — БРЕНД СОЛНЦЕЗАЩИТНЫХ ОЧКОВ
                </div>

                <div className="relative">
                  <h1 className="font-serif text-5xl sm:text-7xl lg:text-8xl font-normal uppercase leading-[0.9] tracking-tight text-amov-cream">
                    СТИЛЬ
                    <br />
                    В ДЕТАЛЯХ
                  </h1>
                  <span className="font-serif text-7xl sm:text-9xl text-amov-denim/60 leading-none select-none">
                    ”
                  </span>
                </div>

                <p className="max-w-md text-xs sm:text-sm font-sans uppercase tracking-wider text-amov-cream/70 leading-relaxed">
                  Коллекции солнцезащитных очков вне времени. Бескомпромиссная геометрия, премиальный итальянский ацетат и полная защита UV400.
                </p>
              </div>

              <div className="pt-8 space-y-6">
                <div>
                  <a
                    href="#catalog"
                    className="inline-block bg-amov-cream text-amov-dark hover:bg-amov-cream/90 px-8 py-3.5 text-xs font-sans font-semibold uppercase tracking-widest transition-colors"
                  >
                    ПЕРЕЙТИ В КАТАЛОГ ↗
                  </a>
                </div>

                {/* Marketplace CTAs */}
                <div className="flex items-center gap-6 text-xs font-semibold uppercase tracking-wider text-amov-denim pt-2">
                  <a
                    href="https://wildberries.ru"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-amov-cream transition-colors"
                  >
                    WB ↗
                  </a>
                  <a
                    href="https://ozon.ru"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-amov-cream transition-colors"
                  >
                    OZON ↗
                  </a>
                  <a
                    href="https://lamoda.ru"
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-amov-cream transition-colors"
                  >
                    LAMODA ↗
                  </a>
                </div>
              </div>
            </div>

            {/* Right Column: Hero Visual Full Bleed / Split */}
            <div className="relative hidden lg:block h-full min-h-[500px]">
              <div className="absolute inset-0 bg-[#2C1617] border-l border-amov-cream/15 overflow-hidden flex items-center justify-center">
                <svg
                  className="w-full h-full object-cover opacity-90"
                  viewBox="0 0 600 800"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <rect width="600" height="800" fill="#2E1718" />
                  <path
                    d="M 100 150 L 500 150 L 450 650 L 150 650 Z"
                    stroke="#F2E9DB"
                    strokeWidth="1"
                    strokeOpacity="0.3"
                  />
                  <line x1="300" y1="50" x2="300" y2="750" stroke="#7594B3" strokeWidth="1" strokeOpacity="0.4" />
                  <circle cx="300" cy="400" r="180" stroke="#F2E9DB" strokeWidth="1" strokeOpacity="0.25" />
                  <text
                    x="300"
                    y="390"
                    fill="#F2E9DB"
                    textAnchor="middle"
                    fontFamily="serif"
                    fontSize="54"
                    letterSpacing="8"
                    opacity="0.8"
                  >
                    AMÓV
                  </text>
                  <text
                    x="300"
                    y="430"
                    fill="#7594B3"
                    textAnchor="middle"
                    fontFamily="sans-serif"
                    fontSize="13"
                    letterSpacing="4"
                  >
                    EDITORIAL COLLECTION 2026
                  </text>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. DENIM SECTION: Philosophy / Standards (#7594B3) */}
      <section className="w-full bg-amov-denim text-amov-cream py-14 md:py-20 border-b border-amov-cream/20">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6">
          <div className="mb-10">
            <span className="text-[11px] font-sans font-medium uppercase tracking-widest text-amov-cream/80">
              ( ФИЛОСОФИЯ И ПРОЦЕСС )
            </span>
            <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-amov-cream mt-2">
              ТОТ САМЫЙ АКЦЕНТ
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 divide-y md:divide-y-0 md:divide-x divide-amov-cream/30">
            <div className="pt-6 md:pt-0 md:pr-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-amov-cream">
                (1) АНАЛИЗИРУЕМ ТРЕНДЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-amov-cream/85 leading-relaxed">
                Отбираем вневременные силуэты мировых подиумов. Никаких быстротечных микротрендов — только выверенная классика.
              </p>
            </div>

            <div className="pt-6 md:pt-0 md:px-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-amov-cream">
                (2) ВЫБИРАЕМ МАТЕРИАЛЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-amov-cream/85 leading-relaxed">
                Высококачественный ацетат ручной полировки, надежные шарнирные крепления и стойкое антибликовое покрытие.
              </p>
            </div>

            <div className="pt-6 md:pt-0 md:pl-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-amov-cream">
                (3) ЗАЩИТА UV400
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-amov-cream/85 leading-relaxed">
                Каждая модель проходит лабораторный контроль категории светопропускания и блокирует 100% спектра UVA/UVB лучей.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. CATALOG SECTION: Warm Cream (#F2E9DB) */}
      <section id="catalog" className="w-full bg-[#F2E9DB] py-14 md:py-20">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6">
          {/* Header of catalog & Active Filters */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-8 border-b border-amov-dark/20">
            <div>
              <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-amov-muted">
                ( КАТАЛОГ КОЛЛЕКЦИЙ )
              </span>
              <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-amov-dark mt-1">
                СОЛНЦЕЗАЩИТНЫЕ ОЧКИ
              </h2>
            </div>

            <div className="text-xs font-sans uppercase tracking-wider text-amov-muted">
              ( ПОКАЗАНО: {products.length} ИЗ {totalProducts} МОДЕЛЕЙ )
            </div>
          </div>

          {/* Filter Bar */}
          <div className="py-6 space-y-4">
            {/* Category tabs */}
            {categories.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleCategorySelect('')}
                  className={`px-3 py-1.5 text-xs font-sans uppercase tracking-wider border transition-colors ${
                    !categoryIdParam
                      ? 'bg-amov-dark text-amov-cream border-amov-dark font-semibold'
                      : 'border-amov-dark/30 hover:border-amov-dark text-amov-dark'
                  }`}
                >
                  ВСЕ КАТЕГОРИИ
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => handleCategorySelect(cat.id)}
                    className={`px-3 py-1.5 text-xs font-sans uppercase tracking-wider border transition-colors ${
                      categoryIdParam === cat.id
                        ? 'bg-amov-dark text-amov-cream border-amov-dark font-semibold'
                        : 'border-amov-dark/30 hover:border-amov-dark text-amov-dark'
                    }`}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            )}

            {/* Price range & Search active state */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <form onSubmit={handlePriceFilterApply} className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-sans uppercase tracking-wider text-amov-muted mr-1">
                  ЦЕНА, ₽:
                </span>
                <input
                  type="number"
                  placeholder="ОТ"
                  value={minPriceInput}
                  onChange={(e) => setMinPriceInput(e.target.value)}
                  className="w-24 bg-[#F2E9DB] border border-amov-dark/30 focus:border-amov-dark px-2.5 py-1 text-xs font-sans outline-none"
                />
                <span className="text-amov-muted">—</span>
                <input
                  type="number"
                  placeholder="ДО"
                  value={maxPriceInput}
                  onChange={(e) => setMaxPriceInput(e.target.value)}
                  className="w-24 bg-[#F2E9DB] border border-amov-dark/30 focus:border-amov-dark px-2.5 py-1 text-xs font-sans outline-none"
                />
                <button
                  type="submit"
                  className="bg-amov-dark text-amov-cream hover:bg-amov-black px-3 py-1 text-xs font-sans uppercase tracking-wider"
                >
                  ПРИМЕНИТЬ
                </button>
              </form>

              {(categoryIdParam || searchParam || minPriceParam || maxPriceParam) && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="text-xs font-sans uppercase tracking-wider text-amov-dark hover:opacity-60 underline underline-offset-4"
                >
                  ( СБРОСИТЬ ВСЕ ФИЛЬТРЫ × )
                </button>
              )}
            </div>
          </div>

          {/* Products Grid */}
          {isProductsLoading ? (
            <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-amov-muted">
              ( ЗАГРУЗКА КАТАЛОГА... )
            </div>
          ) : products.length === 0 ? (
            <div className="py-24 text-center border border-amov-dark/20 p-8">
              <div className="font-serif text-2xl uppercase tracking-wider text-amov-dark">
                МОДЕЛИ НЕ НАЙДЕНЫ
              </div>
              <p className="mt-2 text-xs font-sans uppercase tracking-wider text-amov-muted">
                Попробуйте изменить параметры фильтрации или поисковый запрос
              </p>
              <button
                type="button"
                onClick={handleResetFilters}
                className="mt-6 inline-block bg-amov-dark text-amov-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
              >
                СБРОСИТЬ ФИЛЬТРЫ ↗
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 md:gap-8">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  isFavorite={favoriteIds.has(product.id)}
                  onToggleFavorite={(id) => toggleFavoriteMutation.mutate(id)}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-14 pt-8 border-t border-amov-dark/20 flex items-center justify-between">
              <button
                type="button"
                disabled={pageParam <= 1}
                onClick={() => handlePageChange(pageParam - 1)}
                className="border border-amov-dark px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-amov-dark hover:text-amov-cream transition-colors"
              >
                ← ПРЕДЫДУЩАЯ
              </button>

              <div className="text-xs font-sans uppercase tracking-widest text-amov-muted">
                СТРАНИЦА {pageParam} ИЗ {totalPages}
              </div>

              <button
                type="button"
                disabled={pageParam >= totalPages}
                onClick={() => handlePageChange(pageParam + 1)}
                className="border border-amov-dark px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-amov-dark hover:text-amov-cream transition-colors"
              >
                СЛЕДУЮЩАЯ →
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

import { useMemo } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, favoritesApi } from '../api/endpoints';
import { ProductCard } from '../components/ProductCard';
import { useAuthStore } from '../store/auth';

export function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  // Fetch trending products (limit 8)
  const { data: productsData, isLoading: isProductsLoading } = useQuery({
    queryKey: ['trending-products'],
    queryFn: () => productsApi.list({ limit: 8 }),
  });

  const trendingProducts = productsData?.data || [];

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

  return (
    <div className="w-full">
      {/* 1. HERO SECTION: Full Bleed #3F2021 (Dark Chocolate) */}
      <section className="relative w-full bg-sf-dark text-sf-cream overflow-hidden">
        <div className="w-full px-4 md:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[580px] lg:min-h-[680px]">
            {/* Left Column: Editorial Typography */}
            <div className="flex flex-col justify-between py-12 lg:py-20 pr-0 lg:pr-12">
              <div className="space-y-6">
                <div className="text-[12px] font-sans font-medium uppercase tracking-widest text-sf-cream/80">
                  SHOPPERFLOX — ОДЕЖДА И АКСЕССУАРЫ
                </div>

                <div className="relative">
                  <h1 className="font-serif text-5xl sm:text-7xl lg:text-8xl font-normal uppercase leading-[0.9] tracking-tight text-sf-cream">
                    СТИЛЬ
                    <br />
                    В ДЕТАЛЯХ
                  </h1>
                  <span className="font-serif text-7xl sm:text-9xl text-sf-denim/60 leading-none select-none">
                    ”
                  </span>
                </div>

                <p className="max-w-md text-xs sm:text-sm font-sans uppercase tracking-wider text-sf-cream/70 leading-relaxed">
                  Коллекции одежды и аксессуаров вне времени. Бескомпромиссная геометрия, премиальные ткани и архитектурный силуэт.
                </p>
              </div>

              <div className="pt-8 space-y-6">
                <div>
                  <Link
                    to="/catalog"
                    className="inline-block bg-sf-cream text-sf-dark hover:bg-sf-cream/90 px-8 py-3.5 text-xs font-sans font-semibold uppercase tracking-widest transition-colors"
                  >
                    ПЕРЕЙТИ В КАТАЛОГ ↗
                  </Link>
                </div>

                {/* Internal Navigation Shortcuts */}
                <div className="flex items-center gap-6 text-xs font-semibold uppercase tracking-wider text-sf-denim pt-2">
                  <Link
                    to="/catalog"
                    className="hover:text-sf-cream transition-colors"
                  >
                    КОЛЛЕКЦИИ ↗
                  </Link>
                  <Link
                    to="/favorites"
                    className="hover:text-sf-cream transition-colors"
                  >
                    ИЗБРАННОЕ ↗
                  </Link>
                  <Link
                    to="/cart"
                    className="hover:text-sf-cream transition-colors"
                  >
                    КОРЗИНА ↗
                  </Link>
                </div>
              </div>
            </div>

            {/* Right Column: Editorial Hero Visual */}
            <div className="relative w-full h-full min-h-[400px] lg:min-h-full flex items-center justify-center p-6 lg:p-12 border-t lg:border-t-0 lg:border-l border-sf-cream/20">
              <div className="relative w-full max-w-lg aspect-[2/3] bg-sf-cream/10 border border-sf-cream/30 overflow-hidden flex flex-col justify-between p-6">
                <div className="flex justify-between items-start text-xs font-sans tracking-widest text-sf-cream/60">
                  <span>LOOKBOOK // 2026</span>
                  <span>( SHOPPERFLOX )</span>
                </div>

                <div className="text-center space-y-2">
                  <div className="font-serif text-3xl sm:text-4xl uppercase tracking-wider text-sf-cream">
                    АРХИТЕКТУРНЫЙ СИЛУЭТ
                  </div>
                  <div className="text-[11px] font-sans uppercase tracking-widest text-sf-denim">
                    ПРЕМИАЛЬНЫЕ МАТЕРИАЛЫ &amp; ЧЁТКИЕ ЛИНИИ
                  </div>
                </div>

                <div className="flex justify-between items-end text-xs font-sans tracking-widest text-sf-cream/60">
                  <span>01 / 08</span>
                  <Link
                    to="/catalog"
                    className="text-sf-cream hover:underline uppercase text-[11px]"
                  >
                    СМОТРЕТЬ КАТАЛОГ ↗
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. TRENDING PRODUCTS SECTION: Immediately after Hero */}
      <section className="w-full bg-[#F2E9DB] py-14 md:py-20 border-b border-sf-dark/15">
        <div className="w-full px-4 md:px-8 space-y-8">
          {/* Header of Section */}
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-sf-dark/20">
            <div>
              <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
                ( СЕЗОННЫЙ ВЫБОР )
              </span>
              <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-dark mt-1">
                ТРЕНДОВЫЕ ВЕЩИ
              </h2>
            </div>

            <Link
              to="/catalog"
              className="inline-flex items-center gap-1.5 text-xs font-sans font-semibold uppercase tracking-widest text-sf-dark hover:opacity-70 transition-opacity whitespace-nowrap"
            >
              ВЕСЬ КАТАЛОГ ↗
            </Link>
          </div>

          {/* Trending Products Grid */}
          <div>
            {isProductsLoading ? (
              <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-sf-muted">
                ( ЗАГРУЗКА ТРЕНДОВЫХ ВЕЩЕЙ... )
              </div>
            ) : trendingProducts.length === 0 ? (
              <div className="py-14 text-center space-y-3">
                <div className="font-serif text-xl uppercase tracking-wider text-sf-dark">
                  ТРЕНДОВЫЕ МОДЕЛИ СКОРО ПОЯВЯТСЯ
                </div>
                <p className="text-xs font-sans uppercase tracking-wider text-sf-muted">
                  Перейдите в каталог, чтобы ознакомиться с доступными коллекциями
                </p>
                <Link
                  to="/catalog"
                  className="mt-2 inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-sf-black transition-colors"
                >
                  ПЕРЕЙТИ В КАТАЛОГ ↗
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-5 gap-y-10">
                {trendingProducts.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    columns={4}
                    isFavorite={favoriteIds.has(product.id)}
                    onToggleFavorite={(id) => toggleFavoriteMutation.mutate(id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 3. PHILOSOPHY / PROCESS SECTION: Muted Denim (#7594B3) */}
      <section className="w-full bg-sf-denim text-sf-cream py-16 md:py-24">
        <div className="w-full px-4 md:px-8">
          <div className="max-w-2xl mb-12">
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-cream/70">
              ( ТОТ САМЫЙ АКЦЕНТ )
            </span>
            <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-cream mt-2">
              ТОТ САМЫЙ АКЦЕНТ
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 divide-y md:divide-y-0 md:divide-x divide-sf-cream/30">
            <div className="pt-6 md:pt-0 md:pr-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-sf-cream">
                (1) АНАЛИЗИРУЕМ ТРЕНДЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-cream/85 leading-relaxed">
                Отбираем вневременные силуэты мировых подиумов. Никаких быстротечных микротрендов — только выверенная классика.
              </p>
            </div>

            <div className="pt-6 md:pt-0 md:px-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-sf-cream">
                (2) ВЫБИРАЕМ МАТЕРИАЛЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-cream/85 leading-relaxed">
                Высококачественные премиальные материалы, надежная фурнитура и безупречное качество пошива каждого изделия.
              </p>
            </div>

            <div className="pt-6 md:pt-0 md:pl-8 space-y-3">
              <div className="text-[13px] font-sans font-bold uppercase tracking-wider text-sf-cream">
                (3) ПРЕМИУМ МАТЕРИАЛЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-cream/85 leading-relaxed">
                Каждое изделие проходит строгий контроль качества материалов, прочности швов и идеальной посадки.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

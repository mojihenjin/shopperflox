import { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { brandsApi } from '../api/brands';
import { productsApi, favoritesApi } from '../api/endpoints';
import { ProductCard } from '../components/ProductCard';
import { useAuthStore } from '../store/auth';
import { formatImageUrl } from '../utils/format';

export function BrandDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  // 1. Fetch Brand Data
  const {
    data: brandData,
    isLoading: isBrandLoading,
    error: brandError,
  } = useQuery({
    queryKey: ['brand', slug],
    queryFn: () => brandsApi.getBySlug(slug || ''),
    enabled: Boolean(slug),
  });

  const brand = brandData?.data;

  // 2. Fetch Active Products (limit 100)
  const { data: productsData, isLoading: isProductsLoading } = useQuery({
    queryKey: ['products', { brand_slug: slug, limit: 100 }],
    queryFn: () => productsApi.list({ limit: 100 }),
    enabled: Boolean(brand && !brand.is_deleted),
  });

  // Filter products by brand_slug or brand name
  const brandProducts = useMemo(() => {
    if (!brand || brand.is_deleted) return [];
    return (productsData?.data || []).filter(
      (p) =>
        (p.brand_slug && p.brand_slug.toLowerCase() === brand.slug.toLowerCase()) ||
        (p.brand && p.brand.trim().toLowerCase() === brand.name.trim().toLowerCase())
    );
  }, [brand, productsData]);

  // 3. Favorites
  const { data: favoritesData } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => favoritesApi.list(),
    enabled: isAuthenticated,
  });

  const favoriteIds = useMemo(() => {
    return new Set((favoritesData?.data || []).map((f) => f.id));
  }, [favoritesData]);

  const toggleFavoriteMutation = useMutation({
    mutationFn: async (productId: string) => {
      const isFav = favoriteIds.has(productId);
      if (isFav) {
        await favoritesApi.remove(productId);
      } else {
        await favoritesApi.add(productId);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
  });

  if (isBrandLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ЗАГРУЗКА БРЕНДА... )
        </div>
      </div>
    );
  }

  if (brandError || !brand) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex flex-col items-center justify-center px-4 py-24 text-center space-y-4">
        <span className="text-[11px] font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( 404 / НЕ НАЙДЕНО )
        </span>
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          БРЕНД НЕ НАЙДЕН
        </h1>
        <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-sm">
          Запрашиваемый бренд не существует либо был удален с платформы.
        </p>
        <div className="pt-2">
          <Link
            to="/catalog"
            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
          >
            ВЕСЬ КАТАЛОГ ↗
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#F2E9DB] min-h-[85vh] py-8 md:py-12 px-4 md:px-8">
      <div className="w-full max-w-none space-y-8">
        {/* Breadcrumbs */}
        <div className="border-b border-[#3F2021]/15 pb-3">
          <div className="flex items-center gap-2 text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
            <Link to="/catalog" className="hover:text-[#3F2021]">
              КАТАЛОГ
            </Link>
            <span>/</span>
            <span className="text-[#3F2021]/60">БРЕНДЫ</span>
            <span>/</span>
            <span className="text-[#3F2021] font-medium">{brand.name}</span>
          </div>
        </div>

        {/* Brand Header / Hero Banner */}
        <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-10 rounded-none flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-5 sm:gap-8">
            {brand.logo_url ? (
              <img
                src={formatImageUrl(brand.logo_url, brand.name)}
                alt={brand.name}
                className="w-20 h-20 sm:w-28 sm:h-28 object-cover border border-[#3F2021] rounded-none shrink-0"
              />
            ) : (
              <div className="w-20 h-20 sm:w-28 sm:h-28 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-center font-serif text-2xl sm:text-4xl text-[#3F2021] font-bold rounded-none shrink-0 select-none">
                {brand.name.slice(0, 2).toUpperCase()}
              </div>
            )}

            <div className="space-y-1.5">
              <span className="text-[10px] sm:text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                ( ОФИЦИАЛЬНАЯ СТРАНИЦА БРЕНДА )
              </span>
              <h1 className="font-serif text-3xl sm:text-5xl uppercase tracking-wider text-[#3F2021] leading-none">
                {brand.name}
              </h1>

              {brand.his_url && !brand.is_deleted && (
                <div className="pt-1">
                  <a
                    href={brand.his_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] hover:opacity-70 underline underline-offset-4 font-semibold"
                  >
                    ОФИЦИАЛЬНЫЙ РЕСУРС ↗
                  </a>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <Link
              to="/catalog"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none whitespace-nowrap"
            >
              ВЕСЬ КАТАЛОГ ↗
            </Link>
          </div>
        </div>

        {/* IF DELETED: Editorial Notice (NO CATALOG) */}
        {brand.is_deleted ? (
          <div className="p-8 md:p-14 bg-[#3F2021] text-[#F2E9DB] border border-[#3F2021] text-center space-y-4 rounded-none my-8">
            <span className="text-[10px] font-mono uppercase tracking-widest text-[#FF8562] font-bold">
              ( ВНИМАНИЕ )
            </span>
            <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#F2E9DB]">
              БРЕНД СНЯЛСЯ С ПРОДАЖИ
            </h2>
            <p className="text-xs font-sans uppercase tracking-wider text-[#F2E9DB]/75 max-w-lg mx-auto leading-relaxed">
              Бренд «{brand.name}» прекратил продажи на платформе ShopperFlox. Все товары бренда сняты с витрины и недоступны для заказа.
            </p>
            <div className="pt-3">
              <Link
                to="/catalog"
                className="inline-block border border-[#F2E9DB] text-[#F2E9DB] hover:bg-[#F2E9DB] hover:text-[#3F2021] px-6 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
              >
                ПЕРЕЙТИ В КАТАЛОГ ↗
              </Link>
            </div>
          </div>
        ) : (
          /* IF ACTIVE: Products Section */
          <div className="space-y-6 pt-4">
            <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-3">
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                  ( КОЛЛЕКЦИЯ БРЕНДА )
                </span>
                <span className="text-xs font-mono uppercase text-[#3F2021]/60">
                  [{brandProducts.length} МОДЕЛЕЙ]
                </span>
              </div>
            </div>

            {isProductsLoading ? (
              <div className="p-16 bg-[#FFFFFF] border border-[#3F2021] text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( ЗАГРУЗКА ТОВАРОВ БРЕНДА... )
              </div>
            ) : brandProducts.length === 0 ? (
              <div className="p-14 bg-[#FFFFFF] border border-[#3F2021] text-center space-y-3 rounded-none">
                <span className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
                  ( КАТАЛОГ ПУСТ )
                </span>
                <h3 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  ПОКА НЕТ ТОВАРОВ ЭТОГО БРЕНДА
                </h3>
                <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-sm mx-auto">
                  Следите за обновлениями каталога или ознакомьтесь с другими коллекциями платформы.
                </p>
                <div className="pt-2">
                  <Link
                    to="/catalog"
                    className="inline-block bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
                  >
                    СМОТРЕТЬ ДРУГИЕ ТОВАРЫ ↗
                  </Link>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-5 gap-y-10">
                {brandProducts.map((product) => (
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
        )}
      </div>
    </div>
  );
}

import { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi, favoritesApi } from '../api/endpoints';
import { ProductCard } from '../components/ProductCard';
import { useAuthStore } from '../store/auth';
import { formatDate } from '../utils/format';

export function PublicUserProfilePage() {
  const { login } = useParams<{ login: string }>();
  const queryClient = useQueryClient();
  const { isAuthenticated, user: authUser } = useAuthStore();

  // 1. Fetch Author Public Profile Data
  const {
    data: profileData,
    isLoading: isProfileLoading,
    error: profileError,
  } = useQuery({
    queryKey: ['publicUser', login],
    queryFn: () => usersApi.getPublicProfile(login || ''),
    enabled: Boolean(login),
  });

  const profile = profileData?.data;

  // 2. Fetch User Favorites (for ProductCard heart state)
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

  const isOwnProfile = Boolean(
    authUser && profile && authUser.login.toLowerCase() === profile.login.toLowerCase()
  );

  if (isProfileLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ЗАГРУЗКА ПРОФИЛЯ АВТОРА... )
        </div>
      </div>
    );
  }

  if (profileError || !profile) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex flex-col items-center justify-center px-4 py-24 text-center space-y-4">
        <span className="text-[11px] font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( 404 / НЕ НАЙДЕНО )
        </span>
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          АВТОР НЕ НАЙДЕН
        </h1>
        <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-sm">
          Запрашиваемый профиль автора не существует либо был удален с платформы.
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

  const products = profile.products || [];

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
            <span className="text-[#3F2021]/60">АВТОРЫ</span>
            <span>/</span>
            <span className="text-[#3F2021] font-medium">@{profile.login}</span>
          </div>
        </div>

        {/* Author Header / Hero Banner */}
        <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-10 rounded-none flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-5 sm:gap-8">
            <div className="w-20 h-20 sm:w-28 sm:h-28 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-center font-serif text-2xl sm:text-4xl text-[#3F2021] font-bold rounded-none shrink-0 select-none">
              {(profile.login[0] || 'A').toUpperCase()}
            </div>

            <div className="space-y-1.5">
              <span className="text-[10px] sm:text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
                ( САМОСТОЯТЕЛЬНЫЙ АВТОР · SELF-WORKED )
              </span>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="font-serif text-3xl sm:text-5xl uppercase tracking-wider text-[#3F2021] leading-none">
                  @{profile.login}
                </h1>
                {profile.verified_profile && (
                  <span
                    className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-[#3F2021] text-[#F2E9DB] inline-flex items-center justify-center text-xs font-bold select-none leading-none shrink-0"
                    title="Верифицированный автор"
                  >
                    ✓
                  </span>
                )}
              </div>

              <div className="pt-1 flex flex-wrap items-center gap-3 text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
                <span>НА ПЛАТФОРМЕ С {formatDate(profile.created_at)}</span>
                <span>·</span>
                <span className="font-mono font-semibold text-[#3F2021]">
                  [ {products.length} АВТОРСКИХ ИЗДЕЛИЙ ]
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            {isOwnProfile && (
              <Link
                to="/creator/products/new"
                className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none whitespace-nowrap"
              >
                + СОЗДАТЬ ТОВАР ↗
              </Link>
            )}
            <Link
              to="/catalog"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none whitespace-nowrap"
            >
              ВЕСЬ КАТАЛОГ ↗
            </Link>
          </div>
        </div>

        {/* Self-worked Products Section */}
        <div className="space-y-6 pt-4">
          <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-3">
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                ( АВТОРСКИЕ ИЗДЕЛИЯ SELF-WORKED )
              </span>
              <span className="text-xs font-mono uppercase text-[#3F2021]/60">
                [{products.length} МОДЕЛЕЙ]
              </span>
            </div>
          </div>

          {products.length === 0 ? (
            <div className="p-14 bg-[#FFFFFF] border border-[#3F2021] text-center space-y-3 rounded-none">
              <span className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( КАТАЛОГ ПУСТ )
              </span>
              <h3 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                У АВТОРА ПОКА НЕТ ОПУБЛИКОВАННЫХ ИЗДЕЛИЙ
              </h3>
              <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-sm mx-auto">
                Следите за обновлениями автора или ознакомьтесь с другими коллекциями платформы.
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
              {products.map((product) => (
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
    </div>
  );
}

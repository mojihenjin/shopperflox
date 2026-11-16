import { useQuery } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';
import { authApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';

export function CreatorNewProductPage() {
  const { isAuthenticated } = useAuthStore();

  const { data: profileData, isLoading } = useQuery({
    queryKey: ['userProfile'],
    queryFn: () => authApi.getMe(),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return <Navigate to="/login?redirect=%2Fcreator%2Fproducts%2Fnew" replace />;
  }

  if (isLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ПРОВЕРКА ПРИВИЛЕГИЙ КРИЭЙТОРА... )
        </div>
      </div>
    );
  }

  const user = profileData?.data?.user;
  const permissions = user?.global_permissions || [];
  const isAuthorized =
    permissions.includes('*') ||
    permissions.some((p) => p.startsWith('creator:'));

  if (!isAuthorized) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[70vh] flex items-center justify-center py-20 px-4 md:px-8">
        <div className="max-w-xl w-full bg-[#FFFFFF] border border-[#3F2021] p-8 md:p-12 text-center rounded-none space-y-6">
          <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
            ( 403 / ДОСТУП ОГРАНИЧЕН )
          </div>
          <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
            ТРЕБУЮТСЯ ПРАВА СОЗДАТЕЛЯ
          </h1>
          <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 leading-relaxed">
            Ваш аккаунт <span className="font-mono font-bold text-[#3F2021]">@{user?.login || 'anonymous'}</span> не обладает правами <code className="bg-[#F2E9DB] px-1.5 py-0.5">creator:*</code> или администратора.
          </p>
          <div className="pt-4 flex justify-center gap-4">
            <Link
              to="/"
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-widest transition-colors"
            >
              В КАТАЛОГ ↗
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const creatorPermissions = permissions.filter(
    (p) => p === '*' || p.startsWith('creator:')
  );

  return (
    <div className="w-full bg-[#F2E9DB] min-h-[80vh] py-12 md:py-20 px-4 md:px-8">
      <div className="w-full max-w-4xl mx-auto space-y-8">
        {/* Navigation & Breadcrumbs */}
        <div className="flex items-center justify-between border-b border-[#3F2021]/20 pb-4">
          <Link
            to="/"
            className="text-xs font-sans uppercase tracking-widest text-[#3F2021] hover:opacity-60 transition-opacity"
          >
            ← ВЕРНУТЬСЯ В КАТАЛОГ
          </Link>
          <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            ( ПАНЕЛЬ СОЗДАТЕЛЯ )
          </div>
        </div>

        {/* Main Editorial Card */}
        <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-10 md:p-12 rounded-none space-y-8">
          {/* Header */}
          <div className="border-b border-[#3F2021]/15 pb-6">
            <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 mb-2">
              ( РАЗДЕЛ ПУБЛИКАЦИИ )
            </div>
            <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021]">
              СОЗДАНИЕ НОВОГО ТОВАРА
            </h1>
            <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
              ShopperFlox Creator Studio / Панель добавления моделей в публичную витрину
            </p>
          </div>

          {/* Author metadata panel */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-[#F2E9DB]/60 p-4 sm:p-6 border border-[#3F2021]/20">
            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
                АВТОР / ВЛАДЕЛЕЦ:
              </div>
              <div className="font-mono text-sm md:text-base font-bold text-[#3F2021] mt-1">
                @{user?.login}
              </div>
            </div>

            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
                АКТИВНЫЕ ПРИВИЛЕГИИ CREATOR:
              </div>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {creatorPermissions.length > 0 ? (
                  creatorPermissions.map((perm) => (
                    <span
                      key={perm}
                      className="inline-block bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[10px] font-mono tracking-wider font-semibold"
                    >
                      {perm}
                    </span>
                  ))
                ) : (
                  <span className="text-xs font-mono text-[#3F2021]">НЕТ</span>
                )}
              </div>
            </div>
          </div>

          {/* Editorial Stub Block */}
          <div className="border border-[#3F2021]/25 p-8 text-center space-y-4 bg-[#F2E9DB]/20">
            <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
              ( В РАЗРАБОТКЕ )
            </div>
            <h2 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
              ИНТЕРФЕЙС СОЗДАНИЯ И ПУБЛИКАЦИИ ТОВАРА НАХОДИТСЯ В РАЗРАБОТКЕ
            </h2>
            <p className="max-w-2xl mx-auto text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 leading-relaxed">
              В ближайшем обновлении здесь будет доступна форма загрузки лукбук-фотографий с соотношением 2:3, выбор категорий одежды и аксессуаров, настройка цветовых вариаций и управление складскими SKU.
            </p>
          </div>

          {/* Bottom actions */}
          <div className="pt-4 flex flex-wrap items-center justify-between gap-4 border-t border-[#3F2021]/15">
            <Link
              to="/"
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-3 text-xs font-sans uppercase tracking-widest transition-colors font-semibold"
            >
              ВЕРНУТЬСЯ В КАТАЛОГ ↗
            </Link>

            <Link
              to="/profile"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-6 py-3 text-xs font-sans uppercase tracking-widest transition-colors"
            >
              МОЙ ПРОФИЛЬ ↗
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

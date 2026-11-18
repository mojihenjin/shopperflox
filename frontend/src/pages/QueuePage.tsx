import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { brandsApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { QueueAndAnalyticsView } from '../components/QueueAndAnalyticsView';

export function QueuePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuthStore();

  const permissions = user?.global_permissions || [];
  const hasSelfWorkedAccess =
    permissions.includes('*') ||
    permissions.includes('creator:products');

  // Fetch My Brands
  const { data: myBrandsData, isLoading: isBrandsLoading } = useQuery({
    queryKey: ['myBrands'],
    queryFn: () => brandsApi.my(),
  });

  const activeMyBrands = useMemo(() => {
    return (myBrandsData?.data || []).filter(
      (b) =>
        !b.brand.is_deleted &&
        (b.role === 'representative' ||
          b.role === 'moderator' ||
          b.role === 'queue_manager')
    );
  }, [myBrandsData]);

  // Selected Scope: 'self-worked' | string (brandId)
  const brandParam = searchParams.get('brand');
  const [selectedScope, setSelectedScope] = useState<string>('self-worked');

  // Determine initial scope
  useEffect(() => {
    if (brandParam) {
      setSelectedScope(brandParam);
    } else if (hasSelfWorkedAccess) {
      setSelectedScope('self-worked');
    } else if (activeMyBrands.length > 0) {
      setSelectedScope(activeMyBrands[0].brand.id);
    }
  }, [brandParam, hasSelfWorkedAccess, activeMyBrands]);

  const handleScopeChange = (scope: string) => {
    setSelectedScope(scope);
    if (scope === 'self-worked') {
      const next = new URLSearchParams(searchParams);
      next.delete('brand');
      setSearchParams(next);
    } else {
      const next = new URLSearchParams(searchParams);
      next.set('brand', scope);
      setSearchParams(next);
    }
  };

  const selectedBrand = activeMyBrands.find((b) => b.brand.id === selectedScope)?.brand;
  const currentBrandId = selectedScope === 'self-worked' ? null : selectedScope;
  const currentBrandName = selectedScope === 'self-worked' ? null : selectedBrand?.name || null;

  const hasAnyAccess = hasSelfWorkedAccess || activeMyBrands.length > 0;

  if (isBrandsLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[70vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ЗАГРУЗКА ДАННЫХ ОЧЕРЕДИ... )
        </div>
      </div>
    );
  }

  if (!hasAnyAccess) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[70vh] flex flex-col items-center justify-center px-4 py-24 text-center space-y-4">
        <span className="text-[11px] font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( 403 / НЕДОСТАТОЧНО ПРАВ )
        </span>
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          ДОСТУП К ОЧЕРЕДИ ОГРАНИЧЕН
        </h1>
        <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md leading-relaxed">
          Просмотр очереди отправки и аналитики продаж доступен только авторам изделий (creator:products) или подтверждённым участникам команд брендов.
        </p>
        <div className="pt-2">
          <Link
            to="/catalog"
            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
          >
            В КАТАЛОГ ↗
          </Link>
        </div>
      </div>
    );
  }

  const hasMultipleScopes =
    (hasSelfWorkedAccess ? 1 : 0) + activeMyBrands.length > 1;

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
            <Link to="/profile" className="hover:text-[#3F2021]">
              ЛИЧНЫЙ КАБИНЕТ
            </Link>
            <span>/</span>
            <span className="text-[#3F2021] font-medium">ОЧЕРЕДЬ И СТАТИСТИКА</span>
          </div>
        </div>

        {/* Page Hero Header */}
        <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 rounded-none flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-1.5">
            <span className="text-[10px] sm:text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
              ( УПРАВЛЕНИЕ ЗАКАЗАМИ И ВЫРУЧКОЙ )
            </span>
            <h1 className="font-serif text-3xl sm:text-4xl uppercase tracking-wider text-[#3F2021] leading-none">
              ОЧЕРЕДЬ И СТАТИСТИКА
            </h1>
            <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 pt-1">
              Отслеживание сборки и отправки заказов покупателей, назначение трек-номеров и аналитика продаж
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/profile"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none whitespace-nowrap"
            >
              МОЙ ПРОФИЛЬ ↗
            </Link>
          </div>
        </div>

        {/* Scope Selector (if user has access to multiple scopes) */}
        {hasMultipleScopes && (
          <div className="space-y-2">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60 block">
              ВЫБЕРИТЕ ПРОСТРАНСТВО:
            </span>
            <div className="flex flex-wrap items-center gap-2">
              {hasSelfWorkedAccess && (
                <button
                  type="button"
                  onClick={() => handleScopeChange('self-worked')}
                  className={`px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none border ${
                    selectedScope === 'self-worked'
                      ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021]'
                      : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
                  }`}
                >
                  ( САМОСТОЯТЕЛЬНЫЙ АВТОР · SELF-WORKED )
                </button>
              )}

              {activeMyBrands.map((b) => (
                <button
                  key={b.brand.id}
                  type="button"
                  onClick={() => handleScopeChange(b.brand.id)}
                  className={`px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none border ${
                    selectedScope === b.brand.id
                      ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021]'
                      : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
                  }`}
                >
                  ( БРЕНД: {b.brand.name} )
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Core Queue & Analytics View */}
        <QueueAndAnalyticsView
          brandId={currentBrandId}
          brandName={currentBrandName}
        />
      </div>
    </div>
  );
}

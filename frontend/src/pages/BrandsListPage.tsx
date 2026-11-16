import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { brandsApi } from '../api/brands';
import { useAuthStore } from '../store/auth';
import { formatImageUrl } from '../utils/format';

export function BrandsListPage() {
  const { isAuthenticated, authUser: user } = useAuthStore();
  const [search, setSearch] = useState('');

  const permissions = user?.global_permissions || [];
  const canCreateBrand =
    permissions.includes('*') ||
    permissions.includes('creator:brand') ||
    permissions.some((p) => p.startsWith('creator:') || p === 'creator') ||
    permissions.includes('catalog:manage');

  const { data: brandsData, isLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.list({ limit: 100 }),
  });

  const brands = brandsData?.data || [];

  const filteredBrands = useMemo(() => {
    if (!search.trim()) return brands;
    const q = search.toLowerCase().trim();
    return brands.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.slug.toLowerCase().includes(q)
    );
  }, [brands, search]);

  return (
    <div className="w-full bg-[#F2E9DB] min-h-[85vh] py-10 md:py-16 px-4 md:px-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header Bar */}
        <div className="border-b border-[#3F2021]/20 pb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
              ( РЕЕСТР БРЕНДОВ )
            </span>
            <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021] mt-1">
              БРЕНДЫ И АВТОРЫ
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {isAuthenticated && (
              <Link
                to="/brands/manage"
                className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] border border-[#3F2021] px-4 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
              >
                {canCreateBrand ? '+ КАБИНЕТ БРЕНДОВ' : 'МОИ БРЕНДЫ ↗'}
              </Link>
            )}
            <Link
              to="/catalog"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2.5 text-xs font-sans uppercase tracking-widest transition-colors rounded-none"
            >
              КАТАЛОГ ↗
            </Link>
          </div>
        </div>

        {/* Search Bar */}
        <div className="bg-[#FFFFFF] border border-[#3F2021] p-4 flex items-center justify-between gap-4 rounded-none">
          <div className="flex-1 flex items-center gap-2">
            <span className="text-xs font-sans font-semibold text-[#3F2021]/60 uppercase">
              ПОИСК:
            </span>
            <input
              type="text"
              placeholder="ПО НАЗВАНИЮ ИЛИ SLUG..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-transparent text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none"
            />
          </div>
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="text-xs text-[#3F2021]/60 hover:text-[#3F2021] px-2"
              title="Очистить"
            >
              ×
            </button>
          )}
          <span className="text-[11px] font-mono text-[#3F2021]/60 shrink-0">
            НАЙДЕНО: {filteredBrands.length}
          </span>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="w-full bg-[#FFFFFF] border border-[#3F2021] p-16 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 rounded-none">
            ( ЗАГРУЗКА БРЕНДОВ... )
          </div>
        ) : filteredBrands.length === 0 ? (
          <div className="bg-[#FFFFFF] border border-[#3F2021] p-12 text-center space-y-4 rounded-none">
            <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
              ( НИЧЕГО НЕ НАЙДЕНО )
            </div>
            <h3 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
              ПО ЗАПРОСУ «{search}» БРЕНДОВ НЕ НАЙДЕНО
            </h3>
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="bg-[#3F2021] text-[#F2E9DB] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold rounded-none"
              >
                СБРОСИТЬ ПОИСК
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredBrands.map((b) => (
              <Link
                key={b.id}
                to={`/brands/${b.slug}`}
                className="group bg-[#FFFFFF] border border-[#3F2021] p-6 flex flex-col justify-between space-y-5 rounded-none hover:border-[#3F2021] hover:bg-[#3F2021]/[0.02] transition-all"
              >
                <div className="flex items-start gap-4">
                  {b.logo_url ? (
                    <img
                      src={formatImageUrl(b.logo_url, b.name)}
                      alt={b.name}
                      className="w-16 h-16 object-cover border border-[#3F2021] rounded-none shrink-0"
                    />
                  ) : (
                    <div className="w-16 h-16 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-center font-serif text-xl text-[#3F2021] font-bold rounded-none select-none shrink-0">
                      {b.name.slice(0, 2).toUpperCase()}
                    </div>
                  )}

                  <div className="min-w-0 flex-1">
                    <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021] group-hover:underline underline-offset-4 truncate">
                      {b.name}
                    </h2>
                    <div className="text-[11px] font-mono text-[#3F2021]/60 mt-0.5 truncate">
                      /brands/{b.slug}
                    </div>

                    {b.his_url && (
                      <div className="mt-2 text-[10px] font-sans text-[#3F2021]/80 truncate">
                        {b.his_url.replace(/^https?:\/\//, '')} ↗
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-[#3F2021]/15 flex items-center justify-between text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                  <span>СМОТРЕТЬ КОЛЛЕКЦИЮ</span>
                  <span>↗</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

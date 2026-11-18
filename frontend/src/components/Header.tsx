import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { categoriesApi, cartApi, searchApi, authApi, notificationsApi, moderationApi, brandsApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { useCurrencyStore, type CurrencyCode } from '../store/currency';
import { useDebounce } from '../hooks/useDebounce';
import { NotificationsDrawer } from './NotificationsDrawer';

const CURRENCIES: { code: CurrencyCode; label: string }[] = [
  { code: 'RUB', label: 'RUB ₽' },
  { code: 'USD', label: 'USD $' },
  { code: 'EUR', label: 'EUR €' },
  { code: 'CNY', label: 'CNY ¥' },
];

export function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginUrl =
    location.pathname !== '/login' && location.pathname !== '/register' && currentPath !== '/'
      ? `/login?redirect=${encodeURIComponent(currentPath)}`
      : '/login';

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isOverHero, setIsOverHero] = useState(false);
  const debouncedQuery = useDebounce(searchQuery.trim(), 300);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (location.pathname !== '/') {
      setIsOverHero(false);
      return;
    }

    const checkHeroOverlap = () => {
      const heroEl = document.getElementById('hero-section');
      if (!heroEl) {
        setIsOverHero(false);
        return;
      }
      const heroRect = heroEl.getBoundingClientRect();
      const headerHeight = headerRef.current?.offsetHeight || 80;
      setIsOverHero(heroRect.bottom > headerHeight);
    };

    checkHeroOverlap();
    window.addEventListener('scroll', checkHeroOverlap, { passive: true });
    window.addEventListener('resize', checkHeroOverlap);

    return () => {
      window.removeEventListener('scroll', checkHeroOverlap);
      window.removeEventListener('resize', checkHeroOverlap);
    };
  }, [location.pathname]);

  // Categories query
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
    staleTime: 5 * 60 * 1000,
  });

  const { currency: activeCurrency, setCurrency: setActiveCurrency } = useCurrencyStore();

  const permissions = user?.global_permissions || [];
  const isAdmin =
    permissions.includes('*') ||
    permissions.includes('admin:access');
  const isCreator =
    permissions.includes('*') ||
    permissions.some((p) => p.startsWith('creator:') || p === 'creator');
  const canModerate =
    permissions.includes('*') ||
    permissions.includes('mod:approve_manager');
  const canManageCatalog =
    permissions.includes('*') ||
    permissions.includes('catalog:manage');

  // Brands query for current user
  const { data: myBrandsData } = useQuery({
    queryKey: ['myBrands'],
    queryFn: () => brandsApi.my(),
    enabled: isAuthenticated,
  });

  const myBrands = myBrandsData?.data || [];
  const canCreateBrand =
    permissions.includes('*') ||
    permissions.includes('creator:brand') ||
    isCreator ||
    canManageCatalog;
  const hasBrandAccess =
    canCreateBrand ||
    canModerate ||
    myBrands.length > 0;
  const isBrandActiveManager = myBrands.some(
    (b) => !b.brand.is_deleted && (b.role === 'representative' || b.role === 'moderator')
  );
  const canCreateProduct = isCreator || isBrandActiveManager;

  const rootCategories = (categoriesData?.data || []).filter(
    (c) => c.parent_id === null || c.parent_id === undefined
  );

  // Cart query
  const { data: cartData } = useQuery({
    queryKey: ['cart'],
    queryFn: () => cartApi.get(),
    enabled: isAuthenticated,
    staleTime: 30 * 1000,
  });

  const cartItemsCount = (cartData?.data?.items || []).reduce(
    (acc, item) => acc + item.quantity,
    0
  );

  // Unread notifications query
  const { data: unreadNotificationsData } = useQuery({
    queryKey: ['unreadNotificationsCount'],
    queryFn: () => notificationsApi.getUnreadCount(),
    enabled: isAuthenticated,
    refetchInterval: 30000,
  });

  const unreadCount = unreadNotificationsData?.data?.count ?? 0;

  // Pending moderation count query (for moderators)
  const { data: moderationPendingData } = useQuery({
    queryKey: ['moderationPendingCount'],
    queryFn: () => moderationApi.getPendingCount(),
    enabled: isAuthenticated && canModerate,
    refetchInterval: 30000,
  });

  const pendingModerationCount = moderationPendingData?.data?.pending_count ?? 0;

  // Search query (3-in-1: brands, products, variants)
  const { data: searchResults, isFetching: isSearching } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.search(debouncedQuery, 8),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30 * 1000,
  });

  // Handle clicking outside of search dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(event.target as Node)
      ) {
        setIsSearchOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignored
    } finally {
      logout();
      navigate('/login');
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (debouncedQuery) {
      setIsSearchOpen(false);
      navigate(`/catalog?search=${encodeURIComponent(debouncedQuery)}`);
    }
  };

  const selectBrand = (brandName: string) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    navigate(`/catalog?search=${encodeURIComponent(brandName)}`);
  };

  const selectProduct = (slug: string) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    navigate(`/products/${slug}`);
  };

  const selectVariant = (productId: string, sku: string) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    navigate(`/products/${productId}?sku=${encodeURIComponent(sku)}`);
  };

  const brands = searchResults?.data?.brands || [];
  const products = searchResults?.data?.products || [];
  const variants = searchResults?.data?.variants || [];
  const hasSearchResults = brands.length > 0 || products.length > 0 || variants.length > 0;

  return (
    <header
      ref={headerRef}
      className={`sticky top-0 z-50 transition-colors duration-200 ${
        isOverHero
          ? 'bg-[#3F2021] border-b border-[#F2E9DB]/20 text-[#F2E9DB]'
          : 'bg-[#F2E9DB] border-b border-sf-dark/15 text-sf-dark'
      }`}
    >
      {/* Top Banner / Philosophy slogan & Currency Switcher */}
      <div
        className={`transition-colors duration-200 text-[10px] md:text-[11px] font-sans tracking-widest uppercase py-1.5 px-4 md:px-8 border-b flex flex-wrap items-center justify-between gap-3 ${
          isOverHero
            ? 'bg-[#2B1516] text-[#F2E9DB]/90 border-[#F2E9DB]/20'
            : 'bg-sf-dark text-sf-cream border-sf-cream/20'
        }`}
      >
        <span className="hidden sm:inline text-left text-[10px] tracking-widest opacity-75">
          ПОДДЕРЖКА: support@shopper.flox
        </span>
        <span className="mx-auto sm:mx-0 font-medium">
          SHOPPERFLOX — ЭКОСИСТЕМА АВТОРСКИХ ИЗДЕЛИЙ
        </span>
        <div className="flex items-center gap-1.5 ml-auto sm:ml-0">
          <span className="hidden md:inline text-[10px] tracking-wider opacity-60">
            ВАЛЮТА:
          </span>
          <div className="inline-flex border border-[#F2E9DB]/30 divide-x divide-[#F2E9DB]/30">
            {CURRENCIES.map((c) => {
              const isActive = activeCurrency === c.code;
              return (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => setActiveCurrency(c.code)}
                  className={`px-2 py-0.5 text-[10px] font-mono tracking-wider transition-colors cursor-pointer rounded-none ${
                    isActive
                      ? 'bg-[#F2E9DB] text-[#3F2021] font-bold'
                      : 'bg-transparent text-[#F2E9DB]/80 hover:text-[#F2E9DB] hover:bg-[#F2E9DB]/10'
                  }`}
                  title={`Показывать цены в ${c.code}`}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="w-full max-w-none px-4 md:px-8">
        {/* Main navigation row */}
        <div className="flex items-center justify-between h-16 md:h-20 gap-4">
          {/* Logo */}
          <Link
            to="/"
            className={`font-serif text-2xl md:text-3xl font-normal tracking-wider hover:opacity-80 transition-colors duration-200 whitespace-nowrap ${
              isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
            }`}
          >
            SHOPPERFLOX
          </Link>

          {/* Search bar 3-in-1 */}
          <div ref={searchContainerRef} className="relative flex-1 max-w-md mx-2 md:mx-6">
            <form onSubmit={handleSearchSubmit} className="relative flex items-center">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsSearchOpen(true);
                }}
                onFocus={() => setIsSearchOpen(true)}
                placeholder="ПОИСК: БРЕНД, МОДЕЛЬ, АРТИКУЛ..."
                className={`w-full px-3 py-2 text-[12px] md:text-[13px] tracking-wider font-sans outline-none transition-colors duration-200 ${
                  isOverHero
                    ? 'bg-[#3F2021] border border-[#F2E9DB]/30 text-[#F2E9DB] placeholder:text-[#F2E9DB]/50 focus:border-[#F2E9DB]'
                    : 'bg-[#F2E9DB] border border-sf-dark/30 focus:border-sf-dark placeholder:text-sf-muted/70 text-sf-black'
                }`}
              />
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setIsSearchOpen(false);
                  }}
                  className={`absolute right-8 px-1 text-sm font-sans transition-colors duration-200 ${
                    isOverHero ? 'text-[#F2E9DB]/60 hover:text-[#F2E9DB]' : 'text-sf-muted hover:text-sf-black'
                  }`}
                  title="Очистить"
                >
                  ×
                </button>
              ) : null}
              <button
                type="submit"
                className={`absolute right-2 text-xs font-semibold px-1 transition-colors duration-200 ${
                  isOverHero ? 'text-[#F2E9DB] hover:opacity-70' : 'text-sf-dark hover:opacity-70'
                }`}
                title="Искать"
              >
                ↗
              </button>
            </form>

            {/* Dropdown 3-in-1: Brands, Products, Variants */}
            {isSearchOpen && debouncedQuery.length >= 2 && (
              <div className="absolute left-0 right-0 top-full mt-1 bg-[#F2E9DB] border border-sf-dark shadow-none z-50 max-h-[460px] overflow-y-auto">
                {isSearching ? (
                  <div className="p-4 text-xs font-sans uppercase tracking-wider text-sf-muted">
                    ( ПОИСК В КАТАЛОГЕ... )
                  </div>
                ) : !hasSearchResults ? (
                  <div className="p-4 text-xs font-sans uppercase tracking-wider text-sf-muted">
                    ( ПО ЗАПРОСУ «{debouncedQuery}» НИЧЕГО НЕ НАЙДЕНО )
                  </div>
                ) : (
                  <div className="divide-y divide-sf-dark/15 text-xs font-sans">
                    {/* Brands Section */}
                    {brands.length > 0 && (
                      <div className="p-3">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-sf-muted mb-2">
                          ( БРЕНДЫ )
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {brands.map((brand) => (
                            <button
                              key={brand.name}
                              type="button"
                              onClick={() => selectBrand(brand.name)}
                              className="px-2.5 py-1 border border-sf-dark/25 hover:border-sf-dark hover:bg-sf-dark hover:text-sf-cream text-[11px] uppercase tracking-wider transition-colors"
                            >
                              {brand.name} ({brand.products_count})
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Products Section */}
                    {products.length > 0 && (
                      <div className="p-3">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-sf-muted mb-2">
                          ( МОДЕЛИ И ТОВАРЫ )
                        </div>
                        <div className="space-y-1.5">
                          {products.map((prod) => (
                            <button
                              key={prod.id}
                              type="button"
                              onClick={() => selectProduct(prod.slug)}
                              className="w-full text-left flex items-baseline justify-between p-1.5 hover:bg-sf-dark/5 transition-colors group"
                            >
                              <div className="truncate pr-2">
                                <span className="font-serif text-sm text-sf-black group-hover:text-sf-dark">
                                  {prod.title}
                                </span>
                                {prod.brand && (
                                  <span className="text-[10px] text-sf-muted ml-2 uppercase">
                                    [{prod.brand}]
                                  </span>
                                )}
                              </div>
                              <span className="font-sans font-semibold text-sf-dark whitespace-nowrap">
                                {Number(prod.base_price).toLocaleString('ru-RU')} ₽ ↗
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Variants Section */}
                    {variants.length > 0 && (
                      <div className="p-3">
                        <div className="text-[11px] font-semibold uppercase tracking-wider text-sf-muted mb-2">
                          ( ВАРИАЦИИ / SKU )
                        </div>
                        <div className="space-y-1.5">
                          {variants.map((v) => (
                            <button
                              key={v.id}
                              type="button"
                              onClick={() => selectVariant(v.product_id, v.sku)}
                              className="w-full text-left flex items-baseline justify-between p-1.5 hover:bg-sf-dark/5 transition-colors"
                            >
                              <div>
                                <span className="font-mono text-[11px] font-semibold text-sf-dark">
                                  {v.sku}
                                </span>
                                <span className="text-sf-muted text-[11px] ml-2">
                                  {v.color_name} {v.size ? `/ РАЗМЕР: ${v.size}` : ''}
                                </span>
                              </div>
                              <span className="text-[10px] text-sf-muted">
                                {v.stock_quantity !== undefined && `В НАЛИЧИИ: ${v.stock_quantity}`} ↗
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* User Links / Actions */}
          <nav className="flex items-center gap-4 md:gap-6 text-[12px] md:text-[13px] font-sans uppercase tracking-wider">
            <Link
              to="/catalog"
              className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap font-medium ${
                isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
              }`}
            >
              КАТАЛОГ
            </Link>

            <Link
              to="/favorites"
              className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap ${
                isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
              }`}
            >
              FAVORITES
            </Link>

            <Link
              to="/orders"
              className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap hidden sm:inline-block ${
                isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
              }`}
            >
              ORDERS
            </Link>

            <Link
              to="/cart"
              className={`hover:opacity-70 transition-colors duration-200 font-semibold whitespace-nowrap ${
                isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
              }`}
            >
              CART ({cartItemsCount})
            </Link>

            {isAuthenticated && (
              <button
                type="button"
                onClick={() => setIsNotificationsOpen(true)}
                className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap font-medium uppercase cursor-pointer ${
                  isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
                }`}
              >
                УВЕДОМЛЕНИЯ ({unreadCount})
              </button>
            )}

            {canModerate && (
              <Link
                to="/moderation/requests"
                className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap font-medium uppercase ${
                  isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
                }`}
              >
                ЗАЯВКИ ({pendingModerationCount})
              </Link>
            )}

            {hasBrandAccess && (
              <Link
                to="/brands/manage"
                className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap font-medium uppercase ${
                  isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
                }`}
              >
                БРЕНДЫ
              </Link>
            )}

            {isAdmin && (
              <Link
                to="/admin"
                className={`hover:opacity-70 transition-colors duration-200 whitespace-nowrap font-medium uppercase ${
                  isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
                }`}
              >
                АДМИН
              </Link>
            )}

            {isAuthenticated ? (
              <div className="flex items-center gap-2 sm:gap-3">
                {canCreateProduct && (
                  <Link
                    to="/creator/products/new"
                    className={`px-2.5 sm:px-3 py-1 text-[11px] sm:text-xs font-sans uppercase tracking-wider font-semibold transition-colors duration-200 whitespace-nowrap ${
                      isOverHero
                        ? 'bg-[#F2E9DB] text-[#3F2021] hover:bg-[#F2E9DB]/90 border border-[#F2E9DB]'
                        : 'bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] border border-[#3F2021]'
                    }`}
                  >
                    + СОЗДАТЬ ТОВАР
                  </Link>
                )}

                <Link
                  to="/profile"
                  className={`font-mono text-xs font-bold transition-colors duration-200 hover:opacity-75 whitespace-nowrap ${
                    isOverHero ? 'text-[#F2E9DB]' : 'text-sf-dark'
                  }`}
                  title="Личный кабинет"
                >
                  @{user?.login || 'профиль'}
                </Link>

                <button
                  type="button"
                  onClick={handleLogout}
                  className={`px-2.5 py-1 transition-colors duration-200 text-[11px] whitespace-nowrap ${
                    isOverHero
                      ? 'border border-[#F2E9DB] text-[#F2E9DB] hover:bg-[#F2E9DB] hover:text-[#3F2021]'
                      : 'border border-sf-dark text-sf-dark hover:bg-sf-dark hover:text-sf-cream'
                  }`}
                >
                  ВЫХОД
                </button>
              </div>
            ) : (
              <Link
                to={loginUrl}
                state={{ from: location }}
                className={`px-3 py-1 transition-colors duration-200 text-[11px] whitespace-nowrap font-medium ${
                  isOverHero
                    ? 'border border-[#F2E9DB] text-[#F2E9DB] hover:bg-[#F2E9DB] hover:text-[#3F2021]'
                    : 'border border-sf-dark text-sf-dark hover:bg-sf-dark hover:text-sf-cream'
                }`}
              >
                ВОЙТИ
              </Link>
            )}
          </nav>
        </div>

        {/* Categories Bar */}
        {rootCategories.length > 0 && (
          <div
            className={`flex items-center gap-6 py-2.5 overflow-x-auto scrollbar-none text-[12px] font-serif uppercase tracking-wider transition-colors duration-200 ${
              isOverHero
                ? 'border-t border-[#F2E9DB]/20 text-[#F2E9DB]'
                : 'border-t border-sf-dark/10 text-sf-dark'
            }`}
          >
            <Link
              to="/catalog"
              className="hover:opacity-60 transition-opacity whitespace-nowrap"
            >
              ВСЕ ТОВАРЫ
            </Link>
            {rootCategories.map((cat) => (
              <Link
                key={cat.id}
                to={`/catalog?category=${cat.slug || cat.id}`}
                className="hover:opacity-60 transition-opacity whitespace-nowrap"
              >
                {cat.name}
              </Link>
            ))}
          </div>
        )}
      </div>

      <NotificationsDrawer
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
      />
    </header>
  );
}

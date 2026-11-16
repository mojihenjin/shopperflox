import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { categoriesApi, cartApi, searchApi, authApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { useDebounce } from '../hooks/useDebounce';

export function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const [, setSearchParams] = useSearchParams();
  const { isAuthenticated, user, logout, setUser } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginUrl =
    location.pathname !== '/login' && location.pathname !== '/register' && currentPath !== '/'
      ? `/login?redirect=${encodeURIComponent(currentPath)}`
      : '/login';

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const debouncedQuery = useDebounce(searchQuery.trim(), 300);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Fetch current user if token exists but user info isn't loaded yet
  useEffect(() => {
    if (isAuthenticated && !user) {
      authApi.getMe()
        .then((res) => {
          if (res.data) setUser(res.data);
        })
        .catch(() => {
          // Token might be invalid or handled by refresh
        });
    }
  }, [isAuthenticated, user, setUser]);

  // Categories query
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
    staleTime: 5 * 60 * 1000,
  });

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
      navigate(`/?search=${encodeURIComponent(debouncedQuery)}`);
    }
  };

  const selectBrand = (brandName: string) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    navigate(`/?search=${encodeURIComponent(brandName)}`);
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
    <header className="sticky top-0 z-50 bg-[#F2E9DB] border-b border-sf-dark/15 text-sf-dark">
      {/* Top Banner / Philosophy slogan */}
      <div className="bg-sf-dark text-sf-cream text-[11px] font-sans tracking-widest uppercase py-1.5 px-4 text-center border-b border-sf-cream/20">
        <span>SHOPPERFLOX — СТИЛЬ В ДЕТАЛЯХ &nbsp;|&nbsp; БЕСПЛАТНАЯ ДОСТАВКА ОТ 10 000 ₽</span>
      </div>

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6">
        {/* Main navigation row */}
        <div className="flex items-center justify-between h-16 md:h-20 gap-4">
          {/* Logo */}
          <Link
            to="/"
            className="font-serif text-2xl md:text-3xl font-normal tracking-wider text-sf-dark hover:opacity-80 transition-opacity whitespace-nowrap"
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
                className="w-full bg-[#F2E9DB] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-[12px] md:text-[13px] tracking-wider uppercase font-sans placeholder:text-sf-muted/70 text-sf-black outline-none transition-colors"
              />
              {searchQuery ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setIsSearchOpen(false);
                  }}
                  className="absolute right-8 text-sf-muted hover:text-sf-black px-1 text-sm font-sans"
                  title="Очистить"
                >
                  ×
                </button>
              ) : null}
              <button
                type="submit"
                className="absolute right-2 text-sf-dark hover:opacity-70 text-xs font-semibold px-1"
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
              to="/favorites"
              className="hover:opacity-70 transition-opacity whitespace-nowrap"
            >
              FAVORITES
            </Link>

            <Link
              to="/orders"
              className="hover:opacity-70 transition-opacity whitespace-nowrap hidden sm:inline-block"
            >
              ORDERS
            </Link>

            <Link
              to="/cart"
              className="hover:opacity-70 transition-opacity font-semibold whitespace-nowrap"
            >
              CART ({cartItemsCount})
            </Link>

            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <span className="text-sf-muted hidden lg:inline">
                  {user?.login ? `(${user.login})` : ''}
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="border border-sf-dark px-2.5 py-1 hover:bg-sf-dark hover:text-sf-cream transition-colors text-[11px]"
                >
                  ВЫХОД
                </button>
              </div>
            ) : (
              <Link
                to={loginUrl}
                state={{ from: location }}
                className="border border-sf-dark px-2.5 py-1 hover:bg-sf-dark hover:text-sf-cream transition-colors text-[11px] whitespace-nowrap"
              >
                ACCOUNT / LOGIN
              </Link>
            )}
          </nav>
        </div>

        {/* Categories Bar */}
        {rootCategories.length > 0 && (
          <div className="flex items-center gap-6 py-2.5 overflow-x-auto border-t border-sf-dark/10 scrollbar-none text-[12px] font-serif uppercase tracking-wider text-sf-dark">
            <button
              type="button"
              onClick={() => {
                setSearchParams({});
                navigate('/');
              }}
              className="hover:opacity-60 transition-opacity whitespace-nowrap"
            >
              ВСЕ МОДЕЛИ
            </button>
            {rootCategories.map((cat) => (
              <Link
                key={cat.id}
                to={`/?category_id=${cat.id}`}
                className="hover:opacity-60 transition-opacity whitespace-nowrap"
              >
                {cat.name}
              </Link>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, categoriesApi, favoritesApi } from '../api/endpoints';
import { ProductCard, type GridColumns } from './ProductCard';
import { useAuthStore } from '../store/auth';

const PAGE_SIZE = 12;
const STORAGE_COLUMNS_KEY = 'sf_catalog_columns';

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'ONE SIZE'];

const COLOR_PALETTE = [
  { name: 'ЧЁРНЫЙ', hex: '#000000', value: 'черный' },
  { name: 'БЕЛЫЙ', hex: '#FFFFFF', value: 'белый' },
  { name: 'СЕРЫЙ', hex: '#808080', value: 'серый' },
  { name: 'БЕЖЕВЫЙ', hex: '#D2B48C', value: 'бежевый' },
  { name: 'БОРДОВЫЙ', hex: '#3F2021', value: 'бордовый' },
  { name: 'КРАСНЫЙ', hex: '#D32F2F', value: 'красный' },
  { name: 'СИНИЙ', hex: '#1976D2', value: 'синий' },
  { name: 'ЗЕЛЁНЫЙ', hex: '#388E3C', value: 'зеленый' },
  { name: 'КОРИЧНЕВЫЙ', hex: '#5D4037', value: 'коричневый' },
  { name: 'РОЗОВЫЙ', hex: '#E91E63', value: 'розовый' },
];

export interface CatalogViewProps {
  eyebrow?: string;
  defaultTitle?: string;
  className?: string;
}

export function CatalogView({
  eyebrow = '( ПОЛНЫЙ КАТАЛОГ )',
  defaultTitle = 'ВСЕ ТОВАРЫ',
  className = '',
}: CatalogViewProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  const categoryParam =
    searchParams.get('category') || searchParams.get('category_id') || '';
  const searchParam = searchParams.get('search') || '';
  const minPriceParam = searchParams.get('min_price') || '';
  const maxPriceParam = searchParams.get('max_price') || '';
  const sizeParam = searchParams.get('size') || '';
  const colorParam = searchParams.get('color') || '';
  const isLimitedParam = searchParams.get('is_limited') === 'true';
  const pageParam = parseInt(searchParams.get('page') || '1', 10);
  const offset = (Math.max(1, pageParam) - 1) * PAGE_SIZE;

  // Local filter states for input forms
  const [minPriceInput, setMinPriceInput] = useState(minPriceParam);
  const [maxPriceInput, setMaxPriceInput] = useState(maxPriceParam);

  // Column switcher with localStorage persistence
  const [columns, setColumns] = useState<GridColumns>(() => {
    const saved = localStorage.getItem(STORAGE_COLUMNS_KEY);
    if (saved && ['2', '4', '6', '8'].includes(saved)) {
      return Number(saved) as GridColumns;
    }
    return 4;
  });

  const handleColumnsChange = (cols: GridColumns) => {
    setColumns(cols);
    localStorage.setItem(STORAGE_COLUMNS_KEY, String(cols));
  };

  useEffect(() => {
    setMinPriceInput(minPriceParam);
    setMaxPriceInput(maxPriceParam);
  }, [minPriceParam, maxPriceParam]);

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
  });

  const categories = useMemo(() => categoriesData?.data || [], [categoriesData]);

  // Find selected category
  const selectedCategory = useMemo(() => {
    if (!categoryParam) return null;
    return (
      categories.find(
        (c) => c.slug === categoryParam || c.id === categoryParam
      ) || null
    );
  }, [categories, categoryParam]);

  // Resolve valid UUID for category_id parameter of GET /api/v1/products
  const activeCategoryId = useMemo(() => {
    if (selectedCategory) return selectedCategory.id;
    if (
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        categoryParam
      )
    ) {
      return categoryParam;
    }
    return undefined;
  }, [selectedCategory, categoryParam]);

  const catalogTitle = selectedCategory
    ? selectedCategory.name.toUpperCase()
    : defaultTitle;

  // Fetch products
  const { data: productsData, isLoading: isProductsLoading } = useQuery({
    queryKey: [
      'products',
      activeCategoryId,
      searchParam,
      minPriceParam,
      maxPriceParam,
      sizeParam,
      colorParam,
      isLimitedParam,
      offset,
    ],
    queryFn: () =>
      productsApi.list({
        category_id: activeCategoryId || undefined,
        search: searchParam || undefined,
        min_price: minPriceParam || undefined,
        max_price: maxPriceParam || undefined,
        size: sizeParam || undefined,
        color: colorParam || undefined,
        is_limited: isLimitedParam ? true : undefined,
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
    const set = new Set<string>();
    (favoritesData?.data || []).forEach((prod) => set.add(prod.id));
    return set;
  }, [favoritesData]);

  const toggleFavoriteMutation = useMutation({
    mutationFn: async (productId: string) => {
      if (!isAuthenticated) return;
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

  const handleCategorySelect = (slugOrId: string) => {
    const next = new URLSearchParams(searchParams);
    if (slugOrId) {
      next.set('category', slugOrId);
      next.delete('category_id');
    } else {
      next.delete('category');
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

  const handleSizeSelect = (sz: string) => {
    const next = new URLSearchParams(searchParams);
    if (!sz || sz === sizeParam) {
      next.delete('size');
    } else {
      next.set('size', sz);
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const handleColorSelect = (val: string) => {
    const next = new URLSearchParams(searchParams);
    if (!val || val.toLowerCase() === colorParam.toLowerCase()) {
      next.delete('color');
    } else {
      next.set('color', val);
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const handleLimitedToggle = () => {
    const next = new URLSearchParams(searchParams);
    if (isLimitedParam) {
      next.delete('is_limited');
    } else {
      next.set('is_limited', 'true');
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const handleResetFilters = () => {
    setMinPriceInput('');
    setMaxPriceInput('');
    setSearchParams({});
  };

  const totalProducts =
    productsData?.metadata?.total ?? (productsData?.data?.length || 0);
  const totalPages = Math.ceil(totalProducts / PAGE_SIZE) || 1;
  const products = productsData?.data || [];

  const handlePageChange = (newPage: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(newPage));
    setSearchParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <section className={`w-full bg-[#F2E9DB] py-10 md:py-16 ${className}`}>
      <div className="w-full max-w-none px-4 md:px-8 space-y-6">
        {/* Catalog Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-sf-dark/20">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
              {eyebrow}
            </span>
            <h2 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-dark mt-1">
              {catalogTitle}
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-4 sm:gap-6">
            {/* Grid density switcher */}
            <div className="flex items-center border border-sf-dark/25 p-0.5 bg-[#FFFFFF]">
              <span className="text-[10px] font-sans uppercase tracking-wider text-sf-muted px-2 select-none">
                СЕТКА:
              </span>
              {([2, 4, 6, 8] as GridColumns[]).map((cols) => (
                <button
                  key={cols}
                  type="button"
                  onClick={() => handleColumnsChange(cols)}
                  className={`px-2.5 py-1 text-xs font-sans font-semibold transition-colors ${
                    columns === cols
                      ? 'bg-[#3F2021] text-[#F2E9DB]'
                      : 'text-[#3F2021]/60 hover:text-[#3F2021]'
                  }`}
                  title={`Сетка: ${cols} колонок`}
                >
                  {cols}
                </button>
              ))}
            </div>

            <div className="text-xs font-sans uppercase tracking-wider text-sf-muted">
              ( ПОКАЗАНО: {products.length} ИЗ {totalProducts} МОДЕЛЕЙ )
            </div>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="space-y-4 pb-2">
          {/* Category tabs */}
          {categories.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pb-3 border-b border-sf-dark/15">
              <button
                type="button"
                onClick={() => handleCategorySelect('')}
                className={`px-3.5 py-1.5 text-xs font-sans uppercase tracking-wider border transition-colors ${
                  !categoryParam
                    ? 'bg-sf-dark text-sf-cream border-sf-dark font-semibold'
                    : 'border-sf-dark/30 hover:border-sf-dark text-sf-dark bg-transparent'
                }`}
              >
                ВСЕ
              </button>
              {categories.map((cat) => {
                const isSelected =
                  categoryParam === cat.slug || categoryParam === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => handleCategorySelect(cat.slug || cat.id)}
                    className={`px-3.5 py-1.5 text-xs font-sans uppercase tracking-wider border transition-colors ${
                      isSelected
                        ? 'bg-sf-dark text-sf-cream border-sf-dark font-semibold'
                        : 'border-sf-dark/30 hover:border-sf-dark text-sf-dark bg-transparent'
                    }`}
                  >
                    {cat.name}
                  </button>
                );
              })}
            </div>
          )}

          {/* Price range */}
          <div className="flex flex-wrap items-center gap-4 pt-1">
            <form
              onSubmit={handlePriceFilterApply}
              className="flex flex-wrap items-center gap-2"
            >
              <span className="text-xs font-sans uppercase tracking-wider text-sf-muted mr-1 select-none">
                ЦЕНА, ₽:
              </span>
              <input
                type="number"
                placeholder="ОТ"
                value={minPriceInput}
                onChange={(e) => setMinPriceInput(e.target.value)}
                className="w-24 bg-[#F2E9DB] border border-sf-dark/30 focus:border-sf-dark px-2.5 py-1 text-xs font-sans outline-none"
              />
              <span className="text-sf-muted">—</span>
              <input
                type="number"
                placeholder="ДО"
                value={maxPriceInput}
                onChange={(e) => setMaxPriceInput(e.target.value)}
                className="w-24 bg-[#F2E9DB] border border-sf-dark/30 focus:border-sf-dark px-2.5 py-1 text-xs font-sans outline-none"
              />
              <button
                type="submit"
                className="bg-sf-dark text-sf-cream hover:bg-sf-black px-3 py-1 text-xs font-sans uppercase tracking-wider transition-colors"
              >
                ПРИМЕНИТЬ
              </button>
            </form>
          </div>

          {/* Extended Filters: Size, Color Swatches, Limited */}
          <div className="space-y-3 pt-3 border-t border-sf-dark/15">
            {/* Sizes */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-sans uppercase tracking-wider text-sf-muted mr-1 select-none">
                РАЗМЕР:
              </span>
              <button
                type="button"
                onClick={() => handleSizeSelect('')}
                className={`px-3 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                  !sizeParam
                    ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                    : 'border-[#3F2021]/30 hover:border-[#3F2021] text-[#3F2021] bg-transparent'
                }`}
              >
                ВСЕ
              </button>
              {SIZES.map((s) => {
                const isActive = sizeParam.toUpperCase() === s.toUpperCase();
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleSizeSelect(s)}
                    className={`px-3 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                      isActive
                        ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                        : 'border-[#3F2021]/30 hover:border-[#3F2021] text-[#3F2021] bg-transparent'
                    }`}
                  >
                    {s}
                  </button>
                );
              })}
            </div>

            {/* Colors */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-sans uppercase tracking-wider text-sf-muted mr-1 select-none">
                ЦВЕТ:
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {COLOR_PALETTE.map((c) => {
                  const isActive =
                    colorParam.toLowerCase() === c.value.toLowerCase() ||
                    colorParam.toLowerCase() === c.name.toLowerCase();
                  return (
                    <button
                      key={c.name}
                      type="button"
                      title={c.name}
                      onClick={() => handleColorSelect(c.value)}
                      style={{ backgroundColor: c.hex }}
                      className={`w-6 h-6 rounded-none transition-all flex items-center justify-center relative cursor-pointer ${
                        isActive
                          ? 'border-2 border-[#3F2021] ring-1 ring-[#3F2021] scale-110 shadow-none'
                          : 'border border-[#3F2021]/30 hover:border-[#3F2021]'
                      }`}
                    >
                      {isActive && (
                        <span
                          className={`text-xs font-bold leading-none select-none ${
                            c.hex === '#FFFFFF' || c.hex === '#D2B48C'
                              ? 'text-[#3F2021]'
                              : 'text-[#FFFFFF]'
                          }`}
                        >
                          ✓
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              {colorParam && (
                <button
                  type="button"
                  onClick={() => handleColorSelect('')}
                  className="text-[11px] font-sans uppercase tracking-wider text-sf-muted hover:text-sf-dark underline underline-offset-4 ml-1"
                >
                  СБРОСИТЬ ЦВЕТ ×
                </button>
              )}
            </div>

            {/* Limited switch & Active filters reset */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isLimitedParam}
                  onChange={handleLimitedToggle}
                  className="w-4 h-4 rounded-none accent-[#3F2021] border-[#3F2021] cursor-pointer"
                />
                <span className="text-xs font-sans uppercase tracking-wider font-semibold text-[#3F2021]">
                  ТОЛЬКО LIMITED
                </span>
              </label>

              {(categoryParam || searchParam || minPriceParam || maxPriceParam || sizeParam || colorParam || isLimitedParam) && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="text-xs font-sans uppercase tracking-wider text-sf-dark hover:opacity-60 underline underline-offset-4"
                >
                  ( СБРОСИТЬ ВСЕ ФИЛЬТРЫ × )
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Divider above products grid */}
        <div className="border-t border-sf-dark/15 pt-6">
          {/* Products Grid */}
          {isProductsLoading ? (
            <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-sf-muted">
              ( ЗАГРУЗКА КАТАЛОГА... )
            </div>
          ) : products.length === 0 ? (
            <div className="py-14 text-center space-y-3">
              <div className="font-serif text-xl md:text-2xl uppercase tracking-wider text-sf-dark">
                МОДЕЛИ НЕ НАЙДЕНЫ
              </div>
              <p className="text-xs font-sans uppercase tracking-wider text-sf-muted">
                Попробуйте изменить параметры фильтрации или поисковый запрос
              </p>
              <button
                type="button"
                onClick={handleResetFilters}
                className="mt-2 inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-sf-black transition-colors"
              >
                СБРОСИТЬ ФИЛЬТРЫ ↗
              </button>
            </div>
          ) : (
            <div
              className={
                columns === 2
                  ? 'grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-10'
                  : columns === 6
                  ? 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-x-3 gap-y-6'
                  : columns === 8
                  ? 'grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-x-3 gap-y-6'
                  : 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-5 gap-y-10'
              }
            >
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  columns={columns}
                  isFavorite={favoriteIds.has(product.id)}
                  onToggleFavorite={(id) => toggleFavoriteMutation.mutate(id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pt-8 border-t border-sf-dark/20 flex items-center justify-between">
            <button
              type="button"
              disabled={pageParam <= 1}
              onClick={() => handlePageChange(pageParam - 1)}
              className="border border-sf-dark px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-sf-dark hover:text-sf-cream transition-colors"
            >
              ← ПРЕДЫДУЩАЯ
            </button>

            <div className="text-xs font-sans uppercase tracking-widest text-sf-muted">
              СТРАНИЦА {pageParam} ИЗ {totalPages}
            </div>

            <button
              type="button"
              disabled={pageParam >= totalPages}
              onClick={() => handlePageChange(pageParam + 1)}
              className="border border-sf-dark px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-sf-dark hover:text-sf-cream transition-colors"
            >
              СЛЕДУЮЩАЯ →
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, categoriesApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import type { ProductUpdateRequest } from '../types/api';
import type { ApiError } from '../api/client';

export function CreatorEditProductPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user: authUser } = useAuthStore();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form Fields
  const [title, setTitle] = useState('');
  const [productSlug, setProductSlug] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [brand, setBrand] = useState('');
  const [isSelfWorked, setIsSelfWorked] = useState(false);
  const [basePrice, setBasePrice] = useState('');
  const [priceUsd, setPriceUsd] = useState('');
  const [priceEur, setPriceEur] = useState('');
  const [material, setMaterial] = useState('');
  const [density, setDensity] = useState('');
  const [composition, setComposition] = useState('');
  const [printMethod, setPrintMethod] = useState('');
  const [note, setNote] = useState('');
  const [description, setDescription] = useState('');
  const [isHidden, setIsHidden] = useState<0 | 1 | 2>(0);
  const [isLimited, setIsLimited] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // Fetch product detail
  const {
    data: productData,
    isLoading: isProductLoading,
    error: productError,
  } = useQuery({
    queryKey: ['product', slug],
    queryFn: () => productsApi.getBySlug(slug || ''),
    enabled: Boolean(slug),
  });

  const product = productData?.data?.product;

  // Current user
  const currentUser = authUser;

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
  });

  const categories = categoriesData?.data || [];

  // Initialize form state once product is loaded
  useEffect(() => {
    if (product && !isInitialized) {
      setTitle(product.title || '');
      setProductSlug(product.slug || '');
      setCategoryId(product.category_id || '');
      setBrand(product.brand || '');
      setIsSelfWorked(Boolean(product.is_self_worked));
      setBasePrice(product.base_price ? String(product.base_price) : '');
      setPriceUsd(product.price_usd ? String(product.price_usd) : '');
      setPriceEur(product.price_eur ? String(product.price_eur) : '');
      setMaterial(product.material || '');
      setDensity(product.density || '');
      setComposition(product.composition || '');
      setPrintMethod(product.print_method || '');
      setNote(product.note || '');
      setDescription(product.description || '');
      setIsHidden((product.is_hidden as 0 | 1 | 2) ?? 0);
      setIsLimited(Boolean(product.is_limited));
      setIsInitialized(true);
    }
  }, [product, isInitialized]);

  // Compute permissions
  const permissions = useMemo(() => {
    if (!currentUser || !product) {
      return { canUpdate: false };
    }
    const isCreator = Boolean(product.creator_id && currentUser.id === product.creator_id);
    const globalPermissions = currentUser.global_permissions || [];
    const isSuperAdmin = globalPermissions.includes('*');
    const hasBrandAccess = Boolean(
      product.brand &&
      (globalPermissions.some((p) => p.toLowerCase() === `brand:${product.brand!.toLowerCase()}`) ||
       globalPermissions.includes('brand:*'))
    );
    const canUpdate = isCreator || isSuperAdmin || hasBrandAccess || globalPermissions.includes('mod:update');
    return { canUpdate };
  }, [currentUser, product]);

  // Update Mutation
  const updateMutation = useMutation({
    mutationFn: async (payload: ProductUpdateRequest) => {
      if (!product?.id) throw new Error('Идентификатор товара не найден');
      return productsApi.update(product.id, payload);
    },
    onSuccess: (res) => {
      const updated = res.data;
      setSuccessMessage('ИЗМЕНЕНИЯ УСПЕШНО СОХРАНЕНЫ');
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      queryClient.invalidateQueries({ queryKey: ['product', updated.slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setTimeout(() => {
        navigate(`/products/${updated.slug}`);
      }, 1000);
    },
    onError: (err: ApiError) => {
      setErrorMessage(err.message || 'Ошибка при сохранении изменений');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!title.trim()) {
      setErrorMessage('Укажите название модели');
      return;
    }
    if (!productSlug.trim()) {
      setErrorMessage('Укажите slug для URL товара');
      return;
    }
    if (!basePrice || Number(basePrice) < 0) {
      setErrorMessage('Укажите корректную базовую цену в рублях');
      return;
    }

    const payload: ProductUpdateRequest = {
      title: title.trim(),
      slug: productSlug.trim(),
      category_id: categoryId || undefined,
      brand: brand.trim() || null,
      is_self_worked: isSelfWorked,
      base_price: basePrice.trim(),
      price_usd: priceUsd.trim() ? priceUsd.trim() : null,
      price_eur: priceEur.trim() ? priceEur.trim() : null,
      material: material.trim() || null,
      density: density.trim() || null,
      composition: composition.trim() || null,
      print_method: printMethod.trim() || null,
      note: note.trim() || null,
      description: description.trim() || null,
      is_published: isHidden !== 2,
      is_hidden: isHidden,
      is_limited: isLimited,
    };

    updateMutation.mutate(payload);
  };

  if (isProductLoading) {
    return (
      <div className="w-full min-h-[60vh] bg-[#F2E9DB] flex items-center justify-center py-32 px-4 text-center">
        <div className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
          ( ЗАГРУЗКА РЕДАКТОРА ТОВАРА... )
        </div>
      </div>
    );
  }

  if (productError || !product) {
    return (
      <div className="w-full min-h-[60vh] bg-[#F2E9DB] flex flex-col items-center justify-center py-24 px-4 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          ТОВАР НЕ НАЙДЕН
        </h1>
        <Link
          to="/catalog"
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-[#2B1516] transition-colors"
        >
          В КАТАЛОГ ↗
        </Link>
      </div>
    );
  }

  if (!permissions.canUpdate) {
    return (
      <div className="w-full min-h-[60vh] bg-[#F2E9DB] flex flex-col items-center justify-center py-24 px-4 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-[#3F2021]">
          ДОСТУП ОГРАНИЧЕН
        </h1>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 max-w-md">
          У вас нет прав для редактирования характеристик этой модели.
        </p>
        <Link
          to={`/products/${slug}`}
          className="mt-6 inline-block bg-[#3F2021] text-[#F2E9DB] px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-[#2B1516] transition-colors"
        >
          ВЕРНУТЬСЯ К ТОВАРУ ↗
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#F2E9DB] min-h-screen py-10 md:py-16">
      <div className="w-full max-w-4xl mx-auto px-4 md:px-8 space-y-8">
        {/* Header */}
        <div className="border-b border-[#3F2021]/20 pb-4 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
              ( РЕДАКТИРОВАНИЕ ТОВАРА )
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl uppercase tracking-wider text-[#3F2021] mt-1">
              {product.title}
            </h1>
          </div>
          <Link
            to={`/products/${slug}`}
            className="text-xs font-sans uppercase tracking-wider text-[#3F2021] hover:underline underline-offset-4"
          >
            ← ВЕРНУТЬСЯ К ТОВАРУ
          </Link>
        </div>

        {/* Notices */}
        {product.moderation_status === 'approved' && (
          <div className="p-4 bg-[#FFFFFF] border border-[#3F2021]/30 text-xs font-sans uppercase tracking-wider text-[#3F2021] leading-relaxed rounded-none">
            <span className="font-semibold block mb-1">( ИНФОРМАЦИЯ О ПОВТОРНОЙ МОДЕРАЦИИ )</span>
            Изменение названия, описания или характеристик изделия отправит карточку на повторную проверку модератором (тип заявки: EDIT). Изменение базовых цен и видимости применяется сразу без повторной проверки.
          </div>
        )}
        {product.moderation_status === 'rejected' && (
          <div className="p-4 bg-[#FF8562]/10 border border-[#FF8562] text-xs font-sans uppercase tracking-wider text-[#3F2021] leading-relaxed rounded-none">
            <span className="font-semibold block mb-1">( ТОВАР БЫЛ ОТКЛОНЁН МОДЕРАТОРОМ )</span>
            Причина: {product.rejection_reason || 'Причина не указана'}. Внесите необходимые исправления и сохраните изменения для повторной отправки заявки на модерацию.
          </div>
        )}
        {errorMessage && (
          <div className="p-4 bg-[#FF8562]/10 border border-[#FF8562] text-xs font-sans uppercase tracking-wider text-[#3F2021]">
            {errorMessage}
          </div>
        )}
        {successMessage && (
          <div className="p-4 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-wider text-center">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section: Основная информация */}
          <div className="border border-[#3F2021]/30 p-6 bg-[#F2E9DB] space-y-6">
            <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
              ( 1. ОСНОВНАЯ ИНФОРМАЦИЯ )
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  НАЗВАНИЕ МОДЕЛИ *
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                    URL-ИДЕНТИФИКАТОР (SLUG) *
                  </label>
                  <input
                    type="text"
                    required
                    value={productSlug}
                    onChange={(e) => setProductSlug(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-mono lowercase tracking-wider text-[#3F2021] outline-none rounded-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                    КАТЕГОРИЯ
                  </label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                  >
                    <option value="">БЕЗ КАТЕГОРИИ</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                    БРЕНД / АВТОР
                  </label>
                  <input
                    type="text"
                    value={brand}
                    onChange={(e) => setBrand(e.target.value)}
                    placeholder="НЕ УКАЗАНО"
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                  />
                </div>

                <div className="flex items-center gap-3 pt-6">
                  <input
                    type="checkbox"
                    id="self_worked_cb"
                    checked={isSelfWorked}
                    onChange={(e) => setIsSelfWorked(e.target.checked)}
                    className="w-4 h-4 accent-[#3F2021] rounded-none cursor-pointer"
                  />
                  <label
                    htmlFor="self_worked_cb"
                    className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021] cursor-pointer"
                  >
                    ( SELF-WORKED ) АВТОРСКИЙ КАСТОМ / РУЧНАЯ РАБОТА
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  ОПИСАНИЕ МОДЕЛИ
                </label>
                <textarea
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="ОПИСАНИЕ И ОСОБЕННОСТИ МОДЕЛИ..."
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none resize-y"
                />
              </div>
            </div>
          </div>

          {/* Section: Стоимость */}
          <div className="border border-[#3F2021]/30 p-6 bg-[#F2E9DB] space-y-6">
            <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
              ( 2. ЦЕНООБРАЗОВАНИЕ )
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  БАЗОВАЯ ЦЕНА (₽ RUB) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={basePrice}
                  onChange={(e) => setBasePrice(e.target.value)}
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-mono tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  ЦЕНА В ДОЛЛАРАХ ($ USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={priceUsd}
                  onChange={(e) => setPriceUsd(e.target.value)}
                  placeholder="НЕ УКАЗАНО"
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-mono tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  ЦЕНА В ЕВРО (€ EUR)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={priceEur}
                  onChange={(e) => setPriceEur(e.target.value)}
                  placeholder="НЕ УКАЗАНО"
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-mono tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>
            </div>
          </div>

          {/* Section: Характеристики */}
          <div className="border border-[#3F2021]/30 p-6 bg-[#F2E9DB] space-y-6">
            <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
              ( 3. ХАРАКТЕРИСТИКИ И МАТЕРИАЛЫ )
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  МАТЕРИАЛ
                </label>
                <input
                  type="text"
                  value={material}
                  onChange={(e) => setMaterial(e.target.value)}
                  placeholder="100% ХЛОПОК, ШЕРСТЬ..."
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  ПЛОТНОСТЬ
                </label>
                <input
                  type="text"
                  value={density}
                  onChange={(e) => setDensity(e.target.value)}
                  placeholder="450 Г/М², HEAVYWEIGHT..."
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  СОСТАВ
                </label>
                <input
                  type="text"
                  value={composition}
                  onChange={(e) => setComposition(e.target.value)}
                  placeholder="80% ХЛОПОК, 20% ПОЛИЭСТЕР..."
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                  СПОСОБ НАНЕСЕНИЯ
                </label>
                <input
                  type="text"
                  value={printMethod}
                  onChange={(e) => setPrintMethod(e.target.value)}
                  placeholder="ШЕЛКОГРАФИЯ, ВЫШИВКА..."
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                ПРИМЕЧАНИЕ / УХОД
              </label>
              <textarea
                rows={2}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="СТИРКА ПРИ 30°C НАИЗНАНКУ..."
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none resize-none"
              />
            </div>
          </div>

          {/* Section: Видимость и лимитированный тираж */}
          <div className="border border-[#3F2021]/30 p-6 bg-[#F2E9DB] space-y-6">
            <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
              ( 4. ВИДИМОСТЬ И СТАТУС ТИРАЖА )
            </div>

            {/* Visibility Level */}
            <div className="space-y-3">
              <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                ВИДИМОСТЬ ТОВАРА *
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setIsHidden(0)}
                  className={`p-3.5 text-left border transition-all rounded-none flex flex-col justify-between ${
                    isHidden === 0
                      ? 'border-[#3F2021] bg-[#3F2021] text-[#F2E9DB]'
                      : 'border-[#3F2021]/30 bg-[#FFFFFF] text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  <div className="text-xs font-sans font-bold uppercase tracking-wider">
                    0 — ОТКРЫТ ВСЕМ
                  </div>
                  <div className="text-[10px] font-sans uppercase tracking-wide opacity-80 mt-1 leading-relaxed">
                    Отображается в каталоге, поиске и по прямой ссылке.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setIsHidden(1)}
                  className={`p-3.5 text-left border transition-all rounded-none flex flex-col justify-between ${
                    isHidden === 1
                      ? 'border-[#3F2021] bg-[#3F2021] text-[#F2E9DB]'
                      : 'border-[#3F2021]/30 bg-[#FFFFFF] text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  <div className="text-xs font-sans font-bold uppercase tracking-wider">
                    1 — ТОЛЬКО ПО ССЫЛКЕ
                  </div>
                  <div className="text-[10px] font-sans uppercase tracking-wide opacity-80 mt-1 leading-relaxed">
                    Не показывается в каталоге и поиске, открывается только по прямому URL.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setIsHidden(2)}
                  className={`p-3.5 text-left border transition-all rounded-none flex flex-col justify-between ${
                    isHidden === 2
                      ? 'border-[#3F2021] bg-[#3F2021] text-[#F2E9DB]'
                      : 'border-[#3F2021]/30 bg-[#FFFFFF] text-[#3F2021] hover:border-[#3F2021]'
                  }`}
                >
                  <div className="text-xs font-sans font-bold uppercase tracking-wider">
                    2 — ПОЛНОСТЬЮ СКРЫТ
                  </div>
                  <div className="text-[10px] font-sans uppercase tracking-wide opacity-80 mt-1 leading-relaxed">
                    Черновик, виден только автору и модераторам.
                  </div>
                </button>
              </div>
            </div>

            {/* Limited Edition */}
            <div className="pt-2 border-t border-[#3F2021]/15">
              <label className="flex items-start gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isLimited}
                  onChange={(e) => setIsLimited(e.target.checked)}
                  className="w-4 h-4 mt-0.5 accent-[#3F2021] rounded-none cursor-pointer"
                />
                <div>
                  <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                    ЛИМИТИРОВАННЫЙ ТИРАЖ
                  </div>
                  <p className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mt-0.5 leading-relaxed">
                    Если включено, товар помечается как лимитированный и не подразумевает повторного пополнения после распродажи.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 pt-2">
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] py-4 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50 rounded-none"
            >
              {updateMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ИЗМЕНЕНИЯ ↗'}
            </button>
            <button
              type="button"
              onClick={() => navigate(`/products/${slug}`)}
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] py-4 px-8 text-xs font-sans font-semibold uppercase tracking-wider transition-colors rounded-none"
            >
              ОТМЕНА
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

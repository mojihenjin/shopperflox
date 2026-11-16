import { useState, useId } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { categoriesApi, productsApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import type { VariantCreateItem } from '../types/api';

interface UploadPhotoItem {
  id: string;
  file: File;
  previewUrl: string;
}

interface SizeItem {
  id: string;
  size: string;
  stock_quantity: number;
}

interface ColorBlockItem {
  id: string;
  name: string;
  photos: UploadPhotoItem[];
  sizes: SizeItem[];
}

const PRESET_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'ONE SIZE'];

function generateSlug(text: string): string {
  const ruToEn: Record<string, string> = {
    а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh',
    з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o',
    п: 'p', р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'ts',
    ч: 'ch', ш: 'sh', щ: 'sch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
  };
  const base = text
    .toLowerCase()
    .split('')
    .map((ch) => ruToEn[ch] ?? ch)
    .join('')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
  const rand = Math.random().toString(36).slice(2, 7);
  return `${base || 'item'}-${rand}`;
}

export function CreatorNewProductPage() {
  const navigate = useNavigate();
  const { isAuthenticated, authUser: user } = useAuthStore();
  const baseId = useId();

  // Categories query
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(),
  });

  const categories = categoriesData?.data || [];

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [isSelfWorked, setIsSelfWorked] = useState(false);
  const [brand, setBrand] = useState('');

  // Prices
  const [basePrice, setBasePrice] = useState('');
  const [priceUsd, setPriceUsd] = useState('');
  const [priceEur, setPriceEur] = useState('');

  // Characteristics
  const [material, setMaterial] = useState('');
  const [density, setDensity] = useState('');
  const [composition, setComposition] = useState('');
  const [printMethod, setPrintMethod] = useState('');
  const [note, setNote] = useState('');

  // Colors & Matrix
  const [colorBlocks, setColorBlocks] = useState<ColorBlockItem[]>([
    {
      id: `${baseId}-color-1`,
      name: 'Основной',
      photos: [],
      sizes: [
        { id: `${baseId}-sz-1`, size: 'M', stock_quantity: 10 },
        { id: `${baseId}-sz-2`, size: 'L', stock_quantity: 10 },
      ],
    },
  ]);
  const [customSizeInputs, setCustomSizeInputs] = useState<Record<string, string>>({});

  // Visibility and Edition
  const [isHidden, setIsHidden] = useState<0 | 1 | 2>(0);
  const [isLimited, setIsLimited] = useState(false);

  // Publishing State
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishProgress, setPublishProgress] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  if (!isAuthenticated) {
    return <Navigate to="/login?redirect=%2Fcreator%2Fproducts%2Fnew" replace />;
  }

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
            Ваш аккаунт{' '}
            <span className="font-mono font-bold text-[#3F2021]">
              @{user?.login || 'anonymous'}
            </span>{' '}
            не обладает правами <code className="bg-[#F2E9DB] px-1.5 py-0.5">creator:*</code> или администратора.
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

  // Self-worked toggle handler
  const handleToggleSelfWorked = (checked: boolean) => {
    setIsSelfWorked(checked);
    if (checked && !brand) {
      setBrand('self-worked');
    }
  };

  // Color Block Management
  const handleAddColorBlock = () => {
    setColorBlocks((prev) => [
      ...prev,
      {
        id: `color-${Date.now()}`,
        name: `Цвет ${prev.length + 1}`,
        photos: [],
        sizes: [{ id: `sz-${Date.now()}`, size: 'ONE SIZE', stock_quantity: 10 }],
      },
    ]);
  };

  const handleRemoveColorBlock = (colorId: string) => {
    setColorBlocks((prev) => {
      const target = prev.find((c) => c.id === colorId);
      if (target) {
        target.photos.forEach((p) => URL.revokeObjectURL(p.previewUrl));
      }
      return prev.filter((c) => c.id !== colorId);
    });
  };

  const handleColorNameChange = (colorId: string, newName: string) => {
    setColorBlocks((prev) =>
      prev.map((c) => (c.id === colorId ? { ...c, name: newName } : c))
    );
  };

  // Photos Management for a Color Block
  const handlePhotoFilesSelected = (colorId: string, files: FileList | null) => {
    if (!files || files.length === 0) return;
    setFormError(null);

    const newPhotos: UploadPhotoItem[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.size > 5 * 1024 * 1024) {
        setFormError(`Файл ${file.name} превышает лимит 5 МБ`);
        continue;
      }
      const allowed = ['image/jpeg', 'image/png', 'image/webp'];
      if (!allowed.includes(file.type)) {
        setFormError(`Файл ${file.name} имеет неподдерживаемый формат (разрешены JPEG, PNG, WebP)`);
        continue;
      }
      newPhotos.push({
        id: `photo-${Date.now()}-${i}-${Math.random().toString(36).slice(2, 6)}`,
        file,
        previewUrl: URL.createObjectURL(file),
      });
    }

    setColorBlocks((prev) =>
      prev.map((c) =>
        c.id === colorId ? { ...c, photos: [...c.photos, ...newPhotos] } : c
      )
    );
  };

  const handleMovePhoto = (colorId: string, photoIdx: number, direction: 'left' | 'right') => {
    setColorBlocks((prev) =>
      prev.map((c) => {
        if (c.id !== colorId) return c;
        const photos = [...c.photos];
        const targetIdx = direction === 'left' ? photoIdx - 1 : photoIdx + 1;
        if (targetIdx < 0 || targetIdx >= photos.length) return c;
        const temp = photos[photoIdx];
        photos[photoIdx] = photos[targetIdx];
        photos[targetIdx] = temp;
        return { ...c, photos };
      })
    );
  };

  const handleRemovePhoto = (colorId: string, photoId: string) => {
    setColorBlocks((prev) =>
      prev.map((c) => {
        if (c.id !== colorId) return c;
        const target = c.photos.find((p) => p.id === photoId);
        if (target) URL.revokeObjectURL(target.previewUrl);
        return {
          ...c,
          photos: c.photos.filter((p) => p.id !== photoId),
        };
      })
    );
  };

  // Sizes Management for a Color Block
  const handleAddPresetSize = (colorId: string, sizeName: string) => {
    setColorBlocks((prev) =>
      prev.map((c) => {
        if (c.id !== colorId) return c;
        if (c.sizes.some((s) => s.size.toLowerCase() === sizeName.toLowerCase())) {
          return c;
        }
        return {
          ...c,
          sizes: [
            ...c.sizes,
            { id: `sz-${Date.now()}-${Math.random()}`, size: sizeName, stock_quantity: 10 },
          ],
        };
      })
    );
  };

  const handleAddCustomSize = (colorId: string) => {
    const val = (customSizeInputs[colorId] || '').trim().toUpperCase();
    if (!val) return;
    setColorBlocks((prev) =>
      prev.map((c) => {
        if (c.id !== colorId) return c;
        if (c.sizes.some((s) => s.size.toLowerCase() === val.toLowerCase())) {
          return c;
        }
        return {
          ...c,
          sizes: [
            ...c.sizes,
            { id: `sz-${Date.now()}-${Math.random()}`, size: val, stock_quantity: 10 },
          ],
        };
      })
    );
    setCustomSizeInputs((prev) => ({ ...prev, [colorId]: '' }));
  };

  const handleSizeQuantityChange = (colorId: string, sizeId: string, qty: number) => {
    setColorBlocks((prev) =>
      prev.map((c) => {
        if (c.id !== colorId) return c;
        return {
          ...c,
          sizes: c.sizes.map((s) =>
            s.id === sizeId ? { ...s, stock_quantity: Math.max(0, qty) } : s
          ),
        };
      })
    );
  };

  const handleRemoveSize = (colorId: string, sizeId: string) => {
    setColorBlocks((prev) =>
      prev.map((c) => {
        if (c.id !== colorId) return c;
        return {
          ...c,
          sizes: c.sizes.filter((s) => s.id !== sizeId),
        };
      })
    );
  };

  // Submit Handler
  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setFormError('Укажите название модели');
      return;
    }
    if (!categoryId) {
      setFormError('Выберите категорию товара');
      return;
    }
    const numBasePrice = parseFloat(basePrice);
    if (isNaN(numBasePrice) || numBasePrice < 0) {
      setFormError('Укажите корректную базовую цену в рублях (>= 0)');
      return;
    }
    if (colorBlocks.length === 0) {
      setFormError('Добавьте хотя бы один цвет');
      return;
    }

    // Prepare variants array
    const variantItems: VariantCreateItem[] = [];
    for (const cb of colorBlocks) {
      const colorName = cb.name.trim() || 'Основной';
      if (cb.sizes.length === 0) {
        variantItems.push({
          color: colorName,
          color_name: colorName,
          size: 'ONE SIZE',
          stock_quantity: 0,
        });
      } else {
        for (const s of cb.sizes) {
          variantItems.push({
            color: colorName,
            color_name: colorName,
            size: s.size.trim(),
            stock_quantity: s.stock_quantity,
          });
        }
      }
    }

    setIsPublishing(true);
    setPublishProgress('1/3 Создание записи товара в каталоге...');

    try {
      const productSlug = generateSlug(cleanTitle);

      const resolvedBrand = isSelfWorked
        ? brand.trim() || 'self-worked'
        : brand.trim() || null;

      const createdRes = await productsApi.create({
        category_id: categoryId,
        title: cleanTitle,
        slug: productSlug,
        brand: resolvedBrand,
        is_self_worked: isSelfWorked,
        base_price: numBasePrice,
        price_usd: priceUsd ? parseFloat(priceUsd) : null,
        price_eur: priceEur ? parseFloat(priceEur) : null,
        material: material.trim() || null,
        density: density.trim() || null,
        composition: composition.trim() || null,
        print_method: printMethod.trim() || null,
        note: note.trim() || null,
        description: description.trim() || null,
        is_published: isHidden !== 2,
        is_hidden: isHidden,
        is_limited: isLimited,
        variants: variantItems,
      });

      const product = createdRes.data;

      // Collect all photos across all color blocks
      const allPhotosToUpload: { file: File; color: string; sort_order: number; is_main: boolean }[] = [];
      let globalSortOrder = 0;

      colorBlocks.forEach((cb) => {
        const colorName = cb.name.trim() || 'Основной';
        cb.photos.forEach((photo) => {
          allPhotosToUpload.push({
            file: photo.file,
            color: colorName,
            sort_order: globalSortOrder,
            is_main: globalSortOrder === 0,
          });
          globalSortOrder++;
        });
      });

      if (allPhotosToUpload.length > 0) {
        for (let idx = 0; idx < allPhotosToUpload.length; idx++) {
          const item = allPhotosToUpload[idx];
          setPublishProgress(
            `2/3 Загрузка фотографий (${idx + 1} из ${allPhotosToUpload.length})...`
          );

          const formData = new FormData();
          formData.append('file', item.file);
          formData.append('color', item.color);
          formData.append('sort_order', String(item.sort_order));
          if (item.is_main) {
            formData.append('is_main', 'true');
          }

          await productsApi.uploadImage(product.id, formData);
        }
      }

      setPublishProgress('3/3 Товар опубликован! Перенаправление...');
      // Clean up object URLs
      colorBlocks.forEach((cb) => {
        cb.photos.forEach((p) => URL.revokeObjectURL(p.previewUrl));
      });

      setTimeout(() => {
        navigate(`/products/${product.slug}`);
      }, 600);
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error ? err.message : 'Не удалось опубликовать товар';
      setFormError(errorMsg);
      setIsPublishing(false);
      setPublishProgress(null);
    }
  };

  // Preview data helpers
  const firstPhotoWithPreview =
    colorBlocks.flatMap((c) => c.photos)[0]?.previewUrl || null;

  return (
    <div className="w-full bg-[#F2E9DB] min-h-[90vh] py-10 md:py-16 px-4 md:px-8">
      <div className="w-full max-w-7xl mx-auto space-y-8">
        {/* Navigation & Breadcrumbs */}
        <div className="flex items-center justify-between border-b border-[#3F2021]/20 pb-4">
          <Link
            to="/catalog"
            className="text-xs font-sans uppercase tracking-widest text-[#3F2021] hover:opacity-60 transition-opacity"
          >
            ← ВЕРНУТЬСЯ В КАТАЛОГ
          </Link>
          <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            ( CREATOR STUDIO / НОВЫЙ ТОВАР )
          </div>
        </div>

        {/* Header Title */}
        <div className="border-b border-[#3F2021]/15 pb-6">
          <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70 mb-1">
            ( АВТОРСКАЯ ПАНЕЛЬ ПУБЛИКАЦИИ )
          </div>
          <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021]">
            СОЗДАНИЕ ТОВАРА
          </h1>
          <p className="mt-2 text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
            Автор: <span className="font-mono font-bold text-[#3F2021]">@{user?.login}</span> &nbsp;|&nbsp; Все созданные товары связываются с вашим аккаунтом
          </p>
        </div>

        {formError && (
          <div className="p-4 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-wider">
            {formError}
          </div>
        )}

        {/* TWO-COLUMN GRID: Form on Left, Sticky Preview on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT COLUMN: THE FORM (7 cols) */}
          <form onSubmit={handlePublish} className="lg:col-span-7 space-y-8">
            {/* 1. Основная информация */}
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-5">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                  ( РАЗДЕЛ 1 )
                </span>
                <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  ОСНОВНАЯ ИНФОРМАЦИЯ
                </h2>
              </div>

              {/* Название */}
              <div className="space-y-1.5">
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                  НАЗВАНИЕ МОДЕЛИ *
                </label>
                <input
                  type="text"
                  required
                  placeholder="НАПР. ОВЕРСАЙЗ ХУДИ «CYBER FLOCK»"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2.5 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                />
              </div>

              {/* Категория */}
              <div className="space-y-1.5">
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                  КАТЕГОРИЯ *
                </label>
                <select
                  required
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2.5 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                >
                  <option value="">-- ВЫБЕРИТЕ КАТЕГОРИЮ --</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              {/* Описание */}
              <div className="space-y-1.5">
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                  ОПИСАНИЕ
                </label>
                <textarea
                  rows={3}
                  placeholder="Особенности кроя, концепция дропа, философия изделия..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none leading-relaxed"
                />
              </div>

              {/* Бренд & self-worked */}
              <div className="pt-2 border-t border-[#3F2021]/15 space-y-3">
                <label className="flex items-center gap-3 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isSelfWorked}
                    onChange={(e) => handleToggleSelfWorked(e.target.checked)}
                    className="w-4 h-4 accent-[#3F2021] rounded-none cursor-pointer"
                  />
                  <span className="text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                    SELF-WORKED (АВТОРСКАЯ РАБОТА / КАСТОМ)
                  </span>
                </label>

                <div className="space-y-1">
                  <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70">
                    БРЕНД ИЛИ ИМЯ АВТОРА
                  </label>
                  <input
                    type="text"
                    placeholder={isSelfWorked ? 'self-worked' : 'ShopperFlox или ваш бренд'}
                    value={brand}
                    onChange={(e) => setBrand(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                  />
                </div>
              </div>
            </div>

            {/* 2. Мультивалютная цена */}
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-5">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                  ( РАЗДЕЛ 2 )
                </span>
                <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  МУЛЬТИВАЛЮТНАЯ СТОИМОСТЬ
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                    ЦЕНА В ₽ (RUB) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    placeholder="4500"
                    value={basePrice}
                    onChange={(e) => setBasePrice(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans font-bold text-[#000000] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021]/80">
                    ЦЕНА В $ (USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="49.99"
                    value={priceUsd}
                    onChange={(e) => setPriceUsd(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans text-[#000000] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021]/80">
                    ЦЕНА В € (EUR)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="45.50"
                    value={priceEur}
                    onChange={(e) => setPriceEur(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans text-[#000000] outline-none"
                  />
                </div>
              </div>
            </div>

            {/* 3. Характеристики изделия */}
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-5">
              <div className="border-b border-[#3F2021]/15 pb-3">
                <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                  ( РАЗДЕЛ 3 )
                </span>
                <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  ХАРАКТЕРИСТИКИ ИЗДЕЛИЯ
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                    МАТЕРИАЛ
                  </label>
                  <input
                    type="text"
                    placeholder="НАПР. ФУТЕР 3-НИТКА ПЕТЛЯ"
                    value={material}
                    onChange={(e) => setMaterial(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                    ПЛОТНОСТЬ
                  </label>
                  <input
                    type="text"
                    placeholder="НАПР. 460 Г/М²"
                    value={density}
                    onChange={(e) => setDensity(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                    СОСТАВ
                  </label>
                  <input
                    type="text"
                    placeholder="НАПР. 100% ХЛОПОК"
                    value={composition}
                    onChange={(e) => setComposition(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                    НАНЕСЕНИЕ
                  </label>
                  <input
                    type="text"
                    placeholder="НАПР. ШЕЛКОГРАФИЯ + ВЫШИВКА"
                    value={printMethod}
                    onChange={(e) => setPrintMethod(e.target.value)}
                    className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5 pt-1">
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                  ПРИМЕЧАНИЕ (ПОСАДКА, УХОД)
                </label>
                <textarea
                  rows={2}
                  placeholder="Особенности кроя (оверсайз, спущенное плечо), рекомендации по стирке..."
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none leading-relaxed"
                />
              </div>
            </div>

            {/* 4. Цвета, фото и размеры */}
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3F2021]/15 pb-3">
                <div>
                  <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                    ( РАЗДЕЛ 4 )
                  </span>
                  <h2 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                    ЦВЕТА, ФОТО И МАТРИЦА РАЗМЕРОВ
                  </h2>
                </div>

                <button
                  type="button"
                  onClick={handleAddColorBlock}
                  className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3.5 py-1.5 text-xs font-sans font-semibold uppercase tracking-wider transition-colors self-start sm:self-auto"
                >
                  + ДОБАВИТЬ ЦВЕТ
                </button>
              </div>

              {/* List of Color Blocks */}
              <div className="space-y-8">
                {colorBlocks.map((cb, colorIdx) => (
                  <div
                    key={cb.id}
                    className="border border-[#3F2021]/30 p-5 bg-[#F2E9DB]/20 space-y-5"
                  >
                    {/* Color Header */}
                    <div className="flex items-center justify-between gap-3 border-b border-[#3F2021]/20 pb-3">
                      <div className="flex items-center gap-3 flex-1">
                        <span className="text-xs font-serif font-bold text-[#3F2021]">
                          #{colorIdx + 1}
                        </span>
                        <input
                          type="text"
                          required
                          placeholder="НАЗВАНИЕ ЦВЕТА (НАПР. БОРДОВЫЙ)"
                          value={cb.name}
                          onChange={(e) => handleColorNameChange(cb.id, e.target.value)}
                          className="flex-1 max-w-xs bg-[#FFFFFF] border border-[#3F2021]/40 px-3 py-1.5 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none"
                        />
                      </div>

                      {colorBlocks.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveColorBlock(cb.id)}
                          className="text-xs font-sans uppercase tracking-wider text-sf-coral hover:underline"
                        >
                          УДАЛИТЬ ЦВЕТ ×
                        </button>
                      )}
                    </div>

                    {/* Photos Upload Zone */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                          ФОТОГРАФИИ ЦВЕТА «{cb.name || 'БЕЗ НАЗВАНИЯ'}» ({cb.photos.length})
                        </span>
                        <label className="cursor-pointer bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3 py-1 text-xs font-sans uppercase tracking-wider font-semibold transition-colors">
                          + ВЫБРАТЬ ФАЙЛЫ
                          <input
                            type="file"
                            multiple
                            accept="image/jpeg,image/png,image/webp"
                            onChange={(e) => {
                              handlePhotoFilesSelected(cb.id, e.target.files);
                              e.target.value = '';
                            }}
                            className="hidden"
                          />
                        </label>
                      </div>

                      {cb.photos.length === 0 ? (
                        <label className="block border-2 border-dashed border-[#3F2021]/30 p-6 text-center cursor-pointer hover:border-[#3F2021] transition-colors">
                          <input
                            type="file"
                            multiple
                            accept="image/jpeg,image/png,image/webp"
                            onChange={(e) => {
                              handlePhotoFilesSelected(cb.id, e.target.files);
                              e.target.value = '';
                            }}
                            className="hidden"
                          />
                          <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
                            КЛИКНИТЕ ИЛИ ПЕРЕТАЩИТЕ СЮДА ФОТОГРАФИИ ДЛЯ ЭТОГО ЦВЕТА
                          </div>
                          <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/50 mt-1">
                            ( JPEG, PNG, WEBP ДО 5 МБ, ПРОПОРЦИЯ 2:3 )
                          </div>
                        </label>
                      ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3">
                          {cb.photos.map((photo, pIdx) => (
                            <div
                              key={photo.id}
                              className="relative aspect-[2/3] bg-[#E5DBCB] border border-[#3F2021]/30 overflow-hidden group flex flex-col justify-between"
                            >
                              <img
                                src={photo.previewUrl}
                                alt="preview"
                                className="w-full h-full object-cover"
                              />

                              {/* Action Overlay */}
                              <div className="absolute inset-0 bg-[#3F2021]/70 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-1.5 text-[#F2E9DB]">
                                <div className="flex justify-between items-center text-[10px] font-mono">
                                  <span>#{pIdx + 1}</span>
                                  <button
                                    type="button"
                                    onClick={() => handleRemovePhoto(cb.id, photo.id)}
                                    className="hover:text-sf-coral font-bold px-1"
                                    title="Удалить"
                                  >
                                    ×
                                  </button>
                                </div>

                                <div className="flex justify-center gap-2 text-xs font-mono">
                                  <button
                                    type="button"
                                    disabled={pIdx === 0}
                                    onClick={() => handleMovePhoto(cb.id, pIdx, 'left')}
                                    className="px-2 py-0.5 bg-[#F2E9DB] text-[#3F2021] disabled:opacity-30 hover:bg-[#FFFFFF]"
                                    title="Переместить влево"
                                  >
                                    ←
                                  </button>
                                  <button
                                    type="button"
                                    disabled={pIdx === cb.photos.length - 1}
                                    onClick={() => handleMovePhoto(cb.id, pIdx, 'right')}
                                    className="px-2 py-0.5 bg-[#F2E9DB] text-[#3F2021] disabled:opacity-30 hover:bg-[#FFFFFF]"
                                    title="Переместить вправо"
                                  >
                                    →
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Sizes and Stock Matrix */}
                    <div className="space-y-3 pt-2 border-t border-[#3F2021]/20">
                      <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                        РАЗМЕРЫ И ОСТАТКИ (СКЛАД):
                      </div>

                      {/* Quick preset buttons */}
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60 mr-1">
                          ДОБАВИТЬ:
                        </span>
                        {PRESET_SIZES.map((sz) => (
                          <button
                            key={sz}
                            type="button"
                            onClick={() => handleAddPresetSize(cb.id, sz)}
                            className="px-2 py-1 border border-[#3F2021]/30 hover:border-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] text-[11px] font-sans font-semibold transition-colors"
                          >
                            + {sz}
                          </button>
                        ))}
                      </div>

                      {/* Custom Size Form */}
                      <div className="flex items-center gap-2 max-w-xs">
                        <input
                          type="text"
                          placeholder="СВОЙ РАЗМЕР"
                          value={customSizeInputs[cb.id] || ''}
                          onChange={(e) =>
                            setCustomSizeInputs((prev) => ({
                              ...prev,
                              [cb.id]: e.target.value,
                            }))
                          }
                          className="flex-1 bg-[#FFFFFF] border border-[#3F2021]/30 px-2.5 py-1 text-xs font-sans uppercase outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => handleAddCustomSize(cb.id)}
                          className="bg-[#3F2021] text-[#F2E9DB] px-3 py-1 text-xs font-sans uppercase font-semibold"
                        >
                          +
                        </button>
                      </div>

                      {/* Active Sizes List */}
                      {cb.sizes.length === 0 ? (
                        <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/50 italic">
                          ( РАЗМЕРЫ НЕ ДОБАВЛЕНЫ — БУДЕТ СОЗДАН ОДИН ВАРИАНТ ONE SIZE С НУЛЕВЫМ ОСТАТКОМ )
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {cb.sizes.map((s) => (
                            <div
                              key={s.id}
                              className="flex items-center justify-between p-2.5 bg-[#FFFFFF] border border-[#3F2021]/30"
                            >
                              <span className="font-sans font-bold text-xs uppercase text-[#3F2021]">
                                РАЗМЕР: {s.size}
                              </span>

                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-sans uppercase text-[#3F2021]/60">
                                  ШТ:
                                </span>
                                <input
                                  type="number"
                                  min="0"
                                  value={s.stock_quantity}
                                  onChange={(e) =>
                                    handleSizeQuantityChange(
                                      cb.id,
                                      s.id,
                                      parseInt(e.target.value, 10) || 0
                                    )
                                  }
                                  className="w-16 bg-[#F2E9DB]/40 border border-[#3F2021]/40 px-2 py-0.5 text-xs font-mono font-bold text-center outline-none"
                                />
                                <button
                                  type="button"
                                  onClick={() => handleRemoveSize(cb.id, s.id)}
                                  className="text-[#3F2021]/60 hover:text-sf-coral px-1 font-bold text-sm"
                                  title="Удалить размер"
                                >
                                  ×
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 5. Видимость и статус тиража */}
            <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-5 rounded-none">
              <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
                ( 5. ВИДИМОСТЬ И СТАТУС ТИРАЖА )
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

            {/* Submit Action */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isPublishing}
                className="w-full bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] py-4 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50"
              >
                {isPublishing
                  ? publishProgress || 'ОПУБЛИКАЦИЯ...'
                  : 'ОПУБЛИКОВАТЬ ТОВАР ↗'}
              </button>
            </div>
          </form>

          {/* RIGHT COLUMN: REALTIME STICKY PREVIEW (5 cols) */}
          <div className="lg:col-span-5 sticky top-24 space-y-4">
            <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021]/70">
              ( ЖУРНАЛЬНОЕ ПРЕВЬЮ В РЕАЛЬНОМ ВРЕМЕНИ )
            </div>

            <div className="bg-[#FFFFFF] border border-[#3F2021] overflow-hidden flex flex-col">
              {/* Photo Stage 2:3 */}
              <div className="relative aspect-[2/3] w-full bg-[#E5DBCB] overflow-hidden flex flex-col justify-between p-4">
                {firstPhotoWithPreview ? (
                  <img
                    src={firstPhotoWithPreview}
                    alt="preview"
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                ) : (
                  <div className="absolute inset-0 flex flex-col justify-between p-6 bg-[#3F2021]/5">
                    <div className="flex justify-between items-start text-[10px] font-sans tracking-widest text-[#3F2021]/50">
                      <span>LOOKBOOK // 2026</span>
                      <span>( PREVIEW )</span>
                    </div>

                    <div className="text-center space-y-1">
                      <div className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]/70">
                        ФОТОГРАФИЯ 2:3
                      </div>
                      <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/50">
                        {colorBlocks[0]?.photos.length === 0
                          ? 'ЗАГРУЗИТЕ ФОТО В ФОРМЕ'
                          : 'ПРЕДПРОСМОТР КАДРА'}
                      </div>
                    </div>

                    <div className="text-[9px] font-sans uppercase tracking-widest text-[#3F2021]/50 text-right">
                      SHOPPERFLOX CREATOR
                    </div>
                  </div>
                )}

                {/* Badge tags overlay */}
                <div className="relative z-10 flex flex-wrap gap-1 items-start justify-between">
                  <div className="flex flex-wrap gap-1 items-start">
                    {isSelfWorked ? (
                      <span className="bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[9px] font-sans uppercase tracking-widest font-semibold rounded-none">
                        SELF-WORKED
                      </span>
                    ) : (
                      <span className="bg-[#3F2021]/80 text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase tracking-widest rounded-none">
                        {brand || 'ShopperFlox'}
                      </span>
                    )}

                    {isLimited && (
                      <span className="bg-[#3F2021] text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase tracking-widest font-semibold rounded-none">
                        LIMITED
                      </span>
                    )}

                    {isHidden === 1 && (
                      <span className="bg-[#3F2021]/70 text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase tracking-widest rounded-none">
                        ПО ССЫЛКЕ
                      </span>
                    )}

                    {isHidden === 2 && (
                      <span className="bg-[#FF8562] text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase tracking-widest rounded-none">
                        СКРЫТ
                      </span>
                    )}
                  </div>

                  {colorBlocks.flatMap((c) => c.photos).length > 1 && (
                    <span className="bg-[#F2E9DB]/90 text-[#3F2021] px-1.5 py-0.5 text-[9px] font-mono font-bold rounded-none">
                      {colorBlocks.flatMap((c) => c.photos).length} ФОТО
                    </span>
                  )}
                </div>
              </div>

              {/* Information Block */}
              <div className="p-5 space-y-3 bg-[#FFFFFF]">
                <div className="space-y-1">
                  <div className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                    [ {isSelfWorked ? 'SELF-WORKED // ' + (brand || `@${user?.login}`) : brand || 'ShopperFlox'} ]
                  </div>
                  <div className="font-serif text-lg uppercase tracking-wider text-[#3F2021] truncate">
                    {title || 'НАЗВАНИЕ МОДЕЛИ'}
                  </div>
                </div>

                {/* Price Display */}
                <div className="flex items-baseline justify-between border-y border-[#3F2021]/15 py-2.5">
                  <div className="font-sans font-bold text-xl text-[#3F2021]">
                    {basePrice ? `${Number(basePrice).toLocaleString('ru-RU')} ₽` : '0 ₽'}
                  </div>
                  {(priceUsd || priceEur) && (
                    <div className="text-xs font-mono text-[#3F2021]/70 space-x-2">
                      {priceUsd && <span>${priceUsd}</span>}
                      {priceEur && <span>€{priceEur}</span>}
                    </div>
                  )}
                </div>

                {/* Characteristics Preview */}
                {(material || density || composition) && (
                  <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/80 space-y-1 pt-1">
                    {material && <div>• МАТЕРИАЛ: {material}</div>}
                    {density && <div>• ПЛОТНОСТЬ: {density}</div>}
                    {composition && <div>• СОСТАВ: {composition}</div>}
                  </div>
                )}

                {/* Colors & Sizes Chips */}
                <div className="space-y-2 pt-1 border-t border-[#3F2021]/10">
                  <div className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                    ДОСТУПНЫЕ ЦВЕТА И РАЗМЕРЫ:
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {colorBlocks.map((c) => (
                      <span
                        key={c.id}
                        className="bg-[#F2E9DB] text-[#3F2021] border border-[#3F2021]/30 px-2 py-0.5 text-[10px] font-sans uppercase font-semibold"
                      >
                        {c.name || 'ЦВЕТ'} (
                        {c.sizes.map((s) => s.size).join(', ') || 'ONE SIZE'}
                        )
                      </span>
                    ))}
                  </div>
                </div>

                {/* Demo CTA */}
                <div className="pt-2">
                  <div className="w-full text-center bg-[#3F2021] text-[#F2E9DB] py-2.5 text-xs font-sans uppercase tracking-widest font-semibold select-none opacity-90">
                    В КОРЗИНУ ↗
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

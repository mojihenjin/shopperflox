import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { productsApi, categoriesApi, brandsApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import type { ProductUpdateRequest, ProductVariantResponse, ProductDetailResponse, ProductImageReorderItem } from '../types/api';
import type { ApiError } from '../api/client';

const PRESET_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'ONE SIZE'];

const RU_TO_EN: Record<string, string> = {
  а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh',
  з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o',
  п: 'p', р: 'r', с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'ts',
  ч: 'ch', ш: 'sh', щ: 'sch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
};

function transliterateToLatin(text: string): string {
  return text
    .toLowerCase()
    .split('')
    .map((ch) => RU_TO_EN[ch] ?? ch)
    .join('')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toUpperCase();
}

function generateSafeVariantSku(
  productSlug: string,
  color?: string,
  size?: string,
  index?: number
): string {
  const slugPart = transliterateToLatin(productSlug).slice(0, 16) || 'ITEM';
  const colorPart = color ? transliterateToLatin(color).slice(0, 8) : '';
  const sizePart = size ? transliterateToLatin(size).slice(0, 6) : '';
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();

  const parts = [slugPart];
  if (colorPart) parts.push(colorPart);
  if (sizePart) parts.push(sizePart);
  if (index !== undefined) parts.push(String(index));
  parts.push(rand);

  return parts.join('-').slice(0, 64);
}

interface VariantReplenishCardProps {
  variant: ProductVariantResponse;
  onUpdateStock: (variantId: string, newStock: number) => Promise<void>;
  isUpdating: boolean;
}

function VariantReplenishCard({ variant, onUpdateStock, isUpdating }: VariantReplenishCardProps) {
  const [stock, setStock] = useState<number>(variant.stock_quantity ?? 0);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    setStock(variant.stock_quantity ?? 0);
  }, [variant.stock_quantity]);

  const handleQuickAdd = (delta: number) => {
    setStock((prev) => Math.max(0, prev + delta));
  };

  const handleSave = async () => {
    try {
      await onUpdateStock(variant.id, stock);
      setStatusMsg(`✓ ОСТАТОК ОБНОВЛЕН: ${stock} ШТ`);
      setTimeout(() => setStatusMsg(null), 3500);
    } catch {
      setStatusMsg('× ОШИБКА ОБНОВЛЕНИЯ');
      setTimeout(() => setStatusMsg(null), 3500);
    }
  };

  const isChanged = stock !== (variant.stock_quantity ?? 0);

  return (
    <div className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4 rounded-none space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#3F2021]/15 pb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-xs font-bold text-[#3F2021]">
            {variant.sku}
          </span>
          <span className="text-[11px] font-sans uppercase text-[#3F2021]/70">
            {variant.color_name || variant.color || 'ЦВЕТ НЕ УКАЗАН'}
            {variant.size ? ` / РАЗМЕР: ${variant.size}` : ''}
          </span>
          {variant.price_override && (
            <span className="text-[10px] font-mono text-[#3F2021]/60">
              [{Number(variant.price_override).toLocaleString('ru-RU')} ₽]
            </span>
          )}
        </div>
        <div>
          {(variant.stock_quantity ?? 0) > 0 ? (
            <span className="text-[10px] font-mono uppercase bg-[#3F2021]/10 text-[#3F2021] px-2 py-0.5 font-semibold">
              В НАЛИЧИИ: {variant.stock_quantity} ШТ
            </span>
          ) : (
            <span className="text-[10px] font-mono uppercase bg-[#FF8562]/20 text-[#3F2021] border border-[#FF8562] px-2 py-0.5 font-bold">
              РАСПРОДАНО (0 ШТ)
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-[10px] font-sans uppercase font-semibold text-[#3F2021]/60 mr-1">
            ПОПОЛНИТЬ:
          </span>
          {[1, 5, 10, 25, 50, 100].map((delta) => (
            <button
              key={delta}
              type="button"
              onClick={() => handleQuickAdd(delta)}
              className="px-2 py-1 border border-[#3F2021]/30 hover:border-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] text-[10px] font-mono transition-colors rounded-none cursor-pointer"
            >
              +{delta}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setStock(0)}
            className="px-2 py-1 border border-[#FF8562]/40 hover:border-[#FF8562] hover:bg-[#FF8562] hover:text-[#FFFFFF] text-[10px] font-mono transition-colors rounded-none cursor-pointer text-[#3F2021]"
            title="Обнулить остаток"
          >
            ОБНУЛИТЬ
          </button>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center border border-[#3F2021]/30 bg-[#F2E9DB]/20">
            <span className="px-2 text-[10px] font-sans font-semibold uppercase text-[#3F2021]/70">
              ИТОГО:
            </span>
            <input
              type="number"
              min="0"
              value={stock}
              onChange={(e) => setStock(Math.max(0, parseInt(e.target.value) || 0))}
              className="w-20 p-1.5 text-xs font-mono font-bold text-[#3F2021] bg-transparent outline-none rounded-none text-right"
            />
            <span className="pr-2 text-[10px] font-mono text-[#3F2021]/60">ШТ</span>
          </div>

          <button
            type="button"
            disabled={isUpdating || !isChanged}
            onClick={handleSave}
            className={`px-3 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold border transition-colors rounded-none cursor-pointer ${
              isChanged
                ? 'bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] border-[#3F2021]'
                : 'bg-[#F2E9DB]/50 text-[#3F2021]/40 border-[#3F2021]/20 cursor-not-allowed'
            }`}
          >
            {isUpdating ? '...' : 'СОХРАНИТЬ ✓'}
          </button>
        </div>
      </div>

      {statusMsg && (
        <div className="text-[11px] font-mono font-bold uppercase text-emerald-800 bg-emerald-100/70 p-1.5 border border-emerald-800/20 text-center">
          {statusMsg}
        </div>
      )}
    </div>
  );
}

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
  const [brandChoice, setBrandChoice] = useState<string>('');
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

  // My Brands Query
  const { data: myBrandsData } = useQuery({
    queryKey: ['myBrands'],
    queryFn: () => brandsApi.my(),
  });

  const activeMyBrands = useMemo(() => {
    return (myBrandsData?.data || []).filter(
      (b) => !b.brand.is_deleted && (b.role === 'representative' || b.role === 'moderator')
    );
  }, [myBrandsData]);

  const hasGlobalCreatorProducts = useMemo(() => {
    const perms = currentUser?.global_permissions || [];
    return perms.includes('*') || perms.includes('creator:products') || perms.some((p) => p.startsWith('creator:'));
  }, [currentUser?.global_permissions]);

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
      const initialChoice = product.brand_id
        ? `brand:${product.brand_id}`
        : product.is_self_worked
        ? 'self-worked'
        : product.brand
        ? `custom:${product.brand}`
        : 'self-worked';
      setBrandChoice(initialChoice);
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
    const isBrandMember = activeMyBrands.some(
      (b) =>
        (product.brand_id && b.brand.id === product.brand_id) ||
        (product.brand && b.brand.name.toLowerCase() === product.brand.toLowerCase())
    );
    const canUpdate = isCreator || isSuperAdmin || hasBrandAccess || isBrandMember || globalPermissions.includes('mod:update');
    return { canUpdate };
  }, [currentUser, product, activeMyBrands]);

  const handleBrandChoiceChange = (choice: string) => {
    setBrandChoice(choice);
    if (choice === 'self-worked') {
      setIsSelfWorked(true);
      setBrand('self-worked');
    } else if (choice.startsWith('brand:')) {
      const bId = choice.replace('brand:', '');
      const found = activeMyBrands.find((b) => b.brand.id === bId);
      if (found) {
        setIsSelfWorked(false);
        setBrand(found.brand.name);
      }
    }
  };

  // Variants from product detail
  const variants = productData?.data?.variants || [];
  const images = productData?.data?.images || [];
  const totalStock = variants.reduce((sum, v) => sum + (v.stock_quantity ?? 0), 0);

  // Photos state: color grouping, DnD and uploading
  const [extraColors, setExtraColors] = useState<string[]>([]);
  const [isAddingColorBlock, setIsAddingColorBlock] = useState(false);
  const [newColorBlockName, setNewColorBlockName] = useState('');
  const [isUploadingPhotos, setIsUploadingPhotos] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [photoSuccess, setPhotoSuccess] = useState<string | null>(null);
  const [draggedImageId, setDraggedImageId] = useState<string | null>(null);
  const [dragOverImageId, setDragOverImageId] = useState<string | null>(null);
  const [dragOverColorKey, setDragOverColorKey] = useState<string | null>(null);

  // Compute all unique color blocks for photos
  const colorBlocksList = useMemo(() => {
    const set = new Set<string>();
    variants.forEach((v) => {
      const c = v.color_name || v.color;
      if (c && c.trim()) set.add(c.trim());
    });
    images.forEach((img) => {
      if (img.color && img.color.trim()) set.add(img.color.trim());
    });
    extraColors.forEach((c) => {
      if (c && c.trim()) set.add(c.trim());
    });

    const list = Array.from(set);
    const hasGeneral = images.some((img) => !img.color || !img.color.trim());
    if (hasGeneral || list.length === 0) {
      list.push('__GENERAL__');
    }
    return list;
  }, [variants, images, extraColors]);

  // Upload handler for photos in a specific color block
  const handleUploadFilesForColor = async (colorKey: string, files: FileList | null) => {
    if (!files || files.length === 0 || !product?.id) return;
    setPhotoError(null);
    setPhotoSuccess(null);
    setIsUploadingPhotos(true);

    const isGeneral = colorKey === '__GENERAL__';
    const colorVal = isGeneral ? null : colorKey;

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.size > 5 * 1024 * 1024) {
          setPhotoError(`Файл ${file.name} превышает лимит 5 МБ`);
          continue;
        }
        const allowed = ['image/jpeg', 'image/png', 'image/webp'];
        if (!allowed.includes(file.type)) {
          setPhotoError(`Файл ${file.name} имеет неподдерживаемый формат (JPEG, PNG, WebP)`);
          continue;
        }

        setUploadProgress(`Загрузка фото (${i + 1} из ${files.length})...`);
        const formData = new FormData();
        formData.append('file', file);
        if (colorVal) {
          formData.append('color', colorVal);
        }
        formData.append('sort_order', String(images.length + i));
        if (images.length === 0 && i === 0) {
          formData.append('is_main', 'true');
        }

        await productsApi.uploadImage(product.id, formData);
      }

      await queryClient.invalidateQueries({ queryKey: ['product', slug] });
      await queryClient.invalidateQueries({ queryKey: ['products'] });
      setPhotoSuccess('Фотографии успешно загружены!');
      setTimeout(() => setPhotoSuccess(null), 3000);
    } catch (err: unknown) {
      setPhotoError(err instanceof Error ? err.message : 'Ошибка при загрузке фотографий');
    } finally {
      setIsUploadingPhotos(false);
      setUploadProgress(null);
    }
  };

  // Reorder images and persist immediately via PATCH /api/v1/products/{id}/images/reorder
  const handleReorderImages = async (draggedId: string, targetId: string) => {
    if (!product?.id) return;
    const sourceIdx = images.findIndex((img) => img.id === draggedId);
    const targetIdx = images.findIndex((img) => img.id === targetId);
    if (sourceIdx === -1 || targetIdx === -1 || sourceIdx === targetIdx) return;

    const newImages = [...images];
    const [moved] = newImages.splice(sourceIdx, 1);

    // If target has color, adopt target color
    const targetImg = newImages[targetIdx < sourceIdx ? targetIdx : targetIdx - 1] || newImages[targetIdx];
    if (targetImg) {
      moved.color = targetImg.color;
    }

    newImages.splice(targetIdx, 0, moved);

    const reorderedPayload: ProductImageReorderItem[] = newImages.map((img, idx) => ({
      image_id: img.id,
      sort_order: idx,
      color: img.color ?? null,
    }));

    // Optimistic cache update
    queryClient.setQueryData<ProductDetailResponse>(['product', slug], (old) => {
      if (!old) return old;
      return {
        ...old,
        images: newImages.map((img, idx) => ({
          ...img,
          sort_order: idx,
          is_main: idx === 0,
        })),
      };
    });

    try {
      const res = await productsApi.reorderImages(product.id, reorderedPayload);
      if (res.data) {
        queryClient.setQueryData<ProductDetailResponse>(['product', slug], (old) => {
          if (!old) return old;
          return {
            ...old,
            images: res.data,
          };
        });
      }
      setPhotoSuccess('Порядок фотографий сохранён');
      setTimeout(() => setPhotoSuccess(null), 2500);
    } catch (err: unknown) {
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      setPhotoError(err instanceof Error ? err.message : 'Ошибка при сохранении порядка фотографий');
    }
  };

  // Move image by direction button (← / →)
  const handleMoveImageRelative = async (imgId: string, direction: 'left' | 'right') => {
    if (!product?.id) return;
    const idx = images.findIndex((img) => img.id === imgId);
    if (idx === -1) return;
    const targetIdx = direction === 'left' ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= images.length) return;
    const targetId = images[targetIdx].id;
    await handleReorderImages(imgId, targetId);
  };

  // Move image to an empty color block
  const handleMoveImageToColorBlock = async (draggedId: string, targetColorKey: string) => {
    if (!product?.id) return;
    const sourceIdx = images.findIndex((img) => img.id === draggedId);
    if (sourceIdx === -1) return;

    const newImages = [...images];
    const [moved] = newImages.splice(sourceIdx, 1);
    moved.color = targetColorKey === '__GENERAL__' ? null : targetColorKey;
    newImages.push(moved);

    const reorderedPayload: ProductImageReorderItem[] = newImages.map((img, idx) => ({
      image_id: img.id,
      sort_order: idx,
      color: img.color ?? null,
    }));

    queryClient.setQueryData<ProductDetailResponse>(['product', slug], (old) => {
      if (!old) return old;
      return {
        ...old,
        images: newImages.map((img, idx) => ({
          ...img,
          sort_order: idx,
          is_main: idx === 0,
        })),
      };
    });

    try {
      const res = await productsApi.reorderImages(product.id, reorderedPayload);
      if (res.data) {
        queryClient.setQueryData<ProductDetailResponse>(['product', slug], (old) => {
          if (!old) return old;
          return {
            ...old,
            images: res.data,
          };
        });
      }
      setPhotoSuccess('Фото перемещено в новый цвет');
      setTimeout(() => setPhotoSuccess(null), 2500);
    } catch (err: unknown) {
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      setPhotoError(err instanceof Error ? err.message : 'Ошибка при перемещении фото');
    }
  };

  const handleAddExtraColorBlock = () => {
    const trimmed = newColorBlockName.trim();
    if (!trimmed) return;
    if (!extraColors.some((c) => c.toLowerCase() === trimmed.toLowerCase())) {
      setExtraColors((prev) => [...prev, trimmed]);
    }
    setNewColorBlockName('');
    setIsAddingColorBlock(false);
  };

  const deletePhotoMutation = useMutation({
    mutationFn: async (imageId: string) => {
      if (!product?.id) throw new Error('Товар не найден');
      return productsApi.deleteImage(product.id, imageId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError: (err: ApiError) => {
      setPhotoError(err.message || 'Ошибка удаления фотографии');
    },
  });

  // Variant Replenishment State
  const [updatingVariantId, setUpdatingVariantId] = useState<string | null>(null);
  const [isBulkUpdating, setIsBulkUpdating] = useState(false);
  const [variantNotice, setVariantNotice] = useState<string | null>(null);

  // Update single variant stock
  const handleUpdateVariantStock = async (variantId: string, newStock: number) => {
    setUpdatingVariantId(variantId);
    try {
      await productsApi.updateVariant(variantId, { stock_quantity: newStock });
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    } finally {
      setUpdatingVariantId(null);
    }
  };

  // Bulk replenish all variants by delta
  const handleBulkReplenish = async (delta: number) => {
    if (!variants.length) return;
    setIsBulkUpdating(true);
    setVariantNotice(null);
    try {
      for (const v of variants) {
        const nextQty = Math.max(0, (v.stock_quantity ?? 0) + delta);
        await productsApi.updateVariant(v.id, { stock_quantity: nextQty });
      }
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setVariantNotice(`✓ Все вариации успешно пополнены на +${delta} шт!`);
      setTimeout(() => setVariantNotice(null), 4000);
    } catch {
      setVariantNotice('× Ошибка массового пополнения остатков');
      setTimeout(() => setVariantNotice(null), 4000);
    } finally {
      setIsBulkUpdating(false);
    }
  };

  // Add new variant state
  const [isAddVariantOpen, setIsAddVariantOpen] = useState(false);
  const [newSku, setNewSku] = useState('');
  const [newSize, setNewSize] = useState('M');
  const [newColorName, setNewColorName] = useState('');
  const [newPriceOverride, setNewPriceOverride] = useState('');
  const [newStockQuantity, setNewStockQuantity] = useState('10');
  const [addVariantError, setAddVariantError] = useState<string | null>(null);
  const [addVariantSuccess, setAddVariantSuccess] = useState<string | null>(null);

  const createVariantMutation = useMutation({
    mutationFn: async () => {
      setAddVariantError(null);
      setAddVariantSuccess(null);
      if (!product?.id) throw new Error('Товар не найден');

      let resolvedSku = newSku.trim();
      if (!resolvedSku) {
        resolvedSku = generateSafeVariantSku(
          product.slug,
          newColorName,
          newSize,
          variants.length + 1
        );
      } else {
        const latinBase = transliterateToLatin(resolvedSku);
        const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
        resolvedSku = `${(latinBase || 'SKU').slice(0, 56)}-${rand}`;
      }

      return productsApi.createVariant(product.id, {
        sku: resolvedSku,
        size: newSize.trim() || null,
        color_name: newColorName.trim() || null,
        color: newColorName.trim() || null,
        price_override: newPriceOverride.trim() ? newPriceOverride.trim() : null,
        stock_quantity: parseInt(newStockQuantity, 10) || 0,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', slug] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setAddVariantSuccess('Вариация успешно добавлена!');
      setNewSku('');
      setNewColorName('');
      setNewPriceOverride('');
      setNewStockQuantity('10');
      setTimeout(() => {
        setAddVariantSuccess(null);
        setIsAddVariantOpen(false);
      }, 2000);
    },
    onError: (err: ApiError) => {
      setAddVariantError(err.message || 'Ошибка создания вариации');
    },
  });

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

    const selectedBrandId = brandChoice.startsWith('brand:')
      ? brandChoice.replace('brand:', '')
      : null;

    const resolvedBrand = isSelfWorked
      ? brand.trim() || 'self-worked'
      : brand.trim() || null;

    const payload: ProductUpdateRequest = {
      title: title.trim(),
      slug: productSlug.trim(),
      category_id: categoryId || undefined,
      brand_id: selectedBrandId,
      brand: resolvedBrand,
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
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
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

              <div className="space-y-4 pt-2 border-t border-[#3F2021]/15">
                <div>
                  <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                    АВТОР / БРЕНД ИЗДЕЛИЯ *
                  </label>
                  <select
                    value={brandChoice}
                    onChange={(e) => handleBrandChoiceChange(e.target.value)}
                    className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                  >
                    {activeMyBrands.map((b) => (
                      <option key={b.brand.id} value={`brand:${b.brand.id}`}>
                        {b.brand.name} ({b.role === 'representative' ? 'ПРЕДСТАВИТЕЛЬ' : 'МОДЕРАТОР'})
                      </option>
                    ))}
                    {hasGlobalCreatorProducts && (
                      <option value="self-worked">
                        self-worked (личный выпуск автора)
                      </option>
                    )}
                    {brandChoice.startsWith('custom:') && (
                      <option value={brandChoice}>
                        {product?.brand || 'Текущий бренд'}
                      </option>
                    )}
                  </select>
                </div>

                {isSelfWorked && (
                  <div>
                    <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1.5">
                      ИМЯ АВТОРА / ПОДПИСЬ (ОПЦИОНАЛЬНО)
                    </label>
                    <input
                      type="text"
                      value={brand}
                      onChange={(e) => setBrand(e.target.value)}
                      placeholder="self-worked"
                      className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
                    />
                  </div>
                )}
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
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none resize-y"
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
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
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
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
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
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
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
                  className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
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
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] p-3 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none resize-none"
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

          {/* Section: 5. НАЛИЧИЕ И ПОПОЛНЕНИЕ ТОВАРА / SKU */}
          <div className="border border-[#3F2021]/30 p-6 bg-[#F2E9DB] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#3F2021]/15 pb-2">
              <div>
                <div className="text-xs font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                  ( 5. СКЛАДСКИЕ ОСТАТКИ И ПОПОЛНЕНИЕ / SKU )
                </div>
                <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mt-0.5">
                  Управление наличием по размерам и цветам. Изменение остатков сохраняется моментально.
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold bg-[#3F2021] text-[#F2E9DB] px-2.5 py-1">
                  ВСЕГО: {totalStock} ШТ
                </span>
                <span className="text-[11px] font-mono text-[#3F2021]/70">
                  ({variants.length} ВАР.)
                </span>
              </div>
            </div>

            {variantNotice && (
              <div className="p-3 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-wider text-center font-semibold rounded-none">
                {variantNotice}
              </div>
            )}

            {/* Bulk Replenish Bar */}
            {variants.length > 0 && (
              <div className="bg-[#FFFFFF] border border-[#3F2021]/20 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-none">
                <div className="text-xs font-sans uppercase font-semibold text-[#3F2021]">
                  ПОПОЛНИТЬ ВСЕ РАЗМЕРЫ НА:
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {[5, 10, 25, 50, 100].map((delta) => (
                    <button
                      key={delta}
                      type="button"
                      disabled={isBulkUpdating}
                      onClick={() => handleBulkReplenish(delta)}
                      className="px-3 py-1.5 bg-[#F2E9DB]/60 hover:bg-[#3F2021] hover:text-[#F2E9DB] border border-[#3F2021]/40 text-xs font-mono font-semibold transition-colors rounded-none disabled:opacity-50 cursor-pointer"
                    >
                      +{delta} ШТ
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Variants List */}
            {variants.length === 0 ? (
              <div className="bg-[#FFFFFF] border border-[#3F2021]/30 p-8 text-center space-y-3">
                <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70">
                  У товара пока нет созданных вариаций / размеров
                </div>
                <button
                  type="button"
                  onClick={() => setIsAddVariantOpen(true)}
                  className="bg-[#3F2021] text-[#F2E9DB] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold rounded-none"
                >
                  + ДОБАВИТЬ ПЕРВУЮ ВАРИАЦИЮ
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {variants.map((v) => (
                  <VariantReplenishCard
                    key={v.id}
                    variant={v}
                    onUpdateStock={handleUpdateVariantStock}
                    isUpdating={updatingVariantId === v.id}
                  />
                ))}
              </div>
            )}

            {/* Add Variant Toggle / Form */}
            <div className="pt-2 border-t border-[#3F2021]/15">
              {!isAddVariantOpen ? (
                <button
                  type="button"
                  onClick={() => {
                    setIsAddVariantOpen(true);
                    setNewSku(
                      generateSafeVariantSku(
                        product?.slug || 'item',
                        newColorName,
                        newSize,
                        variants.length + 1
                      )
                    );
                  }}
                  className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none cursor-pointer"
                >
                  + ДОБАВИТЬ НОВУЮ ВАРИАЦИЮ / РАЗМЕР
                </button>
              ) : (
                <div className="bg-[#FFFFFF] border border-[#3F2021] p-5 space-y-4 rounded-none">
                  <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-2">
                    <span className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                      ( НОВАЯ ВАРИАЦИЯ )
                    </span>
                    <button
                      type="button"
                      onClick={() => setIsAddVariantOpen(false)}
                      className="text-xs text-[#3F2021]/60 hover:text-[#3F2021] px-1 font-mono cursor-pointer"
                    >
                      × ЗАКРЫТЬ
                    </button>
                  </div>

                  {addVariantError && (
                    <div className="p-3 text-xs text-red-700 bg-red-100/60 border border-red-700/20 font-sans">
                      {addVariantError}
                    </div>
                  )}
                  {addVariantSuccess && (
                    <div className="p-3 text-xs text-emerald-800 bg-emerald-100/60 border border-emerald-800/20 font-sans">
                      {addVariantSuccess}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1">
                        АРТИКУЛ (SKU) *
                      </label>
                      <input
                        type="text"
                        value={newSku}
                        onChange={(e) => setNewSku(e.target.value)}
                        placeholder="ITEM-BLACK-M"
                        className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] p-2 text-xs font-mono tracking-wider text-[#3F2021] outline-none rounded-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1">
                        РАЗМЕР (SIZE)
                      </label>
                      <div className="flex gap-1">
                        <select
                          value={newSize}
                          onChange={(e) => setNewSize(e.target.value)}
                          className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] p-2 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
                        >
                          {PRESET_SIZES.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1">
                        ЦВЕТ (COLOR NAME)
                      </label>
                      <input
                        type="text"
                        value={newColorName}
                        onChange={(e) => setNewColorName(e.target.value)}
                        placeholder="ЧЕРНЫЙ / BLACK"
                        className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] p-2 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021] mb-1">
                        НАЧАЛЬНЫЙ ОСТАТОК (ШТ)
                      </label>
                      <input
                        type="number"
                        min="0"
                        value={newStockQuantity}
                        onChange={(e) => setNewStockQuantity(e.target.value)}
                        className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] p-2 text-xs font-mono font-bold tracking-wider text-[#3F2021] outline-none rounded-none"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-2">
                    <button
                      type="button"
                      disabled={createVariantMutation.isPending}
                      onClick={() => createVariantMutation.mutate()}
                      className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none disabled:opacity-50 cursor-pointer"
                    >
                      {createVariantMutation.isPending ? 'ДОБАВЛЕНИЕ...' : '+ ДОБАВИТЬ ВАРИАЦИЮ'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsAddVariantOpen(false)}
                      className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2.5 text-xs font-sans uppercase tracking-wider transition-colors rounded-none cursor-pointer"
                    >
                      ОТМЕНА
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Section 6: Photos & Gallery with DnD and Color Blocks */}
          <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-6 rounded-none">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3F2021]/20 pb-3">
              <div>
                <span className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                  ( 6. ФОТОГРАФИИ И ГАЛЕРЕЯ )
                </span>
                <p className="text-[11px] font-sans text-[#3F2021]/60 uppercase tracking-wider mt-0.5">
                  Группировка по цветам и Drag-and-Drop сортировка карточек
                </p>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs font-mono uppercase text-[#3F2021]/80">
                  ВСЕГО ФОТО: {images.length}
                </span>

                {!isAddingColorBlock ? (
                  <button
                    type="button"
                    onClick={() => setIsAddingColorBlock(true)}
                    className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none"
                  >
                    + ДОБАВИТЬ ЦВЕТ
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="НАЗВАНИЕ ЦВЕТА"
                      value={newColorBlockName}
                      onChange={(e) => setNewColorBlockName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddExtraColorBlock();
                        }
                      }}
                      className="bg-[#FFFFFF] border border-[#3F2021]/40 px-2.5 py-1 text-xs font-sans tracking-wider outline-none rounded-none"
                    />
                    <button
                      type="button"
                      onClick={handleAddExtraColorBlock}
                      className="bg-[#3F2021] text-[#F2E9DB] px-2.5 py-1 text-xs font-sans uppercase font-semibold rounded-none"
                    >
                      ✓
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setIsAddingColorBlock(false);
                        setNewColorBlockName('');
                      }}
                      className="text-xs font-sans text-[#3F2021]/60 hover:text-[#3F2021] px-1"
                    >
                      ×
                    </button>
                  </div>
                )}
              </div>
            </div>

            {uploadProgress && (
              <div className="p-3 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-wider text-center font-semibold rounded-none">
                {uploadProgress}
              </div>
            )}
            {photoError && (
              <div className="p-3 text-xs text-red-700 bg-red-100/60 border border-red-700/20 font-sans">
                {photoError}
              </div>
            )}
            {photoSuccess && (
              <div className="p-3 text-xs text-emerald-800 bg-emerald-100/60 border border-emerald-800/20 font-sans">
                {photoSuccess}
              </div>
            )}

            {/* Color Blocks */}
            <div className="space-y-6">
              {colorBlocksList.map((colorKey) => {
                const isGeneral = colorKey === '__GENERAL__';
                const displayName = isGeneral ? 'ОБЩИЕ ФОТО (БЕЗ ЦВЕТА)' : colorKey;
                const colorPhotos = images.filter((img) =>
                  isGeneral
                    ? !img.color || !img.color.trim()
                    : img.color?.trim().toLowerCase() === colorKey.trim().toLowerCase()
                );

                return (
                  <div
                    key={colorKey}
                    className="border border-[#3F2021]/30 p-5 bg-[#F2E9DB]/20 space-y-4 rounded-none"
                  >
                    {/* Color Header */}
                    <div className="flex items-center justify-between gap-3 border-b border-[#3F2021]/20 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                          ФОТОГРАФИИ ЦВЕТА «{displayName}» ({colorPhotos.length})
                        </span>
                      </div>

                      <label className="cursor-pointer bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3 py-1 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none">
                        + ВЫБРАТЬ ФАЙЛЫ
                        <input
                          type="file"
                          multiple
                          accept="image/jpeg,image/png,image/webp"
                          disabled={isUploadingPhotos}
                          onChange={(e) => {
                            handleUploadFilesForColor(colorKey, e.target.files);
                            e.target.value = '';
                          }}
                          className="hidden"
                        />
                      </label>
                    </div>

                    {/* Photos Upload Zone */}
                    {colorPhotos.length === 0 ? (
                      <label
                        onDragOver={(e) => {
                          e.preventDefault();
                          setDragOverColorKey(colorKey);
                        }}
                        onDragLeave={() => {
                          if (dragOverColorKey === colorKey) setDragOverColorKey(null);
                        }}
                        onDrop={(e) => {
                          e.preventDefault();
                          setDragOverColorKey(null);
                          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                            handleUploadFilesForColor(colorKey, e.dataTransfer.files);
                          } else if (draggedImageId) {
                            handleMoveImageToColorBlock(draggedImageId, colorKey);
                            setDraggedImageId(null);
                          }
                        }}
                        className={`block border-2 border-dashed p-6 text-center cursor-pointer transition-colors rounded-none ${
                          dragOverColorKey === colorKey
                            ? 'border-[#3F2021] bg-[#3F2021]/10'
                            : 'border-[#3F2021]/30 hover:border-[#3F2021]'
                        }`}
                      >
                        <input
                          type="file"
                          multiple
                          accept="image/jpeg,image/png,image/webp"
                          disabled={isUploadingPhotos}
                          onChange={(e) => {
                            handleUploadFilesForColor(colorKey, e.target.files);
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
                      <div
                        className="space-y-3"
                        onDragOver={(e) => {
                          if (e.dataTransfer.types.includes('Files')) {
                            e.preventDefault();
                            e.dataTransfer.dropEffect = 'copy';
                          }
                        }}
                        onDrop={(e) => {
                          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                            e.preventDefault();
                            handleUploadFilesForColor(colorKey, e.dataTransfer.files);
                          }
                        }}
                      >
                        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3">
                          {colorPhotos.map((img) => {
                            const isFirstOverall = images[0]?.id === img.id;
                            const isDraggingThis = draggedImageId === img.id;
                            const isHoveringThis = dragOverImageId === img.id;
                            const overallIdx = images.findIndex((i) => i.id === img.id);

                            return (
                              <div
                                key={img.id}
                                draggable={true}
                                onDragStart={(e) => {
                                  e.dataTransfer.setData('text/plain', img.id);
                                  e.dataTransfer.effectAllowed = 'move';
                                  setDraggedImageId(img.id);
                                }}
                                onDragEnd={() => {
                                  setDraggedImageId(null);
                                  setDragOverImageId(null);
                                }}
                                onDragOver={(e) => {
                                  if (draggedImageId) {
                                    e.preventDefault();
                                    e.dataTransfer.dropEffect = 'move';
                                  }
                                }}
                                onDragEnter={() => {
                                  if (draggedImageId && draggedImageId !== img.id) {
                                    setDragOverImageId(img.id);
                                  }
                                }}
                                onDragLeave={() => {
                                  if (dragOverImageId === img.id) {
                                    setDragOverImageId(null);
                                  }
                                }}
                                onDrop={(e) => {
                                  e.preventDefault();
                                  if (draggedImageId && draggedImageId !== img.id) {
                                    handleReorderImages(draggedImageId, img.id);
                                  }
                                  setDraggedImageId(null);
                                  setDragOverImageId(null);
                                }}
                                className={`relative aspect-[2/3] bg-[#E5DBCB] border overflow-hidden group flex flex-col justify-between cursor-grab active:cursor-grabbing transition-all rounded-none ${
                                  isDraggingThis
                                    ? 'opacity-30 border-dashed border-[#3F2021]'
                                    : isHoveringThis
                                    ? 'border-2 border-[#3F2021] scale-[1.03] bg-[#3F2021]/15 ring-2 ring-[#3F2021]'
                                    : 'border-[#3F2021]/30 hover:border-[#3F2021]'
                                }`}
                              >
                                <img
                                  src={img.url}
                                  alt={img.alt_text || product?.title || 'Фото товара'}
                                  className="w-full h-full object-cover"
                                />

                                {/* Main Cover Badge */}
                                {isFirstOverall && (
                                  <span className="absolute top-1 left-1 bg-[#3F2021] text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase font-bold tracking-wider z-10 select-none">
                                    ОСНОВНОЕ
                                  </span>
                                )}

                                {/* Action Overlay */}
                                <div className="absolute inset-0 bg-[#3F2021]/70 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-1.5 text-[#F2E9DB]">
                                  <div className="flex justify-between items-center text-[10px] font-mono">
                                    <span className="select-none">#{overallIdx + 1}</span>
                                    <button
                                      type="button"
                                      disabled={deletePhotoMutation.isPending}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        deletePhotoMutation.mutate(img.id);
                                      }}
                                      className="hover:text-sf-coral font-bold px-1"
                                      title="Удалить фото"
                                    >
                                      ×
                                    </button>
                                  </div>

                                  <div className="flex justify-center gap-2 text-xs font-mono">
                                    <button
                                      type="button"
                                      disabled={overallIdx === 0}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleMoveImageRelative(img.id, 'left');
                                      }}
                                      className="px-2 py-0.5 bg-[#F2E9DB] text-[#3F2021] disabled:opacity-30 hover:bg-[#FFFFFF]"
                                      title="Переместить влево"
                                    >
                                      ←
                                    </button>
                                    <button
                                      type="button"
                                      disabled={overallIdx === images.length - 1}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleMoveImageRelative(img.id, 'right');
                                      }}
                                      className="px-2 py-0.5 bg-[#F2E9DB] text-[#3F2021] disabled:opacity-30 hover:bg-[#FFFFFF]"
                                      title="Переместить вправо"
                                    >
                                      →
                                    </button>
                                  </div>
                                </div>
                              </div>
                            );
                          })}

                          {/* Dropzone tile to add more photos */}
                          <label
                            onDragOver={(e) => {
                              if (e.dataTransfer.types.includes('Files')) {
                                e.preventDefault();
                                e.dataTransfer.dropEffect = 'copy';
                              }
                            }}
                            onDrop={(e) => {
                              if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                                e.preventDefault();
                                handleUploadFilesForColor(colorKey, e.dataTransfer.files);
                              }
                            }}
                            className="border-2 border-dashed border-[#3F2021]/30 aspect-[2/3] flex flex-col items-center justify-center p-3 text-center cursor-pointer hover:border-[#3F2021] hover:bg-[#3F2021]/5 transition-colors bg-[#F2E9DB]/20 rounded-none"
                          >
                            <input
                              type="file"
                              multiple
                              accept="image/jpeg,image/png,image/webp"
                              disabled={isUploadingPhotos}
                              onChange={(e) => {
                                handleUploadFilesForColor(colorKey, e.target.files);
                                e.target.value = '';
                              }}
                              className="hidden"
                            />
                            <span className="text-xl font-mono text-[#3F2021]">+</span>
                            <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mt-1">
                              ДОБАВИТЬ ЕЩЁ
                            </span>
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
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

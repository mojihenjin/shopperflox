import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { ProductResponse } from '../types/api';
import { formatImageUrl, formatPrice } from '../utils/format';

export type GridColumns = 2 | 4 | 6 | 8;

export interface ProductCardProps {
  product: ProductResponse;
  images?: string[];
  isFavorite?: boolean;
  onToggleFavorite?: (productId: string) => void;
  onAddToCart?: (product: ProductResponse, e: React.MouseEvent) => void;
  columns?: GridColumns;
  variationsText?: string;
  totalStock?: number;
  className?: string;
}

export function ProductCard({
  product,
  images = [],
  isFavorite = false,
  onToggleFavorite,
  onAddToCart,
  columns = 4,
  variationsText,
  totalStock,
  className = '',
}: ProductCardProps) {
  const navigate = useNavigate();
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [imageError, setImageError] = useState(false);
  const timerRef = useRef<number | null>(null);

  // Gallery resolution: prioritize explicit images prop, then product.images from API, then attributes.images
  const apiImages = (product.images && Array.isArray(product.images))
    ? product.images.map((img) => img.url)
    : [];
  const rawImages: string[] =
    images.length > 0
      ? images
      : apiImages.length > 0
      ? apiImages
      : (product.attributes?.images as string[] | undefined) || [];
  const gallery = rawImages.filter(
    (img) => Boolean(img && typeof img === 'string' && !img.startsWith('data:image/svg+xml'))
  );

  // Stop interval helper
  const clearHoverTimer = () => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearHoverTimer();
    };
  }, []);

  const handleMouseEnter = () => {
    if (gallery.length > 1) {
      clearHoverTimer();
      // Immediately switch to the second image (index = 1)
      setActiveImageIndex(1);
      // Start 3000ms cycling interval
      timerRef.current = window.setInterval(() => {
        setActiveImageIndex((prev) => (prev + 1) % gallery.length);
      }, 3000);
    }
  };

  const handleMouseLeave = () => {
    clearHoverTimer();
    // Return to first image (index = 0)
    setActiveImageIndex(0);
  };

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onAddToCart) {
      onAddToCart(product, e);
    } else {
      navigate(`/products/${product.slug}`);
    }
  };

  const isCompact = columns >= 6;
  const displayVariations =
    variationsText ||
    (product.attributes?.sizes && Array.isArray(product.attributes.sizes) && product.attributes.sizes.length > 0
      ? `РАЗМЕРЫ: ${(product.attributes.sizes as string[]).join(' · ')}`
      : product.attributes?.colors && Array.isArray(product.attributes.colors) && product.attributes.colors.length > 0
      ? `${(product.attributes.colors as unknown[]).length} ЦВЕТА`
      : product.attributes?.variants_count
      ? `${product.attributes.variants_count} ВАРИАЦИЙ`
      : 'В НАЛИЧИИ');

  const isOutOfStock =
    totalStock !== undefined
      ? totalStock === 0
      : product.attributes?.total_stock !== undefined
      ? Number(product.attributes.total_stock) === 0
      : (product as { stock_quantity?: number }).stock_quantity !== undefined
      ? Number((product as { stock_quantity?: number }).stock_quantity) === 0
      : false;

  return (
    <div
      className={`group relative flex flex-col rounded-none overflow-hidden ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* 2:3 Portrait image container */}
      <div className="relative aspect-[2/3] w-full bg-[#E8DEC9] overflow-hidden rounded-none">
        {gallery.length > 0 && !imageError ? (
          <Link to={`/products/${product.slug}`} className="block w-full h-full">
            <img
              src={formatImageUrl(gallery[activeImageIndex], product.title)}
              alt={product.title}
              className="w-full h-full object-cover transition-opacity duration-300"
              loading="lazy"
              onError={() => setImageError(true)}
            />
          </Link>
        ) : (
          <Link
            to={`/products/${product.slug}`}
            className="w-full h-full bg-[#E8DEC9] border border-[#3F2021]/20 flex flex-col items-center justify-center p-6 text-center select-none group-hover:bg-[#dfd3bc] transition-colors"
          >
            <span className="font-serif text-sm sm:text-base uppercase tracking-wider text-[#3F2021] line-clamp-3 leading-snug">
              {product.title}
            </span>
            <span className="font-sans text-[10px] tracking-[0.2em] text-[#5F5F5F] uppercase mt-3 font-semibold">
              SHOPPERFLOX
            </span>
          </Link>
        )}

        {/* Favorite toggle badge */}
        {onToggleFavorite && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onToggleFavorite(product.id);
            }}
            className={`absolute top-2 right-2 bg-[#F2E9DB]/90 hover:bg-[#F2E9DB] text-[#3F2021] font-sans font-semibold border border-[#3F2021]/30 transition-colors uppercase ${
              isCompact ? 'px-1.5 py-0.5 text-[9px]' : 'px-2 py-1 text-[11px]'
            }`}
            title={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
          >
            {isFavorite ? '♥' : '♡'}
          </button>
        )}

        {/* Brand tag on photo if present */}
        {product.brand && (
          <div className="absolute top-2 left-2 bg-[#3F2021]/80 text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans uppercase tracking-widest">
            {product.brand}
          </div>
        )}

        {/* Minimalist 2px multi-segment indicator along bottom edge */}
        {gallery.length > 1 && (
          <div className="absolute bottom-0 left-0 right-0 h-[2px] flex z-10">
            {gallery.map((_, idx) => (
              <div
                key={idx}
                className={`flex-1 h-full transition-colors duration-300 ${
                  activeImageIndex === idx ? 'bg-[#3F2021]' : 'bg-[#3F2021]/20'
                }`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Bottom Information Block: #FFFFFF background */}
      <div
        className={`bg-[#FFFFFF] flex flex-col justify-between flex-1 ${
          isCompact ? 'p-2.5 gap-2' : 'p-4 gap-3'
        }`}
      >
        <div className="space-y-1">
          {/* Author / Brand in text-[#3F2021]/60 with LIMITED badge */}
          <div
            className={`font-sans uppercase text-[#3F2021]/60 font-semibold flex items-center justify-between gap-1 ${
              isCompact ? 'text-[9px] tracking-wider' : 'text-[11px] tracking-widest'
            }`}
          >
            {product.brand_slug ? (
              <Link
                to={`/brands/${product.brand_slug}`}
                onClick={(e) => e.stopPropagation()}
                className="truncate hover:underline hover:text-[#3F2021]"
              >
                {product.brand || 'ShopperFlox'}
              </Link>
            ) : (
              <span className="truncate">{product.brand || 'ShopperFlox'}</span>
            )}
            {product.is_limited && (
              <span className="bg-[#3F2021] text-[#F2E9DB] px-1.5 py-0.5 text-[9px] font-sans font-bold uppercase tracking-wider rounded-none whitespace-nowrap">
                LIMITED
              </span>
            )}
          </div>

          {/* Product Title in text-[#3F2021] */}
          <Link
            to={`/products/${product.slug}`}
            className={`font-serif uppercase text-[#3F2021] group-hover:opacity-75 transition-opacity truncate block ${
              isCompact ? 'text-[13px]' : 'text-[15px] sm:text-[16px]'
            }`}
          >
            {product.title}
          </Link>
        </div>

        {/* Variations row and price in text-[#3F2021] */}
        <div
          className={`flex items-baseline justify-between gap-1 text-[#3F2021] font-sans ${
            isCompact ? 'text-[11px]' : 'text-[13px]'
          }`}
        >
          <span className="truncate text-[#3F2021]/70">{displayVariations}</span>
          <span className="font-bold whitespace-nowrap text-[#3F2021]">
            {formatPrice(product.base_price)}
          </span>
        </div>

        {/* Full-width Add to Cart button */}
        <button
          type="button"
          disabled={isOutOfStock}
          onClick={handleAddToCart}
          className={`w-full rounded-none uppercase tracking-[0.08em] transition-colors ${
            isOutOfStock
              ? 'bg-[#3F2021]/40 text-[#F2E9DB] cursor-not-allowed'
              : 'bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516]'
          } ${isCompact ? 'py-1.5 text-[10px]' : 'py-2.5 text-xs font-semibold'}`}
        >
          {isOutOfStock
            ? product.is_limited
              ? 'РАСПРОДАНО'
              : 'ОЖИДАЕТСЯ'
            : 'В КОРЗИНУ ↗'}
        </button>
      </div>
    </div>
  );
}

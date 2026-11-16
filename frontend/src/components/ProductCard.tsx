import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { ProductResponse } from '../types/api';
import { formatImageUrl, formatPrice } from '../utils/format';

interface ProductCardProps {
  product: ProductResponse;
  images?: string[];
  isFavorite?: boolean;
  onToggleFavorite?: (productId: string) => void;
  className?: string;
}

export function ProductCard({
  product,
  images = [],
  isFavorite = false,
  onToggleFavorite,
  className = '',
}: ProductCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Determine images
  const primaryImg = images[0] || null;
  const secondaryImg = images[1] || primaryImg;

  return (
    <div
      className={`group relative flex flex-col ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 2:3 Portrait image container */}
      <div className="relative aspect-[2/3] w-full bg-[#E5DBCB] overflow-hidden border border-amov-dark/15">
        <Link to={`/products/${product.slug}`} className="block w-full h-full">
          <img
            src={formatImageUrl(isHovered && secondaryImg ? secondaryImg : primaryImg, product.title)}
            alt={product.title}
            className="w-full h-full object-cover transition-opacity duration-300"
            loading="lazy"
          />
        </Link>

        {/* Favorite toggle badge */}
        {onToggleFavorite && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onToggleFavorite(product.id);
            }}
            className="absolute top-2 right-2 bg-amov-cream/90 hover:bg-amov-cream text-amov-dark px-2 py-1 text-[11px] font-sans font-semibold border border-amov-dark/30 transition-colors uppercase"
            title={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
          >
            {isFavorite ? '♥ (СОХРАНЕНО)' : '♡ (В ИЗБРАННОЕ)'}
          </button>
        )}

        {/* Stock / New tag */}
        {product.brand && (
          <div className="absolute bottom-2 left-2 bg-amov-dark/80 text-amov-cream px-2 py-0.5 text-[10px] font-sans uppercase tracking-widest">
            {product.brand}
          </div>
        )}
      </div>

      {/* Product metadata */}
      <div className="pt-3 pb-1 flex flex-col">
        <Link
          to={`/products/${product.slug}`}
          className="font-serif text-[15px] sm:text-[16px] uppercase tracking-wide text-amov-dark group-hover:opacity-75 transition-opacity line-clamp-1"
        >
          {product.title}
        </Link>

        <div className="mt-1 flex items-baseline justify-between text-[13px] font-sans">
          <span className="font-semibold text-amov-black">
            {formatPrice(product.base_price)}
          </span>
          <span className="text-[11px] text-amov-muted uppercase tracking-wider group-hover:text-amov-dark transition-colors">
            СМОТРЕТЬ ↗
          </span>
        </div>
      </div>
    </div>
  );
}

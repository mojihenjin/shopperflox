import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { cartApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { formatPrice } from '../utils/format';
import { formatApiError } from '../utils/errorMapper';

export function CartPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const [cartError, setCartError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: () => cartApi.get(),
    enabled: isAuthenticated,
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ variantId, quantity }: { variantId: string; quantity: number }) =>
      cartApi.updateItem(variantId, quantity),
    onMutate: () => setCartError(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
    onError: (err) => {
      setCartError(formatApiError(err, 'ОШИБКА ОБНОВЛЕНИЯ КОЛИЧЕСТВА'));
    },
  });

  const removeItemMutation = useMutation({
    mutationFn: (variantId: string) => cartApi.removeItem(variantId),
    onMutate: () => setCartError(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
    onError: (err) => {
      setCartError(formatApiError(err, 'ОШИБКА УДАЛЕНИЯ ТОВАРА ИЗ КОРЗИНЫ'));
    },
  });

  const clearCartMutation = useMutation({
    mutationFn: () => cartApi.clear(),
    onMutate: () => setCartError(null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
    onError: (err) => {
      setCartError(formatApiError(err, 'ОШИБКА ОЧИСТКИ КОРЗИНЫ'));
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="max-w-[500px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-sf-dark">
          КОРЗИНА
        </h1>
        <p className="mt-3 text-xs font-sans uppercase tracking-wider text-sf-muted">
          Для оформления заказа и просмотра корзины необходимо авторизоваться
        </p>
        <button
          type="button"
          onClick={() => navigate('/login')}
          className="mt-6 inline-block bg-sf-dark text-sf-cream px-8 py-3 text-xs font-sans uppercase tracking-widest"
        >
          ВОЙТИ В АККАУНТ ↗
        </button>
      </div>
    );
  }

  const items = data?.data?.items || [];
  const totalAmount = data?.data?.total_amount || '0';

  return (
    <div className="w-full max-w-none px-4 md:px-8 py-12 md:py-16">
      <div className="border-b border-sf-dark/20 pb-6 mb-10 flex items-end justify-between">
        <div>
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
            ( ВАШ ЗАКАЗ )
          </span>
          <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-dark mt-1">
            КОРЗИНА ПОКУПОК
          </h1>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={() => clearCartMutation.mutate()}
            className="text-xs font-sans uppercase tracking-wider text-sf-muted hover:text-sf-dark underline underline-offset-4"
          >
            ОЧИСТИТЬ КОРЗИНУ ×
          </button>
        )}
      </div>

      {cartError && (
        <div className="mb-8 p-4 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-wider flex items-center justify-between whitespace-pre-line rounded-none">
          <span>{cartError}</span>
          <button
            type="button"
            onClick={() => setCartError(null)}
            className="text-[#F2E9DB]/70 hover:text-[#F2E9DB] text-sm ml-4 cursor-pointer"
          >
            ×
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-sf-muted">
          ( ЗАГРУЗКА КОРЗИНЫ... )
        </div>
      ) : items.length === 0 ? (
        <div className="py-20 text-center border border-sf-dark/20 p-8">
          <div className="font-serif text-2xl uppercase tracking-wider text-sf-dark">
            ВАША КОРЗИНА ПУСТА
          </div>
          <p className="mt-2 text-xs font-sans uppercase tracking-wider text-sf-muted">
            Выберите понравившиеся товары в нашем каталоге
          </p>
          <Link
            to="/catalog"
            className="mt-6 inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
          >
            ПЕРЕЙТИ В КАТАЛОГ ↗
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* Items list */}
          <div className="lg:col-span-8 divide-y divide-sf-dark/15 border-y border-sf-dark/15">
            {items.map((item) => (
              <div key={item.id} className="py-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  {/* Thumbnail aspect-[2/3] */}
                  {item.product_slug ? (
                    <Link
                      to={`/products/${item.product_slug}`}
                      className="shrink-0 group block"
                    >
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.title || 'Товар'}
                          className="w-14 sm:w-16 aspect-[2/3] object-cover border border-[#3F2021]/20 group-hover:border-[#3F2021] transition-colors rounded-none"
                        />
                      ) : (
                        <div className="w-14 sm:w-16 aspect-[2/3] bg-[#E8DEC9] border border-[#3F2021]/20 flex flex-col items-center justify-center p-1 text-center group-hover:border-[#3F2021] transition-colors rounded-none select-none">
                          <span className="font-serif text-xs font-bold text-[#3F2021]">
                            {(item.title || 'SF')[0].toUpperCase()}
                          </span>
                          <span className="text-[7px] font-sans tracking-widest text-[#5F5F5F] mt-0.5">
                            SF
                          </span>
                        </div>
                      )}
                    </Link>
                  ) : item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.title || 'Товар'}
                      className="w-14 sm:w-16 aspect-[2/3] object-cover border border-[#3F2021]/20 shrink-0 rounded-none"
                    />
                  ) : (
                    <div className="w-14 sm:w-16 aspect-[2/3] bg-[#E8DEC9] border border-[#3F2021]/20 flex flex-col items-center justify-center p-1 text-center shrink-0 rounded-none select-none">
                      <span className="font-serif text-xs font-bold text-[#3F2021]">
                        {(item.title || 'SF')[0].toUpperCase()}
                      </span>
                    </div>
                  )}

                  <div className="space-y-1">
                    {item.product_slug ? (
                      <Link
                        to={`/products/${item.product_slug}`}
                        className="font-serif text-lg uppercase text-sf-dark hover:underline underline-offset-2 block"
                      >
                        {item.title || 'ТОВАР'}
                      </Link>
                    ) : (
                      <div className="font-serif text-lg uppercase text-sf-dark">
                        {item.title || 'ТОВАР'}
                      </div>
                    )}
                    <div className="text-xs font-sans uppercase text-sf-muted flex items-center gap-3 flex-wrap">
                      {item.sku && <span>SKU: {item.sku}</span>}
                      {item.color_name && <span>ЦВЕТ: {item.color_name}</span>}
                      {item.size && <span>РАЗМЕР: {item.size}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between w-full sm:w-auto gap-6">
                  {/* Quantity controls */}
                  <div className="flex items-center border border-sf-dark">
                    <button
                      type="button"
                      disabled={item.quantity <= 1}
                      onClick={() =>
                        updateItemMutation.mutate({
                          variantId: item.variant_id,
                          quantity: item.quantity - 1,
                        })
                      }
                      className="px-2.5 py-0.5 text-xs font-sans hover:bg-sf-dark hover:text-sf-cream transition-colors disabled:opacity-30"
                    >
                      −
                    </button>
                    <span className="px-3 py-0.5 text-xs font-mono font-bold">
                      {item.quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        updateItemMutation.mutate({
                          variantId: item.variant_id,
                          quantity: item.quantity + 1,
                        })
                      }
                      className="px-2.5 py-0.5 text-xs font-sans hover:bg-sf-dark hover:text-sf-cream transition-colors"
                    >
                      +
                    </button>
                  </div>

                  <div className="text-right">
                    <div className="font-sans font-bold text-sm text-sf-black">
                      {formatPrice(item.total_price)}
                    </div>
                    <div className="text-[10px] text-sf-muted">
                      {formatPrice(item.unit_price)} / шт.
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => removeItemMutation.mutate(item.variant_id)}
                    className="text-sf-muted hover:text-sf-dark text-sm px-1"
                    title="Удалить"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Checkout summary */}
          <div className="lg:col-span-4">
            <div className="border border-sf-dark p-6 bg-sf-cream/50 space-y-5">
              <h2 className="font-serif text-xl uppercase tracking-wider text-sf-dark">
                СУММА ЗАКАЗА
              </h2>

              <div className="space-y-2 text-xs font-sans uppercase tracking-wider text-sf-dark border-b border-sf-dark/15 pb-4">
                <div className="flex justify-between">
                  <span>ТОВАРЫ ({items.reduce((s, i) => s + i.quantity, 0)}):</span>
                  <span>{formatPrice(totalAmount)}</span>
                </div>
              </div>

              <div className="flex justify-between items-baseline text-sf-dark">
                <span className="font-sans font-bold text-xs uppercase tracking-wider">
                  ИТОГО К ОПЛАТЕ:
                </span>
                <span className="font-serif text-2xl font-bold">
                  {formatPrice(totalAmount)}
                </span>
              </div>

              <button
                type="button"
                onClick={() => navigate('/checkout')}
                className="w-full bg-sf-dark text-sf-cream hover:bg-sf-black py-3.5 text-xs font-sans font-semibold uppercase tracking-widest transition-colors"
              >
                ПЕРЕЙТИ К ОФОРМЛЕНИЮ ↗
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

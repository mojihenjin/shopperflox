import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { cartApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { formatPrice } from '../utils/format';

export function CartPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: () => cartApi.get(),
    enabled: isAuthenticated,
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ variantId, quantity }: { variantId: string; quantity: number }) =>
      cartApi.updateItem(variantId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });

  const removeItemMutation = useMutation({
    mutationFn: (variantId: string) => cartApi.removeItem(variantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });

  const clearCartMutation = useMutation({
    mutationFn: () => cartApi.clear(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="max-w-[500px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-amov-dark">
          КОРЗИНА
        </h1>
        <p className="mt-3 text-xs font-sans uppercase tracking-wider text-amov-muted">
          Для оформления заказа и просмотра корзины необходимо авторизоваться
        </p>
        <button
          type="button"
          onClick={() => navigate('/login')}
          className="mt-6 inline-block bg-amov-dark text-amov-cream px-8 py-3 text-xs font-sans uppercase tracking-widest"
        >
          ВОЙТИ В АККАУНТ ↗
        </button>
      </div>
    );
  }

  const items = data?.data?.items || [];
  const totalAmount = data?.data?.total_amount || '0';

  return (
    <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-12 md:py-16">
      <div className="border-b border-amov-dark/20 pb-6 mb-10 flex items-end justify-between">
        <div>
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-amov-muted">
            ( ВАШ ЗАКАЗ )
          </span>
          <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-amov-dark mt-1">
            КОРЗИНА ПОКУПОК
          </h1>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={() => clearCartMutation.mutate()}
            className="text-xs font-sans uppercase tracking-wider text-amov-muted hover:text-amov-dark underline underline-offset-4"
          >
            ОЧИСТИТЬ КОРЗИНУ ×
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-amov-muted">
          ( ЗАГРУЗКА КОРЗИНЫ... )
        </div>
      ) : items.length === 0 ? (
        <div className="py-20 text-center border border-amov-dark/20 p-8">
          <div className="font-serif text-2xl uppercase tracking-wider text-amov-dark">
            ВАША КОРЗИНА ПУСТА
          </div>
          <p className="mt-2 text-xs font-sans uppercase tracking-wider text-amov-muted">
            Выберите понравившиеся модели солнцезащитных очков в нашем каталоге
          </p>
          <Link
            to="/"
            className="mt-6 inline-block bg-amov-dark text-amov-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
          >
            ПЕРЕЙТИ В КАТАЛОГ ↗
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* Items list */}
          <div className="lg:col-span-8 divide-y divide-amov-dark/15 border-y border-amov-dark/15">
            {items.map((item) => (
              <div key={item.id} className="py-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="font-serif text-lg uppercase text-amov-dark">
                    {item.title || 'СОЛНЦЕЗАЩИТНЫЕ ОЧКИ'}
                  </div>
                  <div className="text-xs font-sans uppercase text-amov-muted flex items-center gap-3">
                    {item.sku && <span>SKU: {item.sku}</span>}
                    {item.color_name && <span>ЦВЕТ: {item.color_name}</span>}
                    {item.size && <span>РАЗМЕР: {item.size}</span>}
                  </div>
                </div>

                <div className="flex items-center justify-between w-full sm:w-auto gap-6">
                  {/* Quantity controls */}
                  <div className="flex items-center border border-amov-dark">
                    <button
                      type="button"
                      disabled={item.quantity <= 1}
                      onClick={() =>
                        updateItemMutation.mutate({
                          variantId: item.variant_id,
                          quantity: item.quantity - 1,
                        })
                      }
                      className="px-2.5 py-0.5 text-xs font-sans hover:bg-amov-dark hover:text-amov-cream transition-colors disabled:opacity-30"
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
                      className="px-2.5 py-0.5 text-xs font-sans hover:bg-amov-dark hover:text-amov-cream transition-colors"
                    >
                      +
                    </button>
                  </div>

                  <div className="text-right">
                    <div className="font-sans font-bold text-sm text-amov-black">
                      {formatPrice(item.total_price)}
                    </div>
                    <div className="text-[10px] text-amov-muted">
                      {formatPrice(item.unit_price)} / шт.
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => removeItemMutation.mutate(item.variant_id)}
                    className="text-amov-muted hover:text-amov-dark text-sm px-1"
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
            <div className="border border-amov-dark p-6 bg-amov-cream/50 space-y-5">
              <h2 className="font-serif text-xl uppercase tracking-wider text-amov-dark">
                СУММА ЗАКАЗА
              </h2>

              <div className="space-y-2 text-xs font-sans uppercase tracking-wider text-amov-dark border-b border-amov-dark/15 pb-4">
                <div className="flex justify-between">
                  <span>ТОВАРЫ ({items.reduce((s, i) => s + i.quantity, 0)}):</span>
                  <span>{formatPrice(totalAmount)}</span>
                </div>
                <div className="flex justify-between">
                  <span>ДОСТАВКА:</span>
                  <span className="text-emerald-800">БЕСПЛАТНО</span>
                </div>
              </div>

              <div className="flex justify-between items-baseline text-amov-dark">
                <span className="font-sans font-bold text-xs uppercase tracking-wider">
                  ИТОГО К ОПЛАТЕ:
                </span>
                <span className="font-serif text-2xl font-bold">
                  {formatPrice(totalAmount)}
                </span>
              </div>

              <button
                type="button"
                onClick={() => alert('Переход к выбору адреса и оплате (Следующий этап)')}
                className="w-full bg-amov-dark text-amov-cream hover:bg-amov-black py-3.5 text-xs font-sans font-semibold uppercase tracking-widest transition-colors"
              >
                ПЕРЕЙТИ К ОФОРМЛЕНИЮ ↗
              </button>

              <div className="text-[10px] uppercase tracking-wider text-amov-muted text-center pt-1">
                ОПЛАТА ОНЛАЙН ИЛИ ПРИ ПОЛУЧЕНИИ ПОСЛЕ ПРИМЕРКИ
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { favoritesApi } from '../api/endpoints';
import { ProductCard } from '../components/ProductCard';
import { useAuthStore } from '../store/auth';

export function FavoritesPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  const { data, isLoading } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => favoritesApi.list(),
    enabled: isAuthenticated,
  });

  const removeFavoriteMutation = useMutation({
    mutationFn: (productId: string) => favoritesApi.remove(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="max-w-[500px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-sf-dark">
          ИЗБРАННОЕ
        </h1>
        <p className="mt-3 text-xs font-sans uppercase tracking-wider text-sf-muted">
          Войдите в аккаунт, чтобы сохранять понравившиеся модели солнцезащитных очков.
        </p>
        <button
          type="button"
          onClick={() => navigate(loginRedirectUrl, { state: { from: location } })}
          className="mt-6 inline-block bg-sf-dark text-sf-cream px-8 py-3 text-xs font-sans uppercase tracking-widest"
        >
          ВОЙТИ В АККАУНТ ↗
        </button>
      </div>
    );
  }

  const products = data?.data || [];

  return (
    <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-12 md:py-16">
      <div className="border-b border-sf-dark/20 pb-6 mb-10 flex items-end justify-between">
        <div>
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
            ( ПЕРСОНАЛЬНЫЙ ВИШЛИСТ )
          </span>
          <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-dark mt-1">
            ИЗБРАННЫЕ МОДЕЛИ
          </h1>
        </div>
        <div className="text-xs font-sans uppercase tracking-wider text-sf-muted">
          ВСЕГО: {products.length}
        </div>
      </div>

      {isLoading ? (
        <div className="py-24 text-center text-xs font-sans uppercase tracking-widest text-sf-muted">
          ( ЗАГРУЗКА ИЗБРАННОГО... )
        </div>
      ) : products.length === 0 ? (
        <div className="py-20 text-center border border-sf-dark/20 p-8">
          <div className="font-serif text-2xl uppercase tracking-wider text-sf-dark">
            ВАШ СПИСОК ИЗБРАННОГО ПУСТ
          </div>
          <p className="mt-2 text-xs font-sans uppercase tracking-wider text-sf-muted">
            Отмечайте значком «♡» понравившиеся очки в каталоге, чтобы вернуться к ним позже
          </p>
          <Link
            to="/"
            className="mt-6 inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
          >
            ПЕРЕЙТИ В КАТАЛОГ ↗
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 md:gap-8">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              isFavorite={true}
              onToggleFavorite={(id) => removeFavoriteMutation.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

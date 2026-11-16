import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export function OrdersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuthStore();

  const currentPath = `${location.pathname}${location.search}`;
  const loginRedirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  if (!isAuthenticated) {
    return (
      <div className="max-w-[500px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-sf-dark">
          ИСТОРИЯ ЗАКАЗОВ
        </h1>
        <p className="mt-3 text-xs font-sans uppercase tracking-wider text-sf-muted">
          Для просмотра ваших заказов необходимо войти в личный кабинет.
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

  return (
    <div className="w-full max-w-none px-4 md:px-8 py-12 md:py-16">
      <div className="border-b border-sf-dark/20 pb-6 mb-10">
        <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
          ( ЛИЧНЫЙ КАБИНЕТ )
        </span>
        <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-dark mt-1">
          ВАШИ ЗАКАЗЫ
        </h1>
      </div>

      <div className="py-20 text-center border border-sf-dark/20 p-8">
        <div className="font-serif text-2xl uppercase tracking-wider text-sf-dark">
          У ВАС ПОКА НЕТ ОФОРМЛЕННЫХ ЗАКАЗОВ
        </div>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-sf-muted">
          После оформления покупки здесь будут отображаться статус заказа и информация об отправлении
        </p>
        <Link
          to="/catalog"
          className="mt-6 inline-block bg-sf-dark text-sf-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
        >
          ПЕРЕЙТИ В КАТАЛОГ ↗
        </Link>
      </div>
    </div>
  );
}

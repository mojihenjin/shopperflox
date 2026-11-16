import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export function OrdersPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return (
      <div className="max-w-[500px] mx-auto px-4 py-24 text-center">
        <h1 className="font-serif text-3xl uppercase tracking-wider text-amov-dark">
          ИСТОРИЯ ЗАКАЗОВ
        </h1>
        <p className="mt-3 text-xs font-sans uppercase tracking-wider text-amov-muted">
          Для просмотра ваших заказов необходимо войти в личный кабинет.
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

  return (
    <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-12 md:py-16">
      <div className="border-b border-amov-dark/20 pb-6 mb-10">
        <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-amov-muted">
          ( ЛИЧНЫЙ КАБИНЕТ )
        </span>
        <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-amov-dark mt-1">
          ВАШИ ЗАКАЗЫ
        </h1>
      </div>

      <div className="py-20 text-center border border-amov-dark/20 p-8">
        <div className="font-serif text-2xl uppercase tracking-wider text-amov-dark">
          У ВАС ПОКА НЕТ ОФОРМЛЕННЫХ ЗАКАЗОВ
        </div>
        <p className="mt-2 text-xs font-sans uppercase tracking-wider text-amov-muted">
          После оформления покупки здесь будут отображаться статус доставки и трек-номер
        </p>
        <Link
          to="/"
          className="mt-6 inline-block bg-amov-dark text-amov-cream px-6 py-2.5 text-xs font-sans uppercase tracking-wider"
        >
          ПЕРЕЙТИ В КАТАЛОГ ↗
        </Link>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { authApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { getReturnTo } from '../utils/navigation';
import { formatApiError } from '../utils/errorMapper';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { setTokens } = useAuthStore();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const returnTo = getReturnTo(location.state, searchParams, '/');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setErrorMessage('Заполните логин и пароль');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await authApi.login({
        identifier: identifier.trim(),
        password,
      });

      if (res.data.access_token && res.data.refresh_token) {
        setTokens(res.data.access_token, res.data.refresh_token);
        navigate(returnTo, { replace: true });
      }
    } catch (err) {
      setErrorMessage(formatApiError(err, 'ОШИБКА ВХОДА. ПРОВЕРЬТЕ ДАННЫЕ.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-[480px] mx-auto px-4 py-16 md:py-24">
      <div className="bg-[#F2E9DB] border border-sf-dark p-6 sm:p-10">
        <div className="mb-8 text-center">
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
            ( АВТОРИЗАЦИЯ )
          </span>
          <h1 className="font-serif text-3xl md:text-4xl uppercase tracking-wider text-sf-dark mt-2">
            ВХОД В АККАУНТ
          </h1>
        </div>

        {errorMessage && (
          <div className="mb-6 p-3 border border-sf-dark bg-sf-dark/5 text-sf-dark text-xs uppercase tracking-wider whitespace-pre-line">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="identifier"
              className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
            >
              ЛОГИН ИЛИ EMAIL *
            </label>
            <input
              id="identifier"
              type="text"
              autoComplete="username"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="YOUR_LOGIN"
              className="w-full bg-[#F2E9DB] border border-sf-dark/40 focus:border-sf-dark px-3.5 py-2.5 text-xs font-sans tracking-wider outline-none text-sf-black transition-colors"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
            >
              ПАРОЛЬ *
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-[#F2E9DB] border border-sf-dark/40 focus:border-sf-dark px-3.5 py-2.5 text-xs font-sans tracking-wider outline-none text-sf-black transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-sf-dark text-sf-cream hover:bg-sf-black py-3 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50"
          >
            {isLoading ? 'ВХОД...' : 'ВОЙТИ В АККАУНТ ↗'}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-sf-dark/15 text-center">
          <Link
            to={returnTo !== '/' ? `/register?redirect=${encodeURIComponent(returnTo)}` : '/register'}
            className="text-[11px] font-sans uppercase tracking-wider text-sf-dark hover:opacity-70 transition-opacity"
          >
            НЕТ АККАУНТА? ЗАРЕГИСТРИРОВАТЬСЯ ↗
          </Link>
        </div>
      </div>
    </div>
  );
}

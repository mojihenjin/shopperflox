import { useState } from 'react';
import { Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { authApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import { getReturnTo } from '../utils/navigation';
import type { ApiError } from '../api/client';

export function RegisterPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { setTokens } = useAuthStore();

  const returnTo = getReturnTo(location.state, searchParams, '/');

  const [step, setStep] = useState<'FORM' | 'VERIFY'>('FORM');
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [verificationToken, setVerificationToken] = useState('');
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Format code as XXX-XXX on change
  const handleCodeChange = (raw: string) => {
    const cleaned = raw.replace(/[^a-zA-Z0-9]/g, '').slice(0, 6);
    if (cleaned.length > 3) {
      setCode(`${cleaned.slice(0, 3)}-${cleaned.slice(3)}`);
    } else {
      setCode(cleaned);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!login.trim() || !password) {
      setErrorMessage('Заполните логин и пароль');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    const trimmedEmail = email.trim();

    try {
      const res = await authApi.register({
        login: login.trim(),
        password,
        email: trimmedEmail ? trimmedEmail : null,
      });

      if (res.data.requires_verification && res.data.verification_token) {
        // Step 2: Verification code is required
        setVerificationToken(res.data.verification_token);
        setStep('VERIFY');
        setSuccessNotice(`Код подтверждения отправлен на ${trimmedEmail}`);
      } else {
        // Direct registration without email verification
        setSuccessNotice('Регистрация успешно завершена! Выполняется вход...');
        // Perform auto-login
        const loginRes = await authApi.login({
          identifier: login.trim(),
          password,
        });
        if (loginRes.data.access_token && loginRes.data.refresh_token) {
          setTokens(loginRes.data.access_token, loginRes.data.refresh_token);
          navigate(returnTo, { replace: true });
        } else {
          navigate(returnTo !== '/' ? `/login?redirect=${encodeURIComponent(returnTo)}` : '/login');
        }
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMessage(apiErr.message || 'Ошибка регистрации. Проверьте данные.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = code.replace(/-/g, '').trim();
    if (cleanCode.length !== 6) {
      setErrorMessage('Код подтверждения должен состоять из 6 символов (XXX-XXX)');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await authApi.verifyCode({
        verification_token: verificationToken,
        code: cleanCode,
      });

      setSuccessNotice('Email подтверждён! Выполняется вход...');

      // Auto-login after verification
      const loginRes = await authApi.login({
        identifier: login.trim(),
        password,
      });

      if (loginRes.data.access_token && loginRes.data.refresh_token) {
        setTokens(loginRes.data.access_token, loginRes.data.refresh_token);
        navigate(returnTo, { replace: true });
      } else {
        navigate(returnTo !== '/' ? `/login?redirect=${encodeURIComponent(returnTo)}` : '/login');
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setErrorMessage(apiErr.message || 'Неверный код или срок его действия истек.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-[480px] mx-auto px-4 py-16 md:py-24">
      <div className="bg-[#F2E9DB] border border-sf-dark p-6 sm:p-10">
        <div className="mb-8 text-center">
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
            {step === 'FORM' ? '( РЕГИСТРАЦИЯ )' : '( ВЕРИФИКАЦИЯ )'}
          </span>
          <h1 className="font-serif text-3xl md:text-4xl uppercase tracking-wider text-sf-dark mt-2">
            {step === 'FORM' ? 'СОЗДАНИЕ АККАУНТА' : 'ПОДТВЕРЖДЕНИЕ EMAIL'}
          </h1>
        </div>

        {successNotice && (
          <div className="mb-6 p-3 border border-sf-dark bg-sf-dark text-sf-cream text-xs uppercase tracking-wider">
            {successNotice}
          </div>
        )}

        {errorMessage && (
          <div className="mb-6 p-3 border border-sf-dark bg-sf-dark/5 text-sf-dark text-xs uppercase tracking-wider">
            {errorMessage}
          </div>
        )}

        {step === 'FORM' ? (
          <form onSubmit={handleRegisterSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="reg-login"
                className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
              >
                ЛОГИН *
              </label>
              <input
                id="reg-login"
                type="text"
                required
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                placeholder="USER_LOGIN"
                className="w-full bg-[#F2E9DB] border border-sf-dark/40 focus:border-sf-dark px-3.5 py-2.5 text-xs font-sans tracking-wider outline-none text-sf-black transition-colors"
              />
            </div>

            <div>
              <label
                htmlFor="reg-email"
                className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
              >
                EMAIL (НЕОБЯЗАТЕЛЬНО)
              </label>
              <input
                id="reg-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="NAME@EXAMPLE.COM"
                className="w-full bg-[#F2E9DB] border border-sf-dark/40 focus:border-sf-dark px-3.5 py-2.5 text-xs font-sans tracking-wider outline-none text-sf-black transition-colors"
              />
              <p className="mt-1 text-[10px] text-sf-muted uppercase tracking-wider">
                При указании почты потребуется подтверждение кодом XXX-XXX
              </p>
            </div>

            <div>
              <label
                htmlFor="reg-password"
                className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
              >
                ПАРОЛЬ *
              </label>
              <input
                id="reg-password"
                type="password"
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
              {isLoading ? 'РЕГИСТРАЦИЯ...' : 'СОЗДАТЬ АККАУНТ ↗'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifySubmit} className="space-y-5">
            <p className="text-xs uppercase tracking-wider text-sf-muted leading-relaxed">
              Введите 6-значный код подтверждения, отправленный на указанный email:
            </p>

            <div>
              <label
                htmlFor="verify-code"
                className="block text-[11px] font-sans font-semibold uppercase tracking-wider text-sf-dark mb-1.5"
              >
                КОД ПОДТВЕРЖДЕНИЯ (XXX-XXX) *
              </label>
              <input
                id="verify-code"
                type="text"
                required
                maxLength={7}
                value={code}
                onChange={(e) => handleCodeChange(e.target.value)}
                placeholder="123-456"
                className="w-full bg-[#F2E9DB] border border-sf-dark text-center tracking-widest text-lg font-mono py-2.5 outline-none text-sf-black transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-sf-dark text-sf-cream hover:bg-sf-black py-3 text-xs font-sans font-semibold uppercase tracking-widest transition-colors disabled:opacity-50"
            >
              {isLoading ? 'ПРОВЕРКА...' : 'ПОДТВЕРДИТЬ КОД ↗'}
            </button>

            <button
              type="button"
              onClick={() => {
                setStep('FORM');
                setErrorMessage(null);
              }}
              className="w-full border border-sf-dark py-2 text-[11px] font-sans uppercase tracking-wider text-sf-dark hover:bg-sf-dark hover:text-sf-cream transition-colors"
            >
              ( ВЕРНУТЬСЯ К ФОРМЕ )
            </button>
          </form>
        )}

        <div className="mt-8 pt-6 border-t border-sf-dark/15 text-center">
          <Link
            to={returnTo !== '/' ? `/login?redirect=${encodeURIComponent(returnTo)}` : '/login'}
            className="text-[11px] font-sans uppercase tracking-wider text-sf-dark hover:opacity-70 transition-opacity"
          >
            УЖЕ ЕСТЬ АККАУНТ? ВОЙТИ ↗
          </Link>
        </div>
      </div>
    </div>
  );
}

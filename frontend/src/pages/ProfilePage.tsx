import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';

export function ProfilePage() {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuthStore();

  const { data: profileData, isLoading } = useQuery({
    queryKey: ['userProfile'],
    queryFn: () => authApi.getMe(),
    enabled: isAuthenticated,
  });

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignored
    } finally {
      logout();
      navigate('/login');
    }
  };

  if (isLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-sf-muted">
          ( ЗАГРУЗКА ПРОФИЛЯ... )
        </div>
      </div>
    );
  }

  const user = profileData?.data?.user;
  const personal = profileData?.data?.personal;
  const permissions = user?.global_permissions || [];
  const isCreator =
    permissions.includes('*') ||
    permissions.some((p) => p.startsWith('creator:'));

  return (
    <div className="w-full bg-[#F2E9DB] min-h-[80vh] py-12 md:py-20 px-4 md:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Breadcrumb / Title */}
        <div className="border-b border-sf-dark/20 pb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
              ( ЛИЧНЫЙ КАБИНЕТ )
            </span>
            <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-sf-dark mt-1">
              ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ
            </h1>
          </div>
          <div className="font-mono text-sm uppercase text-sf-dark font-bold">
            @{user?.login}
          </div>
        </div>

        {/* Profile Details Card */}
        <div className="bg-[#FFFFFF] border border-sf-dark p-6 sm:p-10 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6 border-b border-sf-dark/15">
            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                ЛОГИН АККАУНТА
              </div>
              <div className="font-mono text-base font-bold text-sf-dark mt-1">
                @{user?.login}
              </div>
            </div>

            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                ЭЛЕКТРОННАЯ ПОЧТА
              </div>
              <div className="text-sm font-sans text-sf-dark mt-1">
                {user?.email || 'Не указана'}
              </div>
            </div>

            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                СТАТУС ВЕРИФИКАЦИИ
              </div>
              <div className="text-xs font-sans uppercase tracking-wider text-sf-dark mt-1 flex items-center gap-2">
                <span>ПРОФИЛЬ: {user?.verified_profile ? '✓ ПОДТВЕРЖДЁН' : 'НЕ ВЕРИФИЦИРОВАН'}</span>
              </div>
            </div>

            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                ПРИВИЛЕГИИ И РОЛИ
              </div>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {permissions.length > 0 ? (
                  permissions.map((p) => (
                    <span
                      key={p}
                      className="bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[10px] font-mono tracking-wider font-semibold"
                    >
                      {p}
                    </span>
                  ))
                ) : (
                  <span className="text-xs font-sans text-sf-muted uppercase">ПОКУПАТЕЛЬ</span>
                )}
              </div>
            </div>
          </div>

          {/* Personal Info if present */}
          {personal && (
            <div className="space-y-3 pb-6 border-b border-sf-dark/15">
              <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
                ( ПЕРСОНАЛЬНЫЕ ДАННЫЕ )
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-sans uppercase">
                {personal.firstname && (
                  <div>
                    <span className="text-sf-muted">ИМЯ: </span>
                    <span className="font-semibold text-sf-dark">{personal.firstname}</span>
                  </div>
                )}
                {personal.lastname && (
                  <div>
                    <span className="text-sf-muted">ФАМИЛИЯ: </span>
                    <span className="font-semibold text-sf-dark">{personal.lastname}</span>
                  </div>
                )}
                {personal.phone_number && (
                  <div>
                    <span className="text-sf-muted">ТЕЛЕФОН: </span>
                    <span className="font-semibold text-sf-dark">{personal.phone_number}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Quick links & Creator entry */}
          <div className="space-y-4">
            <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
              ( БЫСТРЫЙ ДОСТУП )
            </div>
            <div className="flex flex-wrap gap-3">
              {isCreator && (
                <Link
                  to="/creator/products/new"
                  className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors"
                >
                  + СОЗДАТЬ ТОВАР ↗
                </Link>
              )}
              <Link
                to="/favorites"
                className="border border-sf-dark hover:bg-sf-dark hover:text-sf-cream px-4 py-2.5 text-xs font-sans uppercase tracking-wider transition-colors"
              >
                ИЗБРАННОЕ ↗
              </Link>
              <Link
                to="/orders"
                className="border border-sf-dark hover:bg-sf-dark hover:text-sf-cream px-4 py-2.5 text-xs font-sans uppercase tracking-wider transition-colors"
              >
                МОИ ЗАКАЗЫ ↗
              </Link>
            </div>
          </div>

          {/* Logout Action */}
          <div className="pt-4 border-t border-sf-dark/15 flex justify-end">
            <button
              type="button"
              onClick={handleLogout}
              className="border border-sf-dark px-6 py-2.5 text-xs font-sans uppercase tracking-wider hover:bg-sf-dark hover:text-sf-cream transition-colors"
            >
              ВЫЙТИ ИЗ СИСТЕМЫ
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

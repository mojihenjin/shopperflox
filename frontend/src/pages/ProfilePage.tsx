import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { authApi, usersApi, brandsApi, addressesApi } from '../api/endpoints';
import { useAuthStore } from '../store/auth';
import type { ApiError } from '../api/client';

export function ProfilePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated, logout, refreshToken, setTokens } = useAuthStore();

  const { data: profileData, isLoading } = useQuery({
    queryKey: ['userProfile'],
    queryFn: () => authApi.getMe(),
    enabled: isAuthenticated,
  });

  // Email change 2-step flow state
  const [isEmailFormOpen, setIsEmailFormOpen] = useState(false);
  const [emailStep, setEmailStep] = useState<'input' | 'verify'>('input');
  const [newEmailInput, setNewEmailInput] = useState('');
  const [codeInput, setCodeInput] = useState('');
  const [verificationToken, setVerificationToken] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailSuccessMsg, setEmailSuccessMsg] = useState<string | null>(null);
  const [isEmailLoading, setIsEmailLoading] = useState(false);

  // Personal data editing state
  const [isEditingPersonal, setIsEditingPersonal] = useState(false);
  const [firstnameInput, setFirstnameInput] = useState('');
  const [lastnameInput, setLastnameInput] = useState('');
  const [phoneInput, setPhoneInput] = useState('');
  const [personalError, setPersonalError] = useState<string | null>(null);
  const [personalSuccessMsg, setPersonalSuccessMsg] = useState<string | null>(null);

  const user = profileData?.data?.user;
  const personal = profileData?.data?.personal;
  const permissions = user?.global_permissions || [];
  const isAdmin =
    permissions.includes('*') ||
    permissions.includes('admin:access');
  const isCreator =
    permissions.includes('*') ||
    permissions.some((p) => p.startsWith('creator:') || p === 'creator');
  const canManageCatalog =
    permissions.includes('*') ||
    permissions.includes('catalog:manage') ||
    permissions.includes('mod:approve_manager');

  const { data: myBrandsData } = useQuery({
    queryKey: ['myBrands'],
    queryFn: () => brandsApi.my(),
    enabled: isAuthenticated,
  });

  const myBrands = myBrandsData?.data || [];
  const canCreateBrand =
    permissions.includes('*') ||
    permissions.includes('creator:brand') ||
    isCreator ||
    canManageCatalog;
  const hasBrandAccess =
    canCreateBrand ||
    canManageCatalog ||
    myBrands.length > 0;
  const isBrandActiveManager = myBrands.some(
    (b) => !b.brand.is_deleted && (b.role === 'representative' || b.role === 'moderator')
  );
  const canCreateProduct = isCreator || isBrandActiveManager;

  useEffect(() => {
    if (personal) {
      setFirstnameInput(personal.firstname || '');
      setLastnameInput(personal.lastname || '');
      setPhoneInput(personal.phone_number || '');
    }
  }, [personal]);

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

  // Step 1: Send verification code to new email
  const handleSendEmailCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError(null);
    setEmailSuccessMsg(null);
    setIsEmailLoading(true);

    try {
      const res = await authApi.sendEmailCode({ email: newEmailInput.trim() });
      if (res.data?.verification_token) {
        setVerificationToken(res.data.verification_token);
        setEmailStep('verify');
        setEmailSuccessMsg('Код подтверждения отправлен на указанную почту');
      } else {
        throw new Error('Не удалось получить токен верификации');
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setEmailError(apiErr.message || 'Ошибка отправки кода. Проверьте адрес почты.');
    } finally {
      setIsEmailLoading(false);
    }
  };

  // Step 2: Verify code
  const handleVerifyEmailCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError(null);
    setEmailSuccessMsg(null);
    setIsEmailLoading(true);

    const cleanCode = codeInput.replace(/-/g, '').trim();
    if (cleanCode.length !== 6) {
      setEmailError('Код должен состоять из 6 цифр');
      setIsEmailLoading(false);
      return;
    }

    try {
      await authApi.verifyCode({
        verification_token: verificationToken,
        code: cleanCode,
      });

      if (refreshToken) {
        try {
          const refreshRes = await authApi.refresh({ refresh_token: refreshToken });
          if (refreshRes.data?.access_token && refreshRes.data?.refresh_token) {
            setTokens(refreshRes.data.access_token, refreshRes.data.refresh_token);
          }
        } catch (refreshErr) {
          console.error('Failed to refresh tokens after email verification:', refreshErr);
        }
      }

      await queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      setEmailSuccessMsg('Электронная почта успешно подтверждена!');
      setTimeout(() => {
        setIsEmailFormOpen(false);
        setEmailStep('input');
        setNewEmailInput('');
        setCodeInput('');
        setVerificationToken('');
        setEmailSuccessMsg(null);
      }, 1500);
    } catch (err) {
      const apiErr = err as ApiError;
      setEmailError(apiErr.message || 'Неверный или просроченный код подтверждения.');
    } finally {
      setIsEmailLoading(false);
    }
  };

  // Update personal mutation
  const updatePersonalMutation = useMutation({
    mutationFn: async () => {
      setPersonalError(null);
      setPersonalSuccessMsg(null);
      return usersApi.updatePersonal({
        firstname: firstnameInput.trim() || null,
        lastname: lastnameInput.trim() || null,
        phone_number: phoneInput.trim() || null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      setPersonalSuccessMsg('Персональные данные успешно сохранены');
      setIsEditingPersonal(false);
    },
    onError: (err: ApiError) => {
      setPersonalError(err.message || 'Ошибка обновления персональных данных');
    },
  });

  // Addresses query
  const { data: addressesData, isLoading: isAddressesLoading } = useQuery({
    queryKey: ['userAddresses'],
    queryFn: () => addressesApi.list(),
    enabled: isAuthenticated,
  });
  const addresses = addressesData?.data || [];

  // Address Form State
  const [isAddingAddress, setIsAddingAddress] = useState(false);
  const [addressCity, setAddressCity] = useState('');
  const [addressStreet, setAddressStreet] = useState('');
  const [addressPostalCode, setAddressPostalCode] = useState('');
  const [addressIsDefault, setAddressIsDefault] = useState(false);
  const [addressError, setAddressError] = useState<string | null>(null);
  const [addressSuccessMsg, setAddressSuccessMsg] = useState<string | null>(null);

  const createAddressMutation = useMutation({
    mutationFn: async () => {
      setAddressError(null);
      setAddressSuccessMsg(null);
      if (!addressCity.trim() || !addressStreet.trim() || !addressPostalCode.trim()) {
        throw new Error('Заполните все обязательные поля адреса');
      }
      return addressesApi.create({
        city: addressCity.trim(),
        street: addressStreet.trim(),
        postal_code: addressPostalCode.trim(),
        is_default: addressIsDefault,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userAddresses'] });
      setAddressSuccessMsg('Адрес успешно добавлен!');
      setAddressCity('');
      setAddressStreet('');
      setAddressPostalCode('');
      setAddressIsDefault(false);
      setIsAddingAddress(false);
      setTimeout(() => setAddressSuccessMsg(null), 3000);
    },
    onError: (err: ApiError) => {
      setAddressError(err.message || 'Ошибка при добавлении адреса');
    },
  });

  const setDefaultAddressMutation = useMutation({
    mutationFn: (addressId: string) => addressesApi.setDefault(addressId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userAddresses'] });
    },
    onError: (err: ApiError) => {
      setAddressError(err.message || 'Ошибка назначения адреса по умолчанию');
    },
  });

  const deleteAddressMutation = useMutation({
    mutationFn: (addressId: string) => addressesApi.delete(addressId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userAddresses'] });
    },
    onError: (err: ApiError) => {
      setAddressError(err.message || 'Ошибка удаления адреса');
    },
  });

  if (isLoading) {
    return (
      <div className="w-full bg-[#F2E9DB] min-h-[60vh] flex items-center justify-center py-20 px-4">
        <div className="text-xs font-sans uppercase tracking-widest text-sf-muted">
          ( ЗАГРУЗКА ПРОФИЛЯ... )
        </div>
      </div>
    );
  }

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
            {/* Login */}
            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                ЛОГИН АККАУНТА
              </div>
              <div className="font-mono text-base font-bold text-sf-dark mt-1">
                @{user?.login}
              </div>
            </div>

            {/* Email with Change / Bind button and 2-step inline form */}
            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                ЭЛЕКТРОННАЯ ПОЧТА
              </div>
              <div className="flex items-center justify-between gap-2 mt-1">
                <div className="text-sm font-sans text-sf-dark truncate">
                  {user?.email || 'Не указана'}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsEmailFormOpen(!isEmailFormOpen);
                    setEmailStep('input');
                    setEmailError(null);
                    setEmailSuccessMsg(null);
                  }}
                  className="text-[11px] font-sans uppercase tracking-wider text-sf-dark underline underline-offset-4 hover:opacity-70 whitespace-nowrap"
                >
                  {isEmailFormOpen ? 'ЗАКРЫТЬ ×' : (user?.email ? 'ИЗМЕНИТЬ' : 'ПРИВЯЗАТЬ')}
                </button>
              </div>

              {/* 2-Step Email Verification Form */}
              {isEmailFormOpen && (
                <div className="mt-3 p-4 bg-[#F2E9DB]/60 border border-sf-dark/20 space-y-3">
                  {emailError && (
                    <div className="text-[11px] text-red-700 bg-red-100/60 p-2 border border-red-700/20 font-sans">
                      {emailError}
                    </div>
                  )}
                  {emailSuccessMsg && (
                    <div className="text-[11px] text-emerald-800 bg-emerald-100/60 p-2 border border-emerald-800/20 font-sans">
                      {emailSuccessMsg}
                    </div>
                  )}

                  {emailStep === 'input' ? (
                    <form onSubmit={handleSendEmailCode} className="space-y-3">
                      <div className="text-[10px] font-sans uppercase tracking-wider text-sf-muted">
                        Шаг 1 из 2: Введите новый email
                      </div>
                      <input
                        type="email"
                        required
                        placeholder="NAME@DOMAIN.COM"
                        value={newEmailInput}
                        onChange={(e) => setNewEmailInput(e.target.value)}
                        className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-1.5 text-xs font-sans outline-none"
                      />
                      <button
                        type="submit"
                        disabled={isEmailLoading}
                        className="bg-sf-dark text-sf-cream hover:bg-sf-black px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-50 transition-colors"
                      >
                        {isEmailLoading ? 'ОТПРАВКА...' : 'ОТПРАВИТЬ КОД ↗'}
                      </button>
                    </form>
                  ) : (
                    <form onSubmit={handleVerifyEmailCode} className="space-y-3">
                      <div className="text-[10px] font-sans uppercase tracking-wider text-sf-muted">
                        Шаг 2 из 2: Введите 6-значный код из письма
                      </div>
                      <input
                        type="text"
                        required
                        maxLength={7}
                        placeholder="123-456"
                        value={codeInput}
                        onChange={(e) => {
                          const raw = e.target.value.replace(/[^\d]/g, '').slice(0, 6);
                          if (raw.length > 3) {
                            setCodeInput(`${raw.slice(0, 3)}-${raw.slice(3)}`);
                          } else {
                            setCodeInput(raw);
                          }
                        }}
                        className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-1.5 text-xs font-mono tracking-widest outline-none text-center"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          type="submit"
                          disabled={isEmailLoading}
                          className="bg-sf-dark text-sf-cream hover:bg-sf-black px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-50 transition-colors"
                        >
                          {isEmailLoading ? 'ПРОВЕРКА...' : 'ПОДТВЕРДИТЬ КОД ↗'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEmailStep('input');
                            setEmailError(null);
                          }}
                          className="text-xs font-sans uppercase tracking-wider text-sf-muted hover:text-sf-dark px-2 py-1"
                        >
                          НАЗАД
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </div>

            {/* Verification Status with Round Burgundy Badge */}
            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                СТАТУС ВЕРИФИКАЦИИ
              </div>
              <div className="text-xs font-sans uppercase tracking-wider text-sf-dark mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sf-muted">ПРОФИЛЬ:</span>
                  {user?.verified_profile ? (
                    <span className="inline-flex items-center gap-1.5 font-semibold text-sf-dark">
                      <span className="w-4 h-4 rounded-full bg-[#3F2021] text-[#F2E9DB] inline-flex items-center justify-center text-[10px] font-bold select-none leading-none">
                        ✓
                      </span>
                      <span>ПОДТВЕРЖДЁН</span>
                    </span>
                  ) : (
                    <span className="text-sf-muted">НЕ ВЕРИФИЦИРОВАН</span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-sf-muted">ПОЧТА:</span>
                  {user?.verified_email ? (
                    <span className="inline-flex items-center gap-1.5 font-semibold text-sf-dark">
                      <span className="w-4 h-4 rounded-full bg-[#3F2021] text-[#F2E9DB] inline-flex items-center justify-center text-[10px] font-bold select-none leading-none">
                        ✓
                      </span>
                      <span>ПОДТВЕРЖДЕНА</span>
                    </span>
                  ) : (
                    <span className="text-sf-muted">НЕ ПОДТВЕРЖДЕНА</span>
                  )}
                </div>
              </div>
            </div>

            {/* Permissions / Roles */}
            <div>
              <div className="text-[10px] font-sans uppercase tracking-widest text-sf-muted">
                ПРИВИЛЕГИИ И РОЛИ
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2">
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

          {/* Personal Info Section */}
          <div className="space-y-4 pb-6 border-b border-sf-dark/15">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
                ( ПЕРСОНАЛЬНЫЕ ДАННЫЕ )
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsEditingPersonal(!isEditingPersonal);
                  setPersonalError(null);
                  setPersonalSuccessMsg(null);
                }}
                className="text-[11px] font-sans uppercase tracking-wider text-sf-dark underline underline-offset-4 hover:opacity-70"
              >
                {isEditingPersonal ? 'ОТМЕНА' : 'РЕДАКТИРОВАТЬ'}
              </button>
            </div>

            {personalError && (
              <div className="text-xs text-red-700 bg-red-100/60 p-2.5 border border-red-700/20 font-sans">
                {personalError}
              </div>
            )}
            {personalSuccessMsg && (
              <div className="text-xs text-emerald-800 bg-emerald-100/60 p-2.5 border border-emerald-800/20 font-sans">
                {personalSuccessMsg}
              </div>
            )}

            {isEditingPersonal ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  updatePersonalMutation.mutate();
                }}
                className="space-y-4 bg-[#F2E9DB]/40 p-4 border border-sf-dark/15"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-sf-muted mb-1">
                      ИМЯ
                    </label>
                    <input
                      type="text"
                      maxLength={100}
                      placeholder="Иван"
                      value={firstnameInput}
                      onChange={(e) => setFirstnameInput(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-xs font-sans outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-sf-muted mb-1">
                      ФАМИЛИЯ
                    </label>
                    <input
                      type="text"
                      maxLength={100}
                      placeholder="Иванов"
                      value={lastnameInput}
                      onChange={(e) => setLastnameInput(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-xs font-sans outline-none"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-sf-muted mb-1">
                      НОМЕР ТЕЛЕФОНА
                    </label>
                    <input
                      type="tel"
                      maxLength={30}
                      placeholder="+7 999 000-00-00"
                      value={phoneInput}
                      onChange={(e) => setPhoneInput(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-xs font-sans outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={updatePersonalMutation.isPending}
                    className="bg-sf-dark text-sf-cream hover:bg-sf-black px-5 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-50 transition-colors"
                  >
                    {updatePersonalMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ↗'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditingPersonal(false)}
                    className="text-xs font-sans uppercase tracking-wider text-sf-muted hover:text-sf-dark px-2"
                  >
                    ОТМЕНА
                  </button>
                </div>
              </form>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-sans uppercase">
                <div>
                  <span className="text-sf-muted">ИМЯ: </span>
                  <span className="font-semibold text-sf-dark">
                    {personal?.firstname || 'Не указано'}
                  </span>
                </div>
                <div>
                  <span className="text-sf-muted">ФАМИЛИЯ: </span>
                  <span className="font-semibold text-sf-dark">
                    {personal?.lastname || 'Не указана'}
                  </span>
                </div>
                <div>
                  <span className="text-sf-muted">ТЕЛЕФОН: </span>
                  <span className="font-semibold text-sf-dark">
                    {personal?.phone_number || 'Не указан'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Delivery Addresses Section */}
          <div className="space-y-4 pb-6 border-b border-sf-dark/15">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
                ( АДРЕСА ДОСТАВКИ )
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsAddingAddress(!isAddingAddress);
                  setAddressError(null);
                  setAddressSuccessMsg(null);
                }}
                className="text-[11px] font-sans uppercase tracking-wider text-sf-dark underline underline-offset-4 hover:opacity-70"
              >
                {isAddingAddress ? 'ОТМЕНА' : '+ ДОБАВИТЬ АДРЕС'}
              </button>
            </div>

            {addressError && (
              <div className="text-xs text-red-700 bg-red-100/60 p-2.5 border border-red-700/20 font-sans">
                {addressError}
              </div>
            )}
            {addressSuccessMsg && (
              <div className="text-xs text-emerald-800 bg-emerald-100/60 p-2.5 border border-emerald-800/20 font-sans">
                {addressSuccessMsg}
              </div>
            )}

            {/* Inline Add Address Form */}
            {isAddingAddress && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  createAddressMutation.mutate();
                }}
                className="space-y-4 bg-[#F2E9DB]/40 p-4 border border-sf-dark/15"
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-sf-muted mb-1">
                      ГОРОД *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Москва"
                      value={addressCity}
                      onChange={(e) => setAddressCity(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-xs font-sans outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-sf-muted mb-1">
                      УЛИЦА И ДОМ / КВАРТИРА *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="ул. Тверская, д. 1, кв. 10"
                      value={addressStreet}
                      onChange={(e) => setAddressStreet(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-xs font-sans outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-sans uppercase tracking-wider text-sf-muted mb-1">
                      ПОЧТОВЫЙ ИНДЕКС *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="101000"
                      value={addressPostalCode}
                      onChange={(e) => setAddressPostalCode(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-sf-dark/30 focus:border-sf-dark px-3 py-2 text-xs font-sans outline-none font-mono"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="isDefaultAddr"
                    checked={addressIsDefault}
                    onChange={(e) => setAddressIsDefault(e.target.checked)}
                    className="w-4 h-4 rounded-none accent-[#3F2021] border-sf-dark cursor-pointer"
                  />
                  <label htmlFor="isDefaultAddr" className="text-xs font-sans uppercase tracking-wider text-sf-dark cursor-pointer select-none">
                    СДЕЛАТЬ АДРЕСОМ ПО УМОЛЧАНИЮ
                  </label>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={createAddressMutation.isPending}
                    className="bg-sf-dark text-sf-cream hover:bg-sf-black px-5 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-50 transition-colors"
                  >
                    {createAddressMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ АДРЕС ↗'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsAddingAddress(false)}
                    className="text-xs font-sans uppercase tracking-wider text-sf-muted hover:text-sf-dark px-2"
                  >
                    ОТМЕНА
                  </button>
                </div>
              </form>
            )}

            {/* Address List */}
            {isAddressesLoading ? (
              <div className="text-xs font-sans uppercase tracking-wider text-sf-muted py-2">
                ( ЗАГРУЗКА АДРЕСОВ... )
              </div>
            ) : addresses.length === 0 ? (
              <div className="text-xs font-sans uppercase tracking-wider text-sf-muted py-2">
                ( НЕТ СОХРАНЁННЫХ АДРЕСОВ )
              </div>
            ) : (
              <div className="space-y-3">
                {addresses.map((addr) => (
                  <div
                    key={addr.id}
                    className="p-3.5 bg-[#FFFFFF] border border-sf-dark/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-sans font-bold text-xs uppercase text-sf-dark">
                          Г. {addr.city}, {addr.street}
                        </span>
                        {addr.is_default && (
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-sans uppercase font-bold tracking-wider text-sf-dark">
                            <span className="w-4 h-4 rounded-full bg-[#3F2021] text-[#F2E9DB] inline-flex items-center justify-center text-[10px] font-bold select-none leading-none">
                              ✓
                            </span>
                            ПО УМОЛЧАНИЮ
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] font-mono text-sf-muted">
                        ИНДЕКС: {addr.postal_code}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {!addr.is_default && (
                        <button
                          type="button"
                          disabled={setDefaultAddressMutation.isPending}
                          onClick={() => setDefaultAddressMutation.mutate(addr.id)}
                          className="text-[11px] font-sans uppercase tracking-wider text-sf-dark underline underline-offset-4 hover:opacity-70 disabled:opacity-40"
                        >
                          СДЕЛАТЬ ОСНОВНЫМ
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={deleteAddressMutation.isPending}
                        onClick={() => deleteAddressMutation.mutate(addr.id)}
                        className="text-[11px] font-sans uppercase tracking-wider text-red-700 underline underline-offset-4 hover:opacity-70 disabled:opacity-40"
                      >
                        УДАЛИТЬ ×
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick links & Creator entry */}
          <div className="space-y-4">
            <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-sf-muted">
              ( БЫСТРЫЙ ДОСТУП )
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/catalog"
                className="bg-sf-dark text-sf-cream hover:bg-sf-black px-4 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors"
              >
                ВЕСЬ КАТАЛОГ ↗
              </Link>
              {hasBrandAccess && (
                <Link
                  to="/brands/manage"
                  className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors"
                >
                  БРЕНДЫ ↗
                </Link>
              )}
              {isAdmin && (
                <Link
                  to="/admin"
                  className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] border border-[#3F2021] px-4 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors"
                >
                  АДМИНПАНЕЛЬ ↗
                </Link>
              )}
              {canCreateProduct && (
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

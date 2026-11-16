import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';
import { brandsApi } from '../api/brands';
import { useAuthStore } from '../store/auth';
import { formatImageUrl, formatDate } from '../utils/format';
import type { ApiError } from '../api/client';
import type { BrandMemberResponse } from '../types/api';

export function BrandsManagePage() {
  const queryClient = useQueryClient();
  const { isAuthenticated, authUser: user } = useAuthStore();

  const permissions = user?.global_permissions || [];
  const isSuperAdmin = permissions.includes('*');
  const isCreator =
    isSuperAdmin ||
    permissions.some((p) => p.startsWith('creator:') || p === 'creator');
  const canCreateBrand =
    isSuperAdmin ||
    permissions.includes('creator:brand') ||
    isCreator ||
    permissions.includes('catalog:manage');
  const isGlobalManager =
    isSuperAdmin ||
    permissions.includes('catalog:manage') ||
    permissions.includes('mod:approve_manager');

  const [activeTab, setActiveTab] = useState<'my' | 'all'>('my');

  // --- MY BRANDS QUERY ---
  const { data: myBrandsData, isLoading: isMyBrandsLoading } = useQuery({
    queryKey: ['myBrands'],
    queryFn: () => brandsApi.my(),
    enabled: isAuthenticated,
  });

  const myBrands = myBrandsData?.data || [];

  // --- ALL BRANDS QUERY ---
  const { data: allBrandsData, isLoading: isAllBrandsLoading } = useQuery({
    queryKey: ['allBrands'],
    queryFn: () => brandsApi.list({ limit: 100 }),
    enabled: isAuthenticated,
  });

  const allBrands = allBrandsData?.data || [];

  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);

  // Auto-select first brand
  useEffect(() => {
    if (myBrands.length > 0 && (!selectedBrandId || !myBrands.some((b) => b.brand.id === selectedBrandId))) {
      setSelectedBrandId(myBrands[0].brand.id);
    }
  }, [myBrands, selectedBrandId]);

  const selectedMyBrand = myBrands.find((b) => b.brand.id === selectedBrandId);
  const selectedBrand =
    selectedMyBrand?.brand || (isSuperAdmin || isGlobalManager ? allBrands.find((b) => b.id === selectedBrandId) : undefined);
  const myRoleInSelectedBrand =
    selectedMyBrand?.role || (isSuperAdmin || isGlobalManager ? 'representative' : undefined);
  const isRepresentative = myRoleInSelectedBrand === 'representative' || isSuperAdmin || isGlobalManager;

  // --- BRAND MEMBERS QUERY ---
  const { data: membersData, isLoading: isMembersLoading } = useQuery({
    queryKey: ['brandMembers', selectedBrandId],
    queryFn: () => brandsApi.listMembers(selectedBrandId!),
    enabled: Boolean(selectedBrandId),
  });

  const members = membersData?.data || [];

  // --- CREATE BRAND MODAL/FORM STATE ---
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createHisUrl, setCreateHisUrl] = useState('');
  const [createLogoFile, setCreateLogoFile] = useState<File | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccessMsg, setCreateSuccessMsg] = useState<string | null>(null);

  // --- EDIT PROFILE FORM STATE ---
  const [editName, setEditName] = useState('');
  const [editHisUrl, setEditHisUrl] = useState('');
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Sync profile form fields with selected brand
  useEffect(() => {
    if (selectedBrand) {
      setEditName(selectedBrand.name || '');
      setEditHisUrl(selectedBrand.his_url || '');
      setLogoFile(null);
      setProfileMessage(null);
      setProfileError(null);
    }
  }, [selectedBrand]);

  // --- ADD MEMBER FORM STATE ---
  const [memberLogin, setMemberLogin] = useState('');
  const [memberRole, setMemberRole] = useState<'moderator' | 'representative'>('moderator');
  const [memberMessage, setMemberMessage] = useState<string | null>(null);
  const [memberError, setMemberError] = useState<string | null>(null);

  // --- CONFIRMATION STATES ---
  const [showSelfRemovalConfirm, setShowSelfRemovalConfirm] = useState(false);
  const [showDeleteBrandConfirm, setShowDeleteBrandConfirm] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // --- MUTATIONS ---

  // 1. Create Brand
  const createBrandMutation = useMutation({
    mutationFn: async () => {
      setCreateError(null);
      setCreateSuccessMsg(null);
      if (!createName.trim()) throw new Error('Укажите название бренда');

      const res = await brandsApi.create({
        name: createName.trim(),
        his_url: createHisUrl.trim() || null,
      });

      const newBrand = res.data;

      if (createLogoFile && newBrand?.id) {
        const formData = new FormData();
        formData.append('file', createLogoFile);
        await brandsApi.uploadLogo(newBrand.id, formData);
      }

      return newBrand;
    },
    onSuccess: (newBrand) => {
      queryClient.invalidateQueries({ queryKey: ['myBrands'] });
      setCreateSuccessMsg('Бренд успешно создан!');
      setCreateName('');
      setCreateHisUrl('');
      setCreateLogoFile(null);
      if (newBrand?.id) {
        setSelectedBrandId(newBrand.id);
      }
      setTimeout(() => {
        setIsCreateOpen(false);
        setCreateSuccessMsg(null);
      }, 1500);
    },
    onError: (err: ApiError) => {
      setCreateError(err.message || 'Ошибка создания бренда');
    },
  });

  // 2. Update Brand Profile
  const updateProfileMutation = useMutation({
    mutationFn: async () => {
      if (!selectedBrandId) throw new Error('Бренд не выбран');
      setProfileError(null);
      setProfileMessage(null);

      await brandsApi.update(selectedBrandId, {
        name: editName.trim() || null,
        his_url: editHisUrl.trim() || null,
      });

      if (logoFile) {
        const formData = new FormData();
        formData.append('file', logoFile);
        await brandsApi.uploadLogo(selectedBrandId, formData);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myBrands'] });
      if (selectedBrand?.slug) {
        queryClient.invalidateQueries({ queryKey: ['brand', selectedBrand.slug] });
      }
      setLogoFile(null);
      setProfileMessage('Профиль бренда успешно обновлен');
      setTimeout(() => setProfileMessage(null), 3000);
    },
    onError: (err: ApiError) => {
      setProfileError(err.message || 'Ошибка обновления профиля бренда');
    },
  });

  // 3. Add or update team member
  const addMemberMutation = useMutation({
    mutationFn: async () => {
      if (!selectedBrandId) throw new Error('Бренд не выбран');
      setMemberError(null);
      setMemberMessage(null);

      const cleanLogin = memberLogin.replace(/^@/, '').trim();
      if (!cleanLogin) throw new Error('Укажите логин участника');

      return brandsApi.addMember(selectedBrandId, {
        login: cleanLogin,
        role: memberRole,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brandMembers', selectedBrandId] });
      setMemberMessage('Участник успешно добавлен в команду');
      setMemberLogin('');
      setTimeout(() => setMemberMessage(null), 3000);
    },
    onError: (err: ApiError) => {
      setMemberError(err.message || 'Ошибка добавления участника');
    },
  });

  // 4. Change member role
  const changeRoleMutation = useMutation({
    mutationFn: async ({ member, newRole }: { member: BrandMemberResponse; newRole: 'representative' | 'moderator' }) => {
      if (!selectedBrandId || !member.user_login) throw new Error('Некорректные данные участника');
      return brandsApi.addMember(selectedBrandId, {
        login: member.user_login,
        role: newRole,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brandMembers', selectedBrandId] });
      queryClient.invalidateQueries({ queryKey: ['myBrands'] });
      setActionNotice('Роль участника изменена');
      setTimeout(() => setActionNotice(null), 3000);
    },
    onError: (err: ApiError) => {
      setActionNotice(err.message || 'Ошибка смены роли');
      setTimeout(() => setActionNotice(null), 3000);
    },
  });

  // 5. Remove member
  const removeMemberMutation = useMutation({
    mutationFn: async (targetUserId: string) => {
      if (!selectedBrandId) throw new Error('Бренд не выбран');
      return brandsApi.removeMember(selectedBrandId, targetUserId);
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['brandMembers', selectedBrandId] });
      queryClient.invalidateQueries({ queryKey: ['myBrands'] });
      if (res.data?.brand_deleted) {
        setActionNotice('Бренд удален, так как был снят последний представитель');
      } else {
        setActionNotice('Участник удален из команды');
      }
      setTimeout(() => setActionNotice(null), 3000);
    },
    onError: (err: ApiError) => {
      setActionNotice(err.message || 'Ошибка удаления участника');
      setTimeout(() => setActionNotice(null), 3000);
    },
  });

  // 6. Self-removal
  const selfRemovalMutation = useMutation({
    mutationFn: async () => {
      if (!selectedBrandId || !user?.id) throw new Error('Бренд или пользователь не определен');
      return brandsApi.removeMember(selectedBrandId, user.id);
    },
    onSuccess: (res) => {
      setShowSelfRemovalConfirm(false);
      queryClient.invalidateQueries({ queryKey: ['myBrands'] });
      queryClient.invalidateQueries({ queryKey: ['brandMembers', selectedBrandId] });
      if (res.data?.brand_deleted) {
        setActionNotice('Вы покинули команду. Бренд и его товары сняты с продажи.');
      } else {
        setActionNotice('Вы успешно сняли с себя роль в бренде.');
      }
      setSelectedBrandId(null);
      setTimeout(() => setActionNotice(null), 4000);
    },
    onError: (err: ApiError) => {
      setShowSelfRemovalConfirm(false);
      setActionNotice(err.message || 'Ошибка при снятии роли');
      setTimeout(() => setActionNotice(null), 4000);
    },
  });

  // 7. Delete Brand
  const deleteBrandMutation = useMutation({
    mutationFn: async () => {
      if (!selectedBrandId) throw new Error('Бренд не выбран');
      return brandsApi.delete(selectedBrandId);
    },
    onSuccess: () => {
      setShowDeleteBrandConfirm(false);
      queryClient.invalidateQueries({ queryKey: ['myBrands'] });
      if (selectedBrand?.slug) {
        queryClient.invalidateQueries({ queryKey: ['brand', selectedBrand.slug] });
      }
      setActionNotice('Бренд и все его товары успешно сняты с продажи');
      setTimeout(() => setActionNotice(null), 4000);
    },
    onError: (err: ApiError) => {
      setShowDeleteBrandConfirm(false);
      setActionNotice(err.message || 'Ошибка снятия бренда с продажи');
      setTimeout(() => setActionNotice(null), 4000);
    },
  });

  if (!isAuthenticated) {
    return <Navigate to="/login?redirect=%2Fbrands%2Fmanage" replace />;
  }

  // Count representatives in current brand team
  const representativeCount = members.filter((m) => m.role === 'representative').length;
  const isLastRepresentative = isRepresentative && representativeCount <= 1;

  return (
    <div className="w-full bg-[#F2E9DB] min-h-[85vh] py-10 md:py-16 px-4 md:px-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Top Header */}
        <div className="border-b border-[#3F2021]/20 pb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
              ( УПРАВЛЕНИЕ БРЕНДАМИ )
            </span>
            <h1 className="font-serif text-3xl md:text-5xl uppercase tracking-wider text-[#3F2021] mt-1">
              КАБИНЕТ БРЕНДОВ
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {canCreateBrand && (
              <button
                type="button"
                onClick={() => {
                  setIsCreateOpen(!isCreateOpen);
                  setCreateError(null);
                  setCreateSuccessMsg(null);
                }}
                className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
              >
                {isCreateOpen ? 'ЗАКРЫТЬ ×' : '+ СОЗДАТЬ БРЕНД'}
              </button>
            )}
            <Link
              to="/profile"
              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2.5 text-xs font-sans uppercase tracking-widest transition-colors rounded-none"
            >
              ПРОФИЛЬ ↗
            </Link>
          </div>
        </div>

        {/* Global Action Notice */}
        {actionNotice && (
          <div className="p-3.5 bg-[#3F2021] text-[#F2E9DB] text-xs font-sans uppercase tracking-widest text-center font-semibold rounded-none border border-[#3F2021]">
            {actionNotice}
          </div>
        )}

        {/* 1. CREATE BRAND FORM (Expandable / Modal block) */}
        {isCreateOpen && canCreateBrand && (
          <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 space-y-6 rounded-none">
            <div className="border-b border-[#3F2021]/15 pb-3">
              <span className="text-[10px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
                ( НОВЫЙ БРЕНД )
              </span>
              <h2 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                СОЗДАНИЕ БРЕНДА
              </h2>
            </div>

            {createError && (
              <div className="text-xs text-red-700 bg-red-100/60 p-3 border border-red-700/20 font-sans">
                {createError}
              </div>
            )}
            {createSuccessMsg && (
              <div className="text-xs text-emerald-800 bg-emerald-100/60 p-3 border border-emerald-800/20 font-sans">
                {createSuccessMsg}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                createBrandMutation.mutate();
              }}
              className="space-y-4 max-w-xl"
            >
              <div>
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold mb-1">
                  НАЗВАНИЕ БРЕНДА (NAME) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="НАПРИМЕР: ARCHIVE STUDIO"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold mb-1">
                  ССЫЛКА НА РЕСУРС (HISURL)
                </label>
                <input
                  type="url"
                  placeholder="HTTPS://BRAND.COM"
                  value={createHisUrl}
                  onChange={(e) => setCreateHisUrl(e.target.value)}
                  className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2 text-xs font-sans tracking-wider text-[#000000] outline-none rounded-none"
                />
              </div>

              <div>
                <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold mb-1">
                  ЛОГОТИП / ФОТО БРЕНДА (ОПЦИОНАЛЬНО)
                </label>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => setCreateLogoFile(e.target.files?.[0] || null)}
                  className="w-full text-xs font-sans text-[#3F2021] file:mr-4 file:py-2 file:px-4 file:border file:border-[#3F2021] file:text-xs file:font-sans file:uppercase file:bg-[#3F2021] file:text-[#F2E9DB] file:cursor-pointer hover:file:bg-[#2B1516] rounded-none cursor-pointer"
                />
              </div>

              <div className="pt-2 flex items-center gap-3">
                <button
                  type="submit"
                  disabled={createBrandMutation.isPending}
                  className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors disabled:opacity-50 rounded-none"
                >
                  {createBrandMutation.isPending ? 'СОЗДАНИЕ...' : 'СОЗДАТЬ БРЕНД ✓'}
                </button>
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2.5 text-xs font-sans uppercase tracking-widest transition-colors rounded-none"
                >
                  ОТМЕНА
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Navigation Tabs: МОИ БРЕНДЫ / ВСЕ БРЕНДЫ */}
        <div className="flex items-center gap-2 border-b border-[#3F2021]/20 pb-3">
          <button
            type="button"
            onClick={() => setActiveTab('my')}
            className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
              activeTab === 'my'
                ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
            }`}
          >
            МОИ БРЕНДЫ ({myBrands.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
              activeTab === 'all'
                ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
            }`}
          >
            ВСЕ БРЕНДЫ ({allBrands.length})
          </button>
        </div>

        {/* 2. ALL BRANDS TAB VIEW */}
        {activeTab === 'all' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <span className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 font-semibold">
                ( КАТАЛОГ ВСЕХ АКТИВНЫХ БРЕНДОВ ПЛАТФОРМЫ )
              </span>
              <span className="text-xs font-mono text-[#3F2021]/60">
                ВСЕГО: {allBrands.length}
              </span>
            </div>

            {isAllBrandsLoading ? (
              <div className="w-full bg-[#FFFFFF] border border-[#3F2021] p-16 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( ЗАГРУЗКА СПИСКА ВСЕХ БРЕНДОВ... )
              </div>
            ) : allBrands.length === 0 ? (
              <div className="bg-[#FFFFFF] border border-[#3F2021] p-12 text-center space-y-4">
                <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
                  ( НЕТ БРЕНДОВ )
                </div>
                <h3 className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
                  В СИСТЕМЕ ПОКА НЕТ СОЗДАННЫХ БРЕНДОВ
                </h3>
                {canCreateBrand && (
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(true)}
                    className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] border border-[#3F2021] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
                  >
                    + СОЗДАТЬ ПЕРВЫЙ БРЕНД
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {allBrands.map((b) => {
                  const isMyBrand = myBrands.some((mb) => mb.brand.id === b.id);
                  return (
                    <div
                      key={b.id}
                      className="bg-[#FFFFFF] border border-[#3F2021] p-5 flex flex-col justify-between space-y-4 rounded-none hover:border-[#3F2021] transition-all"
                    >
                      <div className="flex items-start gap-3.5">
                        {b.logo_url ? (
                          <img
                            src={formatImageUrl(b.logo_url, b.name)}
                            alt={b.name}
                            className="w-12 h-12 object-cover border border-[#3F2021] rounded-none shrink-0"
                          />
                        ) : (
                          <div className="w-12 h-12 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-center font-serif text-sm text-[#3F2021] font-bold rounded-none select-none shrink-0">
                            {b.name.slice(0, 2).toUpperCase()}
                          </div>
                        )}
                        <div className="min-w-0">
                          <h3 className="font-serif text-lg uppercase tracking-wider text-[#3F2021] truncate">
                            {b.name}
                          </h3>
                          <div className="text-[11px] font-mono text-[#3F2021]/60 truncate">
                            @{b.slug}
                          </div>
                          {b.his_url && (
                            <a
                              href={b.his_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[10px] font-sans text-[#3F2021] hover:underline underline-offset-2 flex items-center gap-1 mt-1 truncate"
                            >
                              <span>{b.his_url.replace(/^https?:\/\//, '')}</span>
                              <span>↗</span>
                            </a>
                          )}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-[#3F2021]/15 flex items-center justify-between gap-2">
                        <Link
                          to={`/brands/${b.slug}`}
                          className="text-xs font-sans uppercase tracking-wider text-[#3F2021] hover:underline underline-offset-4 font-semibold"
                        >
                          КАТАЛОГ БРЕНДА ↗
                        </Link>
                        {(isMyBrand || isSuperAdmin || isGlobalManager) && (
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedBrandId(b.id);
                              setActiveTab('my');
                            }}
                            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors rounded-none"
                          >
                            УПРАВЛЯТЬ
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* 3. MY BRANDS SELECTION & MAIN MANAGEMENT VIEW */}
        {activeTab === 'my' && (
          <>
            {isMyBrandsLoading ? (
              <div className="w-full bg-[#FFFFFF] border border-[#3F2021] p-16 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                ( ЗАГРУЗКА СПИСКА БРЕНДОВ... )
              </div>
            ) : myBrands.length === 0 ? (
              <div className="bg-[#FFFFFF] border border-[#3F2021] p-10 md:p-14 text-center space-y-5">
                <div className="text-[10px] font-sans uppercase tracking-widest text-[#3F2021]/60">
                  ( СПИСОК ПУСТ )
                </div>
                <h2 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021]">
                  ВЫ ПОКА НЕ СОСТОИТЕ НИ В ОДНОМ БРЕНДЕ
                </h2>
                <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 max-w-md mx-auto leading-relaxed">
                  {canCreateBrand
                    ? 'Создайте свой собственный бренд, чтобы выпускать фирменные товары, загружать логотип и управлять командой представителей.'
                    : 'Попросите представителя существующего бренда добавить ваш аккаунт по @login в команду.'}
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                  {canCreateBrand && (
                    <button
                      type="button"
                      onClick={() => setIsCreateOpen(true)}
                      className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] border border-[#3F2021] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none cursor-pointer"
                    >
                      + СОЗДАТЬ СВОЙ БРЕНД
                    </button>
                  )}
                  {allBrands.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setActiveTab('all')}
                      className="bg-[#FFFFFF] text-[#3F2021] hover:bg-[#F2E9DB] border border-[#3F2021] px-5 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none cursor-pointer"
                    >
                      СМОТРЕТЬ ВСЕ БРЕНДЫ ({allBrands.length}) ↗
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Brands Tabs / Chips */}
                <div className="flex flex-wrap gap-2 border-b border-[#3F2021]/20 pb-4">
                  {myBrands.map((b) => {
                    const isSelected = b.brand.id === selectedBrandId;
                    const isDeleted = Boolean(b.brand.is_deleted);
                    return (
                      <button
                        key={b.brand.id}
                        type="button"
                        onClick={() => setSelectedBrandId(b.brand.id)}
                        className={`px-4 py-2.5 text-xs font-sans uppercase tracking-wider border transition-colors flex items-center gap-2 rounded-none cursor-pointer ${
                          isSelected
                            ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                            : 'bg-[#FFFFFF] border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                        }`}
                      >
                        <span>{b.brand.name}</span>
                        <span
                          className={`text-[9px] px-1.5 py-0.2 font-mono font-bold tracking-wider ${
                            isSelected ? 'bg-[#F2E9DB] text-[#3F2021]' : 'bg-[#3F2021] text-[#F2E9DB]'
                          }`}
                        >
                          {b.role === 'representative' ? 'ПРЕДСТАВИТЕЛЬ' : 'МОДЕРАТОР'}
                        </span>
                        {isDeleted && (
                          <span className="text-[9px] text-[#FF8562] font-semibold">
                            [СНЯТ]
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>

            {selectedBrand && (
              <div className="space-y-8">
                {/* Brand Overview Card */}
                <div className="bg-[#FFFFFF] border border-[#3F2021] p-6 sm:p-8 space-y-6 rounded-none">
                  {/* Top Bar for Selected Brand */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
                    <div className="flex items-center gap-4">
                      {selectedBrand.logo_url ? (
                        <img
                          src={formatImageUrl(selectedBrand.logo_url, selectedBrand.name)}
                          alt={selectedBrand.name}
                          className="w-16 h-16 object-cover border border-[#3F2021] rounded-none"
                        />
                      ) : (
                        <div className="w-16 h-16 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-center font-serif text-xl text-[#3F2021] font-bold rounded-none select-none">
                          {selectedBrand.name.slice(0, 2).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="font-serif text-2xl md:text-3xl uppercase tracking-wider text-[#3F2021]">
                            {selectedBrand.name}
                          </h2>
                          <span className="bg-[#3F2021] text-[#F2E9DB] text-[10px] font-mono uppercase px-2 py-0.5 tracking-wider font-semibold">
                            {myRoleInSelectedBrand === 'representative' ? 'ПРЕДСТАВИТЕЛЬ' : 'МОДЕРАТОР'}
                          </span>
                        </div>
                        <div className="text-[11px] font-mono text-[#3F2021]/60 mt-0.5">
                          SLUG: {selectedBrand.slug} · СОЗДАН: {formatDate(selectedBrand.created_at)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <Link
                        to={`/brands/${selectedBrand.slug}`}
                        className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-3.5 py-1.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none inline-block whitespace-nowrap"
                      >
                        СТРАНИЦА БРЕНДА ↗
                      </Link>

                      {/* Button to surrender role */}
                      <button
                        type="button"
                        onClick={() => setShowSelfRemovalConfirm(true)}
                        className="border border-[#3F2021]/40 text-[#3F2021]/80 hover:bg-[#3F2021] hover:text-[#F2E9DB] px-3 py-1.5 text-xs font-sans uppercase tracking-widest transition-colors rounded-none whitespace-nowrap"
                      >
                        СНЯТЬ С СЕБЯ РОЛЬ
                      </button>
                    </div>
                  </div>

                  {/* Warning if brand is deleted */}
                  {selectedBrand.is_deleted && (
                    <div className="p-4 bg-[#3F2021] text-[#F2E9DB] border border-[#3F2021] space-y-1 rounded-none">
                      <div className="text-xs font-mono uppercase tracking-widest font-bold text-[#FF8562]">
                        ( ВНИМАНИЕ ) БРЕНД СНЯТ С ПРОДАЖИ
                      </div>
                      <p className="text-xs font-sans uppercase tracking-wider text-[#F2E9DB]/80">
                        Товары этого бренда скрыты из каталога, заказ товаров невозможен.
                      </p>
                    </div>
                  )}

                  {/* Inline Warning for Self-Removal */}
                  {showSelfRemovalConfirm && (
                    <div className="p-4 border border-[#3F2021] bg-[#F2E9DB] space-y-3 rounded-none">
                      <div className="text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                        {isLastRepresentative ? (
                          <span className="text-[#3F2021] font-bold">
                            ВЫ ПОСЛЕДНИЙ ПРЕДСТАВИТЕЛЬ. Снятие роли удалит бренд и снимет все его товары с продажи.
                          </span>
                        ) : (
                          <span>Вы уверены, что хотите выйти из команды бренда «{selectedBrand.name}»?</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          disabled={selfRemovalMutation.isPending}
                          onClick={() => selfRemovalMutation.mutate()}
                          className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none disabled:opacity-50"
                        >
                          {selfRemovalMutation.isPending
                            ? 'СНЯТИЕ РОЛИ...'
                            : isLastRepresentative
                            ? 'ПОДТВЕРДИТЬ СНЯТИЕ И УДАЛЕНИЕ БРЕНДА'
                            : 'ПОДТВЕРДИТЬ ВЫХОД ИЗ КОМАНДЫ'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowSelfRemovalConfirm(false)}
                          className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2 text-xs font-sans uppercase tracking-widest transition-colors rounded-none"
                        >
                          ОТМЕНА
                        </button>
                      </div>
                    </div>
                  )}

                  {/* PROFILE EDIT SECTION */}
                  <div className="space-y-4 pt-2">
                    <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-2">
                      <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                        ( ПРОФИЛЬ БРЕНДА )
                      </span>
                      {!isRepresentative && (
                        <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60">
                          ( ТОЛЬКО ДЛЯ ЧТЕНИЯ: Редактирование доступно представителю )
                        </span>
                      )}
                    </div>

                    {profileMessage && (
                      <div className="text-xs text-emerald-800 bg-emerald-100/60 p-2.5 border border-emerald-800/20 font-sans">
                        {profileMessage}
                      </div>
                    )}
                    {profileError && (
                      <div className="text-xs text-red-700 bg-red-100/60 p-2.5 border border-red-700/20 font-sans">
                        {profileError}
                      </div>
                    )}

                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (isRepresentative) updateProfileMutation.mutate();
                      }}
                      className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl"
                    >
                      <div>
                        <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold mb-1">
                          НАЗВАНИЕ БРЕНДА
                        </label>
                        <input
                          type="text"
                          disabled={!isRepresentative || selectedBrand.is_deleted}
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2 text-xs font-sans uppercase tracking-wider text-[#000000] outline-none disabled:opacity-60 rounded-none"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold mb-1">
                          ССЫЛКА НА РЕСУРС (HISURL)
                        </label>
                        <input
                          type="url"
                          disabled={!isRepresentative || selectedBrand.is_deleted}
                          placeholder="HTTPS://BRAND.COM"
                          value={editHisUrl}
                          onChange={(e) => setEditHisUrl(e.target.value)}
                          className="w-full bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2 text-xs font-sans tracking-wider text-[#000000] outline-none disabled:opacity-60 rounded-none"
                        />
                      </div>

                      {isRepresentative && !selectedBrand.is_deleted && (
                        <div className="md:col-span-2">
                          <label className="block text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold mb-1">
                            ОБНОВИТЬ ЛОГОТИП / ФОТО БРЕНДА
                          </label>
                          <input
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
                            className="w-full text-xs font-sans text-[#3F2021] file:mr-4 file:py-2 file:px-4 file:border file:border-[#3F2021] file:text-xs file:font-sans file:uppercase file:bg-[#3F2021] file:text-[#F2E9DB] file:cursor-pointer hover:file:bg-[#2B1516] rounded-none cursor-pointer"
                          />
                        </div>
                      )}

                      {isRepresentative && !selectedBrand.is_deleted && (
                        <div className="md:col-span-2 pt-1">
                          <button
                            type="submit"
                            disabled={updateProfileMutation.isPending}
                            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-widest font-semibold transition-colors disabled:opacity-50 rounded-none"
                          >
                            {updateProfileMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ИЗМЕНЕНИЯ ПРОФИЛЯ ✓'}
                          </button>
                        </div>
                      )}
                    </form>
                  </div>

                  {/* BRAND TEAM SECTION */}
                  <div className="space-y-4 pt-6 border-t border-[#3F2021]/15">
                    <div className="flex items-center justify-between border-b border-[#3F2021]/15 pb-2">
                      <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                        ( КОМАНДА БРЕНДА: ПРЕДСТАВИТЕЛИ И МОДЕРАТОРЫ )
                      </span>
                      <span className="text-[11px] font-mono text-[#3F2021]/70">
                        ВСЕГО УЧАСТНИКОВ: {members.length}
                      </span>
                    </div>

                    {memberMessage && (
                      <div className="text-xs text-emerald-800 bg-emerald-100/60 p-2.5 border border-emerald-800/20 font-sans">
                        {memberMessage}
                      </div>
                    )}
                    {memberError && (
                      <div className="text-xs text-red-700 bg-red-100/60 p-2.5 border border-red-700/20 font-sans">
                        {memberError}
                      </div>
                    )}

                    {/* Members List Table */}
                    {isMembersLoading ? (
                      <div className="p-6 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
                        ( ЗАГРУЗКА УЧАСТНИКОВ... )
                      </div>
                    ) : (
                      <div className="border border-[#3F2021]/20 divide-y divide-[#3F2021]/15">
                        {members.map((m) => {
                          const isSelf = m.user_id === user?.id;
                          const isRep = m.role === 'representative';

                          return (
                            <div
                              key={m.user_id}
                              className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#F2E9DB]/20"
                            >
                              <div className="flex items-center gap-3">
                                <span className="font-mono text-sm font-bold text-[#3F2021]">
                                  @{m.user_login || 'anonymous'}
                                </span>
                                {isSelf && (
                                  <span className="text-[10px] font-mono text-[#3F2021]/60">
                                    (ВЫ)
                                  </span>
                                )}
                                <span
                                  className={`text-[10px] font-mono uppercase px-2 py-0.5 tracking-wider font-semibold ${
                                    isRep ? 'bg-[#3F2021] text-[#F2E9DB]' : 'border border-[#3F2021] text-[#3F2021]'
                                  }`}
                                >
                                  {isRep ? 'ПРЕДСТАВИТЕЛЬ' : 'МОДЕРАТОР'}
                                </span>
                              </div>

                              {/* Representative controls for managing members */}
                              {isRepresentative && !selectedBrand.is_deleted && (
                                <div className="flex items-center gap-2">
                                  {/* Change role button */}
                                  <button
                                    type="button"
                                    disabled={changeRoleMutation.isPending}
                                    onClick={() =>
                                      changeRoleMutation.mutate({
                                        member: m,
                                        newRole: isRep ? 'moderator' : 'representative',
                                      })
                                    }
                                    className="border border-[#3F2021]/40 text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors rounded-none"
                                    title={isRep ? 'Понизить до модератора' : 'Повысить до представителя'}
                                  >
                                    {isRep ? 'СДЕЛАТЬ МОДЕРАТОРОМ' : 'СДЕЛАТЬ ПРЕДСТАВИТЕЛЕМ'}
                                  </button>

                                  {/* Remove member button */}
                                  {!isSelf && (
                                    <button
                                      type="button"
                                      disabled={removeMemberMutation.isPending}
                                      onClick={() => removeMemberMutation.mutate(m.user_id)}
                                      className="border border-red-700/60 text-red-700 hover:bg-red-700 hover:text-[#FFFFFF] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors rounded-none"
                                    >
                                      × ИСКЛЮЧИТЬ
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Add Member Form (for representatives) */}
                    {isRepresentative && !selectedBrand.is_deleted && (
                      <div className="pt-3 border-t border-[#3F2021]/15 space-y-3">
                        <div className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021] font-semibold">
                          ДОБАВИТЬ УЧАСТНИКА В КОМАНДУ
                        </div>
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            addMemberMutation.mutate();
                          }}
                          className="flex flex-col sm:flex-row gap-3 max-w-2xl"
                        >
                          <input
                            type="text"
                            required
                            placeholder="@LOGIN ПОЛЬЗОВАТЕЛЯ"
                            value={memberLogin}
                            onChange={(e) => setMemberLogin(e.target.value)}
                            className="flex-1 bg-[#F2E9DB]/30 border border-[#3F2021]/40 focus:border-[#3F2021] px-3.5 py-2 text-xs font-sans tracking-wider text-[#000000] outline-none rounded-none"
                          />

                          <select
                            value={memberRole}
                            onChange={(e) => setMemberRole(e.target.value as 'representative' | 'moderator')}
                            className="bg-[#FFFFFF] border border-[#3F2021]/40 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
                          >
                            <option value="moderator">МОДЕРАТОР БРЕНДА</option>
                            <option value="representative">ПРЕДСТАВИТЕЛЬ БРЕНДА</option>
                          </select>

                          <button
                            type="submit"
                            disabled={addMemberMutation.isPending}
                            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2 text-xs font-sans uppercase tracking-widest font-semibold transition-colors disabled:opacity-50 rounded-none whitespace-nowrap"
                          >
                            {addMemberMutation.isPending ? 'ДОБАВЛЕНИЕ...' : '+ ДОБАВИТЬ'}
                          </button>
                        </form>
                      </div>
                    )}
                  </div>

                  {/* BRAND DELETION SECTION (FOR REPRESENTATIVES) */}
                  {isRepresentative && !selectedBrand.is_deleted && (
                    <div className="pt-6 border-t border-[#3F2021]/15 space-y-3">
                      <div className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]">
                        ( СНЯТИЕ БРЕНДА С ПРОДАЖИ )
                      </div>

                      {!showDeleteBrandConfirm ? (
                        <button
                          type="button"
                          onClick={() => setShowDeleteBrandConfirm(true)}
                          className="border border-red-700 text-red-700 hover:bg-red-700 hover:text-[#FFFFFF] px-4 py-2 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none"
                        >
                          УДАЛИТЬ БРЕНД
                        </button>
                      ) : (
                        <div className="p-4 border border-red-700/60 bg-red-50 space-y-3 rounded-none">
                          <div className="text-xs font-sans uppercase tracking-wider text-red-800 font-semibold">
                            ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ БРЕНД «{selectedBrand.name}»? БРЕНД И ВСЕ ЕГО ТОВАРЫ БУДУТ СНЯТЫ С ПРОДАЖИ. ДЕЙСТВИЕ НЕОБРАТИМО.
                          </div>
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              disabled={deleteBrandMutation.isPending}
                              onClick={() => deleteBrandMutation.mutate()}
                              className="bg-red-700 text-[#FFFFFF] hover:bg-red-800 px-4 py-2 text-xs font-sans uppercase tracking-widest font-semibold transition-colors rounded-none disabled:opacity-50"
                            >
                              {deleteBrandMutation.isPending ? 'УДАЛЕНИЕ...' : 'ПОДТВЕРДИТЬ УДАЛЕНИЕ'}
                            </button>
                            <button
                              type="button"
                              onClick={() => setShowDeleteBrandConfirm(false)}
                              className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-4 py-2 text-xs font-sans uppercase tracking-widest transition-colors rounded-none"
                            >
                              ОТМЕНА
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </>
    )}
      </div>
    </div>
  );
}

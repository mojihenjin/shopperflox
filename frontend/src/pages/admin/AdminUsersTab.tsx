import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { formatDate } from '../../utils/format';
import type { AdminUserResponse } from '../../types/api';
import type { ApiError } from '../../api/client';

const PAGE_SIZE = 20;

const BASE_PERMISSIONS = [
  '*',
  'admin:access',
  'creator:products',
  'creator:brand',
  'mod:approve_manager',
  'catalog:manage',
  'orders:manage',
];

interface AdminUsersTabProps {
  onFeedback: (msg: string) => void;
}

export function AdminUsersTab({ onFeedback }: AdminUsersTabProps) {
  const queryClient = useQueryClient();

  // Filters & Sorting state
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'banned' | 'unbanned' | 'deleted'>('all');
  const [verifiedFilter, setVerifiedFilter] = useState<'all' | 'verified' | 'unverified'>('all');
  const [sortBy, setSortBy] = useState<'created_at' | 'login'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);

  // Inline action states
  const [editingLoginId, setEditingLoginId] = useState<string | null>(null);
  const [newLoginInput, setNewLoginInput] = useState('');

  const [editingPermsId, setEditingPermsId] = useState<string | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);
  const [customPermInput, setCustomPermInput] = useState('');

  const [banningUserId, setBanningUserId] = useState<string | null>(null);
  const [banReasonInput, setBanReasonInput] = useState('');

  const [confirmResetId, setConfirmResetId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Fetch Users
  const { data: usersData, isLoading, error } = useQuery({
    queryKey: [
      'adminUsers',
      searchQuery,
      statusFilter,
      verifiedFilter,
      sortBy,
      sortOrder,
      page,
    ],
    queryFn: () =>
      adminApi.listUsers({
        search: searchQuery.trim() || undefined,
        status: statusFilter,
        verified_profile:
          verifiedFilter === 'all'
            ? undefined
            : verifiedFilter === 'verified',
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      }),
  });

  const users = usersData?.data || [];

  // Mutations
  const updateMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: { login?: string; verified_profile?: boolean; global_permissions?: string[] } }) =>
      adminApi.updateUser(userId, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      setEditingLoginId(null);
      setEditingPermsId(null);
      if (vars.data.login) onFeedback(`Логин успешно изменён на @${vars.data.login}`);
      else if (vars.data.verified_profile !== undefined) onFeedback('Статус верификации обновлён');
      else if (vars.data.global_permissions) onFeedback('Привилегии пользователя обновлены');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка обновления пользователя');
    },
  });

  const banMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason: string }) =>
      adminApi.banUser(userId, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      setBanningUserId(null);
      setBanReasonInput('');
      onFeedback('Пользователь успешно заблокирован');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка блокировки пользователя');
    },
  });

  const unbanMutation = useMutation({
    mutationFn: (userId: string) => adminApi.unbanUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      onFeedback('Пользователь успешно разблокирован');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка разблокировки');
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (userId: string) => adminApi.resetPassword(userId),
    onSuccess: () => {
      setConfirmResetId(null);
      onFeedback('✓ Новый пароль сгенерирован и отправлен на email пользователя');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка сброса пароля');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => adminApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      setConfirmDeleteId(null);
      onFeedback('Пользователь удалён');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка удаления пользователя');
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
    setPage(1);
  };

  const handleTogglePerm = (perm: string) => {
    if (selectedPerms.includes(perm)) {
      setSelectedPerms(selectedPerms.filter((p) => p !== perm));
    } else {
      setSelectedPerms([...selectedPerms, perm]);
    }
  };

  const handleAddCustomPerm = () => {
    const val = customPermInput.trim();
    if (val && !selectedPerms.includes(val)) {
      setSelectedPerms([...selectedPerms, val]);
      setCustomPermInput('');
    }
  };

  return (
    <div className="space-y-6">
      {/* Control / Filter Bar */}
      <div className="bg-[#FFFFFF] border border-[#3F2021] p-4 sm:p-6 space-y-4 rounded-none">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-lg">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="ПОИСК ПО @LOGIN ИЛИ EMAIL..."
              className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
            />
            <button
              type="submit"
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold whitespace-nowrap transition-colors rounded-none"
            >
              ИСКАТЬ ↗
            </button>
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  setSearchQuery('');
                  setPage(1);
                }}
                className="text-xs text-[#3F2021]/60 hover:text-[#3F2021] px-2 font-mono"
              >
                ×
              </button>
            )}
          </form>

          {/* Sorting */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 select-none">
              СОРТИРОВКА:
            </span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as 'created_at' | 'login');
                setPage(1);
              }}
              className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
            >
              <option value="created_at">ДАТЕ СОЗДАНИЯ</option>
              <option value="login">ЛОГИНУ</option>
            </select>

            <button
              type="button"
              onClick={() => {
                setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                setPage(1);
              }}
              className="border border-[#3F2021]/30 hover:border-[#3F2021] bg-[#F2E9DB]/20 px-3 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold transition-colors rounded-none"
              title="Переключить направление сортировки"
            >
              {sortOrder === 'desc' ? '↓ НОВЫЕ / УБЫВ.' : '↑ СТАРЫЕ / ВОЗР.'}
            </button>
          </div>
        </div>

        {/* Status and Verification quick filters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 mr-1 select-none">
              СТАТУС:
            </span>
            {(
              [
                { id: 'all', label: 'ВСЕ' },
                { id: 'active', label: 'АКТИВНЫЕ' },
                { id: 'banned', label: 'ЗАБАНЕННЫЕ' },
                { id: 'unbanned', label: 'БЕЗ ЗАБАНЕННЫХ' },
                { id: 'deleted', label: 'УДАЛЁННЫЕ' },
              ] as const
            ).map((st) => (
              <button
                key={st.id}
                type="button"
                onClick={() => {
                  setStatusFilter(st.id);
                  setPage(1);
                }}
                className={`px-2.5 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                  statusFilter === st.id
                    ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                    : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 mr-1 select-none">
              ВЕРИФИКАЦИЯ:
            </span>
            {(
              [
                { id: 'all', label: 'ВСЕ' },
                { id: 'verified', label: 'ВЕРИФИЦИРОВАННЫЕ' },
                { id: 'unverified', label: 'НЕ ВЕРИФИЦИРОВАННЫЕ' },
              ] as const
            ).map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => {
                  setVerifiedFilter(v.id);
                  setPage(1);
                }}
                className={`px-2.5 py-1 text-xs font-sans uppercase tracking-wider border transition-colors rounded-none ${
                  verifiedFilter === v.id
                    ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
                    : 'border-[#3F2021]/30 text-[#3F2021] hover:border-[#3F2021]'
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Users List */}
      {isLoading ? (
        <div className="py-20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 bg-[#FFFFFF] border border-[#3F2021]/20">
          ( ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ... )
        </div>
      ) : error ? (
        <div className="p-8 text-center border border-[#3F2021]/20 bg-[#FFFFFF]">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ОШИБКА ЗАГРУЗКИ ПОЛЬЗОВАТЕЛЕЙ
          </div>
        </div>
      ) : users.length === 0 ? (
        <div className="p-12 text-center border border-[#3F2021]/20 bg-[#FFFFFF] space-y-2">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ПОЛЬЗОВАТЕЛИ НЕ НАЙДЕНЫ
          </div>
          <p className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            Попробуйте изменить параметры поиска или фильтрации
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {users.map((user: AdminUserResponse) => {
            const isEditingLogin = editingLoginId === user.id;
            const isEditingPerms = editingPermsId === user.id;
            const isBanning = banningUserId === user.id;
            const isResetting = confirmResetId === user.id;
            const isDeleting = confirmDeleteId === user.id;

            return (
              <div
                key={user.id}
                className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4 sm:p-5 space-y-3.5 rounded-none"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3F2021]/15 pb-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    {/* Login display or inline rename input */}
                    {isEditingLogin ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={newLoginInput}
                          onChange={(e) => setNewLoginInput(e.target.value)}
                          className="bg-[#F2E9DB]/40 border border-[#3F2021] px-2 py-1 text-sm font-mono font-bold text-[#3F2021] outline-none uppercase"
                        />
                        <button
                          type="button"
                          disabled={updateMutation.isPending || !newLoginInput.trim()}
                          onClick={() =>
                            updateMutation.mutate({
                              userId: user.id,
                              data: { login: newLoginInput.trim() },
                            })
                          }
                          className="bg-[#3F2021] text-[#F2E9DB] px-3 py-1 text-xs font-sans uppercase tracking-wider font-semibold transition-colors"
                        >
                          ✓ СОХРАНИТЬ
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingLoginId(null)}
                          className="text-xs font-sans uppercase text-[#3F2021]/60 hover:text-[#3F2021] px-2"
                        >
                          ×
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-base font-bold text-[#3F2021]">
                          @{user.login}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingLoginId(user.id);
                            setNewLoginInput(user.login);
                          }}
                          className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/60 hover:text-[#3F2021] underline underline-offset-2"
                        >
                          ПЕРЕИМЕНОВАТЬ
                        </button>
                      </div>
                    )}

                    {/* Email */}
                    <span className="text-xs font-mono text-[#3F2021]/70">
                      [{user.email || 'БЕЗ EMAIL'}]
                    </span>

                    {/* Verification Badge */}
                    {user.verified_profile ? (
                      <span className="inline-flex items-center gap-1 bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[10px] font-sans font-bold uppercase tracking-wider">
                        <span>✓</span> ВЕРИФИЦИРОВАН
                      </span>
                    ) : (
                      <span className="text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/50 border border-[#3F2021]/20 px-2 py-0.5">
                        НЕ ВЕРИФ
                      </span>
                    )}

                    {/* Active Ban Badge */}
                    {user.active_ban && (
                      <span className="bg-red-700 text-[#FFFFFF] px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider">
                        БАН: {user.active_ban.reason}
                      </span>
                    )}

                    {/* Deleted Badge */}
                    {user.is_deleted && (
                      <span className="bg-[#3F2021]/20 text-red-800 border border-red-800/40 px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider">
                        УДАЛЁН
                      </span>
                    )}
                  </div>

                  {/* Registered date */}
                  <div className="text-[11px] font-mono text-[#3F2021]/60">
                    РЕГИСТРАЦИЯ: {formatDate(user.created_at)}
                  </div>
                </div>

                {/* Permissions & Roles display */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 select-none">
                      ПРАВА:
                    </span>
                    {user.global_permissions && user.global_permissions.length > 0 ? (
                      user.global_permissions.map((p) => (
                        <span
                          key={p}
                          className="bg-[#3F2021] text-[#F2E9DB] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider"
                        >
                          {p}
                        </span>
                      ))
                    ) : (
                      <span className="text-[10px] font-sans uppercase text-[#3F2021]/50">
                        ПОКУПАТЕЛЬ (НЕТ ОСОБЫХ ПРАВ)
                      </span>
                    )}
                  </div>

                  {/* Top action buttons */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => {
                        if (isEditingPerms) {
                          setEditingPermsId(null);
                        } else {
                          setEditingPermsId(user.id);
                          setSelectedPerms(user.global_permissions || []);
                          setCustomPermInput('');
                        }
                      }}
                      className="border border-[#3F2021] text-[#3F2021] hover:bg-[#3F2021] hover:text-[#F2E9DB] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors"
                    >
                      {isEditingPerms ? 'СКРЫТЬ ПРАВА ×' : 'ПРИВИЛЕГИИ ↗'}
                    </button>

                    <button
                      type="button"
                      disabled={updateMutation.isPending}
                      onClick={() =>
                        updateMutation.mutate({
                          userId: user.id,
                          data: { verified_profile: !user.verified_profile },
                        })
                      }
                      className="border border-[#3F2021]/40 text-[#3F2021] hover:border-[#3F2021] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors"
                    >
                      {user.verified_profile ? 'СНЯТЬ ВЕРИФ' : 'ВЕРИФИЦИРОВАТЬ ✓'}
                    </button>

                    <button
                      type="button"
                      onClick={() => setConfirmResetId(isResetting ? null : user.id)}
                      className="border border-[#3F2021]/40 text-[#3F2021] hover:border-[#3F2021] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider transition-colors"
                    >
                      СБРОСИТЬ ПАРОЛЬ
                    </button>

                    {user.active_ban ? (
                      <button
                        type="button"
                        disabled={unbanMutation.isPending}
                        onClick={() => unbanMutation.mutate(user.id)}
                        className="bg-emerald-800 text-[#FFFFFF] hover:bg-emerald-900 px-3 py-1 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors"
                      >
                        РАЗБАНИТЬ ✓
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setBanningUserId(isBanning ? null : user.id);
                          setBanReasonInput('');
                        }}
                        className="border border-red-700 text-red-700 hover:bg-red-700 hover:text-[#FFFFFF] px-2.5 py-1 text-[11px] font-sans uppercase tracking-wider font-semibold transition-colors"
                      >
                        ЗАБАНИТЬ
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(isDeleting ? null : user.id)}
                      className="text-red-700 hover:text-red-900 text-xs px-2 font-mono uppercase"
                      title="Удалить аккаунт"
                    >
                      УДАЛИТЬ ×
                    </button>
                  </div>
                </div>

                {/* Inline Permissions Panel */}
                {isEditingPerms && (
                  <div className="p-4 bg-[#F2E9DB]/50 border border-[#3F2021]/20 space-y-3">
                    <div className="text-[11px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                      ( РЕДАКТИРОВАНИЕ ПРИВИЛЕГИЙ ПОЛЬЗОВАТЕЛЯ @{user.login} )
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {BASE_PERMISSIONS.map((perm) => {
                        const isChecked = selectedPerms.includes(perm);
                        return (
                          <button
                            key={perm}
                            type="button"
                            onClick={() => handleTogglePerm(perm)}
                            className={`px-2.5 py-1 text-xs font-mono uppercase tracking-wider border transition-colors ${
                              isChecked
                                ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-bold'
                                : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
                            }`}
                          >
                            {isChecked ? '✓ ' : '+ '}
                            {perm}
                          </button>
                        );
                      })}
                    </div>

                    {/* Custom permission input */}
                    <div className="flex items-center gap-2 pt-1 max-w-md">
                      <input
                        type="text"
                        placeholder="КАСТОМНОЕ ПРАВО (НАПР. brand:slug)..."
                        value={customPermInput}
                        onChange={(e) => setCustomPermInput(e.target.value)}
                        className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1 text-xs font-mono uppercase outline-none"
                      />
                      <button
                        type="button"
                        onClick={handleAddCustomPerm}
                        className="bg-[#3F2021] text-[#F2E9DB] px-3 py-1 text-xs font-sans uppercase tracking-wider whitespace-nowrap"
                      >
                        + ДОБАВИТЬ
                      </button>
                    </div>

                    <div className="flex items-center gap-3 pt-2">
                      <button
                        type="button"
                        disabled={updateMutation.isPending}
                        onClick={() =>
                          updateMutation.mutate({
                            userId: user.id,
                            data: { global_permissions: selectedPerms },
                          })
                        }
                        className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors"
                      >
                        {updateMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ПРАВА ↗'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingPermsId(null)}
                        className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 hover:text-[#3F2021]"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}

                {/* Inline Ban Reason Panel */}
                {isBanning && (
                  <div className="p-4 bg-red-50 border border-red-700/30 space-y-3">
                    <div className="text-xs font-sans font-semibold uppercase tracking-wider text-red-900">
                      ( БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ @{user.login} )
                    </div>
                    <input
                      type="text"
                      placeholder="УКАЖИТЕ ПРИЧИНУ БАНА (ОБЯЗАТЕЛЬНО)..."
                      value={banReasonInput}
                      onChange={(e) => setBanReasonInput(e.target.value)}
                      className="w-full bg-[#FFFFFF] border border-red-700/40 focus:border-red-700 px-3 py-2 text-xs font-sans uppercase outline-none text-[#3F2021]"
                    />
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        disabled={banMutation.isPending || !banReasonInput.trim()}
                        onClick={() =>
                          banMutation.mutate({
                            userId: user.id,
                            reason: banReasonInput.trim(),
                          })
                        }
                        className="bg-red-700 text-[#FFFFFF] hover:bg-red-800 px-4 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold disabled:opacity-50 transition-colors"
                      >
                        {banMutation.isPending ? 'БЛОКИРОВКА...' : 'ПОДТВЕРДИТЬ БАН'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setBanningUserId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021]/60 hover:text-[#3F2021]"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}

                {/* Inline Reset Password Confirm */}
                {isResetting && (
                  <div className="p-3 bg-[#F2E9DB] border border-[#3F2021] flex items-center justify-between gap-4">
                    <span className="text-xs font-sans uppercase text-[#3F2021]">
                      Сгенерировать новый пароль и отправить на email <strong>{user.email || 'аккаунта'}</strong>?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={resetPasswordMutation.isPending}
                        onClick={() => resetPasswordMutation.mutate(user.id)}
                        className="bg-[#3F2021] text-[#F2E9DB] px-3 py-1 text-xs font-sans uppercase tracking-wider font-semibold"
                      >
                        {resetPasswordMutation.isPending ? 'СБРОС...' : 'ДА, СБРОСИТЬ'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmResetId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021]/70 hover:text-[#3F2021] px-2"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}

                {/* Inline Delete Confirm */}
                {isDeleting && (
                  <div className="p-3 bg-red-100 border border-red-700 flex items-center justify-between gap-4">
                    <span className="text-xs font-sans uppercase text-red-900 font-semibold">
                      ВНИМАНИЕ: Безвозвратно удалить пользователя @{user.login}?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(user.id)}
                        className="bg-red-700 text-[#FFFFFF] px-3 py-1 text-xs font-sans uppercase tracking-wider font-bold"
                      >
                        {deleteMutation.isPending ? 'УДАЛЕНИЕ...' : 'ПОДТВЕРДИТЬ УДАЛЕНИЕ'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021]/70 hover:text-[#3F2021] px-2"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-[#3F2021]/20 pt-4">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
          className="border border-[#3F2021] px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors"
        >
          ← ПРЕДЫДУЩАЯ
        </button>
        <span className="text-xs font-mono uppercase text-[#3F2021]/70">
          СТРАНИЦА {page}
        </span>
        <button
          type="button"
          disabled={users.length < PAGE_SIZE}
          onClick={() => setPage(page + 1)}
          className="border border-[#3F2021] px-4 py-2 text-xs font-sans uppercase tracking-wider disabled:opacity-30 hover:bg-[#3F2021] hover:text-[#F2E9DB] transition-colors"
        >
          СЛЕДУЮЩАЯ →
        </button>
      </div>
    </div>
  );
}

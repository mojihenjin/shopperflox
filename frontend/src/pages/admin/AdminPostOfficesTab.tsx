import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { formatApiError } from '../../utils/errorMapper';
import type { PostOfficeResponse, PostOfficeCreateRequest, PostOfficeUpdateRequest } from '../../types/api';
import type { ApiError } from '../../api/client';

interface AdminPostOfficesTabProps {
  onFeedback: (msg: string) => void;
}

export function AdminPostOfficesTab({ onFeedback }: AdminPostOfficesTabProps) {
  const queryClient = useQueryClient();

  // Search state
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Add form state
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [newCountry, setNewCountry] = useState('Россия');
  const [newRegion, setNewRegion] = useState('');
  const [newCity, setNewCity] = useState('');
  const [newHouse, setNewHouse] = useState('');
  const [newPostalCode, setNewPostalCode] = useState('');
  const [newNote, setNewNote] = useState('');
  const [newIsActive, setNewIsActive] = useState(true);
  const [addError, setAddError] = useState<string | null>(null);

  // Edit item state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editCountry, setEditCountry] = useState('');
  const [editRegion, setEditRegion] = useState('');
  const [editCity, setEditCity] = useState('');
  const [editHouse, setEditHouse] = useState('');
  const [editPostalCode, setEditPostalCode] = useState('');
  const [editNote, setEditNote] = useState('');
  const [editIsActive, setEditIsActive] = useState(true);
  const [editError, setEditError] = useState<string | null>(null);

  // Delete confirmation state
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Query post offices
  const { data: postOfficesData, isLoading, error } = useQuery({
    queryKey: ['adminPostOffices', searchQuery],
    queryFn: () => adminApi.listPostOffices({ search: searchQuery.trim() || undefined }),
  });

  const postOffices = postOfficesData?.data || [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: PostOfficeCreateRequest) => adminApi.createPostOffice(data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['adminPostOffices'] });
      onFeedback(`✓ ПОЧТОВОЕ ОТДЕЛЕНИЕ «${res.data.name}» УСПЕШНО СОЗДАНО`);
      setIsAdding(false);
      setNewName('');
      setNewCountry('Россия');
      setNewRegion('');
      setNewCity('');
      setNewHouse('');
      setNewPostalCode('');
      setNewNote('');
      setNewIsActive(true);
      setAddError(null);
    },
    onError: (err: ApiError) => {
      setAddError(formatApiError(err, 'ОШИБКА СОЗДАНИЯ ПОЧТОВОГО ОТДЕЛЕНИЯ'));
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: PostOfficeUpdateRequest }) =>
      adminApi.updatePostOffice(id, data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['adminPostOffices'] });
      onFeedback(`✓ ПОЧТОВОЕ ОТДЕЛЕНИЕ «${res.data.name}» ОБНОВЛЕНО`);
      setEditingId(null);
      setEditError(null);
    },
    onError: (err: ApiError) => {
      setEditError(formatApiError(err, 'ОШИБКА ОБНОВЛЕНИЯ ПОЧТОВОГО ОТДЕЛЕНИЯ'));
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deletePostOffice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminPostOffices'] });
      onFeedback('✓ ПОЧТОВОЕ ОТДЕЛЕНИЕ УДАЛЕНО');
      setConfirmDeleteId(null);
    },
    onError: (err: ApiError) => {
      onFeedback(formatApiError(err, 'ОШИБКА УДАЛЕНИЯ ПОЧТОВОГО ОТДЕЛЕНИЯ'));
      setConfirmDeleteId(null);
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchQuery('');
  };

  const handleStartEdit = (office: PostOfficeResponse) => {
    setEditingId(office.id);
    setEditName(office.name);
    setEditCountry(office.country || 'Россия');
    setEditRegion(office.region || '');
    setEditCity(office.city);
    setEditHouse(office.house);
    setEditPostalCode(office.postal_code);
    setEditNote(office.note || '');
    setEditIsActive(office.is_active);
    setEditError(null);
  };

  const handleSaveEdit = (id: string) => {
    if (!editName.trim() || !editCity.trim() || !editHouse.trim() || !editPostalCode.trim()) {
      setEditError('Заполните все обязательные поля (Название, Город, Дом, Пост-код)');
      return;
    }
    updateMutation.mutate({
      id,
      data: {
        name: editName.trim(),
        country: editCountry.trim() || 'Россия',
        region: editRegion.trim() || null,
        city: editCity.trim(),
        house: editHouse.trim(),
        postal_code: editPostalCode.trim(),
        note: editNote.trim() || null,
        is_active: editIsActive,
      },
    });
  };

  const handleToggleActive = (office: PostOfficeResponse) => {
    updateMutation.mutate({
      id: office.id,
      data: { is_active: !office.is_active },
    });
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newCity.trim() || !newHouse.trim() || !newPostalCode.trim()) {
      setAddError('Заполните все обязательные поля (Название, Город, Дом, Пост-код)');
      return;
    }
    createMutation.mutate({
      name: newName.trim(),
      country: newCountry.trim() || 'Россия',
      region: newRegion.trim() || null,
      city: newCity.trim(),
      house: newHouse.trim(),
      postal_code: newPostalCode.trim(),
      note: newNote.trim() || null,
      is_active: newIsActive,
    });
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#3F2021]/15 pb-4">
        <div>
          <span className="text-[11px] font-sans font-semibold uppercase tracking-widest text-[#3F2021]/60">
            ( ЛОГИСТИКА И ПУНКТЫ ВЫДАЧИ )
          </span>
          <h2 className="font-serif text-2xl uppercase tracking-wider text-[#3F2021] mt-0.5">
            МЕНЕДЖЕР ПОЧТОВЫХ ТОЧЕК
          </h2>
        </div>

        <button
          type="button"
          onClick={() => {
            setIsAdding(!isAdding);
            setAddError(null);
          }}
          className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none self-start sm:self-auto"
        >
          {isAdding ? 'ЗАКРЫТЬ ФОРМУ ×' : '+ ДОБАВИТЬ ТОЧКУ ↗'}
        </button>
      </div>

      {/* 2. Add Post Office Form */}
      {isAdding && (
        <form
          onSubmit={handleCreateSubmit}
          className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-4 rounded-none"
        >
          <div className="border-b border-[#3F2021]/15 pb-3">
            <span className="text-xs font-sans font-bold uppercase tracking-wider text-[#3F2021]">
              ДОБАВЛЕНИЕ НОВОГО ПОЧТОВОГО ОТДЕЛЕНИЯ
            </span>
          </div>

          {addError && (
            <div className="p-3 bg-red-100 text-red-900 border border-red-300 text-xs font-sans">
              {addError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                НАЗВАНИЕ / СЛУЖБА *
              </label>
              <input
                type="text"
                required
                maxLength={255}
                placeholder="Почта России №620000 / СДЭК Екатеринбург"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                СТРАНА *
              </label>
              <input
                type="text"
                required
                maxLength={128}
                placeholder="Россия"
                value={newCountry}
                onChange={(e) => setNewCountry(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                ОБЛАСТЬ / РЕГИОН
              </label>
              <input
                type="text"
                maxLength={128}
                placeholder="Свердловская область"
                value={newRegion}
                onChange={(e) => setNewRegion(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                ГОРОД *
              </label>
              <input
                type="text"
                required
                maxLength={128}
                placeholder="Екатеринбург"
                value={newCity}
                onChange={(e) => setNewCity(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                ДОМ / АДРЕС *
              </label>
              <input
                type="text"
                required
                maxLength={64}
                placeholder="Главпочтамт, 1 / ул. Ленина, д. 10"
                value={newHouse}
                onChange={(e) => setNewHouse(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
              />
            </div>

            <div>
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                ПОСТ-КОД (ИНДЕКС) *
              </label>
              <input
                type="text"
                required
                maxLength={32}
                placeholder="620000"
                value={newPostalCode}
                onChange={(e) => setNewPostalCode(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-mono outline-none rounded-none text-[#3F2021]"
              />
            </div>

            <div className="lg:col-span-2">
              <label className="block text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                ПРИМЕЧАНИЕ (ГРАФИК, ОСОБЕННОСТИ)
              </label>
              <input
                type="text"
                maxLength={500}
                placeholder="Центральное отделение, пн-вс 08:00-22:00"
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="newIsActive"
              checked={newIsActive}
              onChange={(e) => setNewIsActive(e.target.checked)}
              className="w-4 h-4 rounded-none accent-[#3F2021] cursor-pointer"
            />
            <label
              htmlFor="newIsActive"
              className="text-xs font-sans uppercase tracking-wider text-[#3F2021] cursor-pointer select-none font-semibold"
            >
              АКТИВНО ДЛЯ ВЫБОРА ПОКУПАТЕЛЯМИ
            </label>
          </div>

          <div className="flex items-center gap-3 pt-3 border-t border-[#3F2021]/15">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-6 py-2.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors disabled:opacity-50 cursor-pointer rounded-none"
            >
              {createMutation.isPending ? 'СОЗДАНИЕ...' : 'СОЗДАТЬ ТОЧКУ ↗'}
            </button>
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 hover:text-[#3F2021] px-3 py-2"
            >
              ОТМЕНА
            </button>
          </div>
        </form>
      )}

      {/* 3. Search Bar */}
      <div className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2 items-center">
          <input
            type="text"
            placeholder="ПОИСК: ГОРОД, ИНДЕКС, НАЗВАНИЕ..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1 bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans outline-none rounded-none text-[#3F2021]"
          />
          {searchInput && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="px-2 text-sm text-[#3F2021]/70 hover:text-[#3F2021] cursor-pointer"
              title="Очистить"
            >
              ×
            </button>
          )}
          <button
            type="submit"
            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors cursor-pointer rounded-none"
          >
            ИСКАТЬ ↗
          </button>
        </form>
      </div>

      {/* 4. Post Offices List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs font-sans uppercase text-[#3F2021]/70 px-1">
          <span>ВСЕГО ТОЧЕК: {postOffices.length}</span>
          {searchQuery && (
            <span>ФИЛЬТР ПО ЗАПРОСУ: «{searchQuery}»</span>
          )}
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60">
            ( ЗАГРУЗКА ПОЧТОВЫХ ТОЧЕК... )
          </div>
        ) : error ? (
          <div className="p-8 text-center border border-[#3F2021]/20 bg-[#FFFFFF] text-xs font-sans uppercase text-red-700">
            ( НЕ УДАЛОСЬ ЗАГРУЗИТЬ СПИСОК ПОЧТОВЫХ ТОЧЕК )
          </div>
        ) : postOffices.length === 0 ? (
          <div className="p-12 text-center border border-[#3F2021]/20 bg-[#FFFFFF] text-xs font-sans uppercase tracking-wider text-[#3F2021]/60">
            ( ПОЧТОВЫЕ ТОЧКИ НЕ НАЙДЕНЫ )
          </div>
        ) : (
          <div className="space-y-3">
            {postOffices.map((office) => {
              const isEditing = editingId === office.id;
              const isConfirmingDelete = confirmDeleteId === office.id;

              return (
                <div
                  key={office.id}
                  className="bg-[#FFFFFF] border border-[#3F2021] p-5 rounded-none space-y-3"
                >
                  {isEditing ? (
                    /* Inline Edit Form */
                    <div className="space-y-4">
                      <div className="border-b border-[#3F2021]/15 pb-2 flex items-center justify-between">
                        <span className="text-xs font-sans font-bold uppercase text-[#3F2021]">
                          РЕДАКТИРОВАНИЕ ПОЧТОВОГО ОТДЕЛЕНИЯ
                        </span>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="text-xs font-sans uppercase text-[#3F2021]/70 hover:text-[#3F2021]"
                        >
                          ЗАКРЫТЬ ×
                        </button>
                      </div>

                      {editError && (
                        <div className="p-2.5 bg-red-100 text-red-900 border border-red-300 text-xs font-sans">
                          {editError}
                        </div>
                      )}

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        <div className="lg:col-span-2">
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            НАЗВАНИЕ *
                          </label>
                          <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            СТРАНА *
                          </label>
                          <input
                            type="text"
                            value={editCountry}
                            onChange={(e) => setEditCountry(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            ОБЛАСТЬ
                          </label>
                          <input
                            type="text"
                            value={editRegion}
                            onChange={(e) => setEditRegion(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            ГОРОД *
                          </label>
                          <input
                            type="text"
                            value={editCity}
                            onChange={(e) => setEditCity(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            ДОМ / АДРЕС *
                          </label>
                          <input
                            type="text"
                            value={editHouse}
                            onChange={(e) => setEditHouse(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            ПОСТ-КОД *
                          </label>
                          <input
                            type="text"
                            value={editPostalCode}
                            onChange={(e) => setEditPostalCode(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-mono outline-none rounded-none text-[#3F2021]"
                          />
                        </div>

                        <div className="lg:col-span-2">
                          <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1 font-semibold">
                            ПРИМЕЧАНИЕ
                          </label>
                          <input
                            type="text"
                            value={editNote}
                            onChange={(e) => setEditNote(e.target.value)}
                            className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans outline-none rounded-none text-[#3F2021]"
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id={`editIsActive-${office.id}`}
                          checked={editIsActive}
                          onChange={(e) => setEditIsActive(e.target.checked)}
                          className="w-4 h-4 rounded-none accent-[#3F2021] cursor-pointer"
                        />
                        <label
                          htmlFor={`editIsActive-${office.id}`}
                          className="text-xs font-sans uppercase tracking-wider text-[#3F2021] cursor-pointer font-semibold select-none"
                        >
                          АКТИВНО ДЛЯ ВЫБОРА ПОКУПАТЕЛЯМИ
                        </label>
                      </div>

                      <div className="flex items-center gap-3 pt-2 border-t border-[#3F2021]/15">
                        <button
                          type="button"
                          disabled={updateMutation.isPending}
                          onClick={() => handleSaveEdit(office.id)}
                          className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors disabled:opacity-50 cursor-pointer rounded-none"
                        >
                          {updateMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ↗'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/70 hover:text-[#3F2021] px-3 py-2"
                        >
                          ОТМЕНА
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Display Mode */
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="font-serif text-base sm:text-lg font-bold text-[#3F2021] uppercase tracking-wide">
                            {office.name}
                          </span>
                          <span
                            className={`text-[10px] font-sans font-semibold uppercase px-2.5 py-0.5 tracking-wider rounded-none ${
                              office.is_active
                                ? 'bg-[#3F2021] text-[#F2E9DB]'
                                : 'bg-[#FF8562]/20 text-[#3F2021] border border-[#FF8562]/40'
                            }`}
                          >
                            {office.is_active ? 'АКТИВНА ✓' : 'СКРЫТА ×'}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-sans text-[#3F2021]/80">
                          <div>
                            <span className="text-[#3F2021]/50 uppercase">ГОРОД:</span>{' '}
                            <strong className="text-[#3F2021]">{office.city}</strong>
                          </div>
                          <div>
                            <span className="text-[#3F2021]/50 uppercase">АДРЕС:</span>{' '}
                            <strong className="text-[#3F2021]">{office.house}</strong>
                          </div>
                          {office.region && (
                            <div>
                              <span className="text-[#3F2021]/50 uppercase">РЕГИОН:</span>{' '}
                              <span>{office.region}</span>
                            </div>
                          )}
                          <div>
                            <span className="text-[#3F2021]/50 uppercase">СТРАНА:</span>{' '}
                            <span>{office.country}</span>
                          </div>
                          <div>
                            <span className="text-[#3F2021]/50 uppercase">ИНДЕКС:</span>{' '}
                            <span className="font-mono font-bold text-[#3F2021] bg-[#F2E9DB] px-1.5 py-0.5 border border-[#3F2021]/15">
                              {office.postal_code}
                            </span>
                          </div>
                        </div>

                        {office.note && (
                          <div className="text-[11px] font-sans text-[#3F2021]/70 bg-[#F2E9DB]/40 p-2 border border-[#3F2021]/10 mt-1">
                            <span className="font-semibold uppercase">ПРИМЕЧАНИЕ:</span> {office.note}
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2.5 flex-wrap self-start md:self-center">
                        <button
                          type="button"
                          disabled={updateMutation.isPending}
                          onClick={() => handleToggleActive(office)}
                          className={`px-3 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold border transition-colors cursor-pointer rounded-none disabled:opacity-40 ${
                            office.is_active
                              ? 'border-[#3F2021]/30 hover:border-[#3F2021] text-[#3F2021]'
                              : 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] hover:bg-[#2B1516]'
                          }`}
                        >
                          {office.is_active ? 'СКРЫТЬ' : 'АКТИВИРОВАТЬ ↗'}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleStartEdit(office)}
                          className="px-3 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold border border-[#3F2021]/30 hover:border-[#3F2021] text-[#3F2021] transition-colors cursor-pointer rounded-none"
                        >
                          РЕДАКТИРОВАТЬ
                        </button>

                        {isConfirmingDelete ? (
                          <div className="flex items-center gap-1.5 bg-red-50 p-1 border border-red-300">
                            <span className="text-[10px] text-red-900 font-sans uppercase font-semibold">
                              УДАЛИТЬ?
                            </span>
                            <button
                              type="button"
                              disabled={deleteMutation.isPending}
                              onClick={() => deleteMutation.mutate(office.id)}
                              className="px-2 py-1 bg-red-700 text-white text-[10px] font-sans uppercase font-bold hover:bg-red-800 cursor-pointer rounded-none"
                            >
                              ДА
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmDeleteId(null)}
                              className="px-2 py-1 text-[10px] font-sans uppercase text-[#3F2021] hover:underline cursor-pointer"
                            >
                              НЕТ
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmDeleteId(office.id)}
                            className="px-3 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold text-red-700 border border-red-300 hover:bg-red-700 hover:text-white transition-colors cursor-pointer rounded-none"
                          >
                            УДАЛИТЬ ×
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

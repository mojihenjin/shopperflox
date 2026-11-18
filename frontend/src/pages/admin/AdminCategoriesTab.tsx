import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import type { CategoryResponse } from '../../types/api';
import type { ApiError } from '../../api/client';

interface AdminCategoriesTabProps {
  onFeedback: (msg: string) => void;
}

export function AdminCategoriesTab({ onFeedback }: AdminCategoriesTabProps) {
  const queryClient = useQueryClient();

  // Filters & Sorting state
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'sort_order' | 'created_at' | 'name'>('sort_order');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Create Form State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createSlug, setCreateSlug] = useState('');
  const [createParentId, setCreateParentId] = useState('');
  const [createSortOrder, setCreateSortOrder] = useState('0');

  // Edit State
  const [editingCatId, setEditingCatId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editSlug, setEditSlug] = useState('');
  const [editParentId, setEditParentId] = useState('');
  const [editSortOrder, setEditSortOrder] = useState('0');

  // Delete Confirm State
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Fetch Categories
  const { data: categoriesData, isLoading, error } = useQuery({
    queryKey: ['adminCategories', searchQuery, sortBy, sortOrder],
    queryFn: () =>
      adminApi.listCategories({
        search: searchQuery.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
  });

  const categories = categoriesData?.data || [];

  // Create Mutation
  const createMutation = useMutation({
    mutationFn: () => {
      if (!createName.trim()) throw new Error('Укажите название категории');
      return adminApi.createCategory({
        name: createName.trim(),
        slug: createSlug.trim() || undefined,
        parent_id: createParentId.trim() || undefined,
        sort_order: parseInt(createSortOrder, 10) || 0,
      });
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['adminCategories'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setIsCreateOpen(false);
      setCreateName('');
      setCreateSlug('');
      setCreateParentId('');
      setCreateSortOrder('0');
      onFeedback(`Категория «${res.data?.name}» успешно создана`);
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка создания категории');
    },
  });

  // Update Mutation
  const updateMutation = useMutation({
    mutationFn: (categoryId: string) => {
      if (!editName.trim()) throw new Error('Укажите название категории');
      return adminApi.updateCategory(categoryId, {
        name: editName.trim(),
        slug: editSlug.trim() || null,
        parent_id: editParentId.trim() || null,
        sort_order: parseInt(editSortOrder, 10) || 0,
      });
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['adminCategories'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setEditingCatId(null);
      onFeedback(`Категория «${res.data?.name}» обновлена`);
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка обновления категории');
    },
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (categoryId: string) => adminApi.deleteCategory(categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminCategories'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      setConfirmDeleteId(null);
      onFeedback('Категория успешно удалена');
    },
    onError: (err: ApiError) => {
      onFeedback(err.message || 'Ошибка удаления категории');
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
  };

  const startEdit = (cat: CategoryResponse) => {
    setEditingCatId(cat.id);
    setEditName(cat.name);
    setEditSlug(cat.slug || '');
    setEditParentId(cat.parent_id || '');
    setEditSortOrder(String(cat.sort_order ?? 0));
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
              placeholder="ПОИСК ПО НАЗВАНИЮ КАТЕГОРИИ..."
              className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans tracking-wider text-[#3F2021] outline-none rounded-none"
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
                }}
                className="text-xs text-[#3F2021]/60 hover:text-[#3F2021] px-2 font-mono"
              >
                ×
              </button>
            )}
          </form>

          {/* Action: Create Category */}
          <button
            type="button"
            onClick={() => setIsCreateOpen(!isCreateOpen)}
            className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-2 text-xs font-sans uppercase tracking-wider font-semibold transition-colors rounded-none whitespace-nowrap"
          >
            {isCreateOpen ? 'ОТМЕНА ×' : '+ СОЗДАТЬ КАТЕГОРИЮ'}
          </button>
        </div>

        {/* Sorting Bar */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="text-xs font-mono uppercase text-[#3F2021]/70">
            ВСЕГО КАТЕГОРИЙ: {categories.length}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-sans font-semibold uppercase tracking-wider text-[#3F2021]/70 select-none">
              СОРТИРОВКА:
            </span>
            <select
              value={sortBy}
              onChange={(e) =>
                setSortBy(e.target.value as 'sort_order' | 'created_at' | 'name')
              }
              className="bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] outline-none rounded-none"
            >
              <option value="sort_order">ПОРЯДКУ (SORT ORDER)</option>
              <option value="created_at">ДАТЕ СОЗДАНИЯ</option>
              <option value="name">НАЗВАНИЮ</option>
            </select>

            <button
              type="button"
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="border border-[#3F2021]/30 hover:border-[#3F2021] bg-[#F2E9DB]/20 px-3 py-1.5 text-xs font-sans uppercase tracking-wider text-[#3F2021] font-semibold transition-colors rounded-none"
            >
              {sortOrder === 'asc' ? '↑ ВОЗР.' : '↓ УБЫВ.'}
            </button>
          </div>
        </div>
      </div>

      {/* Inline Create Form */}
      {isCreateOpen && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="bg-[#FFFFFF] border border-[#3F2021] p-6 space-y-4 rounded-none"
        >
          <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021] border-b border-[#3F2021]/15 pb-2">
            ( СОЗДАНИЕ КАТЕГОРИИ )
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                НАЗВАНИЕ (NAME) *
              </label>
              <input
                type="text"
                required
                placeholder="ВЕРХНЯЯ ОДЕЖДА"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans text-[#3F2021] outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                SLUG (ОПЦИОНАЛЬНО)
              </label>
              <input
                type="text"
                placeholder="OUTERWEAR"
                value={createSlug}
                onChange={(e) => setCreateSlug(e.target.value)}
                className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-mono text-[#3F2021] outline-none"
              />
            </div>

            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                РОДИТЕЛЬСКАЯ КАТЕГОРИЯ
              </label>
              <select
                value={createParentId}
                onChange={(e) => setCreateParentId(e.target.value)}
                className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-sans uppercase text-[#3F2021] outline-none"
              >
                <option value="">БЕЗ РОДИТЕЛЯ (КОРНЕВАЯ)</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-sans uppercase tracking-wider text-[#3F2021]/70 mb-1">
                ПОРЯДОК (SORT ORDER)
              </label>
              <input
                type="number"
                value={createSortOrder}
                onChange={(e) => setCreateSortOrder(e.target.value)}
                className="w-full bg-[#F2E9DB]/20 border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-2 text-xs font-mono text-[#3F2021] outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-5 py-2 text-xs font-sans uppercase tracking-wider font-semibold disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? 'СОЗДАНИЕ...' : 'СОЗДАТЬ КАТЕГОРИЮ ↗'}
            </button>
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 hover:text-[#3F2021] px-2"
            >
              ОТМЕНА
            </button>
          </div>
        </form>
      )}

      {/* Categories List */}
      {isLoading ? (
        <div className="py-20 text-center text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 bg-[#FFFFFF] border border-[#3F2021]/20">
          ( ЗАГРУЗКА КАТЕГОРИЙ... )
        </div>
      ) : error ? (
        <div className="p-8 text-center border border-[#3F2021]/20 bg-[#FFFFFF]">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            ОШИБКА ЗАГРУЗКИ КАТЕГОРИЙ
          </div>
        </div>
      ) : categories.length === 0 ? (
        <div className="p-12 text-center border border-[#3F2021]/20 bg-[#FFFFFF] space-y-2">
          <div className="font-serif text-xl uppercase tracking-wider text-[#3F2021]">
            КАТЕГОРИИ НЕ НАЙДЕНЫ
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {categories.map((cat: CategoryResponse) => {
            const isEditing = editingCatId === cat.id;
            const isDeleting = confirmDeleteId === cat.id;
            const parentCat = categories.find((c) => c.id === cat.parent_id);

            return (
              <div
                key={cat.id}
                className="bg-[#FFFFFF] border border-[#3F2021]/30 p-4 sm:p-5 space-y-3 rounded-none"
              >
                {!isEditing ? (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-serif text-lg uppercase font-bold text-[#3F2021]">
                          {cat.name}
                        </span>
                        <span className="font-mono text-xs text-[#3F2021]/60">
                          /{cat.slug}
                        </span>
                        <span className="bg-[#3F2021]/10 text-[#3F2021] px-2 py-0.5 text-[10px] font-mono">
                          ПОРЯДОК: {cat.sort_order ?? 0}
                        </span>
                      </div>

                      <div className="text-[11px] font-sans text-[#3F2021]/70 uppercase">
                        {parentCat ? (
                          <span>РОДИТЕЛЬ: <strong>{parentCat.name}</strong></span>
                        ) : (
                          <span className="text-[#3F2021]/50">КОРНЕВАЯ КАТЕГОРИЯ</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => startEdit(cat)}
                        className="border border-[#3F2021]/40 text-[#3F2021] hover:border-[#3F2021] px-3 py-1 text-xs font-sans uppercase tracking-wider transition-colors"
                      >
                        РЕДАКТИРОВАТЬ
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(isDeleting ? null : cat.id)}
                        className="text-red-700 hover:text-red-900 text-xs px-2 font-mono uppercase"
                      >
                        УДАЛИТЬ ×
                      </button>
                    </div>
                  </div>
                ) : (
                  /* Inline Edit Form */
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      updateMutation.mutate(cat.id);
                    }}
                    className="p-4 bg-[#F2E9DB]/30 border border-[#3F2021]/20 space-y-4"
                  >
                    <div className="text-xs font-sans font-semibold uppercase tracking-wider text-[#3F2021]">
                      ( РЕДАКТИРОВАНИЕ КАТЕГОРИИ «{cat.name}» )
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                      <div>
                        <label className="block text-[10px] font-sans uppercase text-[#3F2021]/70 mb-1">
                          НАЗВАНИЕ *
                        </label>
                        <input
                          type="text"
                          required
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-sans text-[#3F2021] outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-sans uppercase text-[#3F2021]/70 mb-1">
                          SLUG
                        </label>
                        <input
                          type="text"
                          value={editSlug}
                          onChange={(e) => setEditSlug(e.target.value)}
                          className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-mono text-[#3F2021] outline-none"
                        />
                      </div>

                      <div>
                        <label className="block text-[10px] font-sans uppercase text-[#3F2021]/70 mb-1">
                          РОДИТЕЛЬ
                        </label>
                        <select
                          value={editParentId}
                          onChange={(e) => setEditParentId(e.target.value)}
                          className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-2.5 py-1.5 text-xs font-sans uppercase text-[#3F2021] outline-none"
                        >
                          <option value="">БЕЗ РОДИТЕЛЯ</option>
                          {categories
                            .filter((c) => c.id !== cat.id)
                            .map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name}
                              </option>
                            ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-[10px] font-sans uppercase text-[#3F2021]/70 mb-1">
                          ПОРЯДОК
                        </label>
                        <input
                          type="number"
                          value={editSortOrder}
                          onChange={(e) => setEditSortOrder(e.target.value)}
                          className="w-full bg-[#FFFFFF] border border-[#3F2021]/30 focus:border-[#3F2021] px-3 py-1.5 text-xs font-mono text-[#3F2021] outline-none"
                        />
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        type="submit"
                        disabled={updateMutation.isPending}
                        className="bg-[#3F2021] text-[#F2E9DB] hover:bg-[#2B1516] px-4 py-1.5 text-xs font-sans uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
                      >
                        {updateMutation.isPending ? 'СОХРАНЕНИЕ...' : 'СОХРАНИТЬ ✓'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingCatId(null)}
                        className="text-xs font-sans uppercase tracking-wider text-[#3F2021]/60 hover:text-[#3F2021] px-2"
                      >
                        ОТМЕНА
                      </button>
                    </div>
                  </form>
                )}

                {/* Inline Delete Confirmation */}
                {isDeleting && (
                  <div className="p-3 bg-red-100 border border-red-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs font-sans uppercase text-red-900 font-bold">
                      ВНИМАНИЕ: Удалить категорию «{cat.name}»?
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(cat.id)}
                        className="bg-red-700 text-[#FFFFFF] px-3 py-1 text-xs font-sans uppercase font-bold"
                      >
                        {deleteMutation.isPending ? 'УДАЛЕНИЕ...' : 'ПОДТВЕРДИТЬ УДАЛЕНИЕ'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-xs font-sans uppercase text-[#3F2021] px-2"
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
    </div>
  );
}

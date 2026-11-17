import { useState, useEffect } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { AdminUsersTab } from './admin/AdminUsersTab';
import { AdminBrandsTab } from './admin/AdminBrandsTab';
import { AdminCategoriesTab } from './admin/AdminCategoriesTab';
import { AdminProductsTab } from './admin/AdminProductsTab';
import { AdminReviewsTab } from './admin/AdminReviewsTab';

type AdminTab = 'users' | 'brands' | 'categories' | 'products' | 'reviews';

const VALID_TABS: AdminTab[] = ['users', 'brands', 'categories', 'products', 'reviews'];

export function AdminPage() {
  const { isAuthenticated, authUser: user } = useAuthStore();
  const [searchParams, setSearchParams] = useSearchParams();

  // Permission check: global '*' or 'admin:access'
  const permissions = user?.global_permissions || [];
  const isAdmin = permissions.includes('*') || permissions.includes('admin:access');

  // Read current tab from query param or fallback to 'users'
  const tabParam = searchParams.get('tab') as AdminTab | null;
  const currentTab: AdminTab = tabParam && VALID_TABS.includes(tabParam) ? tabParam : 'users';

  // Feedback banner state
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => {
      setFeedback(null);
    }, 4500);
    return () => clearTimeout(timer);
  }, [feedback]);

  const handleSelectTab = (tab: AdminTab) => {
    setSearchParams({ tab });
  };

  const handleFeedback = (msg: string) => {
    setFeedback(msg);
  };

  // Redirect unauthorized users to root
  if (!isAuthenticated || !isAdmin) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="w-full px-4 md:px-8 py-8 space-y-6">
      {/* 1. Page Header */}
      <div className="border-b border-[#3F2021] pb-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-xs font-sans uppercase tracking-widest text-[#3F2021]/60 block mb-1">
              ( СИСТЕМНОЕ УПРАВЛЕНИЕ )
            </span>
            <h1 className="font-serif text-3xl md:text-4xl uppercase tracking-wider text-[#3F2021]">
              АДМИНПАНЕЛЬ
            </h1>
          </div>
          <div className="text-left md:text-right">
            <span className="text-[11px] font-mono text-[#3F2021]/80 block">
              ПРАВА: {permissions.includes('*') ? 'SUPERUSER (*)' : 'ADMIN:ACCESS'}
            </span>
            <span className="text-[11px] font-sans uppercase tracking-wider text-[#3F2021]/60">
              ПОЛЬЗОВАТЕЛЬ: @{user?.login}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Global Feedback Banner */}
      {feedback && (
        <div className="p-4 bg-[#3F2021] text-[#F2E9DB] border border-[#3F2021] flex items-center justify-between">
          <span className="text-xs font-sans uppercase tracking-wider font-semibold">
            ✓ {feedback}
          </span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-xs font-mono text-[#F2E9DB]/70 hover:text-[#F2E9DB] cursor-pointer ml-4"
          >
            [×]
          </button>
        </div>
      )}

      {/* 3. Tab Switcher Navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[#3F2021]/20 pb-3">
        <button
          type="button"
          onClick={() => handleSelectTab('users')}
          className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
            currentTab === 'users'
              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
              : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
          }`}
        >
          ПОЛЬЗОВАТЕЛИ
        </button>
        <button
          type="button"
          onClick={() => handleSelectTab('brands')}
          className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
            currentTab === 'brands'
              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
              : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
          }`}
        >
          БРЕНДЫ
        </button>
        <button
          type="button"
          onClick={() => handleSelectTab('categories')}
          className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
            currentTab === 'categories'
              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
              : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
          }`}
        >
          КАТЕГОРИИ
        </button>
        <button
          type="button"
          onClick={() => handleSelectTab('products')}
          className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
            currentTab === 'products'
              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
              : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
          }`}
        >
          ТОВАРЫ
        </button>
        <button
          type="button"
          onClick={() => handleSelectTab('reviews')}
          className={`px-4 py-2 text-xs font-sans uppercase tracking-wider border rounded-none transition-colors cursor-pointer ${
            currentTab === 'reviews'
              ? 'bg-[#3F2021] text-[#F2E9DB] border-[#3F2021] font-semibold'
              : 'bg-[#FFFFFF] text-[#3F2021] border-[#3F2021]/30 hover:border-[#3F2021]'
          }`}
        >
          ОТЗЫВЫ
        </button>
      </div>

      {/* 4. Tab Content */}
      <div className="pt-2">
        {currentTab === 'users' && <AdminUsersTab onFeedback={handleFeedback} />}
        {currentTab === 'brands' && <AdminBrandsTab onFeedback={handleFeedback} />}
        {currentTab === 'categories' && <AdminCategoriesTab onFeedback={handleFeedback} />}
        {currentTab === 'products' && <AdminProductsTab onFeedback={handleFeedback} />}
        {currentTab === 'reviews' && <AdminReviewsTab onFeedback={handleFeedback} />}
      </div>
    </div>
  );
}

export default AdminPage;

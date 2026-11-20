import { lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';

const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })));
const CatalogPage = lazy(() => import('./pages/CatalogPage').then((m) => ({ default: m.CatalogPage })));
const ProductDetailPage = lazy(() => import('./pages/ProductDetailPage').then((m) => ({ default: m.ProductDetailPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((m) => ({ default: m.RegisterPage })));
const FavoritesPage = lazy(() => import('./pages/FavoritesPage').then((m) => ({ default: m.FavoritesPage })));
const CartPage = lazy(() => import('./pages/CartPage').then((m) => ({ default: m.CartPage })));
const OrdersPage = lazy(() => import('./pages/OrdersPage').then((m) => ({ default: m.OrdersPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })));
const CreatorNewProductPage = lazy(() => import('./pages/CreatorNewProductPage').then((m) => ({ default: m.CreatorNewProductPage })));
const CreatorEditProductPage = lazy(() => import('./pages/CreatorEditProductPage').then((m) => ({ default: m.CreatorEditProductPage })));
const ModerationRequestsPage = lazy(() => import('./pages/ModerationRequestsPage').then((m) => ({ default: m.ModerationRequestsPage })));
const BrandsManagePage = lazy(() => import('./pages/BrandsManagePage').then((m) => ({ default: m.BrandsManagePage })));
const BrandDetailPage = lazy(() => import('./pages/BrandDetailPage').then((m) => ({ default: m.BrandDetailPage })));
const BrandsListPage = lazy(() => import('./pages/BrandsListPage').then((m) => ({ default: m.BrandsListPage })));
const AdminPage = lazy(() => import('./pages/AdminPage').then((m) => ({ default: m.AdminPage })));
const PublicUserProfilePage = lazy(() => import('./pages/PublicUserProfilePage').then((m) => ({ default: m.PublicUserProfilePage })));
const QueuePage = lazy(() => import('./pages/QueuePage').then((m) => ({ default: m.QueuePage })));
const CheckoutPage = lazy(() => import('./pages/CheckoutPage').then((m) => ({ default: m.CheckoutPage })));
const DebugPayPage = lazy(() => import('./pages/DebugPayPage').then((m) => ({ default: m.DebugPayPage })));
const PaymentUnavailablePage = lazy(() => import('./pages/PaymentUnavailablePage').then((m) => ({ default: m.PaymentUnavailablePage })));

export function App() {
  return (
    <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="catalog" element={<CatalogPage />} />
            <Route path="products/:slug" element={<ProductDetailPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route
              path="favorites"
              element={
                <ProtectedRoute>
                  <FavoritesPage />
                </ProtectedRoute>
              }
            />
            <Route path="cart" element={<CartPage />} />
            <Route
              path="checkout"
              element={
                <ProtectedRoute>
                  <CheckoutPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="checkout/pay/:orderId"
              element={
                <ProtectedRoute>
                  <DebugPayPage />
                </ProtectedRoute>
              }
            />
            <Route path="payment-unavailable" element={<PaymentUnavailablePage />} />
            <Route
              path="orders"
              element={
                <ProtectedRoute>
                  <OrdersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="creator/products/new"
              element={
                <ProtectedRoute>
                  <CreatorNewProductPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="creator/products/:slug/edit"
              element={
                <ProtectedRoute>
                  <CreatorEditProductPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="moderation/requests"
              element={
                <ProtectedRoute>
                  <ModerationRequestsPage />
                </ProtectedRoute>
              }
            />
            <Route path="brands" element={<BrandsListPage />} />
            <Route path="brands/:slug" element={<BrandDetailPage />} />
            <Route path="users/:login" element={<PublicUserProfilePage />} />
            <Route
              path="queue"
              element={
                <ProtectedRoute>
                  <QueuePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="brands/manage"
              element={
                <ProtectedRoute>
                  <BrandsManagePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="admin"
              element={
                <ProtectedRoute>
                  <AdminPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
  );
}

export default App;

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { CatalogPage } from './pages/CatalogPage';
import { ProductDetailPage } from './pages/ProductDetailPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { FavoritesPage } from './pages/FavoritesPage';
import { CartPage } from './pages/CartPage';
import { OrdersPage } from './pages/OrdersPage';
import { ProfilePage } from './pages/ProfilePage';
import { CreatorNewProductPage } from './pages/CreatorNewProductPage';
import { CreatorEditProductPage } from './pages/CreatorEditProductPage';
import { ModerationRequestsPage } from './pages/ModerationRequestsPage';
import { BrandsManagePage } from './pages/BrandsManagePage';
import { BrandDetailPage } from './pages/BrandDetailPage';
import { BrandsListPage } from './pages/BrandsListPage';
import { AdminPage } from './pages/AdminPage';
import { PublicUserProfilePage } from './pages/PublicUserProfilePage';
import { QueuePage } from './pages/QueuePage';
import { CheckoutPage } from './pages/CheckoutPage';
import { DebugPayPage } from './pages/DebugPayPage';
import { PaymentUnavailablePage } from './pages/PaymentUnavailablePage';

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

import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    const currentPath = `${location.pathname}${location.search}`;
    const redirectUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;
    return <Navigate to={redirectUrl} state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

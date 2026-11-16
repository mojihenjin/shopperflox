import { create } from 'zustand';
import type { UserResponse } from '../types/api';

const ACCESS_TOKEN_KEY = 'sf_access_token';
const REFRESH_TOKEN_KEY = 'sf_refresh_token';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserResponse | null;
  isAuthenticated: boolean;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: UserResponse | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => {
  const initialAccessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const initialRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

  return {
    accessToken: initialAccessToken,
    refreshToken: initialRefreshToken,
    user: null,
    isAuthenticated: Boolean(initialAccessToken),

    setTokens: (accessToken: string, refreshToken: string) => {
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      set({
        accessToken,
        refreshToken,
        isAuthenticated: true,
      });
    },

    setUser: (user: UserResponse | null) => {
      set({ user });
    },

    logout: () => {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      set({
        accessToken: null,
        refreshToken: null,
        user: null,
        isAuthenticated: false,
      });
    },
  };
});

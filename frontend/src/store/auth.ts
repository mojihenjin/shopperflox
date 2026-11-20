import { create } from 'zustand';

const ACCESS_TOKEN_KEY = 'sf_access_token';
const REFRESH_TOKEN_KEY = 'sf_refresh_token';

export interface AuthUser {
  id: string;
  sub: string;
  login: string;
  email?: string | null;
  global_permissions: string[];
  verified_profile: boolean;
  verified_email: boolean;
  exp: number;
}

export function decodeJwtPayload(token: string): AuthUser | null {
  try {
    if (!token || typeof token !== 'string') return null;
    const parts = token.split('.');
    if (parts.length < 2) return null;

    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4;
    if (pad) {
      base64 += '='.repeat(4 - pad);
    }

    const binaryString = atob(base64);
    const bytes = Uint8Array.from(binaryString, (c) => c.charCodeAt(0));
    const jsonString = new TextDecoder().decode(bytes);
    const raw = JSON.parse(jsonString);

    if (!raw || typeof raw !== 'object') return null;

    const sub = String(raw.sub ?? '');
    const id = sub;
    const login = String(raw.login ?? '');
    const global_permissions: string[] = Array.isArray(raw.global_permissions)
      ? raw.global_permissions.map(String)
      : Array.isArray(raw.permissions)
      ? raw.permissions.map(String)
      : [];
    const verified_profile = Boolean(raw.verified_profile);
    const verified_email = Boolean(raw.verified_email);
    const exp = typeof raw.exp === 'number' ? raw.exp : 0;
    const email = raw.email ? String(raw.email) : null;

    return {
      id,
      sub,
      login,
      email,
      global_permissions,
      verified_profile,
      verified_email,
      exp,
    };
  } catch {
    return null;
  }
}

export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  authUser: AuthUser | null;
  isAuthenticated: boolean;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => {
  const initialAccessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const initialRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  const initialUser = initialAccessToken ? decodeJwtPayload(initialAccessToken) : null;

  return {
    accessToken: initialAccessToken,
    refreshToken: initialRefreshToken,
    user: initialUser,
    authUser: initialUser,
    isAuthenticated: Boolean(initialAccessToken),

    setTokens: (accessToken: string, refreshToken: string) => {
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      const authUser = decodeJwtPayload(accessToken);
      set({
        accessToken,
        refreshToken,
        user: authUser,
        authUser,
        isAuthenticated: true,
      });
    },

    setUser: (user: AuthUser | null) => {
      set({ user, authUser: user });
    },

    logout: () => {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      set({
        accessToken: null,
        refreshToken: null,
        user: null,
        authUser: null,
        isAuthenticated: false,
      });
    },
  };
});

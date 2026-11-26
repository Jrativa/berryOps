import { create } from 'zustand';
import { isAxiosError } from 'axios';
import i18n from '@/i18n/config';
import { authAPI } from '../infrastructure/api';

export interface User {
  username: string;
  role: string; // Ejemplo: "admin"
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  /** Mensaje ya traducido, listo para mostrar */
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const KEYS = ['access_token', 'refresh_token', 'user_data'] as const;

function clearStoredSession() {
  KEYS.forEach((k) => sessionStorage.removeItem(k));
}

// Restaura la sesión de la pestaña al cargar la app (evita perderla al recargar)
function loadStoredUser(): User | null {
  try {
    const token = sessionStorage.getItem('access_token');
    const storedUser = sessionStorage.getItem('user_data');
    return token && storedUser ? JSON.parse(storedUser) : null;
  } catch {
    clearStoredSession();
    return null;
  }
}

function loginErrorMessage(err: unknown): string {
  if (isAxiosError(err)) {
    const status = err.response?.status;
    if (status === 401) return i18n.t('auth.error.invalid');
    // 400 (p. ej. usuario inactivo): el backend envía un mensaje útil
    if (status === 400 && typeof err.response?.data?.detail === 'string') {
      return err.response.data.detail;
    }
  }
  return i18n.t('auth.error.generic');
}

export const useAuthStore = create<AuthState>((set) => ({
  user: loadStoredUser(),
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const data = await authAPI.login(username, password);

      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('refresh_token', data.refresh_token);

      const userData: User = { username: data.username, role: data.role };
      sessionStorage.setItem('user_data', JSON.stringify(userData));

      set({ user: userData, isLoading: false });
    } catch (err) {
      set({ error: loginErrorMessage(err), isLoading: false });
    }
  },

  logout: () => {
    const refreshToken = sessionStorage.getItem('refresh_token');

    // Respuesta inmediata: la sesión local se cierra al instante...
    clearStoredSession();
    set({ user: null, error: null });

    // ...y la revocación en el servidor ocurre en segundo plano (si falla, el token expira solo)
    if (refreshToken) {
      authAPI.logout(refreshToken).catch(() => undefined);
    }
  },
}));

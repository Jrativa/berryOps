import axios from 'axios';

// Instancia base
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
});

// Inyecta el Access Token a todas las peticiones
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Una sola renovación en vuelo: el backend rota el refresh token y trata la
// reutilización de uno ya rotado como robo (revoca todas las sesiones).
let refreshInFlight: Promise<string> | null = null;

function endSession() {
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
  sessionStorage.removeItem('user_data');
  window.location.href = '/login';
}

async function requestNewTokens(refreshToken: string): Promise<string> {
  try {
    // axios "pelado": sin interceptores, para no entrar en bucle. El backend espera el token en el cuerpo
    const res = await axios.post(
      `${api.defaults.baseURL}/auth/refresh`,
      { refresh_token: refreshToken },
      { withCredentials: true }
    );
    sessionStorage.setItem('access_token', res.data.access_token);
    sessionStorage.setItem('refresh_token', res.data.refresh_token);
    return res.data.access_token;
  } catch (refreshError) {
    // Si el refresh token también expiró, cerramos la sesión (una sola vez)
    endSession();
    throw refreshError;
  }
}

function refreshAccessToken(refreshToken: string): Promise<string> {
  refreshInFlight ??= requestNewTokens(refreshToken).finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

// Interceptor de RESPUESTA: La magia del Refresh Token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Un 401 en login/refresh es un error real de credenciales, no un token vencido
    const isAuthEndpoint = /\/auth\/(login|refresh)$/.test(originalRequest?.url ?? '');
    const refreshToken = sessionStorage.getItem('refresh_token');

    // Si el error es 401 (No autorizado) y no hemos reintentado ya
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint && refreshToken) {
      originalRequest._retry = true;
      const newAccessToken = await refreshAccessToken(refreshToken);
      // Reintentamos la petición original que falló con el nuevo token
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    }
    return Promise.reject(error);
  }
);

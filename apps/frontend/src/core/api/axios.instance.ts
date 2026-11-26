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

      try {
        // El backend espera el refresh token en el cuerpo
        const res = await axios.post(
          `${import.meta.env.VITE_API_URL}/auth/refresh`,
          { refresh_token: refreshToken },
          { withCredentials: true }
        );

        // Guardamos los nuevos tokens
        const newAccessToken = res.data.access_token;
        sessionStorage.setItem('access_token', newAccessToken);
        sessionStorage.setItem('refresh_token', res.data.refresh_token);

        // Reintentamos la petición original que falló con el nuevo token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
        
      } catch (refreshError) {
        // Si el refresh token también expiró, cerramos la sesión
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        sessionStorage.removeItem('user_data');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);
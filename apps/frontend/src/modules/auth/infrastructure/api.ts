import { api } from '../../../core/api/axios.instance';

export const authAPI = {
  login: async (username: string, password: string) => {
    const response = await api.post('/auth/login', { username, password });
    return response.data;
  },

  /** Revoca en el servidor la sesión asociada al refresh token. */
  logout: async (refreshToken: string) => {
    await api.post('/auth/logout', { refresh_token: refreshToken });
  },
};


import axios from "axios";

export const API_URL = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("trademind_access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.dispatchEvent(new Event("trademind:unauthorized"));
    }

    return Promise.reject(error);
  }
);

export const simulatorApi = axios.create({
  baseURL: `${API_URL}/api/simulator`,
  timeout: 15000,
});

simulatorApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("trademind_access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

simulatorApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.dispatchEvent(new Event("trademind:unauthorized"));
    }

    return Promise.reject(error);
  }
);

export default api;

/**
 * GestureMed AI — API Client
 * Axios instance with JWT auth, auto-refresh, and typed helpers.
 */
import axios, { AxiosInstance } from "axios";
import { useAuthStore } from "@/store/auth";
import { clearAuthCookie, setAuthCookie } from "@/lib/auth-cookies";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Request interceptor — attach access token ─────────────────────────────────
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — auto-refresh on 401 ────────────────────────────────
let refreshInFlight: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status === 401 && !original._retried) {
      original._retried = true;
      const { refreshToken, updateTokens, clearAuth } = useAuthStore.getState();

      if (!refreshToken) {
        clearAuth();
        return Promise.reject(error);
      }

      try {
        if (!refreshInFlight) {
          refreshInFlight = axios
            .post(`${API_URL}/api/auth/refresh`, { refresh_token: refreshToken })
            .then((res) => {
              const newAccessToken = res.data.access_token;
              const newRefreshToken = res.data.refresh_token || refreshToken;
              updateTokens(newAccessToken, newRefreshToken);
              setAuthCookie(newAccessToken);
              return newAccessToken;
            });
        }

        const newToken = await refreshInFlight;
        refreshInFlight = null;
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch {
        refreshInFlight = null;
        clearAuth();
        clearAuthCookie();
        if (typeof window !== "undefined") {
          window.location.href = "/auth/login";
        }
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

// ── Typed API helpers ─────────────────────────────────────────────────────────

export const authApi = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    role: string;
  }) => api.post("/auth/register", data),

  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),

  logout: (refreshToken: string) =>
    api.post("/auth/logout", { refresh_token: refreshToken }),

  me: () => api.get("/users/me"),
};

export const consultationApi = {
  create: (data: { chief_complaint?: string }) =>
    api.post("/consultations/", data),

  list: () => api.get("/consultations/my"),

  get: (id: string) => api.get(`/consultations/${id}`),

  join: (id: string) => api.post(`/consultations/${id}/join`),

  update: (id: string, data: { doctor_notes?: string; status?: string }) =>
    api.patch(`/consultations/${id}`, data),
};

export const reportApi = {
  generate: (consultationId: string) =>
    api.post(`/reports/${consultationId}/generate`),

  get: (consultationId: string) =>
    api.get(`/reports/${consultationId}`),

  list: () => api.get("/reports/"),
};

export const annotationApi = {
  create: (data: {
    consultation_id: string;
    annotation_type: string;
    coordinates: object;
    body_region?: string;
    note?: string;
    color?: string;
  }) => api.post("/annotations/", data),

  list: (consultationId: string) =>
    api.get(`/annotations/${consultationId}`),
};

export const videoApi = {
  start: (consultationId: string) =>
    api.post("/video/start", { consultation_id: consultationId }),

  stop: (consultationId: string) =>
    api.post("/video/stop", { consultation_id: consultationId }),

  sendFrame: (consultationId: string, frameBlob: Blob, annotationPoint?: { x: number; y: number }) => {
    const form = new FormData();
    form.append("consultation_id", consultationId);
    form.append("frame", frameBlob, "frame.jpg");
    if (annotationPoint) {
      form.append("annotation_x", String(annotationPoint.x));
      form.append("annotation_y", String(annotationPoint.y));
    }
    return api.post("/video/frame", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  status: (consultationId: string) => api.get(`/video/status/${consultationId}`),

  results: (consultationId: string) => api.get(`/video/results/${consultationId}`),
};

export const gpuApi = {
  status: () => api.get("/gpu/status"),
  health: () => api.get("/gpu/health"),
  benchmark: () => api.get("/gpu/benchmark"),
};

export const memoryApi = {
  consultation: (consultationId: string) => api.get(`/memory/consultation/${consultationId}`),
  patient: (patientId: string, query?: string) =>
    api.get(`/memory/patient/${patientId}`, { params: query ? { query } : undefined }),
  health: () => api.get("/memory/health"),
};

export const ragApi = {
  search: (query: string, topK: number = 5) => api.post("/rag/search", { query, top_k: topK }),
  health: () => api.get("/rag/health"),
};

export const agentTimelineApi = {
  timeline: (consultationId: string) => api.get(`/agents/timeline/${consultationId}`),
  consensus: (consultationId: string) => api.get(`/agents/consensus/${consultationId}`),
};

export const reportExportUrl = (consultationId: string, format: "markdown" | "json" | "pdf") =>
  `${API_URL}/api/reports/${consultationId}/export/${format}`;

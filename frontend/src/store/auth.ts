/**
 * GestureMed AI — Auth Store (Zustand)
 * Manages authentication state, JWT tokens, and user profile.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type UserRole = "PATIENT" | "DOCTOR" | "ADMIN";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  hasHydrated: boolean;

  setAuth: (user: AuthUser, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
  updateAccessToken: (token: string) => void;
  updateTokens: (accessToken: string, refreshToken: string) => void;
  setHasHydrated: (hasHydrated: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      hasHydrated: false,

      setAuth: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),

      clearAuth: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),

      setLoading: (isLoading) => set({ isLoading }),

      updateAccessToken: (accessToken) => set({ accessToken }),

      updateTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken, isAuthenticated: true }),

      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
    }),
    {
      name: "gesturemed-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

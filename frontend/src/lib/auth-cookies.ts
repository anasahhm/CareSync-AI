/**
 * GestureMed AI — Client-side auth cookie helpers.
 *
 * JWTs are still stored in the persisted Zustand auth store.
 * This cookie exists so Next.js middleware can keep protected routes
 * accessible after a browser refresh, because middleware cannot read localStorage.
 */
export const AUTH_COOKIE_NAME = "gm_access_token";
export const AUTH_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 days

export function setAuthCookie(accessToken: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=${accessToken}; path=/; max-age=${AUTH_SESSION_MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function clearAuthCookie() {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
}

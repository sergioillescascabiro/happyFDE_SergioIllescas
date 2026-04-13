import { encryptToken, decryptToken } from './crypto';

const TOKEN_KEY = 'hfde_auth_token';

export function saveToken(token: string): void {
  if (typeof window === 'undefined') return;
  const encrypted = encryptToken(token);
  localStorage.setItem(TOKEN_KEY, encrypted);
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  const encrypted = localStorage.getItem(TOKEN_KEY);
  if (!encrypted) return null;
  return decryptToken(encrypted);
}

export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

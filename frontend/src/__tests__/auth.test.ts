// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(global, 'localStorage', { value: localStorageMock });

import { encryptToken, decryptToken } from '../lib/crypto';
import { saveToken, getToken, clearToken, isAuthenticated } from '../lib/auth';

describe('crypto utilities', () => {
  it('encrypts and decrypts a token', () => {
    const original = 'hr-dashboard-token-change-in-production';
    const encrypted = encryptToken(original);
    expect(encrypted).not.toBe(original);
    const decrypted = decryptToken(encrypted);
    expect(decrypted).toBe(original);
  });

  it('returns null for invalid encrypted data', () => {
    const result = decryptToken('not-valid-base64-encrypted-data!!');
    // Should return null or empty string, not throw
    expect(result === null || result === '').toBe(true);
  });
});

describe('auth utilities', () => {
  beforeEach(() => localStorageMock.clear());

  it('saves and retrieves token', () => {
    saveToken('my-test-token');
    expect(getToken()).toBe('my-test-token');
  });

  it('clears token', () => {
    saveToken('my-test-token');
    clearToken();
    expect(getToken()).toBeNull();
  });

  it('isAuthenticated returns false when no token', () => {
    expect(isAuthenticated()).toBe(false);
  });

  it('isAuthenticated returns true when token saved', () => {
    saveToken('some-token');
    expect(isAuthenticated()).toBe(true);
  });
});

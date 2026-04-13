import CryptoJS from 'crypto-js';

// Use a fixed encryption key derived from app identity
// This is client-side obfuscation (not true security), but meets the spec requirement
const ENCRYPTION_KEY = 'happyfde-v1-secure-storage-2026';

export function encryptToken(token: string): string {
  return CryptoJS.AES.encrypt(token, ENCRYPTION_KEY).toString();
}

export function decryptToken(encrypted: string): string | null {
  try {
    const bytes = CryptoJS.AES.decrypt(encrypted, ENCRYPTION_KEY);
    const decrypted = bytes.toString(CryptoJS.enc.Utf8);
    return decrypted || null;
  } catch {
    return null;
  }
}

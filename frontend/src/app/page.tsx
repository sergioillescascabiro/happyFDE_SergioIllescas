'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { getToken, saveToken, clearToken } from '@/lib/auth';
import { validateToken } from '@/lib/api';

export default function TokenGate() {
  const router = useRouter();
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Check if already authenticated
    const stored = getToken();
    if (stored) {
      validateToken(stored).then((valid) => {
        if (valid) {
          router.push('/dashboard');
        } else {
          clearToken();
          setChecking(false);
        }
      });
    } else {
      setChecking(false);
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;

    setLoading(true);
    setError('');

    try {
      const valid = await validateToken(token.trim());
      if (valid) {
        saveToken(token.trim());
        router.push('/dashboard');
      } else {
        clearToken();
        setError('Invalid access token. Please check your credentials.');
      }
    } catch {
      setError('Connection error. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm flex flex-col items-center gap-10">
        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <Image
            src="/logo.svg"
            alt="HappyFDE"
            width={240}
            height={60}
            priority
          />
          <p className="text-[#555555] text-sm tracking-wider uppercase">
            Freight Operations Platform
          </p>
        </div>

        {/* Token Form */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="token"
              className="text-[#888888] text-xs uppercase tracking-wider"
            >
              Access Token
            </label>
            <input
              id="token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Enter access token"
              className="w-full bg-[#111111] border border-[#2a2a2a] rounded-md px-4 py-3 text-white placeholder-[#444444] text-sm focus:outline-none focus:border-[#444444] transition-colors font-mono"
              autoComplete="off"
              disabled={loading}
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !token.trim()}
            className="w-full bg-[#10b981] hover:bg-[#0d9668] text-white font-medium py-3 rounded-md text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Connecting...
              </span>
            ) : (
              'Connect'
            )}
          </button>
        </form>

        {/* Footer */}
        <p className="text-[#333333] text-xs text-center">
          Acme Logistics · Carrier Operations
        </p>
      </div>
    </div>
  );
}

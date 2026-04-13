'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Globe, Package, MessageSquare, Settings, LogOut } from 'lucide-react';
import { clsx } from 'clsx';
import { getToken, clearToken } from '@/lib/auth';
import { validateToken } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

const NAV_ITEMS = [
  { href: '/dashboard',                icon: Globe,          label: 'Overview' },
  { href: '/dashboard/loads',          icon: Package,        label: 'Loads' },
  { href: '/dashboard/communications', icon: MessageSquare,  label: 'Communications' },
  { href: '/dashboard/settings',       icon: Settings,       label: 'Settings' },
];

function Sidebar({ onLogout }: { onLogout: () => void }) {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-16 lg:w-56 bg-[#111111] border-r border-[#2a2a2a] flex flex-col z-50">
      {/* Logo */}
      <div className="h-16 flex items-center justify-center lg:justify-start lg:px-4 border-b border-[#2a2a2a] shrink-0">
        <Image src="/logo.svg" alt="HappyFDE" width={120} height={30} className="hidden lg:block" />
        <span className="lg:hidden text-white font-bold text-sm font-mono-data">HF</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1 p-2 pt-4">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || (href !== '/dashboard' && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-white/10 text-white'
                  : 'text-[#888888] hover:text-white hover:bg-white/5'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="hidden lg:block">{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="p-2 border-t border-[#2a2a2a]">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-[#555555] hover:text-red-400 hover:bg-red-500/5 text-sm transition-colors"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          <span className="hidden lg:block">Disconnect</span>
        </button>
      </div>
    </aside>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/');
      return;
    }
    validateToken(token).then((valid) => {
      if (!valid) {
        clearToken();
        router.push('/');
      } else {
        setAuthorized(true);
        setChecking(false);
      }
    }).catch(() => {
      setAuthorized(true); // Allow offline mode
      setChecking(false);
    });
  }, [router]);

  const handleLogout = () => {
    clearToken();
    router.push('/');
  };

  if (checking) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!authorized) return null;

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Sidebar onLogout={handleLogout} />
      <main className="ml-16 lg:ml-56 min-h-screen">
        {children}
      </main>
    </div>
  );
}

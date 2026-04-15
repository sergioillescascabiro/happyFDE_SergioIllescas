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
    <aside className="fixed left-0 top-0 h-screen w-16 lg:w-64 bg-[#050505] border-r border-white/5 flex flex-col z-50 shadow-2xl">
      {/* Logo */}
      <div className="h-20 flex items-center justify-center lg:justify-start lg:px-6 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.4)]">
             <Globe className="w-5 h-5 text-[#030303]" />
          </div>
          <span className="hidden lg:block text-white font-heading font-extrabold text-lg tracking-tighter">HAPPYFDE</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1.5 p-3 pt-6">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || (href !== '/dashboard' && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm transition-all relative group',
                isActive
                  ? 'bg-emerald-500/[0.08] text-emerald-400 font-bold'
                  : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.03]'
              )}
            >
              <Icon className={clsx('w-4.5 h-4.5 shrink-0 transition-transform group-hover:scale-110', isActive ? 'text-emerald-400' : 'text-slate-500')} />
              <span className="hidden lg:block tracking-tight">{label}</span>
              {isActive && (
                <div className="absolute right-2 w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-white/5">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/5 text-sm transition-all group font-medium"
        >
          <LogOut className="w-4.5 h-4.5 shrink-0 transition-transform group-hover:-translate-x-1" />
          <span className="hidden lg:block tracking-tight text-[11px] font-heading font-bold uppercase tracking-widest">Disconnect</span>
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
    <div className="min-h-screen bg-[#030303]">
      <Sidebar onLogout={handleLogout} />
      <main className="ml-16 lg:ml-64 min-h-screen">
        {children}
      </main>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { Globe, Package, MessageSquare, Settings, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
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

function Sidebar({ onLogout, isCollapsed, setCollapsed }: { 
  onLogout: () => void; 
  isCollapsed: boolean;
  setCollapsed: (v: boolean) => void;
}) {
  const pathname = usePathname();

  return (
    <div className="h-full flex flex-col">
      {/* Logo Area */}
      <div className="h-20 flex items-center justify-between px-6 border-b border-white/5 shrink-0 bg-white/[0.01]">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.4)] shrink-0">
             <Globe className="w-5 h-5 text-[#030303]" />
          </div>
          <div className="flex flex-col whitespace-nowrap group-hover/sidebar:opacity-100 transition-opacity">
            <span className="text-white font-heading font-extrabold text-lg tracking-tighter">HAPPYFDE</span>
            <span className={clsx("text-[9px] font-bold text-emerald-500 uppercase tracking-widest -mt-1", isCollapsed && "lg:hidden group-hover/sidebar:block")}>Acme Logistics</span>
          </div>
        </div>
        <button 
          onClick={() => setCollapsed(!isCollapsed)}
          className="hidden lg:flex p-1.5 hover:bg-white/5 rounded-md text-slate-500 hover:text-white transition-all ml-2"
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1.5 p-3 pt-6 overflow-y-auto">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || (href !== '/dashboard' && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm transition-all relative group/item',
                isActive
                  ? 'bg-emerald-500/[0.08] text-emerald-400 font-bold'
                  : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.03]'
              )}
            >
              <Icon className={clsx('w-5 h-5 shrink-0 transition-transform group-hover/item:scale-110', isActive ? 'text-emerald-400' : 'text-slate-500')} />
              <span className={clsx("tracking-tight whitespace-nowrap transition-all", isCollapsed ? 'opacity-0 lg:hidden group-hover/sidebar:opacity-100 group-hover/sidebar:block' : 'opacity-100')}>{label}</span>
              {isActive && (
                <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-white/5 bg-white/[0.01]">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/5 text-sm transition-all group/item font-medium overflow-hidden"
        >
          <LogOut className="w-5 h-5 shrink-0 transition-transform group-hover/item:-translate-x-1" />
          <span className={clsx("tracking-tight text-[11px] font-heading font-bold uppercase tracking-widest whitespace-nowrap", isCollapsed ? 'opacity-0 lg:hidden group-hover/sidebar:opacity-100 group-hover/sidebar:block' : 'opacity-100')}>Disconnect</span>
        </button>
      </div>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [checking, setChecking] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);

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
      <div className="min-h-screen bg-[#030303] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!authorized) return null;

  return (
    <div className="min-h-screen bg-[#030303] flex">
      {/* Sidebar with interactive expansion */}
      <div 
        className={clsx(
          'fixed left-0 top-0 h-screen transition-all duration-300 ease-in-out z-50 bg-[#050505] border-r border-white/5 shadow-2xl overflow-hidden group/sidebar',
          isCollapsed ? 'w-20 hover:w-64' : 'w-64'
        )}
      >
        <Sidebar onLogout={handleLogout} isCollapsed={isCollapsed} setCollapsed={setIsCollapsed} />
      </div>

      {/* Main content with dynamic margin */}
      <main className={clsx(
        'flex-1 min-h-screen transition-all duration-300 ease-in-out',
        isCollapsed ? 'ml-20' : 'ml-64'
      )}>
        {children}
      </main>
    </div>
  );
}

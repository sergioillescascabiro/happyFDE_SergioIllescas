'use client';

import { useState } from 'react';
import { Settings, Eye, EyeOff, Shield, CheckCircle2, Server, Cpu } from 'lucide-react';
import { getToken } from '@/lib/auth';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-card rounded-2xl overflow-hidden border-white/5 shadow-xl">
      <div className="px-6 py-4 border-b border-white/5 bg-white/[0.01]">
        <h2 className="text-[10px] font-heading font-bold text-slate-500 uppercase tracking-[0.15em]">{title}</h2>
      </div>
      <div className="p-6 space-y-5">{children}</div>
    </div>
  );
}

function InfoRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 group">
      <span className="text-sm text-slate-500 group-hover:text-slate-400 transition-colors">{label}</span>
      <span className={`text-sm text-slate-200 ${mono ? 'font-mono-data opacity-80' : 'font-medium'}`}>{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const [showToken, setShowToken] = useState(false);
  const token = getToken();
  const maskedToken = token ? `${token.slice(0, 6)}${'•'.repeat(Math.max(0, token.length - 10))}${token.slice(-4)}` : '(not set)';

  return (
    <div className="p-10 space-y-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-5">
        <div className="p-3 bg-white/[0.03] rounded-2xl border border-white/10 shadow-inner">
          <Settings className="w-6 h-6 text-slate-400" />
        </div>
        <div>
          <h1 className="text-2xl font-heading font-bold text-white tracking-tight">System Configuration</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage your platform parameters and security keys</p>
        </div>
      </div>

      {/* Authentication */}
      <Section title="Authentication">
        <div className="flex items-start gap-3 p-3 bg-green-500/5 border border-green-500/20 rounded-md">
          <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-green-400 font-medium">Connected</p>
            <p className="text-xs text-[#666666] mt-0.5">Dashboard token validated and stored securely</p>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[#888888]">Dashboard Token</span>
            <button
              onClick={() => setShowToken(!showToken)}
              className="text-[#555555] hover:text-white transition-colors"
            >
              {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <div className="bg-[#0d0d0d] border border-[#2a2a2a] rounded px-3 py-2">
            <code className="text-xs font-mono-data text-[#888888]">
              {showToken ? token : maskedToken}
            </code>
          </div>
          <p className="text-xs text-[#444444]">Token is AES-encrypted in browser localStorage</p>
        </div>
      </Section>

      {/* API Configuration */}
      <Section title="API Configuration">
        <div className="flex items-center gap-2 mb-2">
          <Server className="w-4 h-4 text-[#555555]" />
          <span className="text-xs text-[#555555]">Backend connection</span>
        </div>
        <InfoRow label="API Base URL" value={process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'} mono />
        <InfoRow label="Health Endpoint" value="/api/health" mono />
        <InfoRow label="Auth Endpoint" value="/api/health/auth" mono />
        <InfoRow label="Dashboard Header" value="X-Dashboard-Token" mono />
        <InfoRow label="Agent Header" value="X-Agent-Key" mono />
      </Section>

      {/* Security Info */}
      <Section title="Security">
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <Shield className="w-4 h-4 text-[#555555] shrink-0 mt-0.5" />
            <p className="text-xs text-[#666666] leading-relaxed">
              Dashboard tokens are stored encrypted using AES-256 in browser localStorage.
              The token is never logged or exposed in API responses.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <Shield className="w-4 h-4 text-[#555555] shrink-0 mt-0.5" />
            <p className="text-xs text-[#666666] leading-relaxed">
              Rate fields <code className="font-mono-data text-[#555555]">max_rate</code> and{' '}
              <code className="font-mono-data text-[#555555]">min_rate</code> are internal negotiation
              bounds and are never exposed in any API response or UI.
            </p>
          </div>
        </div>
      </Section>

      {/* App Info */}
      <Section title="Application">
        <InfoRow label="Platform" value="HappyFDE — Freight Operations" />
        <InfoRow label="Operator" value="Acme Logistics" />
        <InfoRow label="Version" value="0.1.0" mono />
        <InfoRow label="Environment" value="Development" mono />
        <div className="pt-2 flex items-start gap-2">
          <Cpu className="w-4 h-4 text-[#555555] shrink-0 mt-0.5" />
          <p className="text-xs text-[#444444] leading-relaxed">
            AI-powered carrier sales automation via HappyRobot voice platform.
            Carriers call in, the system vets via FMCSA, matches loads, and negotiates pricing.
          </p>
        </div>
      </Section>
    </div>
  );
}

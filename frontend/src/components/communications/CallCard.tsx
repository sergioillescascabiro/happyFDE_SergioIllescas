'use client';

import { Phone, PhoneIncoming } from 'lucide-react';
import { clsx } from 'clsx';
import { Call } from '@/types';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TranscriptBubble } from './TranscriptBubble';

interface CallCardProps {
  call: Call;
  onPickUp: () => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function CallCard({ call, onPickUp }: CallCardProps) {
  const transcript = call.transcript_full ?? [];
  const isLive = call.outcome === 'in_progress';

  return (
    <div className={clsx(
      'bg-[#111111] border rounded-lg overflow-hidden flex flex-col',
      isLive ? 'border-green-500/40' : 'border-[#2a2a2a]'
    )}>
      {/* Card header */}
      <div className={clsx(
        'px-4 py-3 flex items-center justify-between border-b',
        isLive ? 'border-green-500/20 bg-green-500/5' : 'border-[#1a1a1a]'
      )}>
        <div className="flex items-center gap-2">
          <div className={clsx(
            'w-7 h-7 rounded-full flex items-center justify-center',
            isLive ? 'bg-green-500/20' : 'bg-[#1a1a1a]'
          )}>
            <PhoneIncoming className={clsx('w-3.5 h-3.5', isLive ? 'text-green-400' : 'text-[#555555]')} />
          </div>
          <div>
            <p className="text-xs font-medium text-white">{call.use_case}</p>
            <p className="text-[10px] text-[#555555] font-mono-data">
              {call.phone_number ?? 'Unknown'} · {formatTime(call.call_start)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isLive && (
            <span className="flex items-center gap-1 text-[10px] text-green-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Live
            </span>
          )}
          <StatusBadge status={call.outcome} />
        </div>
      </div>

      {/* Transcript */}
      <div className="flex-1 px-4 py-3 space-y-2 min-h-[120px] max-h-[220px] overflow-y-auto bg-[#0d0d0d]">
        {transcript.length === 0 ? (
          <div className="flex items-center justify-center h-16">
            <p className="text-[#333333] text-xs">{call.transcript_summary ?? 'No transcript available'}</p>
          </div>
        ) : (
          transcript.map((msg, i) => (
            <TranscriptBubble key={i} message={msg} />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[#1a1a1a] flex items-center justify-between">
        <div className="flex items-center gap-3 text-[10px] text-[#555555] font-mono-data">
          {call.mc_number && <span>MC {call.mc_number}</span>}
          {call.load_load_id && <><span>·</span><span>Load {call.load_load_id}</span></>}
          <span>·</span>
          <span>{formatDuration(call.duration_seconds)}</span>
        </div>
        <button
          onClick={onPickUp}
          className={clsx(
            'flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md font-medium transition-colors',
            isLive
              ? 'bg-green-500 hover:bg-green-400 text-black'
              : 'bg-white/10 hover:bg-white/15 text-white'
          )}
        >
          <Phone className="w-3 h-3" />
          {isLive ? 'Pick Up' : 'Call Back'}
        </button>
      </div>
    </div>
  );
}

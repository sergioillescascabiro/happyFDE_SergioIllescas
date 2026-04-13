'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react';
import { clsx } from 'clsx';
import { TranscriptMessage } from '@/types';

interface TranscriptBubbleProps {
  message: TranscriptMessage;
}

export function TranscriptBubble({ message }: TranscriptBubbleProps) {
  const [expanded, setExpanded] = useState(false);

  if (message.role === 'tool_call') {
    return (
      <div className="flex flex-col gap-1 py-1">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-[10px] text-[#555555] hover:text-[#888888] transition-colors bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 w-full"
        >
          {expanded ? <ChevronDown className="w-3 h-3 shrink-0" /> : <ChevronRight className="w-3 h-3 shrink-0" />}
          <Wrench className="w-3 h-3 shrink-0" />
          <span className="font-mono-data truncate">Tool call</span>
        </button>
        {expanded && (
          <div className="mt-1 w-full bg-[#111111] border border-[#2a2a2a] rounded px-3 py-2">
            <pre className="text-[10px] text-green-400 font-mono-data whitespace-pre-wrap break-all">
              {message.message}
            </pre>
          </div>
        )}
      </div>
    );
  }

  const isAssistant = message.role === 'assistant';

  return (
    <div className={clsx('flex', isAssistant ? 'justify-start' : 'justify-end')}>
      <div
        className={clsx(
          'max-w-[80%] px-3 py-2 rounded-lg text-xs leading-relaxed',
          isAssistant
            ? 'bg-[#1a1a1a] text-[#cccccc] rounded-tl-none'
            : 'bg-blue-600/20 text-blue-200 border border-blue-500/20 rounded-tr-none'
        )}
      >
        <p>{message.message}</p>
        <p className={clsx('text-[9px] mt-1 font-mono-data', isAssistant ? 'text-[#444444]' : 'text-blue-400/60')}>
          {message.timestamp}
        </p>
      </div>
    </div>
  );
}

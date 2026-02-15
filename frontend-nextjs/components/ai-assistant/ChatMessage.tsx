'use client';

import { useState } from 'react';
import { User, Bot, AlertTriangle, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { Citation } from '@/lib/ai/router';

// Message structure
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  citations?: Citation[];
  suggestedQuestions?: string[];
  isRefusal?: boolean;
  isError?: boolean;
  category?: string;
}

interface ChatMessageProps {
  message: Message;
  onSuggestedQuestion?: (question: string) => void;
}

export function ChatMessage({ message, onSuggestedQuestion }: ChatMessageProps) {
  const [showCitations, setShowCitations] = useState(false);

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  // System messages render as separators
  if (isSystem) {
    return (
      <div className="my-4">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <div className="flex-1 border-t border-gray-300" />
          <span className="px-2">context change</span>
          <div className="flex-1 border-t border-gray-300" />
        </div>
        <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm text-blue-800">
          <MessageContent content={message.content} isUser={false} />
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-blue-100 text-blue-600'
            : message.isError
            ? 'bg-red-100 text-red-600'
            : message.isRefusal
            ? 'bg-amber-100 text-amber-600'
            : 'bg-gray-100 text-gray-600'
        }`}
      >
        {isUser ? (
          <User size={16} />
        ) : message.isError || message.isRefusal ? (
          <AlertTriangle size={16} />
        ) : (
          <Bot size={16} />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block max-w-full text-left rounded-lg px-3 py-2 text-sm ${
            isUser
              ? 'bg-blue-600 text-white'
              : message.isError
              ? 'bg-red-50 text-red-800 border border-red-200'
              : message.isRefusal
              ? 'bg-amber-50 text-amber-900 border border-amber-200'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {/* Render markdown-like content */}
          <MessageContent content={message.content} isUser={isUser} />
        </div>

        {/* Category badge for debugging (optional) */}
        {message.category && process.env.NODE_ENV === 'development' && (
          <div className="mt-1">
            <span className="text-[10px] text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded">
              {message.category}
            </span>
          </div>
        )}

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
            >
              {showCitations ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <span>{message.citations.length} source{message.citations.length > 1 ? 's' : ''}</span>
            </button>

            {showCitations && (
              <div className="mt-1 space-y-1">
                {message.citations.map((citation, index) => (
                  <div
                    key={index}
                    className="text-xs text-gray-500 bg-gray-50 rounded px-2 py-1 flex items-center gap-1"
                  >
                    <span className="truncate">{citation.source}</span>
                    {citation.clause && <span>({citation.clause})</span>}
                    {citation.url && (
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-600"
                      >
                        <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Suggested Questions */}
        {message.suggestedQuestions && message.suggestedQuestions.length > 0 && onSuggestedQuestion && (
          <div className="mt-3 space-y-1">
            <p className="text-xs text-gray-500 mb-1">Related questions:</p>
            {message.suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => onSuggestedQuestion(question)}
                className="block w-full text-left text-xs text-blue-600 hover:text-blue-800 hover:underline"
              >
                {question}
              </button>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div className={`text-[10px] text-gray-400 mt-1 ${isUser ? 'text-right' : ''}`}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

// Simple markdown-like content renderer
function MessageContent({ content, isUser }: { content: string; isUser: boolean }) {
  // Split content into parts by markdown-like syntax
  const parts = content.split(/(\*\*[^*]+\*\*|\*[^*]+\*|\n|---)/g);

  return (
    <div className="space-y-1">
      {parts.map((part, index) => {
        // Bold text
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <span key={index} className="font-semibold">
              {part.slice(2, -2)}
            </span>
          );
        }

        // Italic text
        if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**')) {
          return (
            <span key={index} className="italic">
              {part.slice(1, -1)}
            </span>
          );
        }

        // Horizontal rule
        if (part === '---') {
          return <hr key={index} className="my-2 border-gray-300" />;
        }

        // Newline
        if (part === '\n') {
          return <br key={index} />;
        }

        // List items
        if (part.trim().startsWith('- ')) {
          return (
            <div key={index} className="pl-3">
              • {part.trim().slice(2)}
            </div>
          );
        }

        // Regular text
        return <span key={index}>{part}</span>;
      })}
    </div>
  );
}

function formatTime(date: Date | string | undefined): string {
  if (!date) return '';

  // Handle string timestamps (from JSON parse)
  const dateObj = typeof date === 'string' ? new Date(date) : date;

  // Check if date is valid
  if (isNaN(dateObj.getTime())) return '';

  return new Intl.DateTimeFormat('en-AU', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(dateObj);
}

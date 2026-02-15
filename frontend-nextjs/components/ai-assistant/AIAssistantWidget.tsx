'use client';

import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Home, Loader2, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';
import { ChatMessage, Message } from './ChatMessage';
import { QuickActionChips } from './QuickActionChips';
import { PropertyContext } from '@/lib/ai/classifier';

interface AIAssistantWidgetProps {
  propertyContext?: PropertyContext;
  isPropertyLoading?: boolean;
}

export default function AIAssistantWidget({ propertyContext, isPropertyLoading = false }: AIAssistantWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const previousAddressRef = useRef<string | undefined>(undefined);

  // Clear chat history on page load so users always see the intro/scope
  useEffect(() => {
    localStorage.removeItem('ai-assistant-history');
  }, []);

  // Detect property context changes and insert a separator message
  useEffect(() => {
    const currentAddress = propertyContext?.address;
    const previousAddress = previousAddressRef.current;

    // Only add separator if:
    // 1. There's a new address (not undefined)
    // 2. It's different from the previous one
    // 3. There are existing messages (so we need a separator)
    if (currentAddress && currentAddress !== previousAddress && messages.length > 0) {
      // Build property details line
      const details: string[] = [];
      if (propertyContext?.zone) details.push(propertyContext.zone);
      if (propertyContext?.lga) details.push(propertyContext.lga);
      if (propertyContext?.lotSize) details.push(`${propertyContext.lotSize}m²`);
      if (propertyContext?.lotWidth) details.push(`${propertyContext.lotWidth}m wide`);

      const separatorMessage: Message = {
        id: `property-change-${Date.now()}`,
        role: 'system',
        content: `📍 **Property changed:** ${currentAddress}${details.length > 0 ? `\n${details.join(' · ')}` : ''}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, separatorMessage]);
    }

    previousAddressRef.current = currentAddress;
  }, [propertyContext?.address]);

  // Note: Chat history is intentionally not persisted across page reloads
  // so users always see the intro/scope message first

  // Scroll to show new message when added (but don't force to very bottom)
  useEffect(() => {
    if (messages.length > 0 && messagesEndRef.current) {
      // Scroll to show the last message, with some padding
      const container = messagesEndRef.current.parentElement;
      if (container) {
        const lastMessage = messagesEndRef.current.previousElementSibling;
        if (lastMessage) {
          lastMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }
  }, [messages.length]); // Only trigger when message count changes

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus();
    }
  }, [isOpen, isMinimized]);

  const handleSubmit = async (question: string) => {
    if (!question.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: question,
          propertyContext,
        }),
      });

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.success
          ? data.response.message
          : data.error || 'Something went wrong. Please try again.',
        timestamp: new Date(),
        citations: data.success ? data.response.citations : undefined,
        suggestedQuestions: data.success ? data.response.suggestedQuestions : undefined,
        isRefusal: data.success ? data.response.isRefusal : false,
        category: data.classification?.category,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Unable to connect. Please check your connection and try again.',
        timestamp: new Date(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = (question: string) => {
    handleSubmit(question);
  };

  const clearHistory = () => {
    setMessages([]);
  };

  // Button state: disabled when loading OR no property selected
  const isDisabled = isPropertyLoading || !propertyContext?.address;
  const buttonLabel = isPropertyLoading
    ? 'Loading property...'
    : !propertyContext?.address
      ? 'Select a property first'
      : 'Quick Reference';

  // Closed state - floating button
  if (!isOpen) {
    return (
      <button
        onClick={() => !isDisabled && setIsOpen(true)}
        disabled={isDisabled}
        className={`fixed bottom-6 left-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full shadow-lg transition-all focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 ${
          isDisabled
            ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
            : 'bg-gray-600 text-white hover:bg-gray-700 hover:scale-105'
        }`}
        aria-label={buttonLabel}
      >
        {isPropertyLoading ? (
          <>
            <Loader2 size={20} className="animate-spin" />
            <span className="font-medium">Loading property...</span>
          </>
        ) : (
          <>
            <Home size={20} />
            <span className="font-medium">{buttonLabel}</span>
          </>
        )}
      </button>
    );
  }

  // Minimized state
  if (isMinimized) {
    return (
      <div className="fixed bottom-6 left-6 z-50 w-72 bg-white rounded-lg shadow-xl border border-gray-200">
        <button
          onClick={() => setIsMinimized(false)}
          className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg"
        >
          <div className="flex items-center gap-2">
            <Home size={18} className="text-gray-600" />
            <span className="font-medium text-gray-900">Planning Lookup</span>
          </div>
          <ChevronUp size={18} className="text-gray-400" />
        </button>
      </div>
    );
  }

  // Open state - chat panel
  return (
    <div className="fixed bottom-6 left-6 z-50 w-[420px] max-w-[calc(100vw-3rem)] bg-white rounded-lg shadow-2xl border border-gray-200 flex flex-col max-h-[600px]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white rounded-t-lg">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <Home size={20} className="text-gray-600" />
            <h3 className="font-semibold text-gray-900">Quick Reference</h3>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded transition-colors"
              aria-label="New question"
              title="New question"
            >
              <RotateCcw size={18} />
            </button>
          )}
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
            aria-label="Minimize"
          >
            <ChevronDown size={18} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Property Context Banner */}
      {propertyContext?.address ? (
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
          <p className="text-xs text-slate-800">
            <span className="font-medium">Property:</span> {propertyContext.address}
          </p>
          {propertyContext.zone && (
            <p className="text-xs text-slate-700">
              {propertyContext.zone}
              {propertyContext.constraints?.heritage && ' • Heritage Listed'}
            </p>
          )}
        </div>
      ) : (
        <div className="px-4 py-2 bg-amber-50 border-b border-amber-100">
          <p className="text-xs text-amber-800">
            <span className="font-medium">No property selected.</span> Enter an address above for specific requirements.
          </p>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[200px] max-h-[350px]">
        {messages.length === 0 ? (
          <div className="py-2">
            {/* Prominent scope note */}
            <div className="bg-gray-100 border-2 border-gray-300 rounded-lg p-3 mb-4">
              <p className="text-sm font-medium text-gray-900">
                Instant lookup of planning requirements
              </p>
              <p className="text-xs text-gray-700 mt-1">
                Shows what LEP, DCP, and SEPP rules say — not whether your project complies. Click a topic below.
              </p>
            </div>

            {/* HAX Pattern 1D: Demonstrate possible inputs via buttons */}
            <QuickActionChips
              hasProperty={!!propertyContext?.address}
              onSelect={handleQuickAction}
            />
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onSuggestedQuestion={handleQuickAction}
              />
            ))}
            {isLoading && (
              <div className="flex items-center gap-2 text-gray-500 text-sm">
                <Loader2 size={16} className="animate-spin" />
                <span>Looking that up...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(inputValue);
          }}
          className="flex gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type keywords: height limit, FSR, granny flat..."
            disabled={isLoading}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-500 focus:border-gray-500 text-sm disabled:bg-gray-50 disabled:cursor-not-allowed"
            maxLength={500}
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="px-3 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </form>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            className="mt-2 text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Clear conversation
          </button>
        )}
      </div>
    </div>
  );
}

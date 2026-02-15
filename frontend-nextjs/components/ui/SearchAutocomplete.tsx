'use client';

import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchAutocompleteProps {
  query: string;
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  onClose: () => void;
}

export function SearchAutocomplete({
  query,
  suggestions,
  onSelect,
  onClose
}: SearchAutocompleteProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(i => Math.min(i + 1, suggestions.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(i => Math.max(i - 1, 0));
          break;
        case 'Enter':
          if (suggestions[selectedIndex]) {
            e.preventDefault();
            onSelect(suggestions[selectedIndex]);
          }
          break;
        case 'Escape':
          onClose();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedIndex, suggestions, onSelect, onClose]);

  // Reset selection when suggestions change
  useEffect(() => {
    setSelectedIndex(0);
  }, [suggestions]);

  if (suggestions.length === 0) return null;

  return (
    <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
      {suggestions.map((suggestion, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(suggestion)}
          onMouseEnter={() => setSelectedIndex(idx)}
          className={cn(
            "w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors flex items-center gap-2",
            idx === selectedIndex && "bg-gray-100"
          )}
        >
          <Search className="h-3 w-3 text-gray-400 flex-shrink-0" />
          <span className="flex-1">{suggestion}</span>
        </button>
      ))}
    </div>
  );
}

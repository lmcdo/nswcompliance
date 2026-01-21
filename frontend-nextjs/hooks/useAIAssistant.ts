/**
 * useAIAssistant Hook
 *
 * Provides programmatic access to the AI assistant functionality.
 * Can be used to trigger questions from other components.
 */

import { useState, useCallback } from 'react';
import { PropertyContext } from '@/lib/ai/classifier';
import { FormattedResponse } from '@/lib/ai/formatter';

interface ChatResponse {
  success: boolean;
  response?: FormattedResponse;
  classification?: {
    category: string;
    confidence: number;
  };
  error?: string;
  processingTimeMs: number;
}

interface UseAIAssistantReturn {
  askQuestion: (question: string, propertyContext?: PropertyContext) => Promise<ChatResponse>;
  isLoading: boolean;
  lastResponse: ChatResponse | null;
  error: string | null;
}

/**
 * Hook to interact with the AI assistant programmatically
 */
export function useAIAssistant(): UseAIAssistantReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const askQuestion = useCallback(async (
    question: string,
    propertyContext?: PropertyContext
  ): Promise<ChatResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: question,
          propertyContext,
        }),
      });

      const data: ChatResponse = await response.json();

      if (!data.success) {
        setError(data.error || 'Unknown error');
      }

      setLastResponse(data);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to AI assistant';
      setError(errorMessage);

      const errorResponse: ChatResponse = {
        success: false,
        error: errorMessage,
        processingTimeMs: 0,
      };
      setLastResponse(errorResponse);
      return errorResponse;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    askQuestion,
    isLoading,
    lastResponse,
    error,
  };
}

export default useAIAssistant;

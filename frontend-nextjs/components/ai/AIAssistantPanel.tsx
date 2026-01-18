'use client';

import { useState, useCallback } from 'react';
import { useChat, Message } from 'ai/react';
import { ChevronUp, ChevronDown, Sparkles, Send, Loader2, AlertCircle, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import type { PropertyContext, LepCapacityData } from '@/types/regulatory';

interface AIAssistantPanelProps {
  property: PropertyContext | null;
  lepData: LepCapacityData | null;
  developmentType: string;
  isDataReady: boolean;
  onScrollToProvision?: (provisionId: number, tab: 'sepp' | 'lep' | 'dcp') => void;
}

interface KeyRequirement {
  label: string;
  value: string;
  source: string;
  provisionId?: number;
  tab: 'sepp' | 'lep' | 'dcp';
  icon: 'height' | 'setback' | 'parking' | 'heritage' | 'fsr';
}

/**
 * AI Assistant Panel - Hybrid summary + expandable chat
 *
 * Default: Collapsed view with key requirements
 * Expanded: Full chat interface for follow-up questions
 */
export function AIAssistantPanel({
  property,
  lepData,
  developmentType,
  isDataReady,
  onScrollToProvision,
}: AIAssistantPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Build regulatory context for API
  const regulatoryContext = property ? {
    address: property.address,
    zone: property.zone,
    lga: property.lga,
    formerCouncil: property.formerCouncil,
    precinctId: property.precinctId,
    heritage: property.heritage,
    lotArea: property.lotArea,
    developmentType,
  } : null;

  // Build precomputed data from LEP capacity response
  const precomputedData = lepData ? {
    height: lepData.capacity.maxHeight ? {
      value: `${lepData.capacity.maxHeight}m`,
      source: 'LEP Height of Buildings Map',
    } : undefined,
    fsr: lepData.capacity.maxFSR ? {
      value: `${lepData.capacity.maxFSR}:1`,
      source: 'LEP Floor Space Ratio Map',
    } : undefined,
    setbacks: lepData.setbacks?.values?.length ? {
      value: lepData.setbacks.values.map(v =>
        `${v.boundary}: ${v.value || v.range}${v.unit || 'm'}`
      ).join('\n'),
      source: lepData.setbacks.source || 'DCP Setback Controls',
    } : undefined,
    parking: lepData.parking?.length ? {
      value: lepData.parking.map(p => p.text).join('\n'),
      source: 'DCP Parking Controls',
    } : undefined,
  } : undefined;

  // Chat hook with Vercel AI SDK
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    append,
  } = useChat({
    api: '/api/ai/chat',
    body: {
      context: regulatoryContext,
      precomputedData,
    },
    onError: (err) => {
      console.error('[AIAssistantPanel] Chat error:', err);
    },
  });

  // Extract key requirements from LEP data
  const keyRequirements = extractKeyRequirements(lepData, property);

  // Handle quick question suggestions
  const handleQuickQuestion = useCallback((question: string) => {
    if (!regulatoryContext) return;
    setIsExpanded(true);
    append({ role: 'user', content: question });
  }, [regulatoryContext, append]);

  // Handle source click
  const handleSourceClick = useCallback((provisionId: number | undefined, tab: 'sepp' | 'lep' | 'dcp') => {
    if (provisionId && onScrollToProvision) {
      onScrollToProvision(provisionId, tab);
    }
  }, [onScrollToProvision]);

  // Not ready state
  if (!property || !isDataReady) {
    return (
      <Card className="border-dashed border-muted-foreground/30">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">AI Assistant</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Select a property to see AI-powered requirement summaries.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/20 bg-gradient-to-br from-background to-primary/5">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-primary" />
            AI Assistant
            <Badge variant="secondary" className="text-xs">Beta</Badge>
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-8 px-2"
          >
            {isExpanded ? (
              <>
                <ChevronDown className="h-4 w-4 mr-1" />
                Collapse
              </>
            ) : (
              <>
                <ChevronUp className="h-4 w-4 mr-1" />
                Expand
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Collapsed view: Key requirements */}
        {!isExpanded && (
          <>
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Key requirements for {property.zone} zone:
              </p>

              <TooltipProvider>
                <div className="space-y-1.5">
                  {keyRequirements.map((req, idx) => (
                    <RequirementItem
                      key={idx}
                      requirement={req}
                      onSourceClick={handleSourceClick}
                    />
                  ))}

                  {keyRequirements.length === 0 && (
                    <p className="text-sm text-muted-foreground italic">
                      Loading requirements...
                    </p>
                  )}
                </div>
              </TooltipProvider>
            </div>

            {/* Quick question input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (input.trim()) {
                  setIsExpanded(true);
                  handleSubmit(e);
                }
              }}
              className="flex gap-2"
            >
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="Ask about this property..."
                className="flex-1 text-sm"
                disabled={isLoading}
              />
              <Button type="submit" size="sm" disabled={isLoading || !input.trim()}>
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>

            {/* Suggested questions */}
            <div className="flex flex-wrap gap-1.5">
              {suggestedQuestions.map((q, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => handleQuickQuestion(q)}
                  disabled={isLoading}
                >
                  {q}
                </Button>
              ))}
            </div>
          </>
        )}

        {/* Expanded view: Full chat */}
        {isExpanded && (
          <div className="space-y-4">
            {/* Chat messages */}
            <ScrollArea className="h-[300px] rounded-md border p-3">
              {messages.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground py-8">
                  <p>Ask me anything about the requirements for this property.</p>
                  <p className="text-xs mt-2">
                    I can help with height limits, setbacks, parking, heritage, and more.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message, idx) => (
                    <ChatMessage
                      key={idx}
                      message={message}
                      onSourceClick={handleSourceClick}
                    />
                  ))}
                  {isLoading && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Thinking...
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>

            {/* Error display */}
            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                {error.message || 'Something went wrong. Please try again.'}
              </div>
            )}

            {/* Chat input */}
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="Ask a follow-up question..."
                className="flex-1"
                disabled={isLoading}
              />
              <Button type="submit" disabled={isLoading || !input.trim()}>
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>

            {/* Disclaimer */}
            <p className="text-xs text-muted-foreground">
              AI responses are for guidance only. Always verify with official sources before making decisions.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Single requirement item with source popover
 */
function RequirementItem({
  requirement,
  onSourceClick,
}: {
  requirement: KeyRequirement;
  onSourceClick: (provisionId: number | undefined, tab: 'sepp' | 'lep' | 'dcp') => void;
}) {
  const iconMap = {
    height: '📏',
    setback: '↔️',
    parking: '🅿️',
    heritage: '🏛️',
    fsr: '📐',
  };

  return (
    <div className="flex items-center justify-between py-1 px-2 rounded-md bg-muted/50 hover:bg-muted transition-colors">
      <div className="flex items-center gap-2">
        <span className="text-sm">{iconMap[requirement.icon]}</span>
        <span className="text-sm">
          <span className="font-medium">{requirement.label}:</span>{' '}
          {requirement.value}
        </span>
      </div>

      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <Info className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64" align="end">
          <div className="space-y-2">
            <p className="text-sm font-medium">{requirement.label}</p>
            <p className="text-xs text-muted-foreground">{requirement.source}</p>
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0 text-xs"
              onClick={() => onSourceClick(requirement.provisionId, requirement.tab)}
            >
              View in {requirement.tab.toUpperCase()} tab →
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

/**
 * Chat message component
 */
function ChatMessage({
  message,
  onSourceClick,
}: {
  message: Message;
  onSourceClick: (provisionId: number | undefined, tab: 'sepp' | 'lep' | 'dcp') => void;
}) {
  const isUser = message.role === 'user';

  // Parse provision references [provision_id:N]
  const parseContent = (content: string) => {
    const parts = content.split(/\[provision_id:(\d+)\]/g);
    return parts.map((part, idx) => {
      if (idx % 2 === 1) {
        // This is a provision ID
        const provisionId = parseInt(part);
        return (
          <Button
            key={idx}
            variant="link"
            size="sm"
            className="h-auto p-0 text-xs text-primary"
            onClick={() => onSourceClick(provisionId, 'dcp')}
          >
            [source]
          </Button>
        );
      }
      return part;
    });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        }`}
      >
        <div className="whitespace-pre-wrap">
          {isUser ? message.content : parseContent(message.content)}
        </div>
      </div>
    </div>
  );
}

/**
 * Extract key requirements from LEP data
 */
function extractKeyRequirements(
  lepData: LepCapacityData | null,
  property: PropertyContext | null
): KeyRequirement[] {
  const requirements: KeyRequirement[] = [];

  if (!lepData) return requirements;

  // Height
  if (lepData.capacity.maxHeight) {
    requirements.push({
      label: 'Height',
      value: `${lepData.capacity.maxHeight}m max`,
      source: 'LEP Height of Buildings Map (Clause 4.3)',
      tab: 'lep',
      icon: 'height',
    });
  }

  // FSR
  if (lepData.capacity.maxFSR) {
    requirements.push({
      label: 'FSR',
      value: `${lepData.capacity.maxFSR}:1`,
      source: 'LEP Floor Space Ratio Map (Clause 4.4)',
      tab: 'lep',
      icon: 'fsr',
    });
  }

  // Setbacks
  if (lepData.setbacks?.values?.length) {
    const sideSetback = lepData.setbacks.values.find(v => v.boundary === 'side');
    if (sideSetback) {
      requirements.push({
        label: 'Side setback',
        value: `${sideSetback.value || sideSetback.range}${sideSetback.unit || 'm'}`,
        source: lepData.setbacks.source || 'DCP Setback Controls',
        tab: 'dcp',
        icon: 'setback',
      });
    }
  }

  // Parking
  if (lepData.parking?.length) {
    const parkingReq = lepData.parking[0];
    requirements.push({
      label: 'Parking',
      value: parkingReq.spaces ? `${parkingReq.spaces} space(s)` : parkingReq.text,
      source: 'DCP Parking Controls',
      tab: 'dcp',
      icon: 'parking',
    });
  }

  // Heritage (if applicable)
  if (property?.heritage?.isHeritage) {
    requirements.push({
      label: 'Heritage',
      value: property.heritage.heritageType || 'Additional controls apply',
      source: 'Heritage Conservation controls',
      tab: 'dcp',
      icon: 'heritage',
    });
  }

  return requirements;
}

/**
 * Suggested quick questions
 */
const suggestedQuestions = [
  'Can I build a granny flat?',
  'What are the setback requirements?',
  'Do I need a DA or CDC?',
];

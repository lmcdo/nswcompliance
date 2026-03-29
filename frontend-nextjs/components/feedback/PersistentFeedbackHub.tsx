'use client';

import { useState, useEffect, useCallback } from 'react';
import { MessageSquare, X, Minimize2, Maximize2, Plus, History } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SmartFeedbackTrigger } from './SmartFeedbackTrigger';
import { Badge } from '@/components/ui/badge';
import { FeedbackSessionState } from './SmartFeedbackTrigger';

interface PersistentFeedbackHubProps {
  propertyAddress: string;
  propertyId?: string;
  sections?: string[];
  onFeedback?: (feedback: any) => void;
}

interface FeedbackItem {
  id: string;
  type: string;
  context: any;
  description: string;
  userType: string;
  severity: string;
  createdAt: Date;
  propertyAddress: string;
}

export function PersistentFeedbackHub({
  propertyAddress,
  propertyId,
  sections = [],
  onFeedback
}: PersistentFeedbackHubProps) {
  const [sessionState, setSessionState] = useState<FeedbackSessionState>({
    isVisible: false,
    hasSubmitted: false,
    submittedCount: 0,
    lastSubmittedAt: undefined,
    currentPropertyId: propertyId,
    dismissedSections: new Set(),
    userRole: '',
    sessionStartTime: new Date()
  });

  const [feedbackHistory, setFeedbackHistory] = useState<FeedbackItem[]>([]);
  const [isMinimized, setIsMinimized] = useState(false);
  const [activeTrigger, setActiveTrigger] = useState<string | null>(null);
  const [showSuggestionsForm, setShowSuggestionsForm] = useState(false);
  const [suggestionText, setSuggestionText] = useState('');
  const [showThankYou, setShowThankYou] = useState(false);

  // Initialize or update session state
  useEffect(() => {
    if (propertyId !== sessionState.currentPropertyId) {
      // New property - reset but remember some state
      setSessionState((prev: FeedbackSessionState) => ({
        ...prev,
        currentPropertyId: propertyId,
        hasSubmitted: false,
        dismissedSections: new Set(),
        lastSubmittedAt: undefined
      }));
    }
  }, [propertyId]);

  // Load saved role from localStorage
  useEffect(() => {
    const savedRole = localStorage.getItem('feedback-user-role');
    if (savedRole && !sessionState.userRole) {
      setSessionState((prev: FeedbackSessionState) => ({ ...prev, userRole: savedRole }));
    }
  }, []);

  // Save role to localStorage
  useEffect(() => {
    if (sessionState.userRole) {
      localStorage.setItem('feedback-user-role', sessionState.userRole);
    }
  }, [sessionState.userRole]);

  // Smart triggering based on user behavior
  useEffect(() => {
    const timer = setTimeout(() => {
      // Show feedback trigger for relevant sections
      if (shouldShowFeedbackForSection() && !sessionState.dismissedSections.has(activeTrigger ?? '')) {
        setSessionState((prev: FeedbackSessionState) => ({ ...prev, isVisible: true }));
        setActiveTrigger(sections?.[0] || 'general');
      }
    }, 2000); // Shorter delay for persistent hub

    return () => clearTimeout(timer);
  }, [sections, sessionState.dismissedSections, activeTrigger, propertyAddress]);

  const shouldShowFeedbackForSection = (): boolean => {
    // Show feedback if user has been on this property for a while
    const sessionDuration = Date.now() - sessionState.sessionStartTime.getTime();
    return sessionDuration > 10000; // 10 seconds
  };

  const handleFeedbackSubmit = useCallback((feedback: any) => {
    // Add to feedback history
    const newFeedback: FeedbackItem = {
      id: Date.now().toString(),
      ...feedback,
      createdAt: new Date(),
      propertyAddress
    };

    setFeedbackHistory((prev: FeedbackItem[]) => [newFeedback, ...prev]);
    setSessionState((prev: FeedbackSessionState) => ({
      ...prev,
      hasSubmitted: true,
      submittedCount: prev.submittedCount + 1,
      lastSubmittedAt: new Date()
    }));

    onFeedback?.(feedback);
    setShowThankYou(true);
    setTimeout(() => setShowThankYou(false), 3000);
  }, [onFeedback, propertyAddress]);

  const handleSuggestionSubmit = async () => {
    if (!suggestionText.trim() || !sessionState.userRole) return;

    const suggestionData = {
      type: 'user_suggestion',
      context: {
        propertyAddress,
        section: 'general_insight',
        occurrenceContext: 'user_journey'
      },
      description: suggestionText,
      userType: sessionState.userRole,
      severity: 'medium',
      sessionId: sessionState.sessionStartTime.getTime().toString(),
      propertyId
    };

    // Use suggestion-specific API endpoint
    try {
      const response = await fetch('/api/feedback/suggestion', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(suggestionData),
      });

      if (response.ok) {
        setSuggestionText('');
        setShowSuggestionsForm(false);

        // Show thank you message
        setShowThankYou(true);
        setTimeout(() => setShowThankYou(false), 3000);
      }
    } catch (error) {
      console.error('Suggestion submission error:', error);
    }
  };

  const handleDismiss = useCallback((section?: string) => {
    setSessionState((prev: FeedbackSessionState) => ({
      ...prev,
      isVisible: false,
      dismissedSections: section
        ? new Set([...prev.dismissedSections, section])
        : prev.dismissedSections
    }));

    // Reappear after delay for continued session
    setTimeout(() => {
      if (shouldShowFeedbackForSection()) {
        setSessionState((prev: FeedbackSessionState) => ({ ...prev, isVisible: true }));
      }
    }, 15000); // 15 seconds
  }, []);

  const handleMinimize = () => {
    setIsMinimized(true);
    setSessionState((prev: FeedbackSessionState) => ({ ...prev, isVisible: false }));
  };

  const handleMaximize = () => {
    setIsMinimized(false);
    setSessionState((prev: FeedbackSessionState) => ({ ...prev, isVisible: true }));
  };

  const handleClearHistory = () => {
    setFeedbackHistory([]);
    setSessionState((prev: FeedbackSessionState) => ({
      ...prev,
      submittedCount: 0,
      lastSubmittedAt: undefined,
      dismissedSections: new Set()
    }));
  };

  const totalFeedbackCount = feedbackHistory.length;

  return (
    <>
      {/* Feedback Trigger */}
      {(sessionState.isVisible || activeTrigger) && (
        <SmartFeedbackTrigger
          type={(activeTrigger || 'general') as 'address_issue' | 'missing_data' | 'incorrect_calculation' | 'general'}
          context={{
            propertyAddress,
            section: activeTrigger || 'general',
            currentValue: null,
            expectedValue: null
          }}
          onFeedback={handleFeedbackSubmit}
          delay={0} // No delay for persistent access
        />
      )}

      {/* Persistent Feedback Hub */}
      <div className={`fixed bottom-4 right-4 z-50 transition-all duration-300 ${
        isMinimized ? 'translate-y-0' : 'translate-y-0'
      }`}>
        <Card className="shadow-lg border-2 border-blue-200 bg-white max-w-sm">
          {!isMinimized && (
            <>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-blue-500" />
                    Feedback Hub
                    {totalFeedbackCount > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {totalFeedbackCount}
                      </Badge>
                    )}
                  </CardTitle>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleMinimize}
                      className="h-6 w-6 p-0"
                      title="Minimize"
                    >
                      <Minimize2 className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDismiss(activeTrigger ?? undefined)}
                      className="h-6 w-6 p-0"
                      title="Dismiss for this section"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-3">
                {/* Quick Stats */}
                <div className="mb-3 text-xs text-gray-600">
                  <div className="flex justify-between">
                    <span>Session progress:</span>
                    <span>{formatDuration(Date.now() - sessionState.sessionStartTime.getTime())}</span>
                  </div>
                  {sessionState.submittedCount > 0 && (
                    <div className="flex justify-between">
                      <span>Feedback submitted:</span>
                      <span className="font-medium">{sessionState.submittedCount}</span>
                    </div>
                  )}
                </div>

                {/* Active Trigger */}
                {activeTrigger && (
                  <div className="mb-3 p-2 bg-blue-50 rounded border border-blue-200">
                    <p className="text-xs text-blue-700">
                      Currently reviewing: <strong>{activeTrigger}</strong>
                    </p>
                  </div>
                )}

                {/* Quick Actions */}
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSuggestionsForm(true)}
                    className="w-full text-xs justify-start"
                  >
                    <Plus className="h-3 w-3 mr-2" />
                    Add General Suggestion
                  </Button>

                  {sections && sections.length > 1 && (
                    <div className="space-y-1">
                      <p className="text-xs text-gray-500 mb-1">Quick feedback for:</p>
                      {sections.map(section => (
                        <Button
                          key={section}
                          variant="ghost"
                          size="sm"
                          onClick={() => setActiveTrigger(section)}
                          className={`w-full text-xs justify-start text-left ${
                            activeTrigger === section ? 'bg-blue-50 border-blue-200' : ''
                          }`}
                        >
                          {section}
                        </Button>
                      ))}
                    </div>
                  )}

                  {/* Recent Feedback */}
                  {feedbackHistory.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs text-gray-500">Recent feedback:</p>
                      {feedbackHistory.slice(0, 3).map((item, index) => (
                        <div
                          key={item.id}
                          className="p-2 bg-gray-50 rounded text-xs border border-gray-200"
                        >
                          <div className="flex justify-between items-start mb-1">
                            <span className="font-medium text-gray-900 truncate">
                              {item.type.replace('_', ' ')}
                            </span>
                            <span className="text-gray-500">
                              {formatTime(item.createdAt)}
                            </span>
                          </div>
                          <p className="text-gray-600 truncate">
                            {item.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Clear History */}
                  {feedbackHistory.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleClearHistory}
                      className="w-full text-xs text-gray-500"
                    >
                      <History className="h-3 w-3 mr-1" />
                      Clear History
                    </Button>
                  )}
                </div>
              </CardContent>
            </>
          )}

          {/* Minimized State */}
          {isMinimized && (
            <CardContent className="p-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-blue-500" />
                  <span className="text-xs font-medium">Feedback</span>
                  {totalFeedbackCount > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {totalFeedbackCount}
                    </Badge>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleMaximize}
                  className="h-6 w-6 p-0"
                  title="Maximize"
                >
                  <Maximize2 className="h-3 w-3" />
                </Button>
              </div>
            </CardContent>
          )}
        </Card>
      </div>

      {/* Suggestions Form Modal */}
      {showSuggestionsForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="max-w-md w-full mx-4 shadow-xl">
            <CardHeader>
              <CardTitle className="text-sm font-medium">Share Your Professional Insight</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowSuggestionsForm(false)}
                className="h-6 w-6 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-700">
                  Your insight about this property:
                </label>
                <Textarea
                  placeholder="What professional observation or suggestion do you have about this property or compliance analysis?"
                  value={suggestionText}
                  onChange={(e) => setSuggestionText(e.target.value)}
                  className="text-xs mt-1 min-h-[80px]"
                />
              </div>

              {/* Pre-filled role selection */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <label className="text-xs font-semibold text-blue-900 block mb-2">
                  Your Professional Role * (Auto-selected)
                </label>
                <Select value={sessionState.userRole} onValueChange={(value) => setSessionState(prev => ({ ...prev, userRole: value }))}>

                  <SelectTrigger className="text-sm bg-white border-blue-300">
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="certifier">Council Certifier</SelectItem>
                    <SelectItem value="planner">Town Planner</SelectItem>
                    <SelectItem value="developer">Developer</SelectItem>
                    <SelectItem value="architect">Architect</SelectItem>
                    <SelectItem value="other">Other Professional</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleSuggestionSubmit}
                  disabled={!suggestionText.trim() || !sessionState.userRole}
                  className="flex-1 text-xs"
                >
                  Submit Insight
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSuggestionsForm(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Thank You Message */}
      {showThankYou && (
        <div className="fixed bottom-4 right-4 bg-green-50 border border-green-200 rounded-lg shadow-lg p-4 max-w-sm z-50">
          <div className="flex items-center gap-2 text-green-700">
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm font-medium">
              {totalFeedbackCount === 1 ? 'Thank you!' : 'Thank you!'}
            </span>
          </div>
          <p className="text-xs text-green-600 mt-1">
            Your professional insight helps us improve accuracy for everyone.
          </p>
        </div>
      )}
    </>
  );
}

// Helper functions
function formatDuration(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  if (minutes < 1) {
    return `${Math.floor(ms / 1000)}s`;
  }
  return `${minutes}m`;
}

function formatTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const minutes = Math.floor(diffMs / 60000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
}
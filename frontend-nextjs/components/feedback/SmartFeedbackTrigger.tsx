'use client';

import { useState, useEffect } from 'react';
import { AlertCircle, Flag, X, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface FeedbackContext {
  propertyAddress: string;
  section: string;
  currentValue?: any;
  expectedValue?: any;
  userInput?: string;
  confidence?: number;
}

interface FeedbackTriggerProps {
  type: 'address_issue' | 'missing_data' | 'incorrect_calculation' | 'general';
  context: FeedbackContext;
  onFeedback?: (feedback: FeedbackData) => void;
  delay?: number; // Delay before showing (in seconds)
}

interface FeedbackData {
  type: string;
  context: FeedbackContext;
  description: string;
  userType: string;
  severity: 'low' | 'medium' | 'high';
  contactEmail?: string;
  sessionId?: string;
  propertyId?: string;
}

export interface FeedbackSessionState {
  isVisible: boolean;
  hasSubmitted: boolean;
  submittedCount: number;
  lastSubmittedAt?: Date;
  currentPropertyId?: string;
  dismissedSections: Set<string>;
  userRole?: string;
  sessionStartTime: Date;
}

export function SmartFeedbackTrigger({
  type,
  context,
  onFeedback,
  delay = 3
}: FeedbackTriggerProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  const [userType, setUserType] = useState('');
  const [severity, setSeverity] = useState<'low' | 'medium' | 'high'>('medium');
  const [contactEmail, setContactEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showThankYou, setShowThankYou] = useState(false);
  const [showRoleAlert, setShowRoleAlert] = useState(false);

  // Show based on user interaction patterns
  useEffect(() => {
    const timer = setTimeout(() => {
      // Check if user has interacted with the section
      if (hasUserInteractedWithSection(context.section)) {
        setIsVisible(true);
      }
    }, delay * 1000);

    return () => clearTimeout(timer);
  }, [context.section, delay]);

  const hasUserInteractedWithSection = (section: string): boolean => {
    // Simple heuristic: assume interaction if we're rendering this component
    return true;
  };

  const getFeedbackPrompt = (): string => {
    switch (type) {
      case 'address_issue':
        return `Is "${context.propertyAddress}" the correct address for this property?`;
      case 'missing_data':
        return `Are there missing ${context.section} requirements for this property?`;
      case 'incorrect_calculation':
        return `Do the ${context.section} calculations look correct?`;
      default:
        return 'Notice anything that needs attention?';
    }
  };

  const getQuickActions = () => {
    switch (type) {
      case 'address_issue':
        return [
          { label: 'Wrong address', value: 'Address is incorrect' },
          { label: 'Wrong suburb', value: 'Suburb/mapping is incorrect' },
          { label: 'Property not found', value: 'Property does not exist at this address' }
        ];
      case 'missing_data':
        return [
          { label: 'Missing requirements', value: 'Missing DCP requirements' },
          { label: 'No precinct data', value: 'Missing precinct-specific requirements' },
          { label: 'Outdated controls', value: 'Planning controls seem outdated' }
        ];
      case 'incorrect_calculation':
        return [
          { label: 'Wrong setback', value: 'Setback calculation is incorrect' },
          { label: 'Wrong FSR', value: 'FSR calculation is incorrect' },
          { label: 'Wrong height limit', value: 'Height limit is incorrect' }
        ];
      default:
        return [
          { label: 'Data issue', value: 'Data appears incorrect' },
          { label: 'Missing info', value: 'Information is missing' },
          { label: 'Other', value: 'Other issue' }
        ];
    }
  };

  const handleQuickFeedback = (value: string) => {
    setFeedbackText(value);
    setIsExpanded(true);
  };

  const handleSubmit = async () => {
    if (!feedbackText.trim() || !userType) {
      // Alert user that role is required
      if (!userType) {
        setShowRoleAlert(true);
        setTimeout(() => setShowRoleAlert(false), 3000);
      }
      return;
    }

    setIsSubmitting(true);

    const feedbackData: FeedbackData = {
      type,
      context,
      description: feedbackText,
      userType,
      severity,
      contactEmail: contactEmail || undefined
    };

    try {
      // Send to feedback API
      const response = await fetch('/api/feedback/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackData),
      });

      if (response.ok) {
        onFeedback?.(feedbackData);
        setShowThankYou(true);

        // Hide after showing thank you message
        setTimeout(() => {
          setIsVisible(false);
          setShowThankYou(false);
          // Reset form
          setFeedbackText('');
          setUserType('');
          setSeverity('medium');
          setContactEmail('');
          setIsExpanded(false);
        }, 3000);
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismiss = () => {
    setIsVisible(false);
    // Allow re-appearance after delay for continued user journey
    setTimeout(() => {
      // Check if user is still in a context where feedback is relevant
      if (hasUserInteractedWithSection(context.section)) {
        setIsVisible(true);
      }
    }, 15000); // Re-appear after 15 seconds for continued session
  };

  if (!isVisible) return null;

  if (showRoleAlert) {
    return (
      <div className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-lg shadow-lg p-4 max-w-sm z-50">
        <div className="flex items-center gap-2 text-red-700">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Professional Role Required</span>
        </div>
        <p className="text-xs text-red-600 mt-1">
          Please select your professional role to validate this feedback.
        </p>
      </div>
    );
  }

  if (showThankYou) {
    return (
      <div className="fixed bottom-4 right-4 bg-green-50 border border-green-200 rounded-lg shadow-lg p-4 max-w-sm z-50">
        <div className="flex items-center gap-2 text-green-700">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Thank you for your feedback!</span>
        </div>
        <p className="text-xs text-green-600 mt-1">
          Your professional insight helps us improve accuracy for everyone.
        </p>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <Card className="shadow-lg border-2 border-orange-100">
        <CardContent className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Flag className="h-4 w-4 text-orange-500" />
              <span className="text-sm font-medium">Notice something incorrect?</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDismiss}
              className="h-6 w-6 p-0"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>

          {/* Context Prompt */}
          <p className="text-xs text-gray-600 mb-3">
            {getFeedbackPrompt()}
          </p>

          {!isExpanded ? (
            /* Quick Actions */
            <div className="space-y-2">
              <div className="grid grid-cols-1 gap-2">
                {getQuickActions().map((action) => (
                  <Button
                    key={action.value}
                    variant="outline"
                    size="sm"
                    onClick={() => handleQuickFeedback(action.value)}
                    className="text-xs justify-start h-8"
                  >
                    {action.label}
                  </Button>
                ))}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(true)}
                  className="text-xs flex-1"
                >
                  Provide more details
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDismiss}
                  className="text-xs text-gray-500"
                >
                  All good
                </Button>
              </div>
            </div>
          ) : (
            /* Expanded Form */
            <div className="space-y-3">
              <Textarea
                placeholder="Please describe the issue in detail..."
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                className="text-xs min-h-[80px]"
              />

              {/* Prominent Role Selection - Critical for Feedback Validity */}
              <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <label className="text-xs font-semibold text-blue-900 block mb-2">
                  Your Professional Role * (Helps us validate feedback importance)
                </label>
                <Select value={userType} onValueChange={setUserType}>
                  <SelectTrigger className="text-sm bg-white border-blue-300 focus:border-blue-500">
                    <SelectValue placeholder="Select your role (required)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="certifier" className="text-sm">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                        Council Certifier
                      </div>
                    </SelectItem>
                    <SelectItem value="planner" className="text-sm">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                        Town Planner
                      </div>
                    </SelectItem>
                    <SelectItem value="developer" className="text-sm">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                        Developer
                      </div>
                    </SelectItem>
                    <SelectItem value="architect" className="text-sm">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                        Architect
                      </div>
                    </SelectItem>
                    <SelectItem value="other" className="text-sm">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-gray-500 rounded-full"></span>
                        Other Professional
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-blue-600 mt-1">
                  Your role helps prioritize and validate feedback accuracy
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Select value={severity} onValueChange={(value: any) => setSeverity(value)}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low Issue</SelectItem>
                    <SelectItem value="medium">Medium Issue</SelectItem>
                    <SelectItem value="high">High Issue</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <input
                type="email"
                placeholder="Email (optional - for follow-up)"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
              />

              <div className="flex gap-2">
                <Button
                  onClick={handleSubmit}
                  disabled={!feedbackText.trim() || !userType || isSubmitting}
                  className="flex-1 text-xs"
                  size="sm"
                >
                  {isSubmitting ? (
                    <>Sending...</>
                  ) : (
                    <>
                      <Send className="h-3 w-3 mr-1" />
                      Send Feedback
                    </>
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(false)}
                  className="text-xs"
                >
                  Back
                </Button>
              </div>
            </div>
          )}

          {/* Context Info */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Property: {context.propertyAddress}
              {context.section && ` • Section: ${context.section}`}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
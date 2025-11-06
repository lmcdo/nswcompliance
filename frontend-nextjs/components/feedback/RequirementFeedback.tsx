'use client';

import { useState } from 'react';
import { Flag, ThumbsUp, ThumbsDown, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface RequirementFeedbackProps {
  requirement: {
    id: string;
    title: string;
    text: string;
    source?: string;
    section?: string;
  };
  propertyAddress: string;
  onSubmit?: (feedback: any) => void;
  compact?: boolean;
}

interface FeedbackData {
  requirementId: string;
  propertyAddress: string;
  feedbackType: 'correct' | 'incorrect' | 'missing_context' | 'outdated';
  description: string;
  userType: string;
  urgency: 'low' | 'medium' | 'high';
}

export function RequirementFeedback({
  requirement,
  propertyAddress,
  onSubmit,
  compact = false
}: RequirementFeedbackProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackType, setFeedbackType] = useState<FeedbackData['feedbackType']>('incorrect');
  const [description, setDescription] = useState('');
  const [userType, setUserType] = useState('');
  const [urgency, setUrgency] = useState<'low' | 'medium' | 'high'>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);
  const [voteType, setVoteType] = useState<'up' | 'down' | null>(null);

  const handleSubmit = async () => {
    if (!description.trim() || !userType) {
      if (!userType) {
        alert('Please select your professional role to validate this feedback.');
      }
      return;
    }

    setIsSubmitting(true);

    const feedbackData: FeedbackData = {
      requirementId: requirement.id,
      propertyAddress,
      feedbackType,
      description,
      userType,
      urgency
    };

    try {
      const response = await fetch('/api/feedback/requirement', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackData),
      });

      if (response.ok) {
        onSubmit?.(feedbackData);
        setShowFeedback(false);
        setDescription('');
        setUserType('');
        setFeedbackType('incorrect');
        setUrgency('medium');
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVote = async (type: 'up' | 'down') => {
    setVoteType(type);
    setHasVoted(true);

    // Track simple vote without requiring full form
    try {
      await fetch('/api/feedback/vote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          requirementId: requirement.id,
          propertyAddress,
          voteType: type
        }),
      });
    } catch (error) {
      console.error('Failed to record vote:', error);
    }
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2 ml-2">
        {/* Quick vote buttons */}
        {!hasVoted ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleVote('up')}
              className="h-6 w-6 p-0 text-green-600 hover:text-green-700"
              title="This requirement is correct"
            >
              <ThumbsUp className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleVote('down')}
              className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
              title="This requirement needs attention"
            >
              <ThumbsDown className="h-3 w-3" />
            </Button>
          </>
        ) : (
          <span className="text-xs text-gray-500">
            {voteType === 'up' ? '✓ Thanks!' : 'Thanks for the feedback'}
          </span>
        )}

        {/* Detailed feedback trigger */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowFeedback(!showFeedback)}
          className="h-6 w-6 p-0 text-gray-400 hover:text-gray-600"
          title="Report detailed issue with this requirement"
        >
          <Flag className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-2">
      {/* Feedback Trigger */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Is this requirement accurate?</span>
          {!hasVoted && (
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleVote('up')}
                className="h-6 px-2 text-xs text-green-600 hover:text-green-700"
              >
                <ThumbsUp className="h-3 w-3 mr-1" />
                Correct
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleVote('down')}
                className="h-6 px-2 text-xs text-red-600 hover:text-red-700"
              >
                <ThumbsDown className="h-3 w-3 mr-1" />
                Needs review
              </Button>
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowFeedback(!showFeedback)}
          className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700"
        >
          <Flag className="h-3 w-3 mr-1" />
          Report Issue
        </Button>
      </div>

      {/* Expanded Feedback Form */}
      {showFeedback && (
        <Card className="mt-3">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              <span className="text-sm font-medium">Report Issue with Requirement</span>
            </div>

            <div className="space-y-3">
              {/* Feedback Type */}
              <div>
                <label className="text-xs font-medium text-gray-700">What type of issue?</label>
                <Select value={feedbackType} onValueChange={(value: any) => setFeedbackType(value)}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="incorrect">Information is incorrect</SelectItem>
                    <SelectItem value="missing_context">Missing important context</SelectItem>
                    <SelectItem value="outdated">Information is outdated</SelectItem>
                    <SelectItem value="correct">Actually correct (false alarm)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-medium text-gray-700">Please describe the issue</label>
                <Textarea
                  placeholder="What specifically needs to be corrected or added?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="mt-1 text-xs min-h-[60px]"
                />
              </div>

              {/* Prominent Role Selection - Critical for Validity */}
              <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <label className="text-xs font-semibold text-blue-900 block mb-2">
                  Your Professional Role * (Validates feedback importance)
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
                  Professional role validates feedback accuracy and priority
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-medium text-gray-700">Urgency</label>
                  <Select value={urgency} onValueChange={(value: any) => setUrgency(value)}>
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low - Minor issue</SelectItem>
                      <SelectItem value="medium">Medium - Needs attention</SelectItem>
                      <SelectItem value="high">High - Critical issue</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button
                  onClick={handleSubmit}
                  disabled={!description.trim() || !userType || isSubmitting}
                  className="flex-1 text-xs"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowFeedback(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
              </div>
            </div>

            {/* Context Info */}
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                Requirement: {requirement.title}
                {requirement.section && ` • Section: ${requirement.section}`}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
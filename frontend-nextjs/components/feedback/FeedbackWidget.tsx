'use client';

import { useState } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { getCohort } from '@/lib/cohort';

interface FeedbackWidgetProps {
  propertyAddress?: string;
  provisionContext?: {
    id: number;
    title: string;
    source: string;
  };
}

type FeedbackType =
  | 'data_accuracy'
  | 'missing_info'
  | 'feature_request'
  | 'ui_ux'
  | 'bug_report'
  | 'general';

type UserType =
  | 'certifier' | 'town_planner' | 'architect' | 'developer'
  | 'student' | 'academic' | 'other';

export default function FeedbackWidget({
  propertyAddress,
  provisionContext
}: FeedbackWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<FeedbackType>('general');
  const [feedbackText, setFeedbackText] = useState('');
  const [email, setEmail] = useState('');
  // A tagged visitor is a student until they say otherwise. Leaving the
  // default at 'certifier' would mislabel a whole cohort's feedback unless
  // every student remembered to change it every time.
  const cohort = typeof window !== 'undefined' ? getCohort() : null;
  const [userType, setUserType] = useState<UserType>(
    cohort ? 'student' : 'certifier');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const pathname = usePathname();

  const feedbackTypes = [
    { value: 'data_accuracy', label: 'Data Accuracy Issue', icon: '🎯' },
    { value: 'missing_info', label: 'Missing Information', icon: '📋' },
    { value: 'feature_request', label: 'Feature Request', icon: '💡' },
    { value: 'ui_ux', label: 'UI/UX Improvement', icon: '🎨' },
    { value: 'bug_report', label: 'Bug Report', icon: '🐛' },
    { value: 'general', label: 'General Comment', icon: '💬' },
  ];

  const userTypes = [
    { value: 'certifier', label: 'Certifier' },
    { value: 'town_planner', label: 'Town Planner' },
    { value: 'architect', label: 'Architect' },
    { value: 'developer', label: 'Developer' },
    { value: 'student', label: 'Student' },
    { value: 'academic', label: 'Academic / lecturer' },
    { value: 'other', label: 'Other' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedbackType,
          feedbackText,
          email: email || null,
          userType,
          context: {
            cohort,          // null when untagged — never a placeholder
            page: pathname,
            url: typeof window !== 'undefined' ? window.location.href : '',
            propertyAddress: propertyAddress || 'Not specified',
            provisionContext,
            timestamp: new Date().toISOString(),
            browserInfo: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown',
            screenResolution: typeof window !== 'undefined'
              ? `${window.screen.width}x${window.screen.height}`
              : 'Unknown',
          },
        }),
      });

      if (response.ok) {
        setSubmitted(true);
        setTimeout(() => {
          setIsOpen(false);
          setSubmitted(false);
          setFeedbackText('');
          setEmail('');
          setFeedbackType('general');
          // Back to the cohort-aware default, not 'certifier' — a student
          // filing a second report would otherwise be relabelled.
          setUserType(cohort ? 'student' : 'certifier');
        }, 3000);
      } else {
        console.error('Failed to submit feedback');
        alert('Failed to submit feedback. Please try again.');
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-blue-600 text-white px-4 py-3 rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        aria-label="Open feedback panel"
      >
        <MessageCircle size={20} />
        <span className="font-medium">Feedback</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 max-w-[calc(100vw-3rem)] bg-white rounded-lg shadow-2xl border border-gray-200 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center gap-2">
          <MessageCircle size={20} className="text-blue-600" />
          <h3 className="font-semibold text-gray-900">Share Your Feedback</h3>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 rounded"
          aria-label="Close feedback panel"
        >
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 max-h-[calc(100vh-12rem)] overflow-y-auto">
        {submitted ? (
          <div className="py-8 text-center">
            <div className="text-green-600 text-5xl mb-3">✓</div>
            <h4 className="font-semibold text-gray-900 mb-2">Thank You!</h4>
            <p className="text-sm text-gray-600">
              Your feedback helps improve compliance accuracy for all professionals.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Context Display (if available) */}
            {(propertyAddress || provisionContext) && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-xs">
                <p className="font-medium text-blue-900 mb-1">Context:</p>
                {propertyAddress && (
                  <p className="text-blue-700">📍 {propertyAddress}</p>
                )}
                {provisionContext && (
                  <p className="text-blue-700 mt-1">
                    📋 {provisionContext.title}
                  </p>
                )}
              </div>
            )}

            {/* Intro Text */}
            <p className="text-sm text-gray-600">
              As a professional user, your insights help us improve this tool for certifiers and planners.
            </p>

            {/* User Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                I am a:
              </label>
              <select
                value={userType}
                onChange={(e) => setUserType(e.target.value as UserType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              >
                {userTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Feedback Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Feedback Type
              </label>
              <div className="space-y-2">
                {feedbackTypes.map((type) => (
                  <label
                    key={type.value}
                    className="flex items-center gap-2 p-2 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="radio"
                      name="feedbackType"
                      value={type.value}
                      checked={feedbackType === type.value}
                      onChange={(e) => setFeedbackType(e.target.value as FeedbackType)}
                      className="text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-lg">{type.icon}</span>
                    <span className="text-sm text-gray-700">{type.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Feedback Text */}
            <div>
              <label
                htmlFor="feedbackText"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Your Feedback <span className="text-red-500">*</span>
              </label>
              <textarea
                id="feedbackText"
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Please describe your feedback in detail..."
                required
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm resize-y"
              />
            </div>

            {/* Optional Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Email (optional - for follow-up)
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting || !feedbackText.trim()}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Submit Feedback
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

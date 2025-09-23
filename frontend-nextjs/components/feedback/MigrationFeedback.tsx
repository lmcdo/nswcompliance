'use client';

import React, { useState } from 'react';

interface FeedbackData {
 rating: number;
 category: string;
 comment: string;
 phase: string;
 timestamp: string;
}

export const MigrationFeedback: React.FC = () => {
 const [isOpen, setIsOpen] = useState(false);
 const [rating, setRating] = useState(0);
 const [category, setCategory] = useState('');
 const [comment, setComment] = useState('');
 const [submitted, setSubmitted] = useState(false);

 const handleSubmit = async (e: React.FormEvent) => {
 e.preventDefault();

 const feedback: FeedbackData = {
 rating,
 category,
 comment,
 phase: 'migration',
 timestamp: new Date().toISOString(),
 };

 try {
 await fetch('/api/feedback', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(feedback),
 });

 setSubmitted(true);
 setTimeout(() => {
 setIsOpen(false);
 setSubmitted(false);
 setRating(0);
 setCategory('');
 setComment('');
 }, 2000);
 } catch (error) {
 console.error('Failed to submit feedback:', error);
 }
 };

 if (submitted) {
 return (
 <div className="fixed bottom-4 right-4 bg-green-500 text-white p-4 rounded-lg shadow-lg">
 Thank you for your feedback!
 </div>
 );
 }

 return (
 <>
 {/* Feedback Button */}
 <button
 onClick={() => setIsOpen(true)}
 className="fixed bottom-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg hover:bg-blue-700 transition-colors"
 >
 Give Feedback
 </button>

 {/* Feedback Modal */}
 {isOpen && (
 <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
 <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
 <h2 className="text-xl font-bold mb-4">Migration Feedback</h2>

 <form onSubmit={handleSubmit} className="space-y-4">
 {/* Rating */}
 <div>
 <label className="block text-sm font-medium mb-2">
 Overall Experience
 </label>
 <div className="flex space-x-1">
 {[1, 2, 3, 4, 5].map((star) => (
 <button
 key={star}
 type="button"
 onClick={() => setRating(star)}
 className={`text-2xl ${
 rating >= star ? 'text-yellow-400' : 'text-gray-300'
 } hover:text-yellow-400 transition-colors`}
 >
 
 </button>
 ))}
 </div>
 </div>

 {/* Category */}
 <div>
 <label className="block text-sm font-medium mb-2">
 Category
 </label>
 <select
 value={category}
 onChange={(e) => setCategory(e.target.value)}
 className="w-full px-3 py-2 border rounded-md"
 required
 >
 <option value="">Select category...</option>
 <option value="performance">Performance</option>
 <option value="usability">Usability</option>
 <option value="bugs">Bug Report</option>
 <option value="feature-request">Feature Request</option>
 <option value="general">General</option>
 </select>
 </div>

 {/* Comment */}
 <div>
 <label className="block text-sm font-medium mb-2">
 Comments
 </label>
 <textarea
 value={comment}
 onChange={(e) => setComment(e.target.value)}
 className="w-full px-3 py-2 border rounded-md h-24 resize-none"
 placeholder="Tell us about your experience..."
 required
 />
 </div>

 {/* Buttons */}
 <div className="flex space-x-3">
 <button
 type="submit"
 disabled={!rating || !category || !comment}
 className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
 >
 Submit Feedback
 </button>
 <button
 type="button"
 onClick={() => setIsOpen(false)}
 className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
 >
 Cancel
 </button>
 </div>
 </form>
 </div>
 </div>
 )}
 </>
 );
};
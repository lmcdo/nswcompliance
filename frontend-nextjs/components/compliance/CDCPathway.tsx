'use client';

/**
 * CDC/DA Pathway Decision Tree
 *
 * Interactive sequential eligibility checker for owner builders.
 * Asks questions step-by-step and shows real-time verdict.
 */

import { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, ChevronRight, Home } from 'lucide-react';

interface CDCPathwayProps {
  propertyData: any;
  proposedWorkType?: 'deck' | 'garage' | 'extension' | 'other';
}

interface Question {
  id: string;
  text: string;
  type: 'boolean' | 'number' | 'select';
  unit?: string;
  options?: Array<{ value: string; label: string }>;
  guidance?: string;
}

interface Answer {
  questionId: string;
  value: any;
}

interface CheckResult {
  passed: boolean;
  criterion: string;
  reason: string;
  suggestion?: string;
}

const QUESTIONS: Question[] = [
  {
    id: 'lot_area',
    text: 'What is your lot area?',
    type: 'number',
    unit: 'm²',
    guidance: 'Minimum lot size requirements vary by zone and work type. See SEPP Housing Code Part 3.',
  },
  {
    id: 'heritage_item',
    text: 'Is your property a heritage item or in a heritage conservation area?',
    type: 'boolean',
    guidance: 'CDC works are generally restricted on heritage properties. Check property constraints above.',
  },
  {
    id: 'max_height',
    text: 'What is the maximum height of your proposed works?',
    type: 'number',
    unit: 'm',
    guidance: 'Height limits vary by zone. SEPP Housing Code specifies maximum heights for complying development.',
  },
  {
    id: 'floor_area',
    text: 'What is the total floor area of the new works?',
    type: 'number',
    unit: 'm²',
    guidance: 'Include all floor area for decks, garages, extensions. Limits vary by work type and zone.',
  },
  {
    id: 'setback_front',
    text: 'How far is the structure from the front boundary?',
    type: 'number',
    unit: 'm',
    guidance: 'Front setback must match or exceed the prevailing setback of neighboring properties.',
  },
  {
    id: 'setback_side',
    text: 'How far is the structure from the side boundary?',
    type: 'number',
    unit: 'm',
    guidance: 'Side setback requirements depend on lot width and building height. See SEPP Clause 3.10.',
  },
];

export function CDCPathway({ propertyData, proposedWorkType = 'other' }: CDCPathwayProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [results, setResults] = useState<CheckResult[]>([]);
  const [verdict, setVerdict] = useState<'eligible' | 'ineligible' | 'review' | null>(null);

  // Pre-fill lot area from property data
  useEffect(() => {
    if (propertyData?.lotDimensions?.area && answers.length === 0) {
      const lotArea = Math.round(propertyData.lotDimensions.area);
      setAnswers([{ questionId: 'lot_area', value: lotArea }]);
    }
  }, [propertyData, answers.length]);

  // Pre-fill heritage from property data
  useEffect(() => {
    if (propertyData?.heritage && answers.length <= 1) {
      const isHeritage = propertyData.heritage.isHeritage;
      if (!answers.find(a => a.questionId === 'heritage_item')) {
        setAnswers(prev => [...prev, { questionId: 'heritage_item', value: isHeritage }]);
      }
    }
  }, [propertyData, answers]);

  const handleAnswer = (questionId: string, value: any, autoAdvance: boolean = false) => {
    setAnswers(prev => {
      const existing = prev.findIndex(a => a.questionId === questionId);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { questionId, value };
        return updated;
      }
      return [...prev, { questionId, value }];
    });

    // Auto-advance only for boolean questions (single-click Yes/No)
    if (autoAdvance && currentStep < QUESTIONS.length - 1) {
      setTimeout(() => setCurrentStep(currentStep + 1), 300);
    }
  };

  const handleNext = () => {
    if (currentStep < QUESTIONS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const canAdvance = () => {
    const answer = answers.find(a => a.questionId === currentQuestion?.id);
    if (!answer) return false;
    if (currentQuestion?.type === 'number') {
      return !isNaN(answer.value) && answer.value > 0;
    }
    return answer.value !== undefined;
  };

  // Collect answers and show summary - NO VALIDATION (requirements are complex and context-dependent)
  useEffect(() => {
    // Only show summary after all questions answered
    if (answers.length === QUESTIONS.length) {
      const summary: CheckResult[] = [
        {
          passed: true,
          criterion: 'Information Collected',
          reason: 'Your project details have been collected. CDC eligibility requires assessment against SEPP Housing Code provisions.',
        },
      ];

      // Check heritage status as a clear blocker
      const isHeritage = answers.find(a => a.questionId === 'heritage_item')?.value as boolean;
      if (isHeritage) {
        summary.push({
          passed: false,
          criterion: 'Heritage Property',
          reason: 'Property is a heritage item or in a heritage conservation area.',
          suggestion: 'CDC eligibility is severely restricted on heritage properties. Consult a heritage specialist and Private Certifier.',
        });
        setResults(summary);
        setVerdict('review');
        return;
      }

      // Add project summary
      const lotArea = answers.find(a => a.questionId === 'lot_area')?.value as number;
      const height = answers.find(a => a.questionId === 'max_height')?.value as number;
      const floorArea = answers.find(a => a.questionId === 'floor_area')?.value as number;
      const frontSetback = answers.find(a => a.questionId === 'setback_front')?.value as number;
      const sideSetback = answers.find(a => a.questionId === 'setback_side')?.value as number;

      summary.push({
        passed: true,
        criterion: 'Your Project Details',
        reason: `Lot: ${lotArea}m² | Height: ${height}m | Floor Area: ${floorArea}m² | Front Setback: ${frontSetback}m | Side Setback: ${sideSetback}m`,
      });

      summary.push({
        passed: true,
        criterion: 'Next Steps',
        reason: 'Engage a Private Certifier to assess your specific project against SEPP (Exempt and Complying Development Codes) 2008.',
        suggestion: 'For official CDC guidance, visit the NSW Planning Portal: https://www.planningportal.nsw.gov.au/development-assessment/codes-sepp/housing-code',
      });

      setResults(summary);
      setVerdict('review');
    } else {
      setResults([]);
      setVerdict(null);
    }
  }, [answers]);

  const currentQuestion = QUESTIONS[currentStep];
  const currentAnswer = answers.find(a => a.questionId === currentQuestion?.id);

  return (
    <div className="space-y-4">
      {/* Progress */}
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <span className="font-medium">Step {Math.min(currentStep + 1, QUESTIONS.length)} of {QUESTIONS.length}</span>
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-600 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / QUESTIONS.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Questions */}
      <div className="space-y-3">
        {QUESTIONS.map((question, index) => {
          const answer = answers.find(a => a.questionId === question.id);
          const isActive = index === currentStep;
          const isAnswered = answer !== undefined;
          const canEdit = isAnswered && !isActive;

          return (
            <div
              key={question.id}
              onClick={() => canEdit && setCurrentStep(index)}
              className={`group border rounded-lg p-4 transition-all ${
                isActive
                  ? 'border-teal-400 bg-teal-50 shadow-sm'
                  : isAnswered
                  ? 'border-gray-200 bg-white cursor-pointer hover:border-teal-300 hover:shadow-sm'
                  : 'border-gray-100 bg-gray-50 opacity-60'
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    isAnswered ? 'bg-teal-600 text-white' : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  {isAnswered ? <CheckCircle2 className="w-4 h-4" /> : index + 1}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 mb-1">{question.text}</p>
                  {question.guidance && isActive && (
                    <p className="text-xs text-gray-600 mb-2 italic">{question.guidance}</p>
                  )}

                  {/* Input */}
                  {isActive && question.type === 'number' && (
                    <div className="flex gap-2 mt-2">
                      <input
                        type="number"
                        value={answer?.value || ''}
                        onChange={(e) => handleAnswer(question.id, parseFloat(e.target.value))}
                        placeholder="Enter value"
                        className="flex-1 text-sm border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
                      />
                      {question.unit && (
                        <span className="flex items-center px-3 py-2 bg-gray-100 border border-gray-300 rounded text-sm text-gray-600">
                          {question.unit}
                        </span>
                      )}
                    </div>
                  )}

                  {isActive && question.type === 'boolean' && (
                    <div className="flex gap-3 mt-2">
                      <button
                        onClick={() => handleAnswer(question.id, true, true)}
                        className={`flex-1 px-4 py-2 rounded border-2 text-sm font-medium transition-all ${
                          answer?.value === true
                            ? 'border-red-500 bg-red-50 text-red-700'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => handleAnswer(question.id, false, true)}
                        className={`flex-1 px-4 py-2 rounded border-2 text-sm font-medium transition-all ${
                          answer?.value === false
                            ? 'border-green-500 bg-green-50 text-green-700'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        No
                      </button>
                    </div>
                  )}

                  {/* Show answered value */}
                  {isAnswered && !isActive && (
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-sm text-gray-700">
                        <strong>
                          {question.type === 'boolean'
                            ? answer.value
                              ? 'Yes'
                              : 'No'
                            : `${answer.value}${question.unit || ''}`}
                        </strong>
                      </p>
                      <span className="text-xs text-teal-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                        Click to edit
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="mt-6 space-y-4">
          {/* Summary Card */}
          <div className="rounded-xl p-6 border-2 border-blue-500 bg-blue-50">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="w-8 h-8 text-blue-600" />
              <div>
                <h3 className="text-xl font-bold text-blue-900">
                  CDC Assessment Required
                </h3>
                <p className="text-sm mt-1 text-blue-800">
                  CDC eligibility depends on specific SEPP provisions for your work type, zone, and property characteristics.
                  Consult a Private Certifier for a formal CDC assessment.
                </p>
              </div>
            </div>
          </div>

          {/* Project Summary */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-gray-900">Project Information:</h4>
              <p className="text-xs text-gray-600 italic">💡 Click any question above to edit your answer</p>
            </div>
            {results.map((result, index) => (
              <div
                key={index}
                className={`flex items-start gap-3 p-3 rounded-lg border ${
                  result.passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                }`}
              >
                {result.passed ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`text-sm font-medium ${result.passed ? 'text-green-900' : 'text-red-900'}`}>
                    {result.criterion}
                  </p>
                  <p className={`text-xs mt-1 ${result.passed ? 'text-green-800' : 'text-red-800'}`}>{result.reason}</p>
                  {result.suggestion && (
                    <p className="text-xs mt-2 italic text-gray-700 bg-white bg-opacity-50 rounded p-2 border border-gray-200">
                      💡 {result.suggestion}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      {currentStep < QUESTIONS.length && (
        <div className="flex items-center justify-between gap-4 pt-2">
          <button
            onClick={handleBack}
            disabled={currentStep === 0}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentStep === 0
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            ← Back
          </button>
          <button
            onClick={handleNext}
            disabled={!canAdvance() || currentStep === QUESTIONS.length - 1}
            className={`px-6 py-2 rounded-lg text-sm font-medium transition-all ${
              !canAdvance() || currentStep === QUESTIONS.length - 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-teal-600 text-white hover:bg-teal-700 shadow-sm'
            }`}
          >
            {currentStep === QUESTIONS.length - 1 ? 'Complete' : 'Next →'}
          </button>
        </div>
      )}
    </div>
  );
}

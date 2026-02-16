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
    guidance: 'Minimum 450m² required for most CDC works in residential zones.',
  },
  {
    id: 'heritage_item',
    text: 'Is your property a heritage item or in a heritage conservation area?',
    type: 'boolean',
    guidance: 'CDC works are restricted on heritage properties. Check your property constraints above.',
  },
  {
    id: 'max_height',
    text: 'What is the maximum height of your proposed works?',
    type: 'number',
    unit: 'm',
    guidance: 'CDC generally limited to 8.5m building height in residential zones.',
  },
  {
    id: 'floor_area',
    text: 'What is the total floor area of the new works?',
    type: 'number',
    unit: 'm²',
    guidance: 'Including decks, garages, extensions. CDC typically allows up to 60m² additions.',
  },
  {
    id: 'setback_front',
    text: 'How far is the structure from the front boundary?',
    type: 'number',
    unit: 'm',
    guidance: 'Minimum setbacks apply. Check prevailing streetscape for context.',
  },
  {
    id: 'setback_side',
    text: 'How far is the structure from the side boundary?',
    type: 'number',
    unit: 'm',
    guidance: 'Typically minimum 0.9m for single-storey, 1.2m for two-storey.',
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

  const handleAnswer = (questionId: string, value: any) => {
    setAnswers(prev => {
      const existing = prev.findIndex(a => a.questionId === questionId);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { questionId, value };
        return updated;
      }
      return [...prev, { questionId, value }];
    });

    // Auto-advance to next question
    if (currentStep < QUESTIONS.length - 1) {
      setTimeout(() => setCurrentStep(currentStep + 1), 300);
    }
  };

  // Check eligibility based on answers
  useEffect(() => {
    if (answers.length < QUESTIONS.length) {
      setResults([]);
      setVerdict(null);
      return;
    }

    const checks: CheckResult[] = [];

    // Lot area check
    const lotArea = answers.find(a => a.questionId === 'lot_area')?.value as number;
    if (lotArea < 450) {
      checks.push({
        passed: false,
        criterion: 'Minimum lot area',
        reason: `Lot area is ${lotArea}m², minimum 450m² required.`,
        suggestion: 'Consider a DA instead, or reduce the scope of works.',
      });
    } else {
      checks.push({
        passed: true,
        criterion: 'Minimum lot area',
        reason: `Lot area ${lotArea}m² meets 450m² minimum.`,
      });
    }

    // Heritage check
    const isHeritage = answers.find(a => a.questionId === 'heritage_item')?.value as boolean;
    if (isHeritage) {
      checks.push({
        passed: false,
        criterion: 'Heritage restrictions',
        reason: 'Property is a heritage item or in a heritage conservation area.',
        suggestion: 'CDC eligibility is very limited on heritage properties. Consult a heritage consultant.',
      });
    } else {
      checks.push({
        passed: true,
        criterion: 'Heritage status',
        reason: 'Property is not heritage-listed.',
      });
    }

    // Height check
    const height = answers.find(a => a.questionId === 'max_height')?.value as number;
    if (height > 8.5) {
      checks.push({
        passed: false,
        criterion: 'Maximum height',
        reason: `Proposed height ${height}m exceeds 8.5m limit.`,
        suggestion: 'Reduce building height to 8.5m or lodge a DA.',
      });
    } else {
      checks.push({
        passed: true,
        criterion: 'Maximum height',
        reason: `Proposed height ${height}m within 8.5m limit.`,
      });
    }

    // Floor area check
    const floorArea = answers.find(a => a.questionId === 'floor_area')?.value as number;
    if (floorArea > 60) {
      checks.push({
        passed: false,
        criterion: 'Maximum floor area',
        reason: `Proposed floor area ${floorArea}m² exceeds typical 60m² CDC limit.`,
        suggestion: 'Reduce floor area to 60m² or lodge a DA for larger works.',
      });
    } else {
      checks.push({
        passed: true,
        criterion: 'Maximum floor area',
        reason: `Proposed floor area ${floorArea}m² within 60m² limit.`,
      });
    }

    // Setback checks
    const frontSetback = answers.find(a => a.questionId === 'setback_front')?.value as number;
    const sideSetback = answers.find(a => a.questionId === 'setback_side')?.value as number;

    if (frontSetback < 5.5) {
      checks.push({
        passed: false,
        criterion: 'Front setback',
        reason: `Front setback ${frontSetback}m is less than typical 5.5m minimum.`,
        suggestion: 'Check prevailing streetscape — setbacks must match adjoining properties.',
      });
    } else {
      checks.push({
        passed: true,
        criterion: 'Front setback',
        reason: `Front setback ${frontSetback}m meets minimum.`,
      });
    }

    if (sideSetback < 0.9) {
      checks.push({
        passed: false,
        criterion: 'Side setback',
        reason: `Side setback ${sideSetback}m is less than 0.9m minimum for single-storey.`,
        suggestion: 'Move structure at least 0.9m from side boundary.',
      });
    } else {
      checks.push({
        passed: true,
        criterion: 'Side setback',
        reason: `Side setback ${sideSetback}m meets minimum.`,
      });
    }

    setResults(checks);

    // Determine overall verdict
    const failCount = checks.filter(c => !c.passed).length;
    if (failCount === 0) {
      setVerdict('eligible');
    } else if (failCount <= 2) {
      setVerdict('review');
    } else {
      setVerdict('ineligible');
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

          return (
            <div
              key={question.id}
              className={`border rounded-lg p-4 transition-all ${
                isActive
                  ? 'border-teal-400 bg-teal-50 shadow-sm'
                  : isAnswered
                  ? 'border-gray-200 bg-white'
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
                        onClick={() => handleAnswer(question.id, true)}
                        className={`flex-1 px-4 py-2 rounded border-2 text-sm font-medium transition-all ${
                          answer?.value === true
                            ? 'border-red-500 bg-red-50 text-red-700'
                            : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => handleAnswer(question.id, false)}
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
                    <p className="text-sm text-gray-700 mt-1">
                      <strong>
                        {question.type === 'boolean'
                          ? answer.value
                            ? 'Yes'
                            : 'No'
                          : `${answer.value}${question.unit || ''}`}
                      </strong>
                    </p>
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
          {/* Verdict */}
          <div
            className={`rounded-xl p-6 border-2 ${
              verdict === 'eligible'
                ? 'border-green-500 bg-green-50'
                : verdict === 'review'
                ? 'border-amber-500 bg-amber-50'
                : 'border-red-500 bg-red-50'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              {verdict === 'eligible' && <CheckCircle2 className="w-8 h-8 text-green-600" />}
              {verdict === 'review' && <AlertTriangle className="w-8 h-8 text-amber-600" />}
              {verdict === 'ineligible' && <XCircle className="w-8 h-8 text-red-600" />}
              <div>
                <h3
                  className={`text-xl font-bold ${
                    verdict === 'eligible' ? 'text-green-900' : verdict === 'review' ? 'text-amber-900' : 'text-red-900'
                  }`}
                >
                  {verdict === 'eligible' && 'CDC Likely Eligible'}
                  {verdict === 'review' && 'CDC Possible — Requires Review'}
                  {verdict === 'ineligible' && 'CDC Not Eligible'}
                </h3>
                <p
                  className={`text-sm mt-1 ${
                    verdict === 'eligible' ? 'text-green-800' : verdict === 'review' ? 'text-amber-800' : 'text-red-800'
                  }`}
                >
                  {verdict === 'eligible' &&
                    'Your proposed works appear to meet CDC criteria. Engage a Private Certifier to lodge your CDC application.'}
                  {verdict === 'review' &&
                    'Some criteria may need adjustment. Consult a planning consultant or certifier to refine your design.'}
                  {verdict === 'ineligible' &&
                    'Your proposed works do not meet CDC standards. You will need to lodge a Development Application (DA) with council.'}
                </p>
              </div>
            </div>
          </div>

          {/* Detailed Checks */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900">Detailed Checks:</h4>
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
      {currentStep > 0 && currentStep < QUESTIONS.length && (
        <button
          onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
          className="text-sm text-gray-600 hover:text-gray-900 font-medium"
        >
          ← Back to previous question
        </button>
      )}
    </div>
  );
}

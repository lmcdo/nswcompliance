import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { z } from 'zod';
import { formatValidationErrors } from '@/lib/schemas';

// Validation schema for suggestion feedback
const suggestionSchema = z.object({
  type: z.literal('user_suggestion'),
  context: z.object({
    propertyAddress: z.string(),
    section: z.string(),
    occurrenceContext: z.string(),
  }),
  description: z.string().min(1),
  userType: z.enum(['certifier', 'planner', 'developer', 'architect', 'other']),
  severity: z.enum(['low', 'medium', 'high']),
  sessionId: z.string(),
  propertyId: z.string().optional(),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validatedSuggestion = suggestionSchema.parse(body);

    // Store suggestion in database
    const result = await query(`
      INSERT INTO user_feedback (
        type,
        property_address,
        section,
        description,
        user_type,
        severity,
        context_data,
        user_agent,
        ip_address,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      RETURNING id
    `, [
      validatedSuggestion.type,
      validatedSuggestion.context.propertyAddress,
      validatedSuggestion.context.section,
      validatedSuggestion.description,
      validatedSuggestion.userType,
      validatedSuggestion.severity,
      validatedSuggestion.sessionId,
      validatedSuggestion.propertyId
    ]);

    // Send notification for high severity suggestions
    if (validatedSuggestion.severity === 'high') {
      await sendHighPrioritySuggestion(validatedSuggestion);
    }

    return NextResponse.json({
      success: true,
      feedbackId: result.rows[0].id
    });

  } catch (error) {
    console.error('Suggestion submission error:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid suggestion data', details: formatValidationErrors(error) },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to submit suggestion' },
      { status: 500 }
    );
  }
}

async function sendHighPrioritySuggestion(suggestion: any) {
  try {
    // Send to Slack (if configured)
    if (process.env.SLACK_WEBHOOK_URL) {
      await fetch(process.env.SLACK_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `🎯 Professional Suggestion Received`,
          blocks: [
            {
              type: 'section',
              text: `
                Property: ${suggestion.context.propertyAddress}
                Section: ${suggestion.context.section}
                Suggestion: ${suggestion.description.substring(0, 100)}...
              `
            },
            {
              type: 'context',
              text: `
                User Type: ${suggestion.userType}
                Severity: ${suggestion.severity}
                Context: ${suggestion.context.occurrenceContext}
              `
            }
          ]
        }),
      });
    }
  } catch (error) {
      console.error('Failed to send high priority notification:', error);
  }
}
import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { z } from 'zod';
import { FeedbackSubmitSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input using centralized schema
    const validation = validateRequest(FeedbackSubmitSchema, body);

    if (!validation.success) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid feedback data',
          details: formatValidationErrors(validation.details),
        },
        { status: 400 }
      );
    }

    const validatedFeedback = {
      type: body.type || 'general',
      context: body.context || { propertyAddress: '', section: '' },
      description: validation.data.text,
      userType: body.userType || 'other',
      severity: body.severity || 'medium',
      contactEmail: validation.data.email,
    };

    // Store feedback in database
    const result = await query(`
      INSERT INTO user_feedback (
        type,
        property_address,
        section,
        description,
        user_type,
        severity,
        contact_email,
        context_data,
        user_agent,
        ip_address,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
      RETURNING id
    `, [
      validatedFeedback.type,
      validatedFeedback.context.propertyAddress,
      validatedFeedback.context.section,
      validatedFeedback.description,
      validatedFeedback.userType,
      validatedFeedback.severity,
      validatedFeedback.contactEmail || null,
      JSON.stringify(validatedFeedback.context),
      request.headers.get('user-agent') || null,
      request.headers.get('x-forwarded-for') || request.ip || null
    ]);

    // Send notification to development team for high severity issues
    if (validatedFeedback.severity === 'high') {
      await sendHighPriorityNotification(validatedFeedback);
    }

    // Check for similar issues to identify patterns
    await checkForSimilarIssues(validatedFeedback);

    return NextResponse.json({
      success: true,
      feedbackId: result.rows[0].id
    });

  } catch (error) {
    console.error('Feedback submission error:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid feedback data', details: formatValidationErrors(error) },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to submit feedback' },
      { status: 500 }
    );
  }
}

async function sendHighPriorityNotification(feedback: any) {
  try {
    // Send to Slack (if configured)
    if (process.env.SLACK_WEBHOOK_URL) {
      await fetch(process.env.SLACK_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `🚨 High Priority Feedback Received`,
          blocks: [
            {
              type: 'section',
              text: {
                type: 'mrkdwn',
                text: `*High Priority Feedback* from ${feedback.userType}`
              }
            },
            {
              type: 'section',
              fields: [
                {
                  type: 'mrkdwn',
                  text: `*Property:* ${feedback.context.propertyAddress}`
                },
                {
                  type: 'mrkdwn',
                  text: `*Section:* ${feedback.context.section}`
                },
                {
                  type: 'mrkdwn',
                  text: `*Type:* ${feedback.type}`
                },
                {
                  type: 'mrkdwn',
                  text: `*Severity:* ${feedback.severity}`
                }
              ]
            },
            {
              type: 'section',
              text: {
                type: 'plain_text',
                text: feedback.description
              }
            }
          ]
        })
      });
    }

    // Send email notification (if configured)
    if (process.env.ADMIN_EMAIL) {
      // Implement email sending logic here
      console.log('High priority feedback email notification would be sent');
    }

  } catch (error) {
    console.error('Failed to send high priority notification:', error);
  }
}

async function checkForSimilarIssues(feedback: any) {
  try {
    // Look for similar feedback in the last 7 days
    const similarFeedback = await query(`
      SELECT COUNT(*) as similar_count
      FROM user_feedback
      WHERE type = $1
        AND section = $2
        AND created_at > NOW() - INTERVAL '7 days'
        AND description ILIKE '%' || $3 || '%'
    `, [
      feedback.type,
      feedback.context.section,
      feedback.description.split(' ').slice(0, 3).join(' ') // First 3 words for similarity matching
    ]);

    const similarCount = parseInt(similarFeedback.rows[0].similar_count);

    // If 3+ similar issues, create a development task
    if (similarCount >= 3) {
      await createDevelopmentTask(feedback, similarCount);
    }

  } catch (error) {
    console.error('Failed to check for similar issues:', error);
  }
}

async function createDevelopmentTask(feedback: any, similarCount: number) {
  try {
    // Create a task in your project management system
    // This is a placeholder - implement based on your PM tool (Jira, GitHub, etc.)

    console.log(`Development task created for recurring issue: ${feedback.type} in ${feedback.context.section}`);
    console.log(`Similar reports: ${similarCount}`);
    console.log(`Latest report: ${feedback.description}`);

    // You could integrate with:
    // - GitHub Issues API
    // - Jira REST API
    // - Asana API
    // - Custom task management system

  } catch (error) {
    console.error('Failed to create development task:', error);
  }
}
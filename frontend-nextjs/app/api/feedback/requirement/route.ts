import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { z } from 'zod';
import { RequirementFeedbackSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input using centralized schema
    const validation = validateRequest(RequirementFeedbackSchema, body);

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
      requirementId: validation.data.provisionId,
      propertyAddress: body.propertyAddress || '',
      feedbackType: validation.data.isCorrect ? 'correct' : 'incorrect',
      description: validation.data.feedback,
      userType: body.userType || 'other',
      urgency: body.urgency || 'medium',
    };

    // Get requirement details for context
    const requirementDetails = await query(`
      SELECT title, section, source_text, council
      FROM dcp_general_requirements
      WHERE id = $1
    `, [validatedFeedback.requirementId]);

    // Store feedback in database
    const result = await query(`
      INSERT INTO requirement_feedback (
        requirement_id,
        property_address,
        feedback_type,
        description,
        user_type,
        urgency,
        requirement_context,
        user_agent,
        ip_address,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
      RETURNING id
    `, [
      validatedFeedback.requirementId,
      validatedFeedback.propertyAddress,
      validatedFeedback.feedbackType,
      validatedFeedback.description,
      validatedFeedback.userType,
      validatedFeedback.urgency,
      JSON.stringify(requirementDetails.rows[0] || {}),
      request.headers.get('user-agent') || null,
      request.headers.get('x-forwarded-for') || request.ip || null
    ]);

    // Update requirement accuracy metrics
    await updateRequirementMetrics(validatedFeedback.requirementId, validatedFeedback.feedbackType);

    // Check for pattern of issues with this requirement
    await checkRequirementIssuePattern(validatedFeedback);

    return NextResponse.json({
      success: true,
      feedbackId: result.rows[0].id
    });

  } catch (error) {
    console.error('Requirement feedback submission error:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid feedback data', details: formatValidationErrors(error) },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to submit requirement feedback' },
      { status: 500 }
    );
  }
}

async function updateRequirementMetrics(requirementId: string, feedbackType: string) {
  try {
    // Update accuracy statistics for this requirement
    if (feedbackType === 'correct') {
      await query(`
        INSERT INTO requirement_metrics (requirement_id, correct_votes, incorrect_votes, last_updated)
        VALUES ($1, 1, 0, NOW())
        ON CONFLICT (requirement_id)
        DO UPDATE SET
          correct_votes = requirement_metrics.correct_votes + 1,
          last_updated = NOW()
      `, [requirementId]);
    } else if (feedbackType === 'incorrect') {
      await query(`
        INSERT INTO requirement_metrics (requirement_id, correct_votes, incorrect_votes, last_updated)
        VALUES ($1, 0, 1, NOW())
        ON CONFLICT (requirement_id)
        DO UPDATE SET
          incorrect_votes = requirement_metrics.incorrect_votes + 1,
          last_updated = NOW()
      `, [requirementId]);
    }

  } catch (error) {
    console.error('Failed to update requirement metrics:', error);
  }
}

async function checkRequirementIssuePattern(feedback: any) {
  try {
    // Check if this requirement has multiple recent issues
    const recentIssues = await query(`
      SELECT COUNT(*) as issue_count,
             AVG(CASE WHEN urgency = 'high' THEN 3 WHEN urgency = 'medium' THEN 2 ELSE 1 END) as avg_urgency
      FROM requirement_feedback
      WHERE requirement_id = $1
        AND created_at > NOW() - INTERVAL '14 days'
        AND feedback_type != 'correct'
    `, [feedback.requirementId]);

    const issueCount = parseInt(recentIssues.rows[0].issue_count);
    const avgUrgency = parseFloat(recentIssues.rows[0].avg_urgency || 0);

    // Flag requirement for review if multiple issues
    if (issueCount >= 3 && avgUrgency >= 2) {
      await flagRequirementForReview(feedback.requirementId, issueCount, avgUrgency);
    }

  } catch (error) {
    console.error('Failed to check requirement issue pattern:', error);
  }
}

async function flagRequirementForReview(requirementId: string, issueCount: number, avgUrgency: number) {
  try {
    // Add to review queue
    await query(`
      INSERT INTO requirement_review_queue (requirement_id, issue_count, avg_urgency, flagged_at, status)
      VALUES ($1, $2, $3, NOW(), 'pending')
      ON CONFLICT (requirement_id)
      DO UPDATE SET
        issue_count = $2,
        avg_urgency = $3,
        flagged_at = NOW(),
        status = 'pending'
    `, [requirementId, issueCount, avgUrgency]);

    // Send notification to content team
    console.log(`Requirement flagged for review: ${requirementId}`);
    console.log(`Issues: ${issueCount}, Average Urgency: ${avgUrgency.toFixed(1)}`);

    // Implement notification system (email, Slack, etc.)
    if (process.env.CONTENT_TEAM_EMAIL) {
      // Send email to content team about the requirement that needs review
    }

  } catch (error) {
    console.error('Failed to flag requirement for review:', error);
  }
}
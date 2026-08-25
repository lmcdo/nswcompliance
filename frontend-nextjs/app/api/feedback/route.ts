import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';
import { Resend } from 'resend';


export const dynamic = 'force-dynamic';
// Database connection
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'nsw_planning',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  port: parseInt(process.env.DB_PORT || '5432'),
});

// Map our frontend feedback types to database schema
const feedbackTypeMap: Record<string, string> = {
  'data_accuracy': 'data_issue',
  'missing_info': 'missing_data',
  'feature_request': 'feature',
  'ui_ux': 'ui_improvement',
  'bug_report': 'bug',
  'general': 'general',
};

// Determine severity based on feedback type
const getSeverity = (feedbackType: string): string => {
  const highSeverity = ['bug_report', 'data_accuracy'];
  const mediumSeverity = ['missing_info', 'ui_ux'];

  if (highSeverity.includes(feedbackType)) return 'high';
  if (mediumSeverity.includes(feedbackType)) return 'medium';
  return 'low';
};

// Internal alert recipient. Must NOT be @plotdetect.com.au: sending from
// info@plotdetect.com.au to the same domain via Resend is quarantined by
// Google Workspace as self-domain spoofing (Resend reports "delivered" but it
// never reaches the inbox). Route to an off-domain inbox instead.
const NOTIFY_EMAIL = process.env.NOTIFY_EMAIL || 'lawrence.mcdonell@gmail.com';

/**
 * Tell the operator that feedback arrived.
 *
 * Until 2026-08-26 nothing did. Feedback was written to user_feedback and sat
 * there; the `email` field on this route is the SUBMITTER's contact address,
 * not an alert. Every outreach email asks people to report wrong controls, so
 * an unwatched table turns the whole campaign into silence nobody sees.
 *
 * Deliberately fire-and-forget, and deliberately called only AFTER the insert
 * has succeeded: the feedback is already durable by then, so a Resend outage,
 * a missing API key or a malformed address must never turn a stored submission
 * into a 500 for the person who sent it.
 */
export interface FeedbackAlertFields {
  id: number | string;
  feedbackType: string;
  severity: string;
  userType: string;
  address: string;
  section: string;
  text: string;
  contactEmail: string | null;
  cohort: string | null;
}

/**
 * Build the operator alert. Pure, so the wording is testable without sending.
 */
export function buildFeedbackAlert(fields: FeedbackAlertFields): {
  subject: string;
  text: string;
} {
  const cohortTag = fields.cohort ? ` [${fields.cohort}]` : '';
  const text = [
    `Type:     ${fields.feedbackType} (severity ${fields.severity})`,
    `From:     ${fields.userType}${
      fields.contactEmail ? ` <${fields.contactEmail}>` : ' (no contact address)'
    }`,
    fields.cohort ? `Cohort:   ${fields.cohort}` : null,
    `Address:  ${fields.address}`,
    `Section:  ${fields.section}`,
    '',
    fields.text,
    '',
    `Feedback id ${fields.id}.`,
  ]
    .filter((line) => line !== null)
    .join('\n');

  return {
    subject: `Feedback${cohortTag}: ${fields.feedbackType} - ${fields.address}`,
    text,
  };
}

/**
 * Tell the operator that feedback arrived. Never throws.
 *
 * Returns whether a send was DISPATCHED - not whether it was delivered, which
 * this cannot know: the send is deliberately not awaited, and the Workspace
 * self-domain quarantine fails after Resend has already reported success.
 *
 * The caller ignores the result. It exists so the outcome is inspectable and
 * testable rather than vanishing into a void return, and so each failure path
 * says which one it took instead of only writing to a log nobody reads.
 */
export function notifyOperator(fields: FeedbackAlertFields): boolean {
  if (!process.env.RESEND_API_KEY) return false;

  const { subject, text } = buildFeedbackAlert(fields);

  try {
    const resend = new Resend(process.env.RESEND_API_KEY);
    resend.emails
      .send({
        from: 'PlotDetect <info@plotdetect.com.au>',
        to: NOTIFY_EMAIL,
        subject,
        text,
      })
      .catch((err) => console.error('[feedback] resend error:', err));
    return true;
  } catch (err) {
    // Resend's constructor throws on a malformed key. Swallowed for the same
    // reason as the .catch above - the feedback row has already committed, so
    // a mail problem must never become a 500 for the person who sent it.
    console.error('[feedback] notify failed:', err);
    return false;
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const {
      feedbackType,
      feedbackText,
      email,
      userType,
      context,
    } = body;

    // Validate required fields
    if (!feedbackType || !feedbackText) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Map feedback type to database type
    const dbFeedbackType = feedbackTypeMap[feedbackType] || 'general';
    const severity = getSeverity(feedbackType);

    // Get client IP from headers
    const forwardedFor = request.headers.get('x-forwarded-for');
    const realIp = request.headers.get('x-real-ip');
    const clientIp = forwardedFor?.split(',')[0] || realIp || null;

    // Insert feedback into existing database schema
    const query = `
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
        created_at,
        resolved
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), false)
      RETURNING id;
    `;

    const values = [
      dbFeedbackType,
      context.propertyAddress || 'Not specified',
      context.provisionContext?.title || context.page || 'General',
      feedbackText,
      userType || 'other',
      severity,
      email || null,
      JSON.stringify({
        ...context,
        originalFeedbackType: feedbackType,
      }),
      context.browserInfo || null,
      clientIp,
    ];

    const result = await pool.query(query, values);

    console.log(`✅ Feedback submitted: ID ${result.rows[0].id}, Type: ${feedbackType}, User: ${userType}`);

    notifyOperator({
      id: result.rows[0].id,
      feedbackType,
      severity,
      userType: userType || 'other',
      address: context?.propertyAddress || 'Not specified',
      section: context?.provisionContext?.title || context?.page || 'General',
      text: feedbackText,
      contactEmail: email || null,
      cohort: context?.cohort || null,
    });

    return NextResponse.json(
      {
        success: true,
        feedbackId: result.rows[0].id,
        message: 'Feedback submitted successfully'
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('❌ Error saving feedback:', error);
    return NextResponse.json(
      { error: 'Failed to save feedback' },
      { status: 500 }
    );
  }
}

// GET endpoint to retrieve feedback (for admin dashboard)
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const type = searchParams.get('type');
    const status = searchParams.get('status');
    const limit = parseInt(searchParams.get('limit') || '100');

    let query = `
      SELECT
        id,
        type,
        property_address,
        section,
        description,
        user_type,
        severity,
        contact_email,
        created_at,
        resolved,
        resolution_notes,
        resolved_at
      FROM user_feedback
      WHERE 1=1
    `;

    const params: any[] = [];
    let paramIndex = 1;

    if (type && type !== 'all') {
      query += ` AND type = $${paramIndex}`;
      params.push(type);
      paramIndex++;
    }

    if (status === 'resolved') {
      query += ` AND resolved = true`;
    } else if (status === 'unresolved') {
      query += ` AND resolved = false`;
    }

    query += ` ORDER BY created_at DESC LIMIT $${paramIndex}`;
    params.push(limit);

    const result = await pool.query(query, params);

    return NextResponse.json(result.rows, { status: 200 });
  } catch (error) {
    console.error('❌ Error fetching feedback:', error);
    return NextResponse.json(
      { error: 'Failed to fetch feedback' },
      { status: 500 }
    );
  }
}

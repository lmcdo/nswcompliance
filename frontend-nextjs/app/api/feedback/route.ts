import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

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
    const { searchParams } = new URL(request.url);
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

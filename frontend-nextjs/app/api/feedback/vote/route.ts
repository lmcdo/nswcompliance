import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { z } from 'zod';
import { formatValidationErrors } from '@/lib/schemas';

// Validation schema for simple votes
const voteSchema = z.object({
  requirementId: z.string(),
  propertyAddress: z.string(),
  voteType: z.enum(['up', 'down']),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validatedVote = voteSchema.parse(body);

    // Record the vote (simple tracking without requiring full form)
    await query(`
      INSERT INTO requirement_votes (
        requirement_id,
        property_address,
        vote_type,
        user_agent,
        ip_address,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW())
      ON CONFLICT (requirement_id, property_address, ip_address)
      DO UPDATE SET
        vote_type = $3,
        created_at = NOW()
    `, [
      validatedVote.requirementId,
      validatedVote.propertyAddress,
      validatedVote.voteType,
      request.headers.get('user-agent') || null,
      request.headers.get('x-forwarded-for') || request.ip || null
    ]);

    // Update vote counts
    await updateVoteCounts(validatedVote.requirementId);

    return NextResponse.json({
      success: true,
      message: 'Vote recorded successfully'
    });

  } catch (error) {
    console.error('Vote submission error:', error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid vote data', details: formatValidationErrors(error) },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to record vote' },
      { status: 500 }
    );
  }
}

async function updateVoteCounts(requirementId: string) {
  try {
    // Update vote counts in requirements table
    const voteCounts = await query(`
      SELECT
        COUNT(CASE WHEN vote_type = 'up' THEN 1 END) as up_votes,
        COUNT(CASE WHEN vote_type = 'down' THEN 1 END) as down_votes
      FROM requirement_votes
      WHERE requirement_id = $1
        AND created_at > NOW() - INTERVAL '30 days'
    `, [requirementId]);

    const { up_votes, down_votes } = voteCounts.rows[0];

    // Update the requirements table with vote counts
    await query(`
      UPDATE dcp_general_requirements
      SET
        up_votes = $1,
        down_votes = $2,
        vote_score = CASE
          WHEN ($1 + $2) = 0 THEN 0
          ELSE ROUND(($1::float / ($1 + $2)) * 100, 1)
        END,
        last_vote_updated = NOW()
      WHERE id = $3
    `, [up_votes, down_votes, requirementId]);

  } catch (error) {
    console.error('Failed to update vote counts:', error);
  }
}
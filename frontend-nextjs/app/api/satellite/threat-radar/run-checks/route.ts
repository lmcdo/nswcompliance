import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { Resend } from 'resend';

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

const getSupabase = () =>
  createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

/**
 * GET /api/satellite/threat-radar/run-checks
 *
 * Called by Vercel Cron (Monday 21:00 UTC = Tuesday 7:00 AEST).
 * For each active subscription: calls the Python check endpoint,
 * and if new DAs/CDCs are found within 200m, sends a Resend alert email.
 *
 * Protected by CRON_SECRET env var — Vercel passes this automatically
 * via the Authorization header when invoked as a cron job.
 */
export async function GET(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const supabase = getSupabase();
  const { data: subscriptions, error } = await supabase
    .from('threat_radar_subscriptions')
    .select('id, address, email')
    .eq('active', true);

  if (error) {
    console.error('[threat-radar/run-checks] fetch subscriptions error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  if (!subscriptions?.length) {
    return NextResponse.json({ checked: 0, alerted: 0 });
  }

  const resend = new Resend(process.env.RESEND_API_KEY);
  let alerted = 0;
  const errors: string[] = [];

  for (const sub of subscriptions) {
    try {
      const checkResp = await fetch(`${PYTHON_API}/pipeline/threat-radar/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscription_id: sub.id }),
        signal: AbortSignal.timeout(25_000),
      });

      if (!checkResp.ok) {
        const text = await checkResp.text().catch(() => '');
        errors.push(`sub ${sub.id}: check failed (${checkResp.status}) ${text}`);
        continue;
      }

      const result = await checkResp.json();
      if (!result.new_application_count || result.new_application_count === 0) continue;

      const emailResult = await resend.emails.send({
        from: 'PlotDetect Threat Radar <alerts@plotdetect.com.au>',
        to: sub.email,
        subject: `${result.new_application_count} new development application${result.new_application_count > 1 ? 's' : ''} near ${sub.address}`,
        html: buildAlertEmail(sub.address, result.new_applications),
      });

      if (emailResult.error) {
        errors.push(`sub ${sub.id}: resend error: ${emailResult.error.message}`);
      } else {
        alerted++;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      errors.push(`sub ${sub.id}: ${msg}`);
    }
  }

  if (errors.length) {
    console.error('[threat-radar/run-checks] errors:', errors);
  }

  return NextResponse.json({
    checked: subscriptions.length,
    alerted,
    errors: errors.length ? errors : undefined,
  });
}

interface Application {
  PlanningPortalApplicationNumber?: string;
  ApplicationNumber?: string;
  ApplicationType?: string;
  DevelopmentType?: string;
  ApplicationDescription?: string;
  LodgementDate?: string;
  Status?: string;
  _distance_m?: number;
}

function buildAlertEmail(address: string, apps: Application[]): string {
  const rows = apps
    .map((app) => {
      const appNum =
        app.PlanningPortalApplicationNumber || app.ApplicationNumber || 'N/A';
      const type = app.ApplicationType || app.DevelopmentType || 'DA';
      const description = app.ApplicationDescription || '—';
      const lodged = app.LodgementDate
        ? new Date(app.LodgementDate).toLocaleDateString('en-AU')
        : '—';
      const status = app.Status || '—';
      const distance = app._distance_m != null ? `${app._distance_m}m away` : '';

      return `
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#111827;">
            <strong>${appNum}</strong><br>
            <span style="color:#6b7280;font-size:12px;">${type}${distance ? ' · ' + distance : ''}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#374151;">${description}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#374151;">${lodged}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#374151;">${status}</td>
        </tr>`;
    })
    .join('');

  return `
    <!DOCTYPE html>
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9fafb;margin:0;padding:24px;">
      <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;padding:32px;border:1px solid #e5e7eb;">
        <p style="margin:0 0 4px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Threat Radar Alert</p>
        <h1 style="margin:0 0 8px;font-size:20px;color:#111827;">
          ${apps.length} new development application${apps.length > 1 ? 's' : ''} near your property
        </h1>
        <p style="margin:0 0 24px;font-size:14px;color:#4b5563;">
          The following applications were lodged within <strong>200 metres</strong> of
          <strong>${address}</strong> in the past week.
        </p>

        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#f3f4f6;">
              <th style="padding:8px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Application</th>
              <th style="padding:8px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Description</th>
              <th style="padding:8px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Lodged</th>
              <th style="padding:8px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">Status</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>

        <p style="margin:24px 0 0;font-size:12px;color:#9ca3af;">
          Data sourced from NSW ePlanning Portal. Checks run weekly on Mondays.<br>
          You subscribed to Threat Radar alerts for this address via
          <a href="https://verify.plotdetect.com.au/reports/threat-radar" style="color:#0d9488;">PlotDetect</a>.
        </p>
      </div>
    </body>
    </html>`;
}

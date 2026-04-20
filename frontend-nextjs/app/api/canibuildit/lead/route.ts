import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(req: NextRequest) {
  const { email, address, eligible, lga_name, interest_type } = await req.json();
  if (!email?.trim()) {
    return NextResponse.json({ error: 'email required' }, { status: 400 });
  }

  try {
    const supabase = await createClient();
    await supabase.from('canibuildit_leads').insert({
      email: email.trim().toLowerCase(),
      address: address?.trim() || null,
      eligible: eligible ?? null,
      // lga_name + interest_type columns: add via Supabase dashboard if not present
      // ALTER TABLE canibuildit_leads ADD COLUMN IF NOT EXISTS lga_name text;
      // ALTER TABLE canibuildit_leads ADD COLUMN IF NOT EXISTS interest_type text;
      ...(lga_name ? { lga_name: lga_name.trim() } : {}),
      ...(interest_type ? { interest_type: interest_type.trim() } : {}),
    });
  } catch {
    // Non-blocking — table may not exist or columns may need adding; don't error the user
  }

  return NextResponse.json({ ok: true });
}

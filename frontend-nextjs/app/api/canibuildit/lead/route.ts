import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(req: NextRequest) {
  const { email, address, eligible } = await req.json();
  if (!email?.trim() || !address?.trim()) {
    return NextResponse.json({ error: 'email and address required' }, { status: 400 });
  }

  try {
    const supabase = await createClient();
    await supabase.from('canibuildit_leads').insert({
      email: email.trim().toLowerCase(),
      address: address.trim(),
      eligible: eligible ?? null,
    });
  } catch {
    // Non-blocking — table may not exist yet; don't error the user
  }

  return NextResponse.json({ ok: true });
}

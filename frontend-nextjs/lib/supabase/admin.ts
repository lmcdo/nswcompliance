/**
 * Supabase admin client (service role key).
 * Use for server-side operations that bypass RLS — e.g. fetching paid reports.
 * NEVER import this on the client side.
 */

import { createClient } from '@supabase/supabase-js';

export function getAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );
}

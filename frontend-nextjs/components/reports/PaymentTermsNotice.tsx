import Link from 'next/link';
import { TERMS_PATH } from '@/lib/disclaimers';

/**
 * Compact ToS acceptance line shown near every checkout button.
 * Import and render below any "Buy / Unlock / Subscribe" CTA.
 */
export function PaymentTermsNotice() {
  return (
    <p className="text-[11px] text-gray-400 text-center mt-2">
      By purchasing you agree to our{' '}
      <Link href={TERMS_PATH} target="_blank" className="underline hover:text-gray-500">
        Terms of Service
      </Link>
      . Reports are indicative only.
    </p>
  );
}

// Fix negative page numbers in regulatory_provisions
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

// Load .env.local
dotenv.config({ path: '.env.local' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase credentials');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function fixNegativePageNumbers() {
  console.log('=== Fix Negative Page Numbers ===\n');

  // 1. Check current state
  console.log('Step 1: Checking for provisions with negative page numbers...');
  const { data: negativePages, error: checkError } = await supabase
    .from('regulatory_provisions')
    .select('id, pdf_page, pdf_printed_page, provision_text')
    .or('pdf_page.lt.0,pdf_printed_page.lt.0')
    .order('id');

  if (checkError) {
    console.error('Error checking data:', checkError);
    process.exit(1);
  }

  console.log(`Found ${negativePages.length} provisions with negative page numbers:\n`);
  negativePages.forEach(p => {
    console.log(`  ID ${p.id}: pdf_page=${p.pdf_page}, pdf_printed_page=${p.pdf_printed_page}`);
    console.log(`    Preview: ${p.provision_text.substring(0, 80)}...`);
  });

  if (negativePages.length === 0) {
    console.log('\n✓ No negative page numbers found. Database is clean.');
    return;
  }

  // 2. Create backup (export current state)
  console.log('\nStep 2: Creating backup of affected provisions...');
  const backup = {
    timestamp: new Date().toISOString(),
    provisions: negativePages
  };

  const fs = await import('fs');
  const backupFile = `backup-negative-pages-${Date.now()}.json`;
  fs.writeFileSync(backupFile, JSON.stringify(backup, null, 2));
  console.log(`✓ Backup saved to: ${backupFile}`);

  // 3. Fix strategy
  console.log('\nStep 3: Applying fixes...');

  const fixes = [];
  for (const provision of negativePages) {
    let newPdfPage = provision.pdf_page;
    let newPdfPrintedPage = provision.pdf_printed_page;

    // Fix pdf_page if negative
    if (provision.pdf_page < 0) {
      newPdfPage = provision.pdf_printed_page > 0 ? provision.pdf_printed_page : 1;
    }

    // Fix pdf_printed_page if negative
    if (provision.pdf_printed_page < 0) {
      newPdfPrintedPage = provision.pdf_page > 0 ? provision.pdf_page : 1;
    }

    fixes.push({
      id: provision.id,
      oldPdfPage: provision.pdf_page,
      oldPdfPrintedPage: provision.pdf_printed_page,
      newPdfPage,
      newPdfPrintedPage
    });
  }

  console.log('\nPlanned fixes:');
  fixes.forEach(f => {
    console.log(`  ID ${f.id}:`);
    console.log(`    pdf_page: ${f.oldPdfPage} → ${f.newPdfPage}`);
    console.log(`    pdf_printed_page: ${f.oldPdfPrintedPage} → ${f.newPdfPrintedPage}`);
  });

  // 4. Apply updates
  console.log('\nStep 4: Updating database...');
  let successCount = 0;
  let errorCount = 0;

  for (const fix of fixes) {
    const { error } = await supabase
      .from('regulatory_provisions')
      .update({
        pdf_page: fix.newPdfPage,
        pdf_printed_page: fix.newPdfPrintedPage
      })
      .eq('id', fix.id);

    if (error) {
      console.error(`  ✗ Failed to update ID ${fix.id}:`, error.message);
      errorCount++;
    } else {
      console.log(`  ✓ Updated ID ${fix.id}`);
      successCount++;
    }
  }

  // 5. Verify
  console.log('\nStep 5: Verifying fixes...');
  const { data: remainingNegative, error: verifyError } = await supabase
    .from('regulatory_provisions')
    .select('id, pdf_page, pdf_printed_page')
    .or('pdf_page.lt.0,pdf_printed_page.lt.0');

  if (verifyError) {
    console.error('Error verifying:', verifyError);
  } else {
    console.log(`Remaining provisions with negative page numbers: ${remainingNegative.length}`);
    if (remainingNegative.length > 0) {
      console.log('Still negative:', remainingNegative);
    }
  }

  // Summary
  console.log('\n=== Summary ===');
  console.log(`Total provisions fixed: ${successCount}`);
  console.log(`Errors: ${errorCount}`);
  console.log(`Backup file: ${backupFile}`);
  console.log('\n✓ Database cleanup complete!');
}

fixNegativePageNumbers().catch(console.error);

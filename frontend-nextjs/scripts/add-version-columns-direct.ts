#!/usr/bin/env tsx
import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function addColumns() {
  try {
    console.log('Adding version tracking columns one by one...\n');

    const columns = [
      { name: 'consolidated_as_of_date', sql: 'ADD COLUMN IF NOT EXISTS consolidated_as_of_date DATE' },
      { name: 'consolidation_url', sql: 'ADD COLUMN IF NOT EXISTS consolidation_url TEXT' },
      { name: 'amending_epis', sql: 'ADD COLUMN IF NOT EXISTS amending_epis TEXT[]' },
      { name: 'major_amendments', sql: "ADD COLUMN IF NOT EXISTS major_amendments JSONB DEFAULT '[]'::jsonb" },
      { name: 'next_check_date', sql: 'ADD COLUMN IF NOT EXISTS next_check_date DATE' },
      { name: 'is_superseded', sql: 'ADD COLUMN IF NOT EXISTS is_superseded BOOLEAN DEFAULT false' }
    ];

    for (const col of columns) {
      try {
        await pool.query(`ALTER TABLE documents ${col.sql}`);
        console.log(`✅ ${col.name}`);
      } catch (e: any) {
        if (e.code === '42701') {
          console.log(`⚠️  ${col.name} - already exists`);
        } else {
          console.log(`❌ ${col.name} - ${e.message}`);
        }
      }
    }

    console.log('\nVerifying columns exist...');
    const result = await pool.query(`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_name = 'documents'
        AND column_name IN ('consolidated_as_of_date', 'consolidation_url', 'amending_epis',
                            'major_amendments', 'next_check_date', 'is_superseded')
      ORDER BY column_name;
    `);

    console.log(`\nFound ${result.rows.length}/6 columns:`);
    result.rows.forEach((row: any) => {
      console.log(`  - ${row.column_name}`);
    });

    if (result.rows.length === 6) {
      console.log('\n✅ All version tracking columns exist!');
    } else {
      console.log(`\n⚠️  Only ${result.rows.length}/6 columns exist`);
    }

  } catch (error: any) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

addColumns();

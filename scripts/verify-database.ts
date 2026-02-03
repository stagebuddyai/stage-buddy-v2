#!/usr/bin/env tsx
/**
 * Verify Supabase database setup and RLS policies
 *
 * This script checks:
 * 1. Database connectivity
 * 2. Tables exist (performances, analysis_results)
 * 3. RLS policies are configured
 * 4. Storage bucket exists
 *
 * Usage:
 *   NEXT_PUBLIC_SUPABASE_URL=... NEXT_PUBLIC_SUPABASE_ANON_KEY=... tsx scripts/verify-database.ts
 */

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('❌ Error: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables are required');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function verifyDatabase() {
  console.log('🔍 Verifying Supabase Database Setup\n');
  console.log('URL:', SUPABASE_URL);
  console.log('');

  let allChecks = true;

  // Check 1: Test connection
  console.log('1️⃣  Testing database connection...');
  try {
    const { error } = await supabase.from('performances').select('count').limit(0);
    if (error && error.code !== 'PGRST116') { // PGRST116 = no rows, which is OK
      console.error('   ❌ Connection failed:', error.message);
      allChecks = false;
    } else {
      console.log('   ✅ Database connection successful');
    }
  } catch (err) {
    console.error('   ❌ Exception:', err);
    allChecks = false;
  }

  // Check 2: Verify performances table
  console.log('\n2️⃣  Checking performances table...');
  try {
    const { data, error } = await supabase
      .from('performances')
      .select('id')
      .limit(1);

    if (error) {
      console.error('   ❌ Table query failed:', error.message);
      console.error('   Hint: Make sure migrations have been applied');
      allChecks = false;
    } else {
      console.log('   ✅ performances table exists');
      console.log(`   ℹ️  Current record count: ${data?.length || 0}`);
    }
  } catch (err) {
    console.error('   ❌ Exception:', err);
    allChecks = false;
  }

  // Check 3: Verify analysis_results table
  console.log('\n3️⃣  Checking analysis_results table...');
  try {
    const { data, error } = await supabase
      .from('analysis_results')
      .select('id')
      .limit(1);

    if (error) {
      console.error('   ❌ Table query failed:', error.message);
      console.error('   Hint: Make sure migrations have been applied');
      allChecks = false;
    } else {
      console.log('   ✅ analysis_results table exists');
      console.log(`   ℹ️  Current record count: ${data?.length || 0}`);
    }
  } catch (err) {
    console.error('   ❌ Exception:', err);
    allChecks = false;
  }

  // Check 4: Verify storage bucket
  console.log('\n4️⃣  Checking sb-uploads storage bucket...');
  try {
    const { data, error } = await supabase.storage.listBuckets();

    if (error) {
      console.error('   ❌ Failed to list buckets:', error.message);
      allChecks = false;
    } else {
      const bucket = data?.find(b => b.id === 'sb-uploads');
      if (bucket) {
        console.log('   ✅ sb-uploads bucket exists');
        console.log('   ℹ️  Bucket details:', {
          public: bucket.public,
          file_size_limit: bucket.file_size_limit || 'none',
          allowed_mime_types: bucket.allowed_mime_types || 'any',
        });
      } else {
        console.error('   ❌ sb-uploads bucket not found');
        console.log('   ℹ️  Available buckets:', data?.map(b => b.id).join(', '));
        allChecks = false;
      }
    }
  } catch (err) {
    console.error('   ❌ Exception:', err);
    allChecks = false;
  }

  // Check 5: Test RLS policies (without actual user)
  console.log('\n5️⃣  Checking RLS policies...');
  console.log('   ⚠️  Note: Cannot fully test RLS without authenticated user');
  console.log('   ℹ️  Attempting unauthenticated insert (should fail with RLS error)...');
  try {
    const { error } = await supabase
      .from('performances')
      .insert({
        id: 'test-id',
        user_id: 'test-user-id',
        status: 'uploaded',
        video_path: 'test.mp4',
      });

    if (error) {
      if (error.code === '42501' || error.message.includes('row-level security') || error.message.includes('denied')) {
        console.log('   ✅ RLS is enabled (insert correctly rejected)');
      } else {
        console.error('   ❌ Unexpected error:', error.message);
        console.error('   Code:', error.code);
        allChecks = false;
      }
    } else {
      console.error('   ❌ RLS may not be enabled (insert should have been rejected)');
      allChecks = false;
    }
  } catch (err) {
    console.error('   ❌ Exception:', err);
    allChecks = false;
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  if (allChecks) {
    console.log('✅ All checks passed! Database is properly configured.');
  } else {
    console.log('❌ Some checks failed. Review the errors above.');
    console.log('\nTroubleshooting steps:');
    console.log('1. Ensure Supabase project is running');
    console.log('2. Apply migrations: supabase db push (or via Supabase dashboard)');
    console.log('3. Verify RLS policies are enabled on both tables');
    console.log('4. Check that sb-uploads bucket exists in Storage');
  }
  console.log('='.repeat(60));

  return allChecks ? 0 : 1;
}

// Run verification
verifyDatabase()
  .then((exitCode) => {
    process.exit(exitCode);
  })
  .catch((err) => {
    console.error('\n💥 Verification script failed:', err);
    process.exit(1);
  });

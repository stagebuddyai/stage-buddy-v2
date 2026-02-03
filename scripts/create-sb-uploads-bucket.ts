#!/usr/bin/env tsx
/**
 * Create the sb-uploads storage bucket in Supabase
 *
 * This script creates the bucket and sets up RLS policies
 * Run this before using the video upload feature.
 *
 * Usage:
 *   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... tsx scripts/create-sb-uploads-bucket.ts
 */

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required');
  console.error('\nUsage:');
  console.error('  SUPABASE_URL=https://xxx.supabase.co \\');
  console.error('  SUPABASE_SERVICE_ROLE_KEY=xxx \\');
  console.error('  tsx scripts/create-sb-uploads-bucket.ts');
  process.exit(1);
}

// Create admin client (service role bypasses RLS)
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

async function createBucket() {
  console.log('🚀 Creating sb-uploads storage bucket...\n');
  console.log('URL:', SUPABASE_URL);
  console.log('');

  // Check if bucket already exists
  console.log('1️⃣  Checking if bucket exists...');
  const { data: buckets } = await supabase.storage.listBuckets();
  const existingBucket = buckets?.find(b => b.id === 'sb-uploads');

  if (existingBucket) {
    console.log('   ℹ️  Bucket "sb-uploads" already exists');
    console.log('   ✅ Nothing to do!\n');
    return;
  }

  // Create the bucket
  console.log('2️⃣  Creating bucket "sb-uploads"...');
  const { data: newBucket, error: createError } = await supabase.storage.createBucket('sb-uploads', {
    public: false,
    fileSizeLimit: 500 * 1024 * 1024, // 500MB
    allowedMimeTypes: [
      'video/mp4',
      'video/webm',
      'video/quicktime',
      'video/x-msvideo',
      'video/x-matroska',
    ],
  });

  if (createError) {
    console.error('   ❌ Failed to create bucket:', createError.message);
    process.exit(1);
  }

  console.log('   ✅ Bucket created successfully');
  console.log('   ℹ️  Bucket ID:', newBucket?.id || 'sb-uploads');
  console.log('   ℹ️  File size limit: 500MB');
  console.log('   ℹ️  Allowed types: video/*');

  // Note about RLS policies
  console.log('\n3️⃣  Setting up RLS policies...');
  console.log('   ℹ️  Note: RLS policies for storage.objects must be set via SQL');
  console.log('   ℹ️  Migration 003_create_storage_bucket.sql contains the policies');
  console.log('   ℹ️  Apply it via: supabase db push or SQL Editor');

  console.log('\n' + '='.repeat(60));
  console.log('✅ Bucket setup complete!');
  console.log('');
  console.log('Next steps:');
  console.log('1. Apply migration 003 to set up RLS policies');
  console.log('2. Run: tsx scripts/verify-database.ts');
  console.log('3. Try uploading a video');
  console.log('='.repeat(60));
}

createBucket()
  .then(() => {
    console.log('\n✨ Done!');
    process.exit(0);
  })
  .catch((err) => {
    console.error('\n💥 Script failed:', err);
    process.exit(1);
  });

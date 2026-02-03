#!/usr/bin/env tsx
/**
 * Debug storage bucket visibility
 *
 * This script uses both anon key and service role key to check bucket visibility
 */

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL) {
  console.error('❌ SUPABASE_URL is required');
  process.exit(1);
}

async function debugBuckets() {
  console.log('🔍 Debugging Storage Bucket Visibility\n');
  console.log('URL:', SUPABASE_URL);
  console.log('');

  // Test 1: Check with anon key
  if (SUPABASE_ANON_KEY) {
    console.log('1️⃣  Checking with ANON key...');
    const anonClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    const { data: anonBuckets, error: anonError } = await anonClient.storage.listBuckets();

    if (anonError) {
      console.error('   ❌ Error:', anonError.message);
    } else {
      console.log('   ✅ Success');
      console.log('   📦 Buckets visible to anon key:', anonBuckets?.map(b => b.id).join(', ') || 'none');

      const sbUploadsBucket = anonBuckets?.find(b => b.id === 'sb-uploads');
      if (sbUploadsBucket) {
        console.log('   ✅ sb-uploads bucket IS visible to anon key');
      } else {
        console.log('   ⚠️  sb-uploads bucket NOT visible to anon key');
      }
    }
  } else {
    console.log('1️⃣  ANON key not provided, skipping...');
  }

  console.log('');

  // Test 2: Check with service role key
  if (SUPABASE_SERVICE_ROLE_KEY) {
    console.log('2️⃣  Checking with SERVICE ROLE key...');
    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
    const { data: adminBuckets, error: adminError } = await adminClient.storage.listBuckets();

    if (adminError) {
      console.error('   ❌ Error:', adminError.message);
    } else {
      console.log('   ✅ Success');
      console.log('   📦 All buckets in project:');
      adminBuckets?.forEach(bucket => {
        console.log(`      - ${bucket.id} (public: ${bucket.public}, created: ${bucket.created_at})`);
      });

      const sbUploadsBucket = adminBuckets?.find(b => b.id === 'sb-uploads');
      if (sbUploadsBucket) {
        console.log('   ✅ sb-uploads bucket EXISTS in project');
        console.log('   📋 Details:', {
          public: sbUploadsBucket.public,
          file_size_limit: sbUploadsBucket.file_size_limit,
          allowed_mime_types: sbUploadsBucket.allowed_mime_types,
        });
      } else {
        console.log('   ❌ sb-uploads bucket DOES NOT EXIST');
      }
    }
  } else {
    console.log('2️⃣  SERVICE ROLE key not provided, skipping...');
  }

  console.log('');

  // Test 3: Try to create bucket if service role key available
  if (SUPABASE_SERVICE_ROLE_KEY) {
    console.log('3️⃣  Attempting to create sb-uploads bucket...');
    const adminClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

    const { data, error } = await adminClient.storage.createBucket('sb-uploads', {
      public: false,
      fileSizeLimit: 500 * 1024 * 1024,
      allowedMimeTypes: ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska'],
    });

    if (error) {
      if (error.message.includes('already exists')) {
        console.log('   ℹ️  Bucket already exists (this is good!)');
      } else {
        console.error('   ❌ Error:', error.message);
      }
    } else {
      console.log('   ✅ Bucket created successfully!');
      console.log('   📋 New bucket:', data);
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('💡 Diagnosis:');
  console.log('');
  console.log('If sb-uploads is visible to SERVICE ROLE but NOT ANON:');
  console.log('  → This is NORMAL and EXPECTED behavior');
  console.log('  → Storage buckets are not publicly listable');
  console.log('  → Your application can still use the bucket');
  console.log('');
  console.log('If sb-uploads does NOT exist at all:');
  console.log('  → Create it via Supabase Dashboard > Storage > New Bucket');
  console.log('  → Name: sb-uploads');
  console.log('  → Public: NO');
  console.log('  → File size limit: 500MB');
  console.log('='.repeat(60));
}

debugBuckets()
  .then(() => process.exit(0))
  .catch(err => {
    console.error('Error:', err);
    process.exit(1);
  });

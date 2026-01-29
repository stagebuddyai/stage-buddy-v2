#!/usr/bin/env tsx
/**
 * Script to create the Supabase Storage bucket and policies
 * Run with: npx tsx scripts/create-bucket.ts
 */

import { createClient } from '@supabase/supabase-js';

// Load environment variables
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('❌ Missing Supabase environment variables');
  console.error('Make sure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function createStorageBucket() {
  console.log('🚀 Setting up Supabase Storage for Stage Buddy...\n');

  // Check if bucket already exists
  console.log('📦 Checking if "performances" bucket exists...');
  const { data: buckets, error: listError } = await supabase.storage.listBuckets();
  
  if (listError) {
    console.error('❌ Error listing buckets:', listError.message);
    process.exit(1);
  }

  const bucketExists = buckets?.some(b => b.id === 'performances');

  if (bucketExists) {
    console.log('✅ Bucket "performances" already exists');
  } else {
    console.log('📦 Creating "performances" bucket...');
    const { data: bucket, error: createError } = await supabase.storage.createBucket('performances', {
      public: false,
      fileSizeLimit: 524288000, // 500MB
      allowedMimeTypes: ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska'],
    });

    if (createError) {
      console.error('❌ Error creating bucket:', createError.message);
      console.log('\n💡 You may need to create it manually in the Supabase dashboard.');
      console.log('   See SUPABASE_SETUP.md for instructions.');
      process.exit(1);
    }

    console.log('✅ Bucket "performances" created successfully');
  }

  console.log('\n📋 Note: Storage policies need to be set up in the Supabase SQL Editor');
  console.log('   Run the SQL from scripts/setup-supabase-storage.sql');
  console.log('   Or see SUPABASE_SETUP.md for complete instructions\n');
  
  console.log('✨ Setup complete! You can now upload videos.\n');
}

createStorageBucket().catch(error => {
  console.error('❌ Unexpected error:', error);
  process.exit(1);
});

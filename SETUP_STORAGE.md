# Storage Bucket Setup Guide

## Problem
The verification script found that the `sb-uploads` storage bucket doesn't exist, causing video uploads to fail with:
```
Failed to initialize analysis in database
```

## Solution Options

Choose **ONE** of the following methods:

---

## Option 1: Supabase Dashboard (Easiest) ✅ RECOMMENDED

1. Go to your Supabase project dashboard
2. Navigate to **Storage** in the left sidebar
3. Click **"New bucket"** button
4. Configure the bucket:
   - **Name**: `sb-uploads`
   - **Public**: ❌ Unchecked (private)
   - **File size limit**: `500 MB` (or 524288000 bytes)
   - **Allowed MIME types**:
     - `video/mp4`
     - `video/webm`
     - `video/quicktime`
     - `video/x-msvideo`
     - `video/x-matroska`
5. Click **"Create bucket"**
6. Go to **SQL Editor** and run the RLS policies from `supabase/migrations/003_create_storage_bucket.sql`:

```sql
-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can upload to own folder" ON storage.objects;
DROP POLICY IF EXISTS "Users can view own files" ON storage.objects;
DROP POLICY IF EXISTS "Users can update own files" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own files" ON storage.objects;

-- Create policies for sb-uploads bucket
CREATE POLICY "Users can upload to own folder"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'sb-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can view own files"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'sb-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can update own files"
ON storage.objects FOR UPDATE
USING (
  bucket_id = 'sb-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'sb-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

7. Verify by running: `tsx scripts/verify-database.ts`

---

## Option 2: Automated Script (Requires Service Role Key)

If you have your Supabase service role key:

```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# Run the setup script
tsx scripts/create-sb-uploads-bucket.ts

# Then apply the RLS policies via SQL Editor (see Option 1, step 6)
```

---

## Option 3: Apply Migration via Supabase CLI

If you have Supabase CLI set up:

```bash
# Link to your project (if not already linked)
supabase link --project-ref your-project-ref

# Push migrations
supabase db push

# This will apply migration 003 which creates the bucket and policies
```

---

## Verification

After setup, verify everything is working:

```bash
# Run verification script
tsx scripts/verify-database.ts
```

Expected output:
```
✅ Database connection successful
✅ performances table exists
✅ analysis_results table exists
✅ sb-uploads bucket exists
✅ RLS is enabled
```

---

## Troubleshooting

### "Bucket already exists" error
If you get this error, the bucket exists but might be missing RLS policies. Go to SQL Editor and run the policy creation SQL from Option 1, step 6.

### "Permission denied" errors during upload
RLS policies are not set correctly. Re-run the policy creation SQL from Option 1, step 6.

### Server logs show "No authenticated user"
This is a different issue - check that user authentication is working correctly.

---

## What This Fixes

Once the bucket is created:
1. ✅ Video uploads will work
2. ✅ Database inserts will happen (performance records)
3. ✅ Analysis will run
4. ✅ Results will be saved to database
5. ✅ Empty tables will start filling up with data

The verification script showed that your database tables are set up correctly - they're just empty because uploads haven't been working!

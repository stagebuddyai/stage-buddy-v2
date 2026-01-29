# Supabase Setup for Stage Buddy V2

## Issue: "Bucket not found" Error

The app is trying to upload videos to a Supabase Storage bucket called `performances`, but the bucket doesn't exist yet.

## Solution: Create the Storage Bucket

### Option 1: Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard: https://supabase.com/dashboard
2. Navigate to **Storage** in the left sidebar
3. Click **New Bucket**
4. Enter these settings:
   - **Name**: `performances`
   - **Public**: Disabled (unchecked) - keep it private
5. Click **Create Bucket**

6. Now configure the bucket policies:
   - Click on the `performances` bucket
   - Go to **Policies** tab
   - Click **New Policy**
   - Use the following policies (or run the SQL in Option 2):

### Option 2: Using SQL Editor (Alternative)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Create a new query
4. Copy and paste the contents of `scripts/setup-supabase-storage.sql`
5. Click **Run**

This will:
- Create the `performances` bucket
- Set up Row Level Security (RLS) policies so users can only access their own files

## Verifying the Setup

After creating the bucket, you should be able to:
1. Sign in to the app
2. Upload a video file
3. The file should upload successfully to Supabase Storage

## Storage Structure

Videos are organized by user ID and analysis ID:
```
performances/
  └── {user_id}/
      └── {analysis_id}/
          └── video.{ext}
```

This structure ensures:
- Each user can only access their own files
- Analysis results are associated with specific uploads
- No conflicts between different users' uploads

## Troubleshooting

### Still getting "Bucket not found"?

1. **Check bucket name**: Make sure it's exactly `performances` (lowercase, plural)
2. **Verify policies**: Make sure RLS policies are created
3. **Check authentication**: Make sure you're signed in (the app requires authentication)
4. **Browser console**: Check for more detailed error messages in the browser console

### Need to reset?

If you need to start fresh:
```sql
-- Delete all objects in the bucket
DELETE FROM storage.objects WHERE bucket_id = 'performances';

-- Delete the bucket
DELETE FROM storage.buckets WHERE id = 'performances';

-- Then re-run the setup script
```

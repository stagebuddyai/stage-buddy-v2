# Manual Storage Bucket Setup (Step-by-Step)

## The Issue
The SQL migration shows "Success" but the bucket still isn't working. This happens because:
1. SQL `INSERT INTO storage.buckets` may have permission issues
2. The bucket might exist but not be visible to verification scripts
3. Bucket creation via SQL is less reliable than using the UI

## ✅ Solution: Create Bucket via Supabase Dashboard

### Step 1: Open Supabase Dashboard
1. Go to https://supabase.com/dashboard
2. Select your project: **stagebuddyapp**
3. Click **Storage** in the left sidebar

### Step 2: Check if Bucket Already Exists
Look in the buckets list for `sb-uploads`

**If it exists:**
- ✅ Great! Skip to Step 4 (RLS Policies)

**If it doesn't exist:**
- Continue to Step 3

### Step 3: Create the Bucket (if needed)
1. Click the **"New bucket"** button
2. Fill in the form:
   ```
   Name: sb-uploads
   Public bucket: ❌ UNCHECK THIS (must be private)
   ```
3. Click **"Create bucket"**
4. You should see `sb-uploads` appear in the list

### Step 4: Configure RLS Policies
1. Click **SQL Editor** in the left sidebar (or use the existing editor you have open)
2. Click **"New query"**
3. Paste this SQL (ONLY the policies part):

```sql
-- Drop existing policies (cleanup)
DROP POLICY IF EXISTS "Users can upload to own folder" ON storage.objects;
DROP POLICY IF EXISTS "Users can view own files" ON storage.objects;
DROP POLICY IF EXISTS "Users can update own files" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own files" ON storage.objects;

-- Create RLS policies for sb-uploads bucket
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

4. Click **"Run"** (or press Cmd/Ctrl + Enter)
5. Should see: "Success"

### Step 5: Verify Bucket Configuration
1. Go back to **Storage** in the left sidebar
2. Click on the `sb-uploads` bucket
3. Verify settings:
   - **Public**: Should be `false` (Private)
   - You should see the policies tab showing 4 policies

### Step 6: Test Upload
1. Open your application
2. Try uploading a video
3. Check server logs for detailed output
4. Check **Storage** > `sb-uploads` - you should see the uploaded file

---

## Debug Commands (Optional)

If you want to verify everything programmatically:

```bash
# Option 1: Debug script (needs service role key)
SUPABASE_URL=https://xxx.supabase.co \
SUPABASE_SERVICE_ROLE_KEY=xxx \
tsx scripts/debug-storage-bucket.ts

# Option 2: Just test upload
# Go to your app and upload a video, check the console for errors
```

---

## Expected Behavior After Setup

✅ **In Supabase Storage UI:**
- You see `sb-uploads` bucket
- Bucket is marked as **Private**
- When you upload via app, files appear here

✅ **In your app:**
- Video upload works without "Failed to initialize" error
- You get redirected to analysis page
- Server logs show database writes succeeding

✅ **In Table Editor:**
- `performances` table gets new records
- `analysis_results` table gets filled after analysis completes

---

## Troubleshooting

**"Bucket name already exists"**
→ The bucket exists, just apply the RLS policies (Step 4)

**Upload fails with "Permission denied"**
→ RLS policies not applied correctly, re-run Step 4

**Upload fails with "Bucket not found"**
→ Bucket wasn't created properly, verify Step 3

**Database still empty after upload**
→ Different issue - check server logs for database errors

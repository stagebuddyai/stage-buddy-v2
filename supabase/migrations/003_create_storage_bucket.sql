-- supabase/migrations/003_create_storage_bucket.sql
-- Note: Bucket name matches application code usage (sb-uploads)
INSERT INTO storage.buckets (id, name, public)
VALUES ('sb-uploads', 'sb-uploads', false);

-- Storage policies: Users can only access their own folders
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

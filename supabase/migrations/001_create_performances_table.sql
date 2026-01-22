-- supabase/migrations/001_create_performances_table.sql
CREATE TABLE IF NOT EXISTS performances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'uploaded',
  video_path TEXT,
  processing_started_at TIMESTAMPTZ,
  processing_completed_at TIMESTAMPTZ,
  processing_heartbeat TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT status_check CHECK (status IN ('uploaded', 'processing', 'complete', 'error'))
);

ALTER TABLE performances ENABLE ROW LEVEL SECURITY;

-- Users can only see their own performances
CREATE POLICY "Users can view own performances"
  ON performances FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own performances"
  ON performances FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own performances"
  ON performances FOR UPDATE
  USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX performances_user_id_idx ON performances(user_id);
CREATE INDEX performances_status_idx ON performances(status);
CREATE INDEX performances_created_at_idx ON performances(created_at DESC);

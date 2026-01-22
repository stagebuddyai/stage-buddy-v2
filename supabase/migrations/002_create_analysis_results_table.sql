-- supabase/migrations/002_create_analysis_results_table.sql
CREATE TABLE IF NOT EXISTS analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  performance_id UUID NOT NULL REFERENCES performances(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  analysis_output JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(performance_id)
);

ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;

-- Users can only see their own analysis results
CREATE POLICY "Users can view their own analysis results"
  ON analysis_results FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own analysis results"
  ON analysis_results FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own analysis results"
  ON analysis_results FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own analysis results"
  ON analysis_results FOR DELETE
  USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX analysis_results_performance_id_idx ON analysis_results(performance_id);
CREATE INDEX analysis_results_user_id_idx ON analysis_results(user_id);

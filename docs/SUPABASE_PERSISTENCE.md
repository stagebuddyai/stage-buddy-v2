# Supabase Persistence Architecture

## Overview

This document describes the Supabase database persistence layer for Stage Buddy V2 performance analysis.

**Status**: ✅ Migrated from filesystem to Supabase database (as of Feb 2026)

## Architecture

### Database Tables

#### 1. `performances` table
Stores metadata about each performance analysis:
- `id` (UUID) - Analysis identifier
- `user_id` (UUID) - Owner of the performance
- `status` - Current state: `uploaded`, `processing`, `complete`, `error`
- `video_path` - Path to video in Supabase Storage
- `processing_started_at` - When analysis began
- `processing_completed_at` - When analysis finished
- `processing_heartbeat` - Last activity timestamp
- `last_error` - Error message if status is `error`
- `created_at`, `updated_at` - Timestamps

#### 2. `analysis_results` table
Stores the complete analysis output:
- `id` (UUID) - Result record ID
- `performance_id` (UUID) - Foreign key to `performances`
- `user_id` (UUID) - Owner of the result
- `analysis_output` (JSONB) - Complete analysis report
- `created_at` - When result was created

**Note**: `performance_id` has a unique constraint - one result per performance.

#### 3. Storage Bucket: `sb-uploads`
Stores video files uploaded by users:
- Path format: `{user_id}/{analysis_id}/video.{ext}`
- RLS policies enforce user folder isolation

### Data Flow

#### Upload & Analysis Flow
```
1. User uploads video
   → VideoUploader.tsx uploads to Supabase Storage (sb-uploads bucket)
   → Generates analysis_id and storage_path

2. Start analysis
   → POST /api/analysis/run
   → Creates record in performances table (status: uploaded)
   → Downloads video to temporary local file
   → Spawns Python analysis subprocess
   → Updates performances table (status: processing)

3. Analysis completion
   → Python writes result to temporary file
   → Monitor reads temp file and writes to analysis_results table
   → Updates performances table (status: complete)
   → Cleans up temporary files
```

#### Results Display Flow
```
1. User views results page
   → AnalysisView component fetches from /api/analysis/results/{id}
   → API reads from analysis_results table (JSONB column)
   → Returns complete PerformanceReport
```

#### Status Polling Flow
```
1. Frontend polls for status
   → GET /api/analysis/status/{id}
   → API reads from performances table
   → Returns current status, timestamps, and errors
```

### Key Files

**Storage Layer**
- `lib/analysis/storage.ts` - Database operations (create, read, update)

**API Routes**
- `app/api/analysis/run/route.ts` - Start analysis, create DB records
- `app/api/analysis/results/[id]/route.ts` - Read results from DB
- `app/api/analysis/status/[id]/route.ts` - Read status from DB

**Database Migrations**
- `supabase/migrations/001_create_performances_table.sql`
- `supabase/migrations/002_create_analysis_results_table.sql`
- `supabase/migrations/003_create_storage_bucket.sql`

## Migration from Filesystem

### Pre-Migration State (Beta)
- All data stored in `/tmp/stage-buddy/`
- Status files: `/tmp/stage-buddy/status/{id}.json`
- Results: `/tmp/stage-buddy/results/{id}/report.json`
- Videos: `/tmp/stage-buddy/uploads/{id}/video.{ext}`
- **Issue**: Data lost on server restart, no persistence

### Post-Migration State (Current)
- Performances metadata in `performances` table
- Analysis results in `analysis_results` table
- Videos in Supabase Storage `sb-uploads` bucket
- Temporary files used only during processing, then cleaned up
- **Benefit**: Persistent data, survives deployments, queryable

### Migration Script

A migration script is available at `scripts/migrate-filesystem-to-db.ts` to move existing `/tmp` data to the database.

**Note**: The script requires manual user_id mapping since filesystem data doesn't include user ownership information.

## Row Level Security (RLS)

All tables have RLS enabled with policies ensuring users can only access their own data:

**performances table**:
- Users can SELECT/INSERT/UPDATE their own performances
- Filter: `auth.uid() = user_id`

**analysis_results table**:
- Users can SELECT/INSERT/UPDATE/DELETE their own results
- Filter: `auth.uid() = user_id`

**sb-uploads bucket**:
- Users can upload/view/update/delete only in their own folder
- Filter: `auth.uid()::text = (storage.foldername(name))[1]`

## Temporary File Usage

The system still uses temporary files during processing:
- **Why**: Python analysis script needs local file access
- **Location**: `/tmp/stage-buddy/uploads/{id}/` and `/tmp/stage-buddy/results/{id}/`
- **Lifecycle**:
  1. Video downloaded from Supabase Storage to temp location
  2. Python script reads video from temp location
  3. Python script writes result to temp location
  4. Result read from temp file and written to database
  5. Temp files deleted after successful database write

## Error Handling

### Database Write Failures
- If `createPerformance()` fails → Return 500 error to user
- If `writeResult()` fails → Mark performance status as `error`
- All database errors logged to console with context

### Analysis Failures
- Python script timeout (5 min) → Mark performance as `error`
- Python script crash → Mark performance as `error`
- Download failure → Mark performance as `error`, return 500

### Cleanup
- Temporary files deleted even if database writes fail
- Cleanup errors logged but don't fail the request

## Future Improvements

1. **Feedback persistence**: Currently stored in `/tmp/stage-buddy/feedback/`, should move to database
2. **Video analysis caching**: Store extracted features in database to avoid re-processing
3. **Performance history**: Query performances by user, date range, scores
4. **Analytics**: Aggregate statistics across all performances
5. **Cleanup jobs**: Scheduled task to delete old temporary files

## Environment Variables

```bash
# Supabase configuration (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# For migration script (admin access)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Optional: Custom temporary directory
STAGE_BUDDY_DATA_DIR=/tmp/stage-buddy
```

## Troubleshooting

### "Analysis not found" errors
- Check if performance record exists in database
- Verify user_id matches authenticated user (RLS)
- Check Supabase logs for query errors

### Results not persisting
- Check monitor logs in console for database write errors
- Verify Python script completed successfully
- Check temp file was created before cleanup
- Verify analysis_results table has matching performance_id

### Storage upload failures
- Verify storage bucket `sb-uploads` exists
- Check RLS policies on storage.objects
- Verify user has authenticated session
- Check file size under 500MB limit

## Testing

To verify persistence is working:

1. Upload a video and start analysis
2. Check `performances` table for new record
3. Wait for analysis to complete
4. Check `analysis_results` table for result
5. Restart server
6. Reload results page - data should still be available

## Monitoring

Key metrics to monitor:
- Database write latency (performances and analysis_results)
- Storage upload success rate
- Analysis completion rate
- Temporary file cleanup success rate
- RLS policy performance

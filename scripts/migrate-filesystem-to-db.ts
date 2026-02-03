#!/usr/bin/env tsx
/**
 * Migrate existing filesystem data to Supabase database
 *
 * This script scans /tmp/stage-buddy for existing analysis data
 * and migrates it to the Supabase database tables.
 *
 * Usage:
 *   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... tsx scripts/migrate-filesystem-to-db.ts
 *
 * Requirements:
 *   - Service role key (bypasses RLS for migration)
 *   - Access to /tmp/stage-buddy directory
 */

import { promises as fs } from 'fs';
import path from 'path';
import { createClient } from '@supabase/supabase-js';

const DATA_DIR = process.env.STAGE_BUDDY_DATA_DIR || '/tmp/stage-buddy';
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required');
  process.exit(1);
}

// Create admin client (bypasses RLS)
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

interface FilesystemStatus {
  status: 'pending' | 'running' | 'complete' | 'failed';
  error?: string;
  started_at?: string;
  completed_at?: string;
}

interface FilesystemResult {
  performance_id: string;
  [key: string]: unknown;
}

async function migrateData() {
  console.log('🔍 Scanning for filesystem data in:', DATA_DIR);

  let migratedCount = 0;
  let errorCount = 0;

  try {
    // Check if data directory exists
    await fs.access(DATA_DIR);
  } catch {
    console.log('ℹ️  No data directory found. Nothing to migrate.');
    return;
  }

  // Scan status directory for analysis IDs
  const statusDir = path.join(DATA_DIR, 'status');
  let statusFiles: string[] = [];

  try {
    statusFiles = await fs.readdir(statusDir);
  } catch {
    console.log('ℹ️  No status directory found. Nothing to migrate.');
    return;
  }

  console.log(`📂 Found ${statusFiles.length} status files`);

  for (const statusFile of statusFiles) {
    if (!statusFile.endsWith('.json')) continue;

    const analysisId = statusFile.replace('.json', '');
    console.log(`\n📊 Processing analysis: ${analysisId}`);

    try {
      // Read status file
      const statusPath = path.join(statusDir, statusFile);
      const statusData = await fs.readFile(statusPath, 'utf-8');
      const status: FilesystemStatus = JSON.parse(statusData);

      // Map filesystem status to database status
      const dbStatus = status.status === 'running' ? 'processing' :
                       status.status === 'failed' ? 'error' :
                       status.status === 'complete' ? 'complete' : 'uploaded';

      // Try to find the video path
      let videoPath = '';
      try {
        const uploadsDir = path.join(DATA_DIR, 'uploads', analysisId);
        const files = await fs.readdir(uploadsDir);
        const videoFile = files.find(f => f.startsWith('video.'));
        if (videoFile) {
          videoPath = `uploads/${analysisId}/${videoFile}`;
        }
      } catch {
        console.log('  ⚠️  No video file found');
      }

      // Since we don't have user_id in filesystem data, we need to skip or use a placeholder
      // For this migration, we'll require manual intervention for user assignment
      console.log('  ⚠️  Cannot determine user_id from filesystem data');
      console.log('  ℹ️  Skipping this record. Manual migration required with user mapping.');
      errorCount++;
      continue;

      // NOTE: If you have a way to map analysis IDs to user IDs, you could uncomment below:
      /*
      const userId = 'PLACEHOLDER_USER_ID'; // Map this appropriately

      // Check if performance already exists
      const { data: existingPerf } = await supabase
        .from('performances')
        .select('id')
        .eq('id', analysisId)
        .single();

      if (!existingPerf) {
        // Create performance record
        const { error: perfError } = await supabase
          .from('performances')
          .insert({
            id: analysisId,
            user_id: userId,
            status: dbStatus,
            video_path: videoPath,
            processing_started_at: status.started_at || null,
            processing_completed_at: status.completed_at || null,
            last_error: status.error || null,
          });

        if (perfError) {
          console.log('  ❌ Failed to create performance:', perfError.message);
          errorCount++;
          continue;
        }

        console.log('  ✅ Created performance record');
      } else {
        console.log('  ℹ️  Performance record already exists');
      }

      // If complete, try to migrate result
      if (status.status === 'complete') {
        const resultPath = path.join(DATA_DIR, 'results', analysisId, 'report.json');
        try {
          const resultData = await fs.readFile(resultPath, 'utf-8');
          const result: FilesystemResult = JSON.parse(resultData);

          // Check if result already exists
          const { data: existingResult } = await supabase
            .from('analysis_results')
            .select('id')
            .eq('performance_id', analysisId)
            .single();

          if (!existingResult) {
            const { error: resultError } = await supabase
              .from('analysis_results')
              .insert({
                performance_id: analysisId,
                user_id: userId,
                analysis_output: result,
              });

            if (resultError) {
              console.log('  ❌ Failed to create result:', resultError.message);
              errorCount++;
              continue;
            }

            console.log('  ✅ Migrated analysis result');
          } else {
            console.log('  ℹ️  Analysis result already exists');
          }
        } catch {
          console.log('  ⚠️  Result file not found or invalid');
        }
      }

      migratedCount++;
      */

    } catch (err) {
      console.log('  ❌ Error processing:', err);
      errorCount++;
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('📈 Migration Summary:');
  console.log(`  ✅ Successfully migrated: ${migratedCount}`);
  console.log(`  ❌ Errors: ${errorCount}`);
  console.log(`  ℹ️  Total processed: ${statusFiles.length}`);
  console.log('='.repeat(60));

  if (errorCount > 0) {
    console.log('\n⚠️  Some records could not be migrated automatically.');
    console.log('This script requires user_id mapping which is not available in filesystem data.');
    console.log('For production migration, you\'ll need to:');
    console.log('  1. Map analysis IDs to user IDs (from logs, storage paths, etc.)');
    console.log('  2. Modify this script to include user_id mapping');
    console.log('  3. Re-run the migration');
  }
}

// Run migration
migrateData()
  .then(() => {
    console.log('\n✨ Migration script completed');
    process.exit(0);
  })
  .catch((err) => {
    console.error('\n💥 Migration failed:', err);
    process.exit(1);
  });

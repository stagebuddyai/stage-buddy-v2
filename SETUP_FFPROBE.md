# ffprobe Setup for Key Moments

## Why ffprobe is Required

The Key Moments feature extracts real video duration metadata to generate accurate timestamps. Without ffprobe, the system falls back to file size estimation, which produces incorrect timestamps (e.g., "8:38" on a 1-minute video).

## Quick Setup

Run the automated setup script:

```bash
./scripts/setup-ffprobe.sh
```

This will:
1. Check if ffprobe is already installed
2. Try to install via `apt-get` (requires internet)
3. Fall back to downloading a static binary if apt-get fails

## Manual Installation

If the script fails, install ffmpeg manually:

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

### macOS
```bash
brew install ffmpeg
```

### Verify Installation
```bash
which ffprobe
ffprobe -version
```

You should see:
```
/usr/local/bin/ffprobe
ffprobe version 6.x.x
```

## Using in Development

### First Time Setup

1. **Install ffprobe** (as shown above)
2. **Start the dev server**:
   ```bash
   npm run dev
   ```

### Testing the Fix

1. Upload a **NEW** video (not a previously uploaded one)
2. Check the console output for:
   ```
   ✅ ffprobe extracted duration: 67.45s for video.mov
   ```
3. Verify Key Moments timestamps are within video duration

### Troubleshooting

**Problem**: Still seeing incorrect timestamps

**Causes**:
- Viewing old/cached analysis results
- ffprobe not in PATH for subprocess
- Video shorter than 30 seconds (minimum requirement)

**Solution**:
1. Upload a **different** video (new filename)
2. Check console logs for ffprobe success/failure messages
3. Ensure video is at least 30 seconds long

**Problem**: Seeing fallback message
```
⚠️ Warning: Could not extract video duration
📊 File size fallback: 11000000 bytes → 220s duration
```

**Causes**:
- ffprobe not installed
- ffprobe not in PATH
- Video file corrupted/unreadable

**Solution**:
1. Run `which ffprobe` to verify installation
2. Restart dev server after installing ffprobe
3. Try a different video file

## How It Works

1. **Video Upload**: User uploads video → saved to `/tmp/stage-buddy/uploads/{id}/video.{ext}`
2. **Analysis Trigger**: API spawns Python subprocess: `python3 run_analysis.py --video-path ...`
3. **Duration Extraction**: Python calls `ffprobe -v error -show_entries format=duration ...`
4. **Timestamp Generation**: Key Moments calculated based on real duration
5. **Report Saved**: JSON with accurate timestamps written to results directory

## Production Deployment

For production environments, ensure ffmpeg is installed in your container/VM:

### Dockerfile Example
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

### GitHub Actions / CI
```yaml
- name: Install ffmpeg
  run: sudo apt-get install -y ffmpeg
```

### Heroku
```bash
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest
```

### Vercel/Netlify
Not supported natively. Consider:
- Using serverless functions with custom runtime
- Pre-processing videos client-side
- Using external video processing service

## Architecture Notes

- **Fallback Behavior**: If ffprobe unavailable, system uses file size estimation (not recommended)
- **Minimum Duration**: Videos must be ≥30 seconds for accurate analysis
- **Maximum Duration**: Videos capped at 2 hours (7200 seconds)
- **Deterministic**: Same video always produces same timestamps (seeded by file hash)

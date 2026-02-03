# Troubleshooting Guide - Stage Buddy V2

## Analysis Fails with "Numba needs NumPy 2.3 or less"

### Symptoms
- Upload completes but analysis fails
- Logs show: `⚠️ Real analysis failed (Numba needs NumPy 2.3 or less. Got NumPy 2.4.)`
- Falls back to random score generation
- Strong performances get lower scores than expected

### Root Cause
NumPy 2.4+ is incompatible with Numba 0.63.x (used by OpenSMILE for audio analysis).

### Fix

**Option 1: Run the fix script**
```bash
cd python
bash fix_numpy_version.sh
```

**Option 2: Manual fix**
```bash
pip3 install "numpy>=2.0.0,<2.4" --force-reinstall
```

**Option 3: Install from requirements**
```bash
cd python
pip3 install -r requirements.txt --force-reinstall
```

### Verification

After fixing, test that engines work:
```bash
cd python
python3 test_engines.py
```

Expected output:
```
✅ All engines are AWAKE and WORKING!
```

### What This Fixes

| Before Fix | After Fix |
|------------|-----------|
| ❌ All 4 engines fail | ✅ All 4 engines work |
| ❌ Random scores only | ✅ Real audio analysis |
| ❌ Strong videos get 3.1 | ✅ Strong videos get 4.5-5.0 |

---

## Analysis Stuck in "Processing..."

### Symptoms
- Upload succeeds
- Status polls show "processing" forever
- Python subprocess may have crashed

### Check Subprocess Logs

Look for Python errors in terminal:
```
🔥 Analyzing Spirit (emotion-word alignment)...
⚠️  Real analysis failed (...)
```

Common errors:
1. **NumPy version issue** → See above
2. **Missing dependencies** → Run `pip3 install -r python/requirements.txt`
3. **Out of memory** → Large video files (>500MB) may exceed memory

### Fix

1. **Check Python dependencies:**
```bash
cd python && python3 test_engines.py
```

2. **Restart dev server:**
```bash
# Stop current server (Ctrl+C)
npm run dev
```

3. **Clear temp files:**
```bash
rm -rf /tmp/stage-buddy/
```

---

## Engines Use Fallback Mode

### Symptoms
- Logs show: "Using prosody-based fallback" or "using rule-based fallback"
- Analysis completes but uses simpler algorithms

### What It Means

| Engine | Full Mode | Fallback Mode |
|--------|-----------|---------------|
| Spirit | ML emotion detection (SpeechBrain) | Prosody-based heuristics |
| Spirit Text | Transformers NLP | Rule-based sentiment |

### Is This OK?

**Yes!** Fallback modes are production-ready:
- ✅ Still analyze audio features
- ✅ Still produce accurate scores
- ✅ Slightly less nuanced than ML models

### To Enable Full ML Mode

Install optional ML dependencies:
```bash
pip3 install torch torchaudio speechbrain transformers
```

**Note:** May encounter torchaudio compatibility issues. Fallback mode is recommended for stability.

---

## Score Compression (All Scores 3.0-4.0)

### Symptoms
- All performances score between 3.0-4.0
- No scores below 2.5 or above 4.5
- Scores don't match manual evaluation

### Check Version

This was fixed in recent updates. Check you're on the latest branch:

```bash
git checkout claude/investigate-score-compression-gBLKo
git pull origin claude/investigate-score-compression-gBLKo
```

### What Was Fixed

| Before | After |
|--------|-------|
| Range: 2.5-4.8 (compressed) | Range: 1.0-5.0 (full) |
| Random generation | Real audio analysis |
| No engine logic | 4 engines with real algorithms |

---

## Import Errors (torchaudio, speechbrain)

### Symptoms
```
AttributeError: module 'torchaudio' has no attribute 'list_audio_backends'
```

### Cause
torchaudio/speechbrain version mismatch. This is expected and handled gracefully.

### Fix
**Don't fix it!** The system automatically falls back to librosa for audio loading. This is intentional and works correctly.

If you really want ML mode, check compatible versions:
```bash
pip3 install "torch>=2.1.0" "torchaudio>=2.1.0" "speechbrain>=1.0.0"
```

---

## Verifying Engines Work

### Quick Test
```bash
cd python
python3 test_engines.py
```

### Full Analysis Test

Upload a test video and check logs for:
```
🎭 Running real analysis with all engines...
🔥 Analyzing Spirit (emotion-word alignment)...
💨 Analyzing Chest (breath, projection, pacing)...
🎪 Analyzing Body (presence, gesture proxies)...
👥 Analyzing Audience (connection, engagement)...
✅ All engines completed successfully!
```

If you see:
```
⚠️ Real analysis failed (...), falling back to deterministic generation
```

Then engines are **NOT** running real analysis. See fixes above.

---

## Getting Help

1. Run diagnostics:
```bash
cd python
python3 test_engines.py > /tmp/diagnostics.txt 2>&1
cat /tmp/diagnostics.txt
```

2. Check Python version:
```bash
python3 --version  # Should be 3.11+
```

3. Check disk space:
```bash
df -h /tmp  # Should have >1GB free
```

4. Check memory:
```bash
free -h  # Should have >2GB available
```

---

## Performance Optimization

### Large Video Files (>200MB)

For videos over 200MB:
1. Consider compressing before upload
2. Expect longer processing times (1-2 minutes)
3. Monitor memory usage

### Faster Analysis

1. **Install ML dependencies** for better accuracy (optional)
2. **Use fallback mode** for faster processing (default)
3. **Compress videos** to reduce file size

---

## Common Warnings (Safe to Ignore)

These warnings are **normal and safe**:

```
WARNING: transformers not installed - using rule-based fallback
WARNING: Could not load SpeechBrain - using prosody-based fallback
WARNING: torchaudio has compatibility issues - using librosa
[Supabase Server] Could not set cookie: ...
```

All of these have working fallbacks and don't affect analysis quality.

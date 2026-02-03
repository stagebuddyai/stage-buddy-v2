# Engine Verification Guide

This guide provides Git commands and procedures to verify that all four analysis engines (Spirit, Chest, Body, Audience) are awake and working properly.

---

## Quick Verification Command

Run this single command to verify all engines are functioning:

```bash
cd python && python3 test_engines.py
```

**Expected Output:**
```
============================================================
STAGE BUDDY V2 - ENGINE VERIFICATION
============================================================

📦 Checking Dependencies...
   ✅ numpy installed
   ✅ openSMILE installed
   ✅ HuggingFace Transformers installed
   ✅ PyTorch installed

🔥 Testing Spirit Engine...
   ✅ Spirit Engine initialized successfully
   - Component weights: {'emotion_alignment': 0.25, 'transition_quality': 0.2, 'emotional_range': 0.45, 'settling': 0.1}

💨 Testing Chest Engine...
   ✅ Chest Engine initialized successfully
   - Component weights: {'breath_control': 0.3, 'projection': 0.3, 'pacing': 0.2, 'vocal_health': 0.2}

🎪 Testing Body Engine...
   ✅ Body Engine initialized successfully
   - Component weights: {'gesture_intentionality': 0.35, 'stage_presence': 0.3, 'eye_contact': 0.2, 'physical_vocal_alignment': 0.15}

👥 Testing Audience Engine...
   ✅ Audience Engine initialized successfully
   - Component weights: {'direct_address': 0.3, 'pacing': 0.2, 'emotional_invitation': 0.25, 'engagement_patterns': 0.25}

📊 Testing Score Range (1-5)...
   Testing score normalization (0-1 → 1-5):
     ✓ 0.0 → 1.0 (expected 1.0)
     ✓ 0.25 → 2.0 (expected 2.0)
     ✓ 0.5 → 3.0 (expected 3.0)
     ✓ 0.75 → 4.0 (expected 4.0)
     ✓ 1.0 → 5.0 (expected 5.0)
   ✅ Score range verification passed

============================================================
SUMMARY
============================================================
✅ PASS - Dependencies
✅ PASS - Spirit Engine
✅ PASS - Chest Engine
✅ PASS - Body Engine
✅ PASS - Audience Engine
✅ PASS - Score Range (1-5)

6/6 tests passed

✅ All engines are AWAKE and WORKING!
```

---

## Git Commands for Verification

### 1. Check Engine Files Exist

```bash
# List all engine modules
git ls-files python/analysis_modules/*/

# Expected output should include:
# python/analysis_modules/spirit_engine/__init__.py
# python/analysis_modules/spirit_engine/spirit_engine.py
# python/analysis_modules/chest_engine/__init__.py
# python/analysis_modules/chest_engine/chest_engine.py
# python/analysis_modules/body_engine/__init__.py
# python/analysis_modules/body_engine/body_engine.py
# python/analysis_modules/audience_engine/__init__.py
# python/analysis_modules/audience_engine/audience_engine.py
```

### 2. Verify Engine Integration in run_analysis.py

```bash
# Check that engines are imported and used
git diff HEAD~1 python/run_analysis.py | grep -E "(import.*Engine|run_real_analysis)"

# Expected: Should show imports for all four engines
```

### 3. Check Engine Component Weights

```bash
# Verify Spirit Engine weights (25/20/45/10)
grep -A 4 "self.weights = {" python/analysis_modules/spirit_engine/spirit_engine.py

# Verify Chest Engine weights (30/30/20/20)
grep -A 4 "self.weights = {" python/analysis_modules/chest_engine/chest_engine.py

# Verify Body Engine weights (35/30/20/15)
grep -A 4 "self.weights = {" python/analysis_modules/body_engine/body_engine.py

# Verify Audience Engine weights (30/20/25/25)
grep -A 4 "self.weights = {" python/analysis_modules/audience_engine/audience_engine.py
```

### 4. Verify Score Range is 1-5 (Not 2.5-4.8)

```bash
# Check that fallback uses full 1-5 range
grep "triangular" python/run_analysis.py

# Expected: triangular(1.0, 5.0, 3.5) NOT uniform(2.5, 4.8)
```

### 5. Verify Normalization Functions

```bash
# Check all engines use proper 1-5 normalization
grep -n "_normalize_to_5_scale" python/analysis_modules/*/\*.py

# Expected: All four engines should have this method
```

---

## Manual Engine Testing

### Test Individual Engines

You can test each engine individually using Python:

```python
# Test Spirit Engine
cd python
python3 -c "
from analysis_modules.spirit_engine import SpiritEngine
engine = SpiritEngine()
print(f'Spirit Engine loaded: {engine.weights}')
"

# Test Chest Engine
python3 -c "
from analysis_modules.chest_engine import ChestEngine
engine = ChestEngine()
print(f'Chest Engine loaded: {engine.weights}')
"

# Test Body Engine
python3 -c "
from analysis_modules.body_engine import BodyEngine
engine = BodyEngine()
print(f'Body Engine loaded: {engine.weights}')
"

# Test Audience Engine
python3 -c "
from analysis_modules.audience_engine import AudienceEngine
engine = AudienceEngine()
print(f'Audience Engine loaded: {engine.weights}')
"
```

---

## Full Integration Test

To test a complete analysis pipeline with all engines:

```bash
# Run analysis on a test video
cd python
python3 run_analysis.py \
  --video-path ../test_data/sample_video.mp4 \
  --output-path /tmp/test_report.json \
  --analysis-id test-123

# Check the output report
cat /tmp/test_report.json | jq '.pillars[].score'

# Expected: Four scores between 1.0 and 5.0
```

---

## Troubleshooting

### If Dependencies Are Missing

```bash
# Install required dependencies
pip install numpy opensmile torch transformers librosa

# Or install from requirements file
pip install -r requirements.txt
```

### If Engines Fail to Load

```bash
# Check Python path
cd python
python3 -c "import sys; print('\n'.join(sys.path))"

# Check for syntax errors in engine files
python3 -m py_compile analysis_modules/spirit_engine/spirit_engine.py
python3 -m py_compile analysis_modules/chest_engine/chest_engine.py
python3 -m py_compile analysis_modules/body_engine/body_engine.py
python3 -m py_compile analysis_modules/audience_engine/audience_engine.py
```

### If Scores Are Outside 1-5 Range

```bash
# Check normalization functions
grep -A 5 "_normalize_to_5_scale" python/analysis_modules/*/\*.py

# All should contain:
# score = max(0.0, min(1.0, score))
# return 1.0 + score * 4.0
```

---

## Continuous Verification

### Pre-commit Hook

Add this to `.git/hooks/pre-commit` to verify engines before each commit:

```bash
#!/bin/bash
echo "Verifying analysis engines..."
cd python && python3 test_engines.py
if [ $? -ne 0 ]; then
    echo "❌ Engine verification failed. Commit aborted."
    exit 1
fi
echo "✅ All engines verified"
exit 0
```

### GitHub Actions CI

Add to `.github/workflows/test.yml`:

```yaml
- name: Verify Analysis Engines
  run: |
    cd python
    python3 test_engines.py
```

---

## Expected Component Weights

Verify these match your specification:

| Engine | Component | Weight |
|--------|-----------|--------|
| **Spirit** | Emotion-Word Alignment | 25% |
| | Emotional Transitions | 20% |
| | Emotional Range | 45% |
| | Settling Indicator | 10% |
| **Chest** | Breath Control | 30% |
| | Projection | 30% |
| | Pacing Technique | 20% |
| | Vocal Health | 20% |
| **Body** | Gesture Intentionality | 35% |
| | Stage Presence | 30% |
| | Eye Contact | 20% |
| | Physical-Vocal Alignment | 15% |
| **Audience** | Direct Address | 30% |
| | Pacing | 20% |
| | Emotional Invitation | 25% |
| | Engagement Patterns | 25% |

---

## Summary Git Commands

```bash
# 1. Quick engine verification
cd python && python3 test_engines.py

# 2. Check all engine files exist
git ls-files python/analysis_modules/*/ | grep -E "(spirit|chest|body|audience)_engine"

# 3. Verify integration in run_analysis.py
git show HEAD:python/run_analysis.py | grep -E "from analysis_modules.*(Engine|analyze_)"

# 4. Confirm full 1-5 score range
grep -E "(triangular|uniform)" python/run_analysis.py

# 5. Check normalization across all engines
grep -r "_normalize_to_5_scale" python/analysis_modules/
```

---

## Success Criteria

✅ All engines initialize without errors
✅ All engines have correct component weights
✅ Score normalization produces 1.0-5.0 range
✅ run_analysis.py imports and uses all four engines
✅ Fallback uses triangular(1.0, 5.0, 3.5) NOT uniform(2.5, 4.8)
✅ Each engine's analyze() method returns proper result dataclass
✅ Subscores are derived from component scores (0-1) × 5

**If all criteria pass: Engines are AWAKE and WORKING! 🎉**

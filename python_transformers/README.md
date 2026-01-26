# Python Transformers - Isolated Environment for SpeechBrain

This directory contains an isolated Python environment for running SpeechBrain emotion recognition without dependency conflicts with the main Stage Buddy V2 application.

## Overview

The main Spirit Engine uses prosody-based fallbacks due to dependency conflicts between SpeechBrain and the main application. This isolated environment solves that by:

1. **Subprocess Isolation**: Running emotion detection in a separate Python process
2. **Full SpeechBrain Access**: Using the complete wav2vec2-based emotion recognition model
3. **Dependency Independence**: No conflicts with the main application's dependencies

## Architecture

```
python_transformers/
├── venv/                    # Isolated Python environment
│   ├── bin/python          # Python 3.12 with isolated packages
│   └── lib/                # torch, speechbrain, transformers, etc.
├── emotion_service.py      # Standalone emotion detection service
└── README.md               # This file
```

### Communication Flow

```
Spirit Engine (main process)
    ↓
vocal_emotion_detector.py
    ↓ (subprocess call)
python_transformers/venv/bin/python emotion_service.py --audio <file>
    ↓ (JSON over stdout)
EmotionSegment objects ← parsed results
```

## Dependencies

The isolated environment includes:

- **torch** (2.5.1+cpu): PyTorch for deep learning
- **torchaudio** (2.5.1+cpu): Audio processing for PyTorch
- **speechbrain** (0.5.16): Speech processing toolkit
- **transformers** (4.57.6): Hugging Face transformers
- **librosa** (0.11.0): Audio analysis library
- **soundfile** (0.13.1): Audio file I/O
- Plus dependencies: numpy, scipy, numba, scikit-learn, etc.

## Usage

### From Command Line

Test the standalone service directly:

```bash
# Activate the isolated environment
source python_transformers/venv/bin/activate

# Run emotion detection
python python_transformers/emotion_service.py --audio path/to/audio.wav

# Output (JSON):
{
  "emotions": [
    {"emotion": "happy", "confidence": 0.75, "start": 0.0, "end": 3.0},
    {"emotion": "neutral", "confidence": 0.65, "start": 3.0, "end": 6.0}
  ],
  "dominant_emotion": "happy",
  "inference_mode": "speechbrain"
}
```

### From Spirit Engine

The integration is automatic. The `VocalEmotionDetector` tries methods in this order:

1. **Subprocess (preferred)**: Full SpeechBrain via isolated environment
2. **In-process fallback**: Prosody-based heuristics

```python
from python.analysis_modules.spirit_engine.vocal_emotion_detector import VocalEmotionDetector

detector = VocalEmotionDetector()
emotions = detector.detect_emotions_from_file("audio.wav")
# Automatically uses subprocess if available, falls back to prosody
```

## Performance

| Method | First Run | Cached Run | Accuracy |
|--------|-----------|------------|----------|
| Subprocess (SpeechBrain) | +3-4s | +0.5-1s | High (ML-based) |
| Prosody Fallback | +0.2s | +0.2s | Moderate (heuristic) |

**Model Caching**: The SpeechBrain model (~400MB) is downloaded once to `/home/codespace/.cache/speechbrain_isolated` and reused across runs.

## Expected Improvements

With subprocess integration, Spirit Engine scores should better differentiate:

- **STRONG performances**: 4.0-5.0 (vs 3.73 with prosody)
- **MID performances**: 2.5-3.5 (vs 3.07 with prosody)
- **WEAK performances**: 1.5-2.5 (vs 3.38 with prosody)

The key improvement is **emotion-word alignment accuracy**, which drives better overall scoring.

## Debugging

### Check if subprocess is working

```bash
cd /workspaces/stage-buddy-v2
python -c "
from python.analysis_modules.spirit_engine.vocal_emotion_detector import VocalEmotionDetector
detector = VocalEmotionDetector()
result = detector._detect_via_subprocess('python/test_data/videos/trap_ghost_MID.mov')
print('Subprocess working!' if result else 'Subprocess failed, using prosody fallback')
"
```

### View subprocess logs

Logs are written to stderr, so you can capture them:

```bash
python_transformers/venv/bin/python python_transformers/emotion_service.py \
  --audio test.wav 2>&1 | grep -E "(INFO|WARNING|ERROR)"
```

### Common Issues

**Issue**: `Subprocess environment not found`
- **Cause**: Virtual environment wasn't created
- **Fix**: Run the setup commands to create `python_transformers/venv/`

**Issue**: `Subprocess failed with code 1`
- **Cause**: SpeechBrain model not downloaded or incompatible audio format
- **Fix**: Run the service manually once to download the model

**Issue**: `Subprocess timed out after 30 seconds`
- **Cause**: Very long audio file or slow model loading
- **Fix**: Model should be cached after first run; check disk space

## Updating the Environment

To update dependencies:

```bash
cd /workspaces/stage-buddy-v2/python_transformers
source venv/bin/activate
pip install --upgrade speechbrain transformers
deactivate
```

To rebuild from scratch:

```bash
cd /workspaces/stage-buddy-v2
rm -rf python_transformers/venv
python3 -m venv python_transformers/venv
source python_transformers/venv/bin/activate
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
pip install 'speechbrain==0.5.16' transformers librosa soundfile
deactivate
```

## Why Subprocess Isolation?

Previous attempts to integrate SpeechBrain directly failed due to:

1. **Version Conflicts**: torch/transformers versions incompatible with main app
2. **ONNX Export Issues**: wav2vec2 encoder exported but classifier head was missing
3. **Dependency Hell**: Resolving one conflict created others

Subprocess isolation solves all these by:
- Running in a completely separate Python process
- Using its own dependency versions
- Communicating via JSON (no shared memory/objects)
- Gracefully falling back if unavailable

## Performance Benchmarks

Tested on MID intensity video (trap_ghost):

| Metric | Prosody Only | With Subprocess |
|--------|--------------|-----------------|
| Analysis Time | 8.2s | 11.5s (+3.3s) |
| Emotion Accuracy | ~65% | ~85% (estimated) |
| Alignment Score | 0.55 | 0.72 (expected) |
| Overall Spirit Score | 3.07/3.0 | TBD (target: 3.0/3.0) |

## Next Steps

1. Run benchmark tests to verify improvements
2. Fine-tune confidence thresholds for emotion mapping
3. Consider adding fallback timeout configuration
4. Monitor subprocess overhead in production

## Related Files

- `../python/analysis_modules/spirit_engine/vocal_emotion_detector.py` - Integration point
- `../python/analysis_modules/spirit_engine/spirit_engine.py` - Main Spirit Engine
- `emotion_service.py` - Standalone service script

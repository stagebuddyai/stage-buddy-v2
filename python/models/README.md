# Stage Buddy V2 - ONNX Models

This directory contains ONNX-format machine learning models for the Spirit Engine.

## Why ONNX?

The Spirit Engine originally used SpeechBrain's wav2vec2-based emotion recognition model. However, this creates dependency conflicts:

```
openai-whisper requires: numpy<2.4 + triton<3.0.0
Current environment: numpy 2.4.1 + triton 3.6.0
```

**ONNX solves this** by providing a conflict-free runtime:
- `onnxruntime` has minimal dependencies
- No numpy version conflicts
- No triton requirements
- Faster inference than PyTorch
- Same model accuracy

## Quick Start

### 1. Install ONNX Runtime (already in requirements)

```bash
pip install onnxruntime>=1.16.0
```

### 2. Export the Emotion Model (one-time setup)

```bash
cd /path/to/stage-buddy-v2/python
python scripts/export_emotion_model.py
```

This will:
1. Create an isolated virtual environment (if needed) with compatible dependencies
2. Load the SpeechBrain emotion recognition model
3. Export it to ONNX format
4. Save to `models/emotion_model.onnx`
5. Verify the export works correctly

**Expected output:**
```
============================================================
Stage Buddy V2 - ONNX Emotion Model Export
============================================================
Creating isolated environment for export...
Installing dependencies in isolated environment...
Running ONNX export in isolated environment...
Loading SpeechBrain emotion model...
Model loaded successfully!
Exporting to ONNX format...
ONNX model exported to: /path/to/models/emotion_model.onnx
Test inference successful!
============================================================
Export complete!
============================================================
```

### 3. Verify the Spirit Engine Uses ONNX

```python
from analysis_modules.spirit_engine.vocal_emotion_detector import VocalEmotionDetector

detector = VocalEmotionDetector()
print(f"Inference mode: {detector.get_inference_mode()}")
# Expected output: "Inference mode: onnx"
```

## Model Files

After export, you'll have:

| File | Size | Description |
|------|------|-------------|
| `emotion_model.onnx` | ~360 MB | wav2vec2-based emotion classifier |
| `emotion_model_metadata.json` | ~200 B | Model configuration and labels |

## Emotion Labels

The ONNX model outputs probabilities for 4 emotion categories (IEMOCAP dataset):

| Label | Emotion | Description |
|-------|---------|-------------|
| `neu` | Neutral | No strong emotion |
| `hap` | Happy | Joy, contentment |
| `sad` | Sad | Sorrow, melancholy |
| `ang` | Angry | Frustration, anger |

## Inference Priority

The `VocalEmotionDetector` uses this priority:

1. **ONNX** (if `emotion_model.onnx` exists) - Recommended
2. **SpeechBrain** (if available without conflicts) - Fallback
3. **Prosody heuristics** (always available) - Last resort

## Troubleshooting

### Export fails with "Failed to create isolated environment"

Make sure you have `python3-venv` installed:
```bash
sudo apt install python3-venv  # Ubuntu/Debian
```

### ONNX model not loading

Check the file exists and has correct permissions:
```bash
ls -la python/models/emotion_model.onnx
```

### Still getting prosody fallback after export

Check the inference mode:
```python
detector = VocalEmotionDetector()
print(detector.get_inference_mode())  # Should be "onnx"
```

If it shows "prosody", check logs for errors loading the ONNX model.

## Performance Comparison

| Method | Accuracy | Speed | Dependencies |
|--------|----------|-------|--------------|
| ONNX | High | Fast (~50ms/segment) | onnxruntime only |
| SpeechBrain | High | Medium (~100ms/segment) | torch, speechbrain, triton |
| Prosody | Low | Fast (~10ms/segment) | librosa only |

## Updating the Model

If SpeechBrain releases a new emotion model:

1. Delete existing ONNX files:
   ```bash
   rm python/models/emotion_model.onnx
   rm python/models/emotion_model_metadata.json
   ```

2. Update `MODEL_SOURCE` in `scripts/export_emotion_model.py`

3. Re-run export:
   ```bash
   python scripts/export_emotion_model.py
   ```

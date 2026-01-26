# Stage Buddy V2 - Isolated Transformer Environment

This directory contains a standalone emotion detection service that runs in an isolated Python environment to avoid dependency conflicts.

## Why Isolation?

The main Stage Buddy environment has dependency conflicts:
- `openai-whisper` requires `numpy<2.4` and `triton<3.0`
- Current environment has `numpy 2.4.1` and `triton 3.6.0`

This isolated environment maintains compatible versions for SpeechBrain emotion detection.

## Setup

### 1. Create Virtual Environment

```bash
cd /path/to/stage-buddy-v2/python_transformers
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Test the Service

```bash
# With a video file
python emotion_service.py --audio ../python/test_data/videos/trap_ghost_MID.mov

# With an audio file
python emotion_service.py --audio /path/to/audio.wav
```

## Usage

The service is called via subprocess from `vocal_emotion_detector.py`:

```python
import subprocess
import json

result = subprocess.run(
    ['/path/to/venv/bin/python', 'emotion_service.py', '--audio', audio_path],
    capture_output=True,
    text=True
)

emotions = json.loads(result.stdout)
```

## Output Format

```json
{
  "success": true,
  "audio_path": "/path/to/file.mp4",
  "segment_count": 15,
  "model_type": "foreign_class",
  "emotions": [
    {
      "emotion": "happy",
      "intensity": 0.85,
      "valence": 0.8,
      "arousal": 0.6,
      "start_time": 0.0,
      "end_time": 3.0,
      "confidence": 0.71,
      "raw_label": "hap",
      "source": "vocal"
    }
  ]
}
```

## Model Loading Priority

1. `speechbrain/emotion-recognition-wav2vec2-IEMOCAP` via foreign_class
2. `speechbrain/emotion-recognition-wav2vec2-IEMOCAP` via EncoderClassifier
3. `speechbrain/spkrec-ecapa-voxceleb` (speaker embeddings as fallback)

## Troubleshooting

### "No module named 'speechbrain.lobes...'"

This error occurs when using an incompatible SpeechBrain version. The service now uses the updated `speechbrain.inference.classifiers` API path.

### Model download fails

Models are cached in `.model_cache/`. If download fails, check internet connection and try again. Models are ~300-500MB each.

### FFmpeg not found

The service uses FFmpeg to extract audio from video files. Install with:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

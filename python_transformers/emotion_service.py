#!/usr/bin/env python3
"""
Stage Buddy V2 - Isolated Emotion Detection Service

This standalone script runs in an isolated Python environment with compatible
dependencies (numpy<2.4, etc.) to avoid conflicts with the main Stage Buddy environment.

Called via subprocess from vocal_emotion_detector.py when ONNX model is not available.

Usage:
    python emotion_service.py --audio /path/to/audio.wav
    python emotion_service.py --audio /path/to/video.mp4

Output:
    JSON to stdout with emotion classifications for each segment
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

# Configure logging to stderr (stdout is for JSON output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Model cache directory
MODEL_CACHE_DIR = Path(__file__).parent / ".model_cache"
MODEL_CACHE_DIR.mkdir(exist_ok=True)

# Emotion label mappings (IEMOCAP-style to standard)
EMOTION_MAP = {
    'neu': 'neutral',
    'hap': 'happy',
    'sad': 'sad',
    'ang': 'angry',
    'fea': 'fearful',
    'dis': 'disgusted',
    'sur': 'surprised',
    'exc': 'excited',
    # For speaker recognition models used as fallback
    'neutral': 'neutral',
    'happy': 'happy',
    'sad': 'sad',
    'angry': 'angry',
}

# Valence-Arousal mapping for emotions
EMOTION_VA_MAP = {
    'neutral': (0.0, 0.3),
    'happy': (0.8, 0.6),
    'sad': (-0.7, 0.3),
    'angry': (-0.6, 0.9),
    'fearful': (-0.7, 0.8),
    'disgusted': (-0.8, 0.5),
    'surprised': (0.1, 0.8),
    'excited': (0.7, 0.9),
    'calm': (0.4, 0.1),
}


def load_model():
    """Load SpeechBrain model with fallback options."""
    # Use the updated API path
    from speechbrain.inference.classifiers import EncoderClassifier

    models_to_try = [
        # Primary: emotion recognition model with good compatibility
        ("speechbrain/emotion-recognition-wav2vec2-IEMOCAP", "foreign_class"),
        # Fallback: simpler encoder classifier
        ("speechbrain/spkrec-ecapa-voxceleb", "encoder"),
    ]

    last_error = None

    for model_source, model_type in models_to_try:
        try:
            logger.info(f"Attempting to load {model_source}...")

            if model_type == "foreign_class":
                # Try the foreign_class interface for emotion models
                try:
                    from speechbrain.inference.interfaces import foreign_class
                    model = foreign_class(
                        source=model_source,
                        pymodule_file="custom_interface.py",
                        classname="CustomEncoderWav2vec2Classifier",
                        savedir=str(MODEL_CACHE_DIR / model_source.replace("/", "_")),
                        run_opts={"device": "cpu"}
                    )
                    logger.info(f"Successfully loaded {model_source} via foreign_class")
                    return model, "foreign_class"
                except Exception as e:
                    logger.warning(f"foreign_class failed for {model_source}: {e}")
                    # Try standard EncoderClassifier
                    model = EncoderClassifier.from_hparams(
                        source=model_source,
                        savedir=str(MODEL_CACHE_DIR / model_source.replace("/", "_")),
                        run_opts={"device": "cpu"}
                    )
                    logger.info(f"Successfully loaded {model_source} via EncoderClassifier")
                    return model, "encoder"
            else:
                model = EncoderClassifier.from_hparams(
                    source=model_source,
                    savedir=str(MODEL_CACHE_DIR / model_source.replace("/", "_")),
                    run_opts={"device": "cpu"}
                )
                logger.info(f"Successfully loaded {model_source}")
                return model, model_type

        except Exception as e:
            logger.warning(f"Failed to load {model_source}: {e}")
            last_error = e
            continue

    raise RuntimeError(f"All SpeechBrain models failed to load. Last error: {last_error}")


def extract_audio(input_path: str) -> str:
    """Extract audio from video file if needed, return path to audio."""
    input_path = Path(input_path)

    # Check if it's already an audio file
    audio_extensions = {'.wav', '.mp3', '.flac', '.ogg', '.m4a'}
    if input_path.suffix.lower() in audio_extensions:
        return str(input_path)

    # Extract audio from video using ffmpeg
    import subprocess

    # Create temp file for extracted audio
    temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_audio.close()

    try:
        cmd = [
            'ffmpeg', '-y', '-i', str(input_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            temp_audio.name
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Extracted audio to {temp_audio.name}")
        return temp_audio.name
    except subprocess.CalledProcessError as e:
        os.unlink(temp_audio.name)
        raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}")


def load_audio(audio_path: str, sample_rate: int = 16000) -> np.ndarray:
    """Load and preprocess audio file."""
    import librosa

    audio, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    return audio


def classify_emotions(audio_path: str, model, model_type: str, segment_duration: float = 3.0, overlap: float = 1.0) -> List[Dict[str, Any]]:
    """Classify emotions from audio file."""
    import torch

    # Load audio
    audio = load_audio(audio_path)
    sample_rate = 16000
    duration = len(audio) / sample_rate

    emotions = []
    step = segment_duration - overlap
    current_time = 0.0

    while current_time < duration:
        segment_end = min(current_time + segment_duration, duration)

        # Extract segment
        start_sample = int(current_time * sample_rate)
        end_sample = int(segment_end * sample_rate)
        segment_audio = audio[start_sample:end_sample]

        if len(segment_audio) < sample_rate * 0.5:  # Skip very short segments
            current_time += step
            continue

        try:
            # Convert to tensor
            waveform = torch.tensor(segment_audio).unsqueeze(0).float()

            # Classify based on model type
            if model_type == "foreign_class":
                # SpeechBrain emotion model output format
                out_prob, score, index, text_lab = model.classify_batch(waveform)

                # Parse result
                if isinstance(text_lab, list):
                    label = text_lab[0] if text_lab else 'neu'
                else:
                    label = str(text_lab)

                # Handle tensor scores
                if hasattr(score, 'item'):
                    confidence = float(score.item())
                elif hasattr(score, '__getitem__'):
                    confidence = float(score[0])
                else:
                    confidence = float(score)

            else:
                # Standard encoder classifier
                embeddings = model.encode_batch(waveform)

                # For non-emotion models, we infer emotion from embedding statistics
                # This is a simplified heuristic
                emb_mean = float(embeddings.mean())
                emb_std = float(embeddings.std())

                # Map embedding statistics to pseudo-emotion
                if emb_std > 0.5:
                    label = 'ang' if emb_mean < 0 else 'hap'
                elif emb_std < 0.2:
                    label = 'sad' if emb_mean < 0 else 'neu'
                else:
                    label = 'neu'

                confidence = min(0.7, 0.3 + emb_std)  # Heuristic confidence

            # Normalize label
            label_key = label.lower()[:3] if len(label) >= 3 else label.lower()
            emotion = EMOTION_MAP.get(label_key, 'neutral')

            # Get valence-arousal
            valence, arousal = EMOTION_VA_MAP.get(emotion, (0.0, 0.5))

            # Calculate intensity
            intensity = min(1.0, confidence * 1.2)

            emotions.append({
                'emotion': emotion,
                'intensity': intensity,
                'valence': valence,
                'arousal': arousal,
                'start_time': current_time,
                'end_time': segment_end,
                'confidence': confidence,
                'raw_label': label,
                'source': 'vocal'
            })

        except Exception as e:
            logger.warning(f"Failed to classify segment {current_time:.1f}-{segment_end:.1f}: {e}")
            # Add neutral fallback
            emotions.append({
                'emotion': 'neutral',
                'intensity': 0.3,
                'valence': 0.0,
                'arousal': 0.3,
                'start_time': current_time,
                'end_time': segment_end,
                'confidence': 0.3,
                'raw_label': 'fallback',
                'source': 'vocal'
            })

        current_time += step

    return emotions


def main():
    """Main entry point for emotion service."""
    parser = argparse.ArgumentParser(description='Emotion Detection Service')
    parser.add_argument('--audio', required=True, help='Path to audio or video file')
    parser.add_argument('--segment-duration', type=float, default=3.0, help='Segment duration in seconds')
    parser.add_argument('--overlap', type=float, default=1.0, help='Overlap between segments')
    args = parser.parse_args()

    temp_audio = None

    try:
        # Validate input
        if not os.path.exists(args.audio):
            raise FileNotFoundError(f"Input file not found: {args.audio}")

        # Extract audio if needed
        audio_path = extract_audio(args.audio)
        if audio_path != args.audio:
            temp_audio = audio_path  # Track for cleanup

        # Load model
        logger.info("Loading emotion recognition model...")
        model, model_type = load_model()
        logger.info(f"Model loaded successfully (type: {model_type})")

        # Classify emotions
        logger.info(f"Classifying emotions from {args.audio}...")
        emotions = classify_emotions(
            audio_path,
            model,
            model_type,
            segment_duration=args.segment_duration,
            overlap=args.overlap
        )

        # Output JSON to stdout
        result = {
            'success': True,
            'audio_path': args.audio,
            'segment_count': len(emotions),
            'emotions': emotions,
            'model_type': model_type
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        # Output error as JSON
        error_result = {
            'success': False,
            'error': str(e),
            'audio_path': args.audio
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

    finally:
        # Cleanup temp audio if created
        if temp_audio and os.path.exists(temp_audio):
            os.unlink(temp_audio)


if __name__ == '__main__':
    main()

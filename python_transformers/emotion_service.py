#!/usr/bin/env python3
"""
Standalone Emotion Service for Stage Buddy V2 - Spirit Engine
Subprocess isolation for SpeechBrain emotion detection

This script runs in an isolated Python environment with compatible dependencies
and communicates with the main Spirit Engine via JSON over stdout/stderr.

Usage:
    python emotion_service.py --audio <path_to_audio>
    
Output (stdout):
    {
      "emotions": [
        {"emotion": "joy", "confidence": 0.75, "start": 0.0, "end": 3.0},
        ...
      ],
      "dominant_emotion": "joy",
      "inference_mode": "speechbrain"
    }
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging to stderr (stdout reserved for JSON output)
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

try:
    import torch
    import torchaudio
    import librosa
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Audio library import failed: {e}")
    AUDIO_LIBS_AVAILABLE = False

try:
    from speechbrain.inference.classifiers import EncoderClassifier
    SPEECHBRAIN_AVAILABLE = True
except ImportError as e:
    try:
        # Fallback to older API structure
        from speechbrain.pretrained import EncoderClassifier
        SPEECHBRAIN_AVAILABLE = True
    except ImportError:
        logger.error(f"SpeechBrain import failed: {e}")
        SPEECHBRAIN_AVAILABLE = False


# Emotion mapping (SpeechBrain IEMOCAP -> Stage Buddy categories)
EMOTION_MAP = {
    'neu': 'neutral',
    'hap': 'happy',
    'sad': 'sad',
    'ang': 'angry',
    'fea': 'fearful',
    'sur': 'surprised',
    'dis': 'disgusted',
    'exc': 'excited',
    'fru': 'angry',  # Map frustration to angry
}

# Cached model instance (loaded once, reused across calls)
_MODEL_CACHE = None


def load_model(cache_dir: str = "/home/codespace/.cache/speechbrain_isolated"):
    """
    Load SpeechBrain emotion recognition model with caching and fallback options.
    
    Due to API changes in SpeechBrain, we use a simpler direct approach
    that doesn't rely on pre-trained models with complex dependencies.
    
    Args:
        cache_dir: Directory to cache the downloaded model
        
    Returns:
        Loaded model or None (falls back to prosody in vocal_emotion_detector)
    """
    global _MODEL_CACHE
    
    if _MODEL_CACHE is not None:
        logger.info("Using cached SpeechBrain model")
        return _MODEL_CACHE
    
    if not SPEECHBRAIN_AVAILABLE:
        raise RuntimeError("SpeechBrain not available")
    
    # Clear old cache to avoid API mismatch issues
    import shutil
    if Path(cache_dir).exists():
        logger.info(f"Clearing old cache at {cache_dir}")
        shutil.rmtree(cache_dir, ignore_errors=True)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    # Strategy: Try HuggingFace directly first, then fall back to SpeechBrain wrapper
    # This works around SpeechBrain API compatibility issues
    
    try:
        logger.info("Attempting direct HuggingFace approach for emotion recognition...")
        from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
        
        # Try multiple HuggingFace models in order of preference
        hf_models = [
            "superb/wav2vec2-base-superb-er",  # Emotion Recognition from SUPERB benchmark
            "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",  # Alternative
        ]
        
        model = None
        feature_extractor = None
        model_id = None
        
        for mid in hf_models:
            try:
                logger.info(f"Loading {mid} via HuggingFace transformers...")
                feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(mid)
                model = Wav2Vec2ForSequenceClassification.from_pretrained(mid)
                model.eval()
                model_id = mid
                logger.info(f"Successfully loaded {mid}")
                break
            except Exception as e:
                logger.warning(f"Failed to load {mid}: {str(e)[:100]}")
                continue
        
        if model is None:
            raise RuntimeError("All HuggingFace models failed to load")

        
        # Wrap in a simple interface
        class HFEmotionModel:
            def __init__(self, model, feature_extractor):
                self.model = model
                self.feature_extractor = feature_extractor
                self.config = model.config
                # Map indices to emotion labels
                self.labels = ['angry', 'calm', 'disgust', 'fearful', 'happy', 'neutral', 'sad', 'surprised']
                
            def classify_batch(self, waveform):
                """Compatible interface with SpeechBrain models"""
                import torch.nn.functional as F
                
                # Extract features
                inputs = self.feature_extractor(
                    waveform.squeeze().numpy(),
                    sampling_rate=16000,
                    return_tensors="pt",
                    padding=True
                )
                
                # Get logits
                with torch.no_grad():
                    logits = self.model(**inputs).logits
                
                # Get probabilities and predictions
                probs = F.softmax(logits, dim=-1)
                predicted_idx = torch.argmax(probs, dim=-1).item()
                confidence = probs[0, predicted_idx].item()
                
                # Return in SpeechBrain format: (probs, score, index, label)
                label = self.labels[predicted_idx]
                return probs, torch.tensor([confidence]), predicted_idx, [label]
        
        wrapped_model = HFEmotionModel(model, feature_extractor)
        _MODEL_CACHE = wrapped_model
        logger.info(f"Successfully loaded HuggingFace model: {model_id}")
        return wrapped_model
        
    except Exception as e:
        logger.warning(f"HuggingFace approach failed: {str(e)[:200]}")
        logger.info("Falling back to SpeechBrain models...")
    
    # Fallback to SpeechBrain models
    models_to_try = [
        ("speechbrain/emotion-recognition-wav2vec2-IEMOCAP", "IEMOCAP emotion model"),
    ]
    
    last_error = None
    for model_source, description in models_to_try:
        try:
            logger.info(f"Attempting to load {description}: {model_source}")
            model = EncoderClassifier.from_hparams(
                source=model_source,
                savedir=cache_dir,
                run_opts={"device": "cpu"}
            )
            _MODEL_CACHE = model
            logger.info(f"Successfully loaded {model_source}")
            return model
        except Exception as e:
            logger.warning(f"Failed to load {model_source}: {str(e)[:200]}")
            last_error = e
            # Clean up failed attempt
            if Path(cache_dir).exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                Path(cache_dir).mkdir(parents=True, exist_ok=True)
            continue
    
    # All models failed - return None to trigger prosody fallback
    logger.error(f"All emotion models failed. Will use prosody fallback.")
    logger.error(f"Last error: {str(last_error)[:300]}")
    return None


def analyze_audio(audio_path: str, segment_duration: float = 3.0) -> Dict[str, Any]:
    """
    Analyze audio file and detect emotions using SpeechBrain.
    
    Args:
        audio_path: Path to audio file
        segment_duration: Length of each analysis window in seconds
        
    Returns:
        Dict with emotions list, dominant emotion, and inference mode
    """
    if not AUDIO_LIBS_AVAILABLE:
        raise RuntimeError("Audio libraries not available")
    
    # Load the model
    model = load_model()
    
    # If model is None, return error to trigger prosody fallback
    if model is None:
        return {
            "error": "SpeechBrain model unavailable, using prosody fallback",
            "inference_mode": "failed"
        }
    
    # Load audio file
    logger.info(f"Loading audio from {audio_path}")
    try:
        # Use librosa for better compatibility with various formats
        audio_array, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration = len(audio_array) / sr
        logger.info(f"Loaded audio: {duration:.2f}s at {sr}Hz")
    except Exception as e:
        logger.error(f"Failed to load audio: {e}")
        raise
    
    # Process in segments
    emotions = []
    step = segment_duration - 1.0  # 1 second overlap
    current_time = 0.0
    
    logger.info("Processing audio segments...")
    while current_time < duration:
        segment_end = min(current_time + segment_duration, duration)
        
        # Extract segment
        start_sample = int(current_time * sr)
        end_sample = int(segment_end * sr)
        segment_audio = audio_array[start_sample:end_sample]
        
        # Skip very short segments
        if len(segment_audio) < sr * 0.5:
            current_time += step
            continue
        
        # Detect emotion for this segment
        try:
            # Convert to tensor
            waveform = torch.tensor(segment_audio).unsqueeze(0).float()
            
            # Get prediction from model
            out_prob, score, index, text_lab = model.classify_batch(waveform)
            
            # Parse results
            label = text_lab[0] if isinstance(text_lab, list) else str(text_lab)
            confidence = float(score[0]) if hasattr(score, '__getitem__') else float(score)
            
            # Map to our emotion category
            emotion_key = label.lower()[:3]
            emotion = EMOTION_MAP.get(emotion_key, 'neutral')
            
            emotions.append({
                'emotion': emotion,
                'confidence': round(confidence, 3),
                'start': round(current_time, 2),
                'end': round(segment_end, 2)
            })
            
            logger.debug(f"Segment {current_time:.1f}-{segment_end:.1f}s: {emotion} ({confidence:.2f})")
            
        except Exception as e:
            logger.warning(f"Failed to process segment {current_time}-{segment_end}: {e}")
        
        current_time += step
    
    # Determine dominant emotion (most frequent)
    if emotions:
        emotion_counts = {}
        for e in emotions:
            emotion_counts[e['emotion']] = emotion_counts.get(e['emotion'], 0) + 1
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
    else:
        dominant_emotion = 'neutral'
    
    logger.info(f"Analysis complete: {len(emotions)} segments, dominant={dominant_emotion}")
    
    return {
        'emotions': emotions,
        'dominant_emotion': dominant_emotion,
        'inference_mode': 'speechbrain'
    }


def main():
    """Main entry point for the emotion service."""
    parser = argparse.ArgumentParser(
        description='Analyze audio emotions using SpeechBrain'
    )
    parser.add_argument(
        '--audio',
        required=True,
        help='Path to audio file to analyze'
    )
    parser.add_argument(
        '--segment-duration',
        type=float,
        default=3.0,
        help='Duration of each analysis segment in seconds (default: 3.0)'
    )
    
    args = parser.parse_args()
    
    # Validate audio file exists
    audio_path = Path(args.audio)
    if not audio_path.exists():
        error_result = {
            'error': f'Audio file not found: {args.audio}',
            'inference_mode': 'failed'
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
    
    try:
        # Analyze the audio
        result = analyze_audio(str(audio_path), args.segment_duration)
        
        # Output JSON to stdout
        print(json.dumps(result, indent=2))
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        error_result = {
            'error': str(e),
            'inference_mode': 'failed'
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()

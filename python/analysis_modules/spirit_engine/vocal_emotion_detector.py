"""
Stage Buddy V2 - Spirit Engine: Vocal Emotion Detector
Detects emotions from the performer's actual vocal delivery.

This module answers: "What emotions ARE being expressed in the audio?"
Combined with the ideal emotional arc from text analysis, this enables
emotion-word alignment scoring.

INFERENCE PRIORITY:
1. ONNX model (if available) - Zero dependency conflicts, fastest inference
2. SpeechBrain model (if available) - Full accuracy, may have conflicts
3. Prosody-based heuristics - Always available fallback
"""

from typing import List, Dict, Any, Optional
import numpy as np
import logging
import json
from pathlib import Path

# ONNX Runtime - conflict-free inference
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.info("onnxruntime not installed. Install with: pip install onnxruntime")

# SpeechBrain - may have dependency conflicts
try:
    from speechbrain.inference.interfaces import foreign_class
    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    try:
        from speechbrain.pretrained.interfaces import foreign_class
        SPEECHBRAIN_AVAILABLE = True
    except ImportError:
        SPEECHBRAIN_AVAILABLE = False
        logging.warning("speechbrain not installed. Install with: pip install speechbrain")

try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from ..shared.data_structures import (
    EmotionCategory, EmotionSegment, ProsodyFeatures
)

logger = logging.getLogger(__name__)

# Paths for ONNX model
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
ONNX_MODEL_PATH = MODELS_DIR / "emotion_model.onnx"
ONNX_METADATA_PATH = MODELS_DIR / "emotion_model_metadata.json"

# SpeechBrain IEMOCAP model outputs these emotions
SPEECHBRAIN_EMOTION_MAP = {
    'neu': EmotionCategory.NEUTRAL,
    'hap': EmotionCategory.HAPPY,
    'sad': EmotionCategory.SAD,
    'ang': EmotionCategory.ANGRY,
    # Extended mappings for other models
    'fea': EmotionCategory.FEARFUL,
    'sur': EmotionCategory.SURPRISED,
    'dis': EmotionCategory.DISGUSTED,
    'exc': EmotionCategory.EXCITED,
    'fru': EmotionCategory.ANGRY,  # Frustration maps to angry
}

# ONNX model emotion labels (from IEMOCAP)
ONNX_EMOTION_LABELS = ['neu', 'hap', 'sad', 'ang']

# Valence-Arousal from prosodic features
# These thresholds help infer emotion from prosody when ML fails
PROSODY_THRESHOLDS = {
    'high_pitch_var': 30.0,    # Hz variance threshold for "animated" speech
    'low_pitch_var': 10.0,     # Below this = monotone
    'high_loudness_var': 10.0,  # dB variance for dynamic delivery
    'fast_speech': 4.5,        # syllables/sec
    'slow_speech': 2.5,        # syllables/sec
}


class VocalEmotionDetector:
    """
    Detects emotions from vocal audio using deep learning models.

    Inference priority:
    1. ONNX model (if available at python/models/emotion_model.onnx)
    2. SpeechBrain's wav2vec2-based emotion recognition (if available)
    3. Prosody-based heuristics (always available fallback)
    """

    def __init__(
        self,
        model_source: str = "speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        device: str = "auto",
        sample_rate: int = 16000,
        prefer_onnx: bool = True
    ):
        """
        Initialize the vocal emotion detector.

        Args:
            model_source: HuggingFace model path for emotion recognition
            device: "auto", "cpu", or "cuda"
            sample_rate: Expected audio sample rate
            prefer_onnx: If True, prefer ONNX model over SpeechBrain
        """
        self.model_source = model_source
        self.sample_rate = sample_rate
        self.prefer_onnx = prefer_onnx

        # Initialize model references
        self.onnx_session = None
        self.onnx_metadata = None
        self.classifier = None
        self.inference_mode = None

        if device == "auto":
            self.device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Try to load models in priority order
        self._initialize_models()

    def _initialize_models(self):
        """Initialize models in priority order: ONNX > SpeechBrain > Prosody."""

        # 1. Try ONNX first (if preferred and available)
        if self.prefer_onnx and ONNX_AVAILABLE:
            if self._load_onnx_model():
                self.inference_mode = "onnx"
                logger.info("Using ONNX model for emotion detection (zero conflicts)")
                return

        # 2. Try SpeechBrain
        if SPEECHBRAIN_AVAILABLE:
            if self._load_speechbrain_model():
                self.inference_mode = "speechbrain"
                logger.info(f"Using SpeechBrain model on {self.device}")
                return

        # 3. Fall back to prosody
        self.inference_mode = "prosody"
        logger.warning("Using prosody-based fallback for emotion detection")
        logger.warning("For better accuracy, run: python scripts/export_emotion_model.py")

    def _load_onnx_model(self) -> bool:
        """Load the ONNX emotion model if available."""
        if not ONNX_MODEL_PATH.exists():
            logger.info(f"ONNX model not found at: {ONNX_MODEL_PATH}")
            logger.info("To create it, run: python scripts/export_emotion_model.py")
            return False

        try:
            # Load metadata
            if ONNX_METADATA_PATH.exists():
                with open(ONNX_METADATA_PATH, 'r') as f:
                    self.onnx_metadata = json.load(f)
            else:
                # Default metadata
                self.onnx_metadata = {
                    "emotion_labels": ONNX_EMOTION_LABELS,
                    "sample_rate": 16000,
                    "input_name": "audio",
                    "output_name": "emotion_probs"
                }

            # Create ONNX session
            # Use CPU provider for maximum compatibility
            providers = ['CPUExecutionProvider']
            if self.device == "cuda":
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

            self.onnx_session = ort.InferenceSession(
                str(ONNX_MODEL_PATH),
                providers=providers
            )

            logger.info(f"Loaded ONNX emotion model from: {ONNX_MODEL_PATH}")
            return True

        except Exception as e:
            logger.warning(f"Failed to load ONNX model: {e}")
            return False

    def _load_speechbrain_model(self) -> bool:
        """Load the SpeechBrain emotion model."""
        try:
            self.classifier = foreign_class(
                source=self.model_source,
                pymodule_file="custom_interface.py",
                classname="CustomEncoderWav2vec2Classifier",
                run_opts={"device": self.device}
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to load SpeechBrain model: {e}")
            return False

    def detect_emotions_from_file(
        self,
        audio_path: str,
        segment_duration: float = 3.0,
        overlap: float = 1.0
    ) -> List[EmotionSegment]:
        """
        Detect emotions from an audio file.

        Args:
            audio_path: Path to audio file
            segment_duration: Length of each analysis window
            overlap: Overlap between windows

        Returns:
            List of EmotionSegment with detected vocal emotions
        """
        # Load audio - prefer librosa for better compatibility
        if LIBROSA_AVAILABLE:
            audio_array, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        elif TORCH_AVAILABLE:
            try:
                waveform, sr = torchaudio.load(audio_path)
                if sr != self.sample_rate:
                    resampler = torchaudio.transforms.Resample(sr, self.sample_rate)
                    waveform = resampler(waveform)
                # Convert to mono if stereo
                if waveform.shape[0] > 1:
                    waveform = waveform.mean(dim=0, keepdim=True)
                audio_array = waveform.squeeze().numpy()
                sr = self.sample_rate
            except ImportError:
                # Fallback to librosa if torchaudio has issues
                audio_array, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        else:
            raise RuntimeError("Neither torch/torchaudio nor librosa available")

        duration = len(audio_array) / sr

        # Process in segments
        emotions = []
        step = segment_duration - overlap
        current_time = 0.0

        while current_time < duration:
            segment_end = min(current_time + segment_duration, duration)

            # Extract segment
            start_sample = int(current_time * sr)
            end_sample = int(segment_end * sr)
            segment_audio = audio_array[start_sample:end_sample]

            if len(segment_audio) < sr * 0.5:  # Skip very short segments
                current_time += step
                continue

            # Detect emotion
            emotion_result = self._detect_segment_emotion(segment_audio, sr)

            emotions.append(EmotionSegment(
                emotion=emotion_result['emotion'],
                intensity=emotion_result['intensity'],
                valence=emotion_result['valence'],
                arousal=emotion_result['arousal'],
                start_time=current_time,
                end_time=segment_end,
                confidence=emotion_result['confidence'],
                source="vocal"
            ))

            current_time += step

        return emotions

    def _detect_segment_emotion(
        self,
        audio_segment: np.ndarray,
        sample_rate: int
    ) -> Dict[str, Any]:
        """Detect emotion for a single audio segment using the best available method."""

        if self.inference_mode == "onnx":
            return self._detect_with_onnx(audio_segment, sample_rate)
        elif self.inference_mode == "speechbrain":
            return self._detect_with_speechbrain(audio_segment, sample_rate)
        else:
            return self._detect_with_prosody(audio_segment, sample_rate)

    def _detect_with_onnx(
        self,
        audio_segment: np.ndarray,
        sample_rate: int
    ) -> Dict[str, Any]:
        """Use ONNX model for emotion detection."""
        try:
            # Prepare input
            audio_input = audio_segment.astype(np.float32).reshape(1, -1)

            # Get input/output names from metadata
            input_name = self.onnx_metadata.get("input_name", "audio")

            # Run inference
            outputs = self.onnx_session.run(None, {input_name: audio_input})
            probs = outputs[0]

            # Get prediction
            emotion_idx = int(np.argmax(probs))
            confidence = float(probs[0, emotion_idx])

            # Map to emotion category
            emotion_labels = self.onnx_metadata.get("emotion_labels", ONNX_EMOTION_LABELS)
            label = emotion_labels[emotion_idx]
            emotion = SPEECHBRAIN_EMOTION_MAP.get(label, EmotionCategory.NEUTRAL)

            # Get valence-arousal
            from ..shared.data_structures import EMOTION_VA_MAP
            valence, arousal = EMOTION_VA_MAP.get(emotion, (0.0, 0.5))

            # Calculate intensity from probability distribution
            # Higher confidence + more distinct prediction = higher intensity
            prob_std = float(np.std(probs))
            intensity = min(1.0, confidence * (1.0 + prob_std))

            return {
                'emotion': emotion,
                'intensity': intensity,
                'valence': valence,
                'arousal': arousal,
                'confidence': confidence,
                'raw_label': label,
                'inference_mode': 'onnx'
            }

        except Exception as e:
            logger.warning(f"ONNX inference failed: {e}, falling back to prosody")
            return self._detect_with_prosody(audio_segment, sample_rate)

    def _detect_with_speechbrain(
        self,
        audio_segment: np.ndarray,
        sample_rate: int
    ) -> Dict[str, Any]:
        """Use SpeechBrain model for emotion detection."""
        try:
            # Convert to tensor
            waveform = torch.tensor(audio_segment).unsqueeze(0).float()

            # Get prediction
            out_prob, score, index, text_lab = self.classifier.classify_batch(waveform)

            # Parse result
            label = text_lab[0] if isinstance(text_lab, list) else str(text_lab)
            confidence = float(score[0]) if hasattr(score, '__getitem__') else float(score)

            # Map to our emotion category
            emotion = SPEECHBRAIN_EMOTION_MAP.get(label.lower()[:3], EmotionCategory.NEUTRAL)

            # Get valence-arousal
            from ..shared.data_structures import EMOTION_VA_MAP
            valence, arousal = EMOTION_VA_MAP.get(emotion, (0.0, 0.5))

            return {
                'emotion': emotion,
                'intensity': min(1.0, confidence * 1.2),
                'valence': valence,
                'arousal': arousal,
                'confidence': confidence,
                'raw_label': label,
                'inference_mode': 'speechbrain'
            }

        except Exception as e:
            logger.warning(f"SpeechBrain inference failed: {e}, using prosody fallback")
            return self._detect_with_prosody(audio_segment, sample_rate)

    def _detect_with_prosody(
        self,
        audio_segment: np.ndarray,
        sample_rate: int
    ) -> Dict[str, Any]:
        """
        Fallback emotion detection using prosodic features.

        Maps prosody patterns to emotions using established research:
        - High pitch + high variance = excited/happy
        - Low pitch + low variance = sad/neutral
        - High loudness variance = dynamic/emotional
        - Fast speech = excited/angry
        - Slow speech = sad/calm
        """
        if not LIBROSA_AVAILABLE:
            return self._default_emotion()

        # Extract basic prosody
        try:
            # Pitch
            f0, _, _ = librosa.pyin(
                audio_segment,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sample_rate
            )
            f0_clean = f0[~np.isnan(f0)] if f0 is not None else np.array([])

            # Loudness
            rms = librosa.feature.rms(y=audio_segment)[0]
            loudness_db = librosa.amplitude_to_db(rms, ref=np.max)

            # Speech rate estimate (using onset detection as proxy)
            onset_frames = librosa.onset.onset_detect(y=audio_segment, sr=sample_rate)
            duration = len(audio_segment) / sample_rate
            onset_rate = len(onset_frames) / duration if duration > 0 else 0

        except Exception as e:
            logger.warning(f"Prosody extraction failed: {e}")
            return self._default_emotion()

        # Calculate features
        pitch_mean = np.mean(f0_clean) if len(f0_clean) > 0 else 150.0
        pitch_var = np.var(f0_clean) if len(f0_clean) > 1 else 0.0
        loudness_var = np.var(loudness_db) if len(loudness_db) > 1 else 0.0

        # Map to emotion using heuristics
        emotion, valence, arousal = self._prosody_to_emotion(
            pitch_mean, pitch_var, loudness_var, onset_rate
        )

        # Confidence based on signal quality
        voiced_ratio = len(f0_clean) / len(f0) if len(f0) > 0 else 0
        confidence = min(0.7, 0.3 + voiced_ratio * 0.5)  # Cap at 0.7 for heuristic method

        return {
            'emotion': emotion,
            'intensity': arousal,  # Use arousal as intensity
            'valence': valence,
            'arousal': arousal,
            'confidence': confidence,
            'raw_label': 'prosody_inferred',
            'inference_mode': 'prosody'
        }

    def _prosody_to_emotion(
        self,
        pitch_mean: float,
        pitch_var: float,
        loudness_var: float,
        speech_rate: float
    ) -> tuple:
        """Map prosodic features to emotion, valence, arousal."""

        # Calculate arousal from variance/rate
        arousal = 0.3  # base
        if pitch_var > PROSODY_THRESHOLDS['high_pitch_var']:
            arousal += 0.3
        if loudness_var > PROSODY_THRESHOLDS['high_loudness_var']:
            arousal += 0.2
        if speech_rate > PROSODY_THRESHOLDS['fast_speech']:
            arousal += 0.2
        elif speech_rate < PROSODY_THRESHOLDS['slow_speech']:
            arousal -= 0.1
        arousal = np.clip(arousal, 0.1, 1.0)

        # Valence is harder to determine from prosody alone
        # Use pitch height as rough proxy (higher = more positive)
        pitch_z = (pitch_mean - 150) / 50  # Normalize around typical pitch
        valence = np.clip(pitch_z * 0.3, -0.5, 0.5)  # Conservative estimate

        # Determine emotion from VA quadrant
        if arousal > 0.6:
            if valence > 0.1:
                emotion = EmotionCategory.EXCITED if arousal > 0.8 else EmotionCategory.HAPPY
            else:
                emotion = EmotionCategory.ANGRY
        else:
            if valence > 0.1:
                emotion = EmotionCategory.CALM if arousal < 0.4 else EmotionCategory.HAPPY
            elif valence < -0.2:
                emotion = EmotionCategory.SAD
            else:
                emotion = EmotionCategory.NEUTRAL

        return emotion, valence, arousal

    def _default_emotion(self) -> Dict[str, Any]:
        """Return default neutral emotion when detection fails."""
        return {
            'emotion': EmotionCategory.NEUTRAL,
            'intensity': 0.3,
            'valence': 0.0,
            'arousal': 0.3,
            'confidence': 0.3,
            'raw_label': 'default',
            'inference_mode': 'fallback'
        }

    def detect_with_prosody_features(
        self,
        prosody_timeline: List[ProsodyFeatures],
        segment_duration: float = 3.0
    ) -> List[EmotionSegment]:
        """
        Detect emotions using pre-extracted prosody features.

        This method is useful when openSMILE features have already been
        extracted - it reuses them instead of re-analyzing the audio.

        Args:
            prosody_timeline: List of ProsodyFeatures from OpenSMILE
            segment_duration: Duration for each emotion segment

        Returns:
            List of EmotionSegment
        """
        if not prosody_timeline:
            return []

        emotions = []

        # Group prosody features into segments
        total_duration = prosody_timeline[-1].timestamp
        current_time = 0.0

        while current_time < total_duration:
            segment_end = min(current_time + segment_duration, total_duration)

            # Get features in this segment
            segment_features = [
                p for p in prosody_timeline
                if current_time <= p.timestamp < segment_end
            ]

            if segment_features:
                # Aggregate features
                pitches = [p.pitch_hz for p in segment_features if p.pitch_hz > 0]
                loudnesses = [p.loudness_db for p in segment_features]
                voicing = [p.voicing_probability for p in segment_features]

                pitch_mean = np.mean(pitches) if pitches else 150.0
                pitch_var = np.var(pitches) if len(pitches) > 1 else 0.0
                loudness_var = np.var(loudnesses) if len(loudnesses) > 1 else 0.0

                # Use average speech rate if available
                speech_rates = [p.speech_rate for p in segment_features if p.speech_rate > 0]
                speech_rate = np.mean(speech_rates) if speech_rates else 3.0

                # Map to emotion
                emotion, valence, arousal = self._prosody_to_emotion(
                    pitch_mean, pitch_var, loudness_var, speech_rate
                )

                # Confidence based on voicing
                voiced_ratio = np.mean([v > 0.5 for v in voicing]) if voicing else 0.5
                confidence = min(0.7, 0.3 + voiced_ratio * 0.4)

                emotions.append(EmotionSegment(
                    emotion=emotion,
                    intensity=arousal,
                    valence=valence,
                    arousal=arousal,
                    start_time=current_time,
                    end_time=segment_end,
                    confidence=confidence,
                    source="vocal"
                ))

            current_time += segment_duration

        return emotions

    def get_inference_mode(self) -> str:
        """Return the current inference mode being used."""
        return self.inference_mode or "unknown"


def detect_vocal_emotions(
    audio_path: str,
    segment_duration: float = 3.0,
    prefer_onnx: bool = True
) -> List[EmotionSegment]:
    """
    Convenience function to detect vocal emotions from audio file.

    Args:
        audio_path: Path to audio file
        segment_duration: Duration of each analysis segment
        prefer_onnx: If True, prefer ONNX model over SpeechBrain

    Returns:
        List of EmotionSegment with detected vocal emotions
    """
    detector = VocalEmotionDetector(prefer_onnx=prefer_onnx)
    return detector.detect_emotions_from_file(
        audio_path,
        segment_duration=segment_duration
    )

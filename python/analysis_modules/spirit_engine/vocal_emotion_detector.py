"""
Stage Buddy V2 - Spirit Engine: Vocal Emotion Detector
Detects emotions from the performer's actual vocal delivery.

This module answers: "What emotions ARE being expressed in the audio?"
Combined with the ideal emotional arc from text analysis, this enables
emotion-word alignment scoring.
"""

from typing import List, Dict, Any, Optional
import os
import numpy as np
import logging
import warnings

# DO NOT import speechbrain at module level - it has torchaudio dependencies
# that fail at import time. Import it lazily when needed.
SPEECHBRAIN_AVAILABLE = None  # Will be determined on first use

# Suppress transformer/HuggingFace warnings BEFORE imports
# These must be set before transformers/speechbrain are imported
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def _resolve_hf_token() -> str | None:
    """Resolve HuggingFace token from environment with validation."""
    token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
    if not token:
        logging.warning(
            "No HF_TOKEN found in environment. Model downloads may be rate-limited. "
            "Set HF_TOKEN in .env.local for authenticated HuggingFace Hub access."
        )
        return None
    token = token.strip()
    if not token.startswith('hf_'):
        logging.warning(
            "HF_TOKEN does not start with 'hf_' — this may not be a valid "
            "HuggingFace token. Proceeding anyway."
        )
    # Ensure it's available to child processes / other libs that read os.environ
    os.environ['HF_TOKEN'] = token
    logging.info("HuggingFace token configured for authenticated requests")
    return token


HF_TOKEN = _resolve_hf_token()

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import torchaudio

    # COMPATIBILITY SHIM: Add list_audio_backends if missing (removed in torchaudio 2.1+)
    # SpeechBrain internally calls this function, but it was deprecated/removed.
    # We add a stub that returns appropriate backends based on what's available.
    if not hasattr(torchaudio, 'list_audio_backends'):
        def _list_audio_backends():
            """Compatibility shim for deprecated torchaudio.list_audio_backends()"""
            # In torchaudio 2.0+, backends are handled differently
            # Return the backends that are actually available and working
            available = []

            # Check soundfile (libsndfile) - most reliable cross-platform
            try:
                import soundfile as sf
                # Verify it can actually read audio
                if hasattr(sf, 'read'):
                    available.append('soundfile')
            except ImportError:
                pass

            # Check librosa - good fallback
            try:
                import librosa
                if hasattr(librosa, 'load'):
                    available.append('librosa')
            except ImportError:
                pass

            # Check scipy.io.wavfile
            try:
                from scipy.io import wavfile
                available.append('scipy')
            except ImportError:
                pass

            # Check sox_io (Linux)
            try:
                import sox
                available.append('sox_io')
            except ImportError:
                pass

            # ffmpeg is usually available as system tool
            import shutil
            if shutil.which('ffmpeg'):
                available.append('ffmpeg')

            # Return what we found, or default to soundfile (most common)
            return available if available else ['soundfile']

        torchaudio.list_audio_backends = _list_audio_backends
        logging.debug("Added torchaudio.list_audio_backends compatibility shim")

    # For torchaudio 2.0+, try to configure a working backend
    # Priority: soundfile > sox_io > ffmpeg
    try:
        import soundfile
        if hasattr(torchaudio, 'set_audio_backend'):
            try:
                torchaudio.set_audio_backend('soundfile')
                logging.debug("Set torchaudio backend to soundfile")
            except Exception:
                pass  # Backend selection is automatic in newer versions
    except ImportError:
        pass

    # Test basic loading capability
    _ = torchaudio.load  # Just check if the function exists
    TORCHAUDIO_AVAILABLE = True
except (ImportError, AttributeError) as e:
    # Handle both import errors and compatibility issues
    TORCHAUDIO_AVAILABLE = False
    if TORCH_AVAILABLE:
        logging.warning(f"torchaudio has compatibility issues: {e}")
        logging.warning("Will use librosa for audio loading instead")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from ..shared.data_structures import (
    EmotionCategory, EmotionSegment, ProsodyFeatures
)

logger = logging.getLogger(__name__)


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
    
    Primary method uses SpeechBrain's wav2vec2-based emotion recognition
    trained on IEMOCAP dataset. Falls back to prosody-based heuristics
    if the model is unavailable.
    """
    
    def __init__(
        self,
        model_source: str = "speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        device: str = "auto",
        sample_rate: int = 16000
    ):
        """
        Initialize the vocal emotion detector.
        
        Args:
            model_source: HuggingFace model path for emotion recognition
            device: "auto", "cpu", or "cuda"
            sample_rate: Expected audio sample rate
        """
        self.model_source = model_source
        self.sample_rate = sample_rate
        self.classifier = None
        
        if device == "auto":
            self.device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Try to load SpeechBrain model (lazy import to avoid import-time errors)
        if TORCH_AVAILABLE:
            try:
                # Suppress SpeechBrain and HuggingFace warnings during model loading
                # The UNEXPECTED warnings for position_ids and wav2vec2 params are harmless
                # These warnings occur because models were saved with different architectures
                with warnings.catch_warnings():
                    # General warning categories
                    warnings.filterwarnings("ignore", category=UserWarning)
                    warnings.filterwarnings("ignore", category=FutureWarning)
                    warnings.filterwarnings("ignore", category=DeprecationWarning)

                    # Specific UNEXPECTED parameter warnings from safetensors/model loading
                    warnings.filterwarnings("ignore", message=".*UNEXPECTED.*")
                    warnings.filterwarnings("ignore", message=".*unexpected.*")

                    # Roberta position_ids warning (cosmetic, model works fine)
                    warnings.filterwarnings("ignore", message=".*position_ids.*")
                    warnings.filterwarnings("ignore", message=".*roberta.*embeddings.*")

                    # Wav2Vec2 parameter mismatches (7 parameters, all harmless)
                    warnings.filterwarnings("ignore", message=".*wav2vec2.*")
                    warnings.filterwarnings("ignore", message=".*Wav2Vec2.*")
                    warnings.filterwarnings("ignore", message=".*encoder\\.layers.*")
                    warnings.filterwarnings("ignore", message=".*feature_extractor.*")
                    warnings.filterwarnings("ignore", message=".*masked_spec_embed.*")

                    # Audio backend warnings
                    warnings.filterwarnings("ignore", message=".*audio backend.*")
                    warnings.filterwarnings("ignore", message=".*torchaudio.*")

                    # Import speechbrain only when needed (deferred import)
                    try:
                        from speechbrain.inference.interfaces import foreign_class
                    except ImportError:
                        from speechbrain.pretrained.interfaces import foreign_class

                    # Configure run options with proper settings
                    run_opts = {
                        "device": self.device,
                    }

                    # Add HF token if available for authenticated downloads
                    if HF_TOKEN:
                        run_opts["use_auth_token"] = HF_TOKEN

                    self.classifier = foreign_class(
                        source=model_source,
                        pymodule_file="custom_interface.py",
                        classname="CustomEncoderWav2vec2Classifier",
                        run_opts=run_opts
                    )

                    # The IEMOCAP model uses 4 emotion categories: neu, hap, sad, ang
                    # Ensure the encoder is properly configured (if accessible)
                    if hasattr(self.classifier, 'mods') and hasattr(self.classifier.mods, 'label_encoder'):
                        encoder = self.classifier.mods.label_encoder
                        if hasattr(encoder, 'expect_len'):
                            try:
                                encoder.expect_len(4)  # 4 emotion categories
                                logger.debug("CategoricalEncoder configured for 4 emotion categories")
                            except Exception:
                                pass  # Encoder may already be configured

                logger.info(f"Loaded SpeechBrain emotion model on {self.device}")
            except (ImportError, AttributeError) as e:
                # Handle import errors and compatibility issues (like torchaudio.list_audio_backends)
                logger.warning(f"Could not load SpeechBrain: {e}")
                logger.warning("Using prosody-based emotion detection fallback")
                self.classifier = None
            except Exception as e:
                err_str = str(e)
                # Surface actionable auth / network errors clearly
                if '403' in err_str or 'Forbidden' in err_str:
                    logger.error(
                        "SpeechBrain model download returned 403 Forbidden. "
                        "Your HF_TOKEN may be invalid or lack 'read' permissions. "
                        "Verify at https://huggingface.co/settings/tokens"
                    )
                elif '401' in err_str or 'Unauthorized' in err_str:
                    logger.error(
                        "SpeechBrain model download returned 401 Unauthorized. "
                        "Set a valid HF_TOKEN in .env.local."
                    )
                else:
                    logger.warning(f"Failed to load SpeechBrain model: {e}")
                logger.warning("Using prosody-based fallback")
                self.classifier = None
        else:
            logger.warning("PyTorch not available - using prosody-based fallback")
            self.classifier = None
    
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
        elif TORCHAUDIO_AVAILABLE and TORCH_AVAILABLE:
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
            except Exception as e:
                # Fallback to librosa if torchaudio has any issues
                logger.warning(f"torchaudio loading failed: {e}, using librosa fallback")
                if LIBROSA_AVAILABLE:
                    audio_array, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
                else:
                    raise RuntimeError(f"Audio loading failed: {e}")
        else:
            raise RuntimeError("Neither torch/torchaudio nor librosa available for audio loading")
        
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
        """Detect emotion for a single audio segment."""
        
        if self.classifier is not None:
            return self._detect_with_speechbrain(audio_segment, sample_rate)
        else:
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
                'raw_label': label
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
            'raw_label': 'prosody_inferred'
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
            'raw_label': 'default'
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


def detect_vocal_emotions(
    audio_path: str,
    segment_duration: float = 3.0
) -> List[EmotionSegment]:
    """
    Convenience function to detect vocal emotions from audio file.
    
    Args:
        audio_path: Path to audio file
        segment_duration: Duration of each analysis segment
        
    Returns:
        List of EmotionSegment with detected vocal emotions
    """
    detector = VocalEmotionDetector()
    return detector.detect_emotions_from_file(
        audio_path,
        segment_duration=segment_duration
    )

"""
Stage Buddy V2 - Spirit Engine: OpenSMILE Feature Extractor
Extracts prosodic features (pitch, loudness, voice quality) from audio using openSMILE.
"""

import numpy as np
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

try:
    import opensmile
    OPENSMILE_AVAILABLE = True
except ImportError:
    OPENSMILE_AVAILABLE = False
    # Debug level: optional dependency, fallback is available
    logging.debug("opensmile not installed - using fallback feature extraction")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    # Debug level: optional dependency, numpy fallback is available
    logging.debug("librosa not installed - using numpy-based feature extraction")

from ..shared.data_structures import ProsodyFeatures

logger = logging.getLogger(__name__)


class OpenSMILEExtractor:
    """
    Extracts prosodic features from audio using openSMILE.
    
    Uses the eGeMAPS feature set which is specifically designed for
    voice research and affective computing.
    
    Features extracted:
    - Pitch (F0): fundamental frequency, variation
    - Loudness: dB level, dynamics
    - Voice quality: jitter, shimmer, voicing probability
    - Spectral: formants, spectral slope
    """
    
    def __init__(
        self,
        feature_set: str = "eGeMAPSv02",
        feature_level: str = "LowLevelDescriptors",
        sample_rate: int = 16000
    ):
        """
        Initialize the OpenSMILE extractor.
        
        Args:
            feature_set: OpenSMILE feature set to use. Options:
                - "eGeMAPSv02": Extended Geneva Minimalistic Acoustic Parameter Set (recommended)
                - "ComParE_2016": Full paralinguistics feature set (6000+ features)
                - "GeMAPSv01b": Original GeMAPS set
            feature_level: Granularity of features:
                - "LowLevelDescriptors": Per-frame features (what we want for timeline)
                - "Functionals": Summary statistics over whole file
            sample_rate: Expected sample rate of audio
        """
        self.feature_set_name = feature_set
        self.feature_level_name = feature_level
        self.sample_rate = sample_rate
        
        if OPENSMILE_AVAILABLE:
            self.smile = opensmile.Smile(
                feature_set=getattr(opensmile.FeatureSet, feature_set),
                feature_level=getattr(opensmile.FeatureLevel, feature_level),
            )
            self.feature_names = self.smile.feature_names
            logger.info(f"OpenSMILE initialized with {len(self.feature_names)} features")
        else:
            self.smile = None
            self.feature_names = []
            logger.info("OpenSMILE not available - using numpy-based feature extraction")
    
    def extract_features_from_file(self, audio_path: str) -> Dict[str, Any]:
        """
        Extract features from an audio file.
        
        Args:
            audio_path: Path to audio file (WAV recommended)
            
        Returns:
            Dictionary containing:
                - 'features_df': pandas DataFrame with features over time
                - 'timestamps': numpy array of frame timestamps
                - 'prosody_timeline': List[ProsodyFeatures] for easy consumption
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if self.smile is not None:
            return self._extract_with_opensmile(str(audio_path))
        else:
            return self._extract_fallback(str(audio_path))
    
    def _extract_with_opensmile(self, audio_path: str) -> Dict[str, Any]:
        """Extract features using openSMILE."""
        # Process the file
        features_df = self.smile.process_file(audio_path)
        
        # Get timestamps from the index
        if hasattr(features_df.index, 'get_level_values'):
            # Multi-index (file, start, end)
            starts = features_df.index.get_level_values('start').total_seconds().values
            ends = features_df.index.get_level_values('end').total_seconds().values
            timestamps = (starts + ends) / 2  # Center of each frame
        else:
            # Simple index - estimate timestamps from frame count
            n_frames = len(features_df)
            # Assume 10ms frame shift (standard for openSMILE)
            timestamps = np.arange(n_frames) * 0.01
        
        # Convert to our ProsodyFeatures format
        prosody_timeline = self._convert_to_prosody_features(features_df, timestamps)
        
        return {
            'features_df': features_df,
            'timestamps': timestamps,
            'prosody_timeline': prosody_timeline,
            'feature_names': list(features_df.columns)
        }
    
    def _convert_to_prosody_features(
        self, 
        features_df, 
        timestamps: np.ndarray
    ) -> List[ProsodyFeatures]:
        """Convert openSMILE DataFrame to list of ProsodyFeatures."""
        prosody_list = []
        
        # Map openSMILE feature names to our structure
        # eGeMAPS feature names (may vary slightly by version)
        pitch_col = self._find_column(features_df, ['F0semitoneFrom27.5Hz', 'F0final', 'pitch'])
        loudness_col = self._find_column(features_df, ['Loudness', 'loudness', 'pcm_loudness'])
        voicing_col = self._find_column(features_df, ['voicingFinalUnclipped', 'VoicingProbability'])
        jitter_col = self._find_column(features_df, ['jitterLocal', 'jitter'])
        shimmer_col = self._find_column(features_df, ['shimmerLocaldB', 'shimmer'])
        
        for i, ts in enumerate(timestamps):
            row = features_df.iloc[i]
            
            # Extract pitch (convert from semitones if needed)
            pitch_val = row[pitch_col] if pitch_col else 0.0
            if pitch_col and 'semitone' in pitch_col.lower():
                # Convert semitones from 27.5Hz to Hz
                pitch_val = 27.5 * (2 ** (pitch_val / 12)) if pitch_val > 0 else 0.0
            
            # Calculate local variance (using neighboring frames if available)
            pitch_var = self._calculate_local_variance(features_df, pitch_col, i) if pitch_col else 0.0
            loudness_var = self._calculate_local_variance(features_df, loudness_col, i) if loudness_col else 0.0
            
            prosody = ProsodyFeatures(
                timestamp=float(ts),
                pitch_hz=float(pitch_val) if pitch_val and not np.isnan(pitch_val) else 0.0,
                pitch_variance=float(pitch_var),
                loudness_db=float(row[loudness_col]) if loudness_col and not np.isnan(row[loudness_col]) else 0.0,
                loudness_variance=float(loudness_var),
                voicing_probability=float(row[voicing_col]) if voicing_col and not np.isnan(row[voicing_col]) else 0.0,
                jitter=float(row[jitter_col]) if jitter_col and not np.isnan(row[jitter_col]) else 0.0,
                shimmer=float(row[shimmer_col]) if shimmer_col and not np.isnan(row[shimmer_col]) else 0.0,
                speech_rate=0.0  # Will be calculated separately with transcript alignment
            )
            prosody_list.append(prosody)
        
        return prosody_list
    
    def _find_column(self, df, candidates: List[str]) -> Optional[str]:
        """Find the first matching column name from candidates."""
        for candidate in candidates:
            # Try exact match
            if candidate in df.columns:
                return candidate
            # Try case-insensitive partial match
            for col in df.columns:
                if candidate.lower() in col.lower():
                    return col
        return None
    
    def _calculate_local_variance(self, df, col: str, idx: int, window: int = 5) -> float:
        """Calculate variance in a local window around the index."""
        if col is None:
            return 0.0
        
        start_idx = max(0, idx - window)
        end_idx = min(len(df), idx + window + 1)
        values = df[col].iloc[start_idx:end_idx].values
        values = values[~np.isnan(values)]
        
        if len(values) < 2:
            return 0.0
        return float(np.var(values))
    
    def _extract_fallback(self, audio_path: str) -> Dict[str, Any]:
        """
        Fallback feature extraction using librosa when openSMILE is not available.
        Less accurate but functional for development/testing.
        """
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("Neither opensmile nor librosa available for feature extraction")

        logger.debug("Using librosa for feature extraction")
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=self.sample_rate)
        
        # Extract basic features
        # Frame parameters
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop
        
        # Pitch tracking
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, 
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            frame_length=frame_length,
            hop_length=hop_length
        )
        
        # Loudness (RMS energy in dB)
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        loudness_db = librosa.amplitude_to_db(rms, ref=np.max)
        
        # Timestamps
        n_frames = len(f0)
        timestamps = librosa.frames_to_time(
            np.arange(n_frames), 
            sr=sr, 
            hop_length=hop_length
        )
        
        # Convert to ProsodyFeatures
        prosody_list = []
        for i, ts in enumerate(timestamps):
            pitch_val = f0[i] if not np.isnan(f0[i]) else 0.0
            
            prosody = ProsodyFeatures(
                timestamp=float(ts),
                pitch_hz=float(pitch_val),
                pitch_variance=self._local_var(f0, i),
                loudness_db=float(loudness_db[i]) if i < len(loudness_db) else 0.0,
                loudness_variance=self._local_var(loudness_db, i),
                voicing_probability=float(voiced_probs[i]) if voiced_probs is not None and not np.isnan(voiced_probs[i]) else 0.0,
                jitter=0.0,  # Not available in librosa fallback
                shimmer=0.0,  # Not available in librosa fallback
                speech_rate=0.0
            )
            prosody_list.append(prosody)
        
        return {
            'features_df': None,  # No DataFrame in fallback mode
            'timestamps': timestamps,
            'prosody_timeline': prosody_list,
            'feature_names': ['pitch', 'loudness', 'voicing']
        }
    
    def _local_var(self, arr: np.ndarray, idx: int, window: int = 5) -> float:
        """Calculate local variance around an index."""
        start = max(0, idx - window)
        end = min(len(arr), idx + window + 1)
        values = arr[start:end]
        values = values[~np.isnan(values)]
        if len(values) < 2:
            return 0.0
        return float(np.var(values))
    
    def get_summary_statistics(self, prosody_timeline: List[ProsodyFeatures]) -> Dict[str, float]:
        """
        Calculate summary statistics from the prosody timeline.
        Useful for Spirit Engine scoring.
        """
        if not prosody_timeline:
            return {}
        
        pitches = [p.pitch_hz for p in prosody_timeline if p.pitch_hz > 0]
        loudnesses = [p.loudness_db for p in prosody_timeline]
        voicing = [p.voicing_probability for p in prosody_timeline]
        
        return {
            'pitch_mean': float(np.mean(pitches)) if pitches else 0.0,
            'pitch_std': float(np.std(pitches)) if pitches else 0.0,
            'pitch_range': float(np.ptp(pitches)) if pitches else 0.0,
            'pitch_min': float(np.min(pitches)) if pitches else 0.0,
            'pitch_max': float(np.max(pitches)) if pitches else 0.0,
            
            'loudness_mean': float(np.mean(loudnesses)),
            'loudness_std': float(np.std(loudnesses)),
            'loudness_range': float(np.ptp(loudnesses)),
            
            'voicing_ratio': float(np.mean([v > 0.5 for v in voicing])),  # % of voiced frames
            
            'total_frames': len(prosody_timeline),
            'duration_seconds': prosody_timeline[-1].timestamp if prosody_timeline else 0.0
        }


# Convenience function for quick extraction
def extract_prosody(audio_path: str) -> Dict[str, Any]:
    """
    Quick function to extract prosodic features from an audio file.
    
    Usage:
        result = extract_prosody("performance.wav")
        prosody_timeline = result['prosody_timeline']
        stats = result.get('summary', {})
    """
    extractor = OpenSMILEExtractor()
    result = extractor.extract_features_from_file(audio_path)
    result['summary'] = extractor.get_summary_statistics(result['prosody_timeline'])
    return result

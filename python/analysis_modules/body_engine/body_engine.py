"""
Stage Buddy V2 - Body Engine
Analyzes physical presence and intentionality through vocal-physical alignment proxies.

Core Scoring Components:
1. Gesture Intentionality (35%) - Proxy: prosody dynamics suggesting physical engagement
2. Stage Presence (30%) - Proxy: vocal energy and confidence markers
3. Eye Contact (20%) - Proxy: vocal directness and projection patterns
4. Physical-Vocal Alignment (15%) - Prosody consistency with emotional content

Note: Full implementation requires video analysis. Current version uses audio proxies
that correlate with physical intentionality in performance.
"""

from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import logging

from ..shared.data_structures import ProsodyFeatures, WordSegment, EmotionSegment
from ..spirit_engine.opensmile_extractor import OpenSMILEExtractor

logger = logging.getLogger(__name__)


@dataclass
class BodyAnalysisResult:
    """Results from Body engine analysis."""
    overall_score: float
    gesture_intentionality_score: float
    stage_presence_score: float
    eye_contact_score: float
    physical_vocal_alignment_score: float

    # Detailed metrics (proxies from audio)
    energy_variance: float
    dynamic_range: float
    vocal_confidence: float
    projection_consistency: float


class BodyEngine:
    """
    The Body Engine analyzes physical performance through vocal proxies.

    It evaluates:
    1. Gesture intentionality - Energy dynamics suggesting physical movement
    2. Stage presence - Vocal confidence and power
    3. Eye contact - Projection patterns and directness
    4. Physical-vocal alignment - Consistency of physical/vocal expression
    """

    def __init__(
        self,
        opensmile_feature_set: str = "eGeMAPSv02"
    ):
        """
        Initialize the Body Engine.

        Args:
            opensmile_feature_set: Feature set for prosody extraction
        """
        logger.info("Initializing Body Engine...")

        self.prosody_extractor = OpenSMILEExtractor(
            feature_set=opensmile_feature_set,
            feature_level="LowLevelDescriptors"
        )

        # Component weights per specification
        self.weights = {
            'gesture_intentionality': 0.35,
            'stage_presence': 0.30,
            'eye_contact': 0.20,
            'physical_vocal_alignment': 0.15
        }

        logger.info("Body Engine initialized (audio proxy mode)")

    def analyze(
        self,
        audio_path: str,
        word_segments: List[WordSegment],
        vocal_emotions: List[EmotionSegment] = None
    ) -> BodyAnalysisResult:
        """
        Perform complete Body analysis on a performance.

        Args:
            audio_path: Path to audio file
            word_segments: Word-level timing from transcription
            vocal_emotions: Emotion segments from Spirit engine (optional)

        Returns:
            BodyAnalysisResult with scores and detailed analysis
        """
        logger.info(f"Starting Body analysis for: {audio_path}")

        # Extract prosodic features
        logger.info("Extracting prosodic features...")
        prosody_result = self.prosody_extractor.extract_features_from_file(audio_path)
        prosody_timeline = prosody_result['prosody_timeline']
        prosody_summary = self.prosody_extractor.get_summary_statistics(prosody_timeline)

        # Calculate component scores
        gesture_score = self._calculate_gesture_intentionality(prosody_timeline, prosody_summary)
        presence_score = self._calculate_stage_presence(prosody_timeline, prosody_summary)
        eye_contact_score = self._calculate_eye_contact_proxy(prosody_timeline, prosody_summary)
        alignment_score = self._calculate_physical_vocal_alignment(
            prosody_timeline, vocal_emotions
        )

        # Calculate overall Body score
        component_scores = {
            'gesture_intentionality': gesture_score,
            'stage_presence': presence_score,
            'eye_contact': eye_contact_score,
            'physical_vocal_alignment': alignment_score
        }

        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Convert to 1-5 scale
        overall_score = self._normalize_to_5_scale(overall_normalized)

        logger.info(f"Body analysis complete. Score: {overall_score:.2f}/5")

        return BodyAnalysisResult(
            overall_score=overall_score,
            gesture_intentionality_score=gesture_score,
            stage_presence_score=presence_score,
            eye_contact_score=eye_contact_score,
            physical_vocal_alignment_score=alignment_score,
            energy_variance=self._calc_energy_variance(prosody_timeline),
            dynamic_range=prosody_summary.get('loudness_range', 0.0),
            vocal_confidence=np.mean([p.voicing_probability for p in prosody_timeline]),
            projection_consistency=self._calc_projection_consistency(prosody_timeline)
        )

    def _calculate_gesture_intentionality(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float]
    ) -> float:
        """
        Calculate gesture intentionality score (35% of Body).

        Proxy metrics:
        - Energy variance (gestures correlate with prosody dynamics)
        - Pitch-loudness coordination (physical gestures affect vocal dynamics)
        - Dynamic range (intentional gestures create vocal variety)
        """
        # Calculate energy variance over time
        energy_variance = self._calc_energy_variance(prosody_timeline)

        # Get pitch and loudness ranges
        pitch_range = prosody_summary.get('pitch_range', 0.0)
        loudness_range = prosody_summary.get('loudness_range', 0.0)

        # Energy variance score: higher variance suggests physical engagement
        variance_score = min(1.0, energy_variance / 0.15)

        # Dynamic range score: wide range suggests gestural support
        pitch_score = min(1.0, pitch_range / 150)  # 150Hz range is good
        loudness_score = min(1.0, loudness_range / 25)  # 25dB range is good
        range_score = (pitch_score + loudness_score) / 2

        # Coordination score: check if pitch and loudness move together
        coordination_score = self._calc_pitch_loudness_coordination(prosody_timeline)

        # Combine scores
        gesture_intentionality = (
            variance_score * 0.35 +
            range_score * 0.35 +
            coordination_score * 0.30
        )
        return gesture_intentionality

    def _calculate_stage_presence(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float]
    ) -> float:
        """
        Calculate stage presence score (30% of Body).

        Proxy metrics:
        - Vocal power (loudness)
        - Vocal confidence (voicing consistency)
        - Energy consistency (not fading)
        """
        loudness_mean = prosody_summary.get('loudness_mean', 0.0)

        # Get voicing and energy metrics
        voicing_probs = [p.voicing_probability for p in prosody_timeline]
        avg_voicing = np.mean(voicing_probs)

        # Power score: strong presence needs projection
        power_score = 1.0
        if loudness_mean < -35:
            power_score = 0.4  # Too quiet for stage presence
        elif loudness_mean < -28:
            power_score = 0.6  # Moderate
        elif loudness_mean < -22:
            power_score = 0.8  # Good
        elif loudness_mean <= -15:
            power_score = 1.0  # Strong presence
        else:
            power_score = 0.9  # Very strong

        # Confidence score: consistent voicing = confident delivery
        confidence_score = avg_voicing

        # Consistency score: presence doesn't fade
        consistency_score = self._calc_projection_consistency(prosody_timeline)

        # Combine scores
        stage_presence = (
            power_score * 0.4 +
            confidence_score * 0.3 +
            consistency_score * 0.3
        )
        return stage_presence

    def _calculate_eye_contact_proxy(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float]
    ) -> float:
        """
        Calculate eye contact proxy score (20% of Body).

        Proxy metrics:
        - Projection consistency (eye contact correlates with steady projection)
        - Vocal directness (clear articulation)
        - Engagement patterns (sustained energy)

        Note: This is a limited proxy. Video analysis would provide actual eye contact data.
        """
        # Projection consistency as proxy for sustained eye contact
        consistency_score = self._calc_projection_consistency(prosody_timeline)

        # Vocal clarity as proxy for directness (when looking at audience)
        voicing_quality = np.mean([p.voicing_probability for p in prosody_timeline])

        # Energy sustainability as engagement proxy
        energy_sustainability = self._calc_energy_sustainability(prosody_timeline)

        # Combine scores (weighted toward consistency)
        eye_contact_proxy = (
            consistency_score * 0.45 +
            voicing_quality * 0.30 +
            energy_sustainability * 0.25
        )
        return eye_contact_proxy

    def _calculate_physical_vocal_alignment(
        self,
        prosody_timeline: List[ProsodyFeatures],
        vocal_emotions: List[EmotionSegment] = None
    ) -> float:
        """
        Calculate physical-vocal alignment score (15% of Body).

        Measures consistency between vocal expression and implied physical commitment.
        When vocal emotions are strong, prosody should show matching dynamics.
        """
        if not vocal_emotions:
            # Without emotion data, use prosody consistency as proxy
            return self._calc_prosody_consistency(prosody_timeline)

        # Check if high-intensity emotions have matching prosody dynamics
        alignment_scores = []

        for emotion_seg in vocal_emotions:
            # Find prosody features in this time range
            matching_prosody = [
                p for p in prosody_timeline
                if emotion_seg.start_time <= p.timestamp <= emotion_seg.end_time
            ]

            if not matching_prosody:
                continue

            # High intensity emotions should have high prosody variance
            avg_loudness = np.mean([p.loudness_db for p in matching_prosody])
            avg_pitch_var = np.mean([p.pitch_variance for p in matching_prosody])

            # Score: intensity should correlate with vocal dynamics
            expected_dynamics = emotion_seg.intensity
            actual_dynamics = min(1.0, (avg_loudness + 40) / 25)  # Normalize loudness

            alignment = 1.0 - abs(expected_dynamics - actual_dynamics)
            alignment_scores.append(alignment)

        if alignment_scores:
            return np.mean(alignment_scores)
        else:
            return self._calc_prosody_consistency(prosody_timeline)

    def _calc_energy_variance(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate variance in vocal energy (proxy for physical engagement)."""
        energy_values = []
        for p in prosody_timeline:
            # Energy proxy: combination of loudness and pitch activity
            energy = (p.loudness_db + 40) / 40 + p.pitch_variance / 100
            energy_values.append(energy)

        if not energy_values:
            return 0.0
        return np.var(energy_values)

    def _calc_pitch_loudness_coordination(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate coordination between pitch and loudness (proxy for gestural support)."""
        if len(prosody_timeline) < 10:
            return 0.5

        pitch_values = [p.pitch_hz for p in prosody_timeline if p.pitch_hz > 0]
        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]

        if len(pitch_values) < 10 or len(loudness_values) < 10:
            return 0.5

        # Calculate correlation between pitch and loudness changes
        # Truncate to same length
        min_len = min(len(pitch_values), len(loudness_values))
        pitch_values = pitch_values[:min_len]
        loudness_values = loudness_values[:min_len]

        # Correlation coefficient
        if np.std(pitch_values) > 0 and np.std(loudness_values) > 0:
            correlation = np.corrcoef(pitch_values, loudness_values)[0, 1]
            # Convert correlation to 0-1 score (abs value, higher is better)
            return min(1.0, abs(correlation))
        else:
            return 0.5

    def _calc_projection_consistency(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate consistency of vocal projection."""
        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]
        if not loudness_values:
            return 0.5

        # Lower standard deviation = more consistent
        consistency = 1.0 - min(1.0, np.std(loudness_values) / 12.0)
        return consistency

    def _calc_energy_sustainability(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate sustainability of energy throughout performance."""
        if len(prosody_timeline) < 10:
            return 0.5

        # Divide into thirds and compare
        third = len(prosody_timeline) // 3

        first_third = prosody_timeline[:third]
        last_third = prosody_timeline[-third:]

        first_energy = np.mean([p.loudness_db for p in first_third if p.loudness_db > -100])
        last_energy = np.mean([p.loudness_db for p in last_third if p.loudness_db > -100])

        # Score: energy should not drop significantly
        if first_energy == 0:
            return 0.5

        energy_retention = last_energy / first_energy
        # Ideal: retain 90%+ of initial energy
        sustainability = min(1.0, max(0.0, energy_retention - 0.1) / 0.9)
        return sustainability

    def _calc_prosody_consistency(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate overall prosody consistency."""
        if not prosody_timeline:
            return 0.5

        voicing_probs = [p.voicing_probability for p in prosody_timeline]
        pitch_vars = [p.pitch_variance for p in prosody_timeline if p.pitch_variance > 0]

        voicing_consistency = np.mean(voicing_probs)
        pitch_consistency = 1.0 - min(1.0, np.std(pitch_vars) / 50) if pitch_vars else 0.5

        return (voicing_consistency + pitch_consistency) / 2

    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        score = max(0.0, min(1.0, score))
        return 1.0 + score * 4.0


def analyze_body(
    audio_path: str,
    word_segments: List[WordSegment],
    vocal_emotions: List[EmotionSegment] = None
) -> BodyAnalysisResult:
    """
    Convenience function for Body analysis.

    Args:
        audio_path: Path to audio file
        word_segments: Word-level timing information
        vocal_emotions: Emotion segments (optional)

    Returns:
        BodyAnalysisResult with complete analysis
    """
    engine = BodyEngine()
    return engine.analyze(audio_path, word_segments, vocal_emotions)

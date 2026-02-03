"""
Stage Buddy V2 - Chest Engine
Analyzes vocal technique: breath control, projection, pacing, and vocal health.

Core Scoring Components:
1. Breath Control (30%) - Phrase management and breath efficiency
2. Projection (30%) - Vocal volume and consistency
3. Pacing Technique (20%) - Strategic speed/tempo variation
4. Vocal Health (20%) - Voice quality and strain indicators
"""

from typing import List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import logging

from ..shared.data_structures import ProsodyFeatures, WordSegment
from ..spirit_engine.opensmile_extractor import OpenSMILEExtractor

logger = logging.getLogger(__name__)


@dataclass
class ChestAnalysisResult:
    """Results from Chest engine analysis."""
    overall_score: float
    breath_control_score: float
    projection_score: float
    pacing_score: float
    vocal_health_score: float

    # Detailed metrics
    avg_phrase_length: float
    phrase_length_variance: float
    avg_loudness: float
    loudness_range: float
    loudness_stability: float
    speech_rate_mean: float
    speech_rate_variance: float
    avg_jitter: float
    avg_shimmer: float
    voicing_consistency: float


class ChestEngine:
    """
    The Chest Engine analyzes vocal technique and breath support.

    It evaluates:
    1. Breath control - How well the performer manages phrases
    2. Projection - Vocal volume and power
    3. Pacing - Strategic use of speed variation
    4. Vocal health - Voice quality indicators
    """

    def __init__(
        self,
        opensmile_feature_set: str = "eGeMAPSv02"
    ):
        """
        Initialize the Chest Engine.

        Args:
            opensmile_feature_set: Feature set for prosody extraction
        """
        logger.info("Initializing Chest Engine...")

        self.prosody_extractor = OpenSMILEExtractor(
            feature_set=opensmile_feature_set,
            feature_level="LowLevelDescriptors"
        )

        # Component weights per specification
        self.weights = {
            'breath_control': 0.30,
            'projection': 0.30,
            'pacing': 0.20,
            'vocal_health': 0.20
        }

        logger.info("Chest Engine initialized")

    def analyze(
        self,
        audio_path: str,
        word_segments: List[WordSegment]
    ) -> ChestAnalysisResult:
        """
        Perform complete Chest analysis on a performance.

        Args:
            audio_path: Path to audio file
            word_segments: Word-level timing from transcription

        Returns:
            ChestAnalysisResult with scores and detailed analysis
        """
        logger.info(f"Starting Chest analysis for: {audio_path}")

        # Extract prosodic features
        logger.info("Extracting prosodic features...")
        prosody_result = self.prosody_extractor.extract_features_from_file(audio_path)
        prosody_timeline = prosody_result['prosody_timeline']
        prosody_summary = self.prosody_extractor.get_summary_statistics(prosody_timeline)

        # Calculate component scores
        breath_control_score = self._calculate_breath_control(word_segments, prosody_timeline)
        projection_score = self._calculate_projection(prosody_summary, prosody_timeline)
        pacing_score = self._calculate_pacing(prosody_summary, prosody_timeline)
        vocal_health_score = self._calculate_vocal_health(prosody_timeline)

        # Calculate overall Chest score
        component_scores = {
            'breath_control': breath_control_score,
            'projection': projection_score,
            'pacing': pacing_score,
            'vocal_health': vocal_health_score
        }

        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Convert to 1-5 scale
        overall_score = self._normalize_to_5_scale(overall_normalized)

        logger.info(f"Chest analysis complete. Score: {overall_score:.2f}/5")

        return ChestAnalysisResult(
            overall_score=overall_score,
            breath_control_score=breath_control_score,
            projection_score=projection_score,
            pacing_score=pacing_score,
            vocal_health_score=vocal_health_score,
            avg_phrase_length=self._calc_avg_phrase_length(word_segments),
            phrase_length_variance=self._calc_phrase_variance(word_segments),
            avg_loudness=prosody_summary.get('loudness_mean', 0.0),
            loudness_range=prosody_summary.get('loudness_range', 0.0),
            loudness_stability=self._calc_loudness_stability(prosody_timeline),
            speech_rate_mean=prosody_summary.get('speech_rate_mean', 0.0),
            speech_rate_variance=prosody_summary.get('speech_rate_var', 0.0),
            avg_jitter=np.mean([p.jitter for p in prosody_timeline if p.jitter > 0]),
            avg_shimmer=np.mean([p.shimmer for p in prosody_timeline if p.shimmer > 0]),
            voicing_consistency=np.mean([p.voicing_probability for p in prosody_timeline])
        )

    def _calculate_breath_control(
        self,
        word_segments: List[WordSegment],
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate breath control score (30% of Chest).

        Evaluates:
        - Phrase length management (too short = choppy, too long = running out)
        - Consistency of phrase lengths
        - Pauses at appropriate moments
        """
        if not word_segments:
            return 0.5

        # Detect phrases (groups of words between pauses > 0.3s)
        phrases = []
        current_phrase = []

        for i, word in enumerate(word_segments):
            current_phrase.append(word)

            # Check if next word has a significant gap
            if i < len(word_segments) - 1:
                gap = word_segments[i + 1].start_time - word.end_time
                if gap > 0.3:  # Significant pause
                    phrases.append(current_phrase)
                    current_phrase = []
            else:
                phrases.append(current_phrase)

        if not phrases:
            return 0.5

        # Calculate phrase lengths in seconds
        phrase_lengths = []
        for phrase in phrases:
            if phrase:
                duration = phrase[-1].end_time - phrase[0].start_time
                phrase_lengths.append(duration)

        avg_phrase_length = np.mean(phrase_lengths)
        phrase_variance = np.std(phrase_lengths)

        # Scoring: ideal phrase length is 4-8 seconds
        # Too short (<3s) or too long (>10s) indicates breath issues
        length_score = 1.0
        if avg_phrase_length < 3.0:
            length_score = 0.6  # Too choppy
        elif avg_phrase_length < 4.0:
            length_score = 0.8  # A bit short
        elif avg_phrase_length <= 8.0:
            length_score = 1.0  # Ideal range
        elif avg_phrase_length <= 10.0:
            length_score = 0.9  # Slightly long
        else:
            length_score = 0.5  # Running out of breath

        # Consistency score: moderate variance is good (shows intentional variation)
        # Too low variance = monotonous, too high = inconsistent
        consistency_score = 1.0
        if phrase_variance < 0.5:
            consistency_score = 0.7  # Too uniform
        elif phrase_variance <= 2.0:
            consistency_score = 1.0  # Good variation
        else:
            consistency_score = 0.6  # Too erratic

        # Combine scores
        breath_control = (length_score * 0.6 + consistency_score * 0.4)
        return breath_control

    def _calculate_projection(
        self,
        prosody_summary: Dict[str, float],
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate projection score (30% of Chest).

        Evaluates:
        - Average loudness level
        - Loudness consistency (not fading in/out)
        - Dynamic range (ability to vary volume intentionally)
        """
        loudness_mean = prosody_summary.get('loudness_mean', 0.0)
        loudness_range = prosody_summary.get('loudness_range', 0.0)

        # Get loudness values over time
        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]

        if not loudness_values:
            return 0.5

        # Average loudness score: higher is better (within reason)
        # Typical speech loudness is -30dB to -10dB (in dBFS)
        # Stage projection should be -25dB to -15dB
        loudness_score = 1.0
        if loudness_mean < -35:
            loudness_score = 0.4  # Too quiet
        elif loudness_mean < -30:
            loudness_score = 0.6  # Quiet
        elif loudness_mean < -25:
            loudness_score = 0.8  # Moderate
        elif loudness_mean <= -15:
            loudness_score = 1.0  # Strong projection
        else:
            loudness_score = 0.9  # Very loud (might be overdoing it)

        # Consistency score: check for fades or drops
        # Calculate variance across the performance
        loudness_stability = 1.0 - min(1.0, np.std(loudness_values) / 10.0)

        # Dynamic range score: should have some variation (not monotone)
        # But not too much (inconsistent projection)
        range_score = 1.0
        if loudness_range < 5:
            range_score = 0.6  # Too flat
        elif loudness_range < 10:
            range_score = 0.8  # Limited range
        elif loudness_range <= 20:
            range_score = 1.0  # Good dynamic control
        elif loudness_range <= 30:
            range_score = 0.9  # Wide range
        else:
            range_score = 0.7  # Too much variation

        # Combine scores
        projection = (
            loudness_score * 0.4 +
            loudness_stability * 0.3 +
            range_score * 0.3
        )
        return projection

    def _calculate_pacing(
        self,
        prosody_summary: Dict[str, float],
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate pacing technique score (20% of Chest).

        Evaluates:
        - Speech rate variation (intentional speed changes)
        - Average pace (not too fast or slow)
        - Strategic use of tempo
        """
        speech_rate_mean = prosody_summary.get('speech_rate_mean', 0.0)
        speech_rate_var = prosody_summary.get('speech_rate_var', 0.0)

        if speech_rate_mean == 0:
            return 0.5

        # Average pace score: ideal is 120-180 words per minute
        # Which translates to roughly 2-3 syllables per second
        pace_score = 1.0
        if speech_rate_mean < 1.5:
            pace_score = 0.6  # Too slow
        elif speech_rate_mean < 2.0:
            pace_score = 0.9  # Slightly slow
        elif speech_rate_mean <= 3.0:
            pace_score = 1.0  # Ideal range
        elif speech_rate_mean <= 3.5:
            pace_score = 0.9  # Slightly fast
        else:
            pace_score = 0.6  # Too fast

        # Variation score: good performers vary their pace
        # Low variance = monotonous, high variance = dynamic
        variation_score = min(1.0, speech_rate_var / 0.5)

        # Combine scores
        pacing = (pace_score * 0.6 + variation_score * 0.4)
        return pacing

    def _calculate_vocal_health(
        self,
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate vocal health score (20% of Chest).

        Evaluates:
        - Jitter (pitch perturbation - lower is healthier)
        - Shimmer (amplitude perturbation - lower is healthier)
        - Voicing consistency (higher is better)
        """
        jitters = [p.jitter for p in prosody_timeline if p.jitter > 0]
        shimmers = [p.shimmer for p in prosody_timeline if p.shimmer > 0]
        voicing_probs = [p.voicing_probability for p in prosody_timeline]

        if not jitters or not shimmers:
            return 0.5

        avg_jitter = np.mean(jitters)
        avg_shimmer = np.mean(shimmers)
        avg_voicing = np.mean(voicing_probs)

        # Jitter score: healthy voice has jitter < 1%
        jitter_score = 1.0 - min(1.0, avg_jitter * 10)

        # Shimmer score: healthy voice has shimmer < 5%
        # Shimmer values are typically 0-1 range in openSMILE
        shimmer_score = 1.0 - min(1.0, avg_shimmer * 2)

        # Voicing score: consistent voicing is good
        voicing_score = avg_voicing

        # Combine scores
        vocal_health = (
            jitter_score * 0.35 +
            shimmer_score * 0.35 +
            voicing_score * 0.30
        )
        return vocal_health

    def _calc_avg_phrase_length(self, word_segments: List[WordSegment]) -> float:
        """Helper to calculate average phrase length."""
        phrases = []
        current_phrase = []

        for i, word in enumerate(word_segments):
            current_phrase.append(word)
            if i < len(word_segments) - 1:
                gap = word_segments[i + 1].start_time - word.end_time
                if gap > 0.3:
                    phrases.append(current_phrase)
                    current_phrase = []
            else:
                phrases.append(current_phrase)

        if not phrases:
            return 0.0

        lengths = [phrase[-1].end_time - phrase[0].start_time for phrase in phrases if phrase]
        return np.mean(lengths) if lengths else 0.0

    def _calc_phrase_variance(self, word_segments: List[WordSegment]) -> float:
        """Helper to calculate phrase length variance."""
        phrases = []
        current_phrase = []

        for i, word in enumerate(word_segments):
            current_phrase.append(word)
            if i < len(word_segments) - 1:
                gap = word_segments[i + 1].start_time - word.end_time
                if gap > 0.3:
                    phrases.append(current_phrase)
                    current_phrase = []
            else:
                phrases.append(current_phrase)

        if not phrases:
            return 0.0

        lengths = [phrase[-1].end_time - phrase[0].start_time for phrase in phrases if phrase]
        return np.std(lengths) if lengths else 0.0

    def _calc_loudness_stability(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Helper to calculate loudness stability."""
        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]
        if not loudness_values:
            return 0.5
        return 1.0 - min(1.0, np.std(loudness_values) / 10.0)

    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        score = max(0.0, min(1.0, score))
        return 1.0 + score * 4.0


def analyze_chest(
    audio_path: str,
    word_segments: List[WordSegment]
) -> ChestAnalysisResult:
    """
    Convenience function for Chest analysis.

    Args:
        audio_path: Path to audio file
        word_segments: Word-level timing information

    Returns:
        ChestAnalysisResult with complete analysis
    """
    engine = ChestEngine()
    return engine.analyze(audio_path, word_segments)

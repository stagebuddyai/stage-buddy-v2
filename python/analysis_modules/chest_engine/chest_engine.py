"""
Stage Buddy V2 - Chest Engine
Analyzes vocal technique: breath control, projection, pacing, and vocal health.

Core Scoring Components:
1. Breath Control (30%) - Phrase management and breath efficiency
2. Projection (30%) - Vocal volume and consistency
3. Pacing Technique (20%) - Strategic speed/tempo variation
4. Vocal Health (20%) - Voice quality and strain indicators
"""

from typing import List, Dict, Any, Optional, Tuple
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

        return self._score_from_prosody(prosody_timeline, prosody_summary, word_segments)

    def analyze_from_prosody(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float],
        word_segments: List[WordSegment]
    ) -> ChestAnalysisResult:
        """
        Perform Chest analysis using pre-extracted prosody data.

        This avoids duplicate OpenSMILE extraction when Spirit Engine
        has already processed the same audio file.

        Args:
            prosody_timeline: Pre-extracted prosody features from OpenSMILEExtractor
            prosody_summary: Pre-computed summary statistics
            word_segments: Word-level timing from transcription

        Returns:
            ChestAnalysisResult with scores and detailed analysis
        """
        logger.info("Starting Chest analysis from shared prosody data...")
        return self._score_from_prosody(prosody_timeline, prosody_summary, word_segments)

    def _score_from_prosody(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float],
        word_segments: List[WordSegment]
    ) -> ChestAnalysisResult:
        """Core scoring logic shared by analyze() and analyze_from_prosody()."""
        # Detect phrases once, reuse across subscores
        phrases = self._detect_phrases(word_segments)

        # Compute speech rate from word segments
        speech_rate_stats = self._compute_speech_rate(phrases)

        # Calculate raw component scores (0-1)
        breath_control_score = self._calculate_breath_control(phrases)
        projection_score = self._calculate_projection(prosody_summary, prosody_timeline)
        pacing_score = self._calculate_pacing(speech_rate_stats, prosody_timeline)
        vocal_health_score = self._calculate_vocal_health(prosody_timeline)

        # Apply per-subscore power curves to lift compressed scores.
        # Same strategy as Spirit Engine (alignment^0.3, settling^0.3,
        # transition^0.6, range^0.6) adapted for Chest's signal profile:
        #   - vocal_health^0.5  : strong lift — most structurally depressed
        #   - breath_control^0.7: moderate lift — sensitive to placeholder data
        #   - pacing^0.7        : moderate lift — sensitive to placeholder data
        #   - projection^0.8    : light lift — already scores well from OpenSMILE
        breath_control_curved = breath_control_score ** 0.7 if breath_control_score > 0 else 0.0
        projection_curved = projection_score ** 0.8 if projection_score > 0 else 0.0
        pacing_curved = pacing_score ** 0.7 if pacing_score > 0 else 0.0
        vocal_health_curved = vocal_health_score ** 0.5 if vocal_health_score > 0 else 0.0

        # Calculate overall Chest score using curved values
        component_scores = {
            'breath_control': breath_control_curved,
            'projection': projection_curved,
            'pacing': pacing_curved,
            'vocal_health': vocal_health_curved
        }

        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Convert to 1-5 scale
        overall_score = round(self._normalize_to_5_scale(overall_normalized), 1)

        logger.info(f"Chest analysis complete. Score: {overall_score}/5")

        # Calculate detailed metrics
        phrase_lengths = [p[-1].end_time - p[0].start_time for p in phrases if p]
        jitters = [p.jitter for p in prosody_timeline if p.jitter > 0]
        shimmers = [p.shimmer for p in prosody_timeline if p.shimmer > 0]

        return ChestAnalysisResult(
            overall_score=overall_score,
            breath_control_score=breath_control_curved,
            projection_score=projection_curved,
            pacing_score=pacing_curved,
            vocal_health_score=vocal_health_curved,
            avg_phrase_length=float(np.mean(phrase_lengths)) if phrase_lengths else 0.0,
            phrase_length_variance=float(np.std(phrase_lengths)) if phrase_lengths else 0.0,
            avg_loudness=prosody_summary.get('loudness_mean', 0.0),
            loudness_range=prosody_summary.get('loudness_range', 0.0),
            loudness_stability=self._calc_loudness_stability(prosody_timeline),
            speech_rate_mean=speech_rate_stats['mean'],
            speech_rate_variance=speech_rate_stats['variance'],
            avg_jitter=float(np.mean(jitters)) if jitters else 0.0,
            avg_shimmer=float(np.mean(shimmers)) if shimmers else 0.0,
            voicing_consistency=float(np.mean([p.voicing_probability for p in prosody_timeline])) if prosody_timeline else 0.0
        )

    def _detect_phrases(
        self,
        word_segments: List[WordSegment],
        gap_threshold: float = 0.3
    ) -> List[List[WordSegment]]:
        """
        Detect phrases as groups of words between pauses.

        Args:
            word_segments: Word-level timing from transcription
            gap_threshold: Minimum gap (seconds) to consider a phrase boundary

        Returns:
            List of phrases, where each phrase is a list of WordSegments
        """
        if not word_segments:
            return []

        phrases = []
        current_phrase = []

        for i, word in enumerate(word_segments):
            current_phrase.append(word)

            if i < len(word_segments) - 1:
                gap = word_segments[i + 1].start_time - word.end_time
                if gap > gap_threshold:
                    phrases.append(current_phrase)
                    current_phrase = []
            else:
                phrases.append(current_phrase)

        return phrases

    def _compute_speech_rate(
        self,
        phrases: List[List[WordSegment]]
    ) -> Dict[str, float]:
        """
        Compute speech rate (words per second) from detected phrases.

        Returns dict with 'mean', 'variance', and 'per_phrase' rates.
        """
        if not phrases:
            return {'mean': 0.0, 'variance': 0.0, 'per_phrase': []}

        per_phrase_rates = []
        for phrase in phrases:
            if len(phrase) < 2:
                continue
            duration = phrase[-1].end_time - phrase[0].start_time
            if duration > 0.1:  # Avoid division by tiny durations
                rate = len(phrase) / duration  # words per second
                per_phrase_rates.append(rate)

        if not per_phrase_rates:
            return {'mean': 0.0, 'variance': 0.0, 'per_phrase': []}

        return {
            'mean': float(np.mean(per_phrase_rates)),
            'variance': float(np.var(per_phrase_rates)),
            'per_phrase': per_phrase_rates
        }

    def _calculate_breath_control(
        self,
        phrases: List[List[WordSegment]]
    ) -> float:
        """
        Calculate breath control score (30% of Chest).

        Evaluates:
        - Phrase length management (too short = choppy, too long = running out)
        - Consistency of phrase lengths
        """
        if not phrases:
            return 0.5

        phrase_lengths = [p[-1].end_time - p[0].start_time for p in phrases if p]

        if not phrase_lengths:
            return 0.5

        avg_phrase_length = np.mean(phrase_lengths)
        phrase_variance = np.std(phrase_lengths)

        # Scoring: ideal phrase length is 4-8 seconds
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

        # Consistency: moderate variance is good (intentional variation)
        consistency_score = 1.0
        if phrase_variance < 0.5:
            consistency_score = 0.7  # Too uniform
        elif phrase_variance <= 2.0:
            consistency_score = 1.0  # Good variation
        else:
            consistency_score = 0.6  # Too erratic

        return (length_score * 0.6 + consistency_score * 0.4)

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

        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]

        if not loudness_values:
            return 0.5

        # Average loudness score
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
            loudness_score = 0.9  # Very loud (overdoing it)

        # Consistency score
        loudness_stability = 1.0 - min(1.0, np.std(loudness_values) / 10.0)

        # Dynamic range score
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

        return (loudness_score * 0.4 + loudness_stability * 0.3 + range_score * 0.3)

    def _calculate_pacing(
        self,
        speech_rate_stats: Dict[str, float],
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate pacing technique score (20% of Chest).

        Uses speech rate computed from word segments (words per second).
        Ideal conversational pace is ~2-3 words/sec (120-180 wpm).

        Evaluates:
        - Average pace (not too fast or slow)
        - Speech rate variation (intentional speed changes)
        """
        speech_rate_mean = speech_rate_stats['mean']
        speech_rate_var = speech_rate_stats['variance']

        if speech_rate_mean == 0:
            return 0.5

        # Average pace score
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
        variation_score = min(1.0, speech_rate_var / 0.5)

        return (pace_score * 0.6 + variation_score * 0.4)

    def _calculate_vocal_health(
        self,
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate vocal health score (20% of Chest).

        Evaluates:
        - Jitter (pitch perturbation - lower is healthier)
        - Shimmer (amplitude perturbation - lower is healthier)
        - Voicing consistency (higher is better, measured only over voiced frames)

        Calibration notes (v2 — 2026-02-06):
        - Shimmer multiplier reduced from *2 to *0.8. openSMILE eGeMAPSv02
          shimmerLocaldB outputs 0.3-0.8 for normal speech; *2 zeroed out
          all real recordings.
        - Jitter multiplier reduced from *10 to *5. Normal jitter on
          non-studio recordings is 0.02-0.08; *10 penalized healthy voices.
        - Voicing now filtered to frames with voicing_probability > 0.3,
          avoiding dilution from silence/pause frames.
        """
        jitters = [p.jitter for p in prosody_timeline if p.jitter > 0]
        shimmers = [p.shimmer for p in prosody_timeline if p.shimmer > 0]
        # Only count voiced frames — silence frames dilute the average
        voiced_probs = [p.voicing_probability for p in prosody_timeline
                        if p.voicing_probability > 0.3]

        if not jitters or not shimmers:
            return 0.5

        avg_jitter = np.mean(jitters)
        avg_shimmer = np.mean(shimmers)
        avg_voicing = np.mean(voiced_probs) if voiced_probs else 0.5

        # Jitter score: calibrated for real-world recordings (not clinical studio)
        # Normal jitter 0.02-0.08 → scores 0.90-0.60
        jitter_score = 1.0 - min(1.0, avg_jitter * 5)

        # Shimmer score: calibrated for openSMILE dB-scale output
        # Normal shimmer 0.3-0.8 → scores 0.76-0.36
        shimmer_score = 1.0 - min(1.0, avg_shimmer * 0.8)

        # Voicing score: measured over voiced frames only
        voicing_score = avg_voicing

        return (jitter_score * 0.35 + shimmer_score * 0.35 + voicing_score * 0.30)

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

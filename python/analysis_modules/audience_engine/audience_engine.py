"""
Stage Buddy V2 - Audience Engine
Analyzes audience connection, engagement patterns, and performer presence.

Core Scoring Components:
1. Direct Address (30%) - Speaking TO audience vs speaking AT them
2. Pacing (20%) - Strategic timing for audience comprehension
3. Emotional Invitation (25%) - Inviting audience into emotional journey
4. Engagement Patterns (25%) - Sustained attention and dynamic variety
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
class AudienceAnalysisResult:
    """Results from Audience engine analysis."""
    overall_score: float
    direct_address_score: float
    pacing_score: float
    emotional_invitation_score: float
    engagement_patterns_score: float

    # Detailed metrics
    pause_usage_score: float
    dynamic_variety: float
    emotional_arc_strength: float
    attention_sustainability: float


class AudienceEngine:
    """
    The Audience Engine analyzes connection and engagement with listeners.

    It evaluates:
    1. Direct address - Vocal qualities suggesting direct communication
    2. Pacing - Strategic use of tempo for audience comprehension
    3. Emotional invitation - Creating space for audience to feel with you
    4. Engagement patterns - Sustained attention through variety
    """

    def __init__(
        self,
        opensmile_feature_set: str = "eGeMAPSv02"
    ):
        """
        Initialize the Audience Engine.

        Args:
            opensmile_feature_set: Feature set for prosody extraction
        """
        logger.info("Initializing Audience Engine...")

        self.prosody_extractor = OpenSMILEExtractor(
            feature_set=opensmile_feature_set,
            feature_level="LowLevelDescriptors"
        )

        # Component weights per specification
        self.weights = {
            'direct_address': 0.30,
            'pacing': 0.20,
            'emotional_invitation': 0.25,
            'engagement_patterns': 0.25
        }

        logger.info("Audience Engine initialized")

    def analyze(
        self,
        audio_path: str,
        word_segments: List[WordSegment],
        vocal_emotions: List[EmotionSegment] = None
    ) -> AudienceAnalysisResult:
        """
        Perform complete Audience analysis on a performance.

        Args:
            audio_path: Path to audio file
            word_segments: Word-level timing from transcription
            vocal_emotions: Emotion segments from Spirit engine (optional)

        Returns:
            AudienceAnalysisResult with scores and detailed analysis
        """
        logger.info(f"Starting Audience analysis for: {audio_path}")

        # Extract prosodic features
        logger.info("Extracting prosodic features...")
        prosody_result = self.prosody_extractor.extract_features_from_file(audio_path)
        prosody_timeline = prosody_result['prosody_timeline']
        prosody_summary = self.prosody_extractor.get_summary_statistics(prosody_timeline)

        # Calculate component scores
        direct_address_score = self._calculate_direct_address(prosody_timeline, prosody_summary)
        pacing_score = self._calculate_pacing(word_segments, prosody_summary)
        emotional_invitation_score = self._calculate_emotional_invitation(
            prosody_timeline, vocal_emotions
        )
        engagement_patterns_score = self._calculate_engagement_patterns(
            prosody_timeline, prosody_summary, vocal_emotions
        )

        # Calculate overall Audience score
        component_scores = {
            'direct_address': direct_address_score,
            'pacing': pacing_score,
            'emotional_invitation': emotional_invitation_score,
            'engagement_patterns': engagement_patterns_score
        }

        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Convert to 1-5 scale
        overall_score = self._normalize_to_5_scale(overall_normalized)

        logger.info(f"Audience analysis complete. Score: {overall_score:.2f}/5")

        return AudienceAnalysisResult(
            overall_score=overall_score,
            direct_address_score=direct_address_score,
            pacing_score=pacing_score,
            emotional_invitation_score=emotional_invitation_score,
            engagement_patterns_score=engagement_patterns_score,
            pause_usage_score=self._calc_pause_usage(word_segments),
            dynamic_variety=prosody_summary.get('loudness_range', 0.0),
            emotional_arc_strength=self._calc_emotional_arc_strength(vocal_emotions),
            attention_sustainability=self._calc_attention_sustainability(prosody_timeline)
        )

    def _calculate_direct_address(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float]
    ) -> float:
        """
        Calculate direct address score (30% of Audience).

        Measures vocal qualities that suggest speaking TO someone:
        - Projection (speaking out to the room)
        - Vocal clarity (making sure you're understood)
        - Consistency (maintaining connection)
        """
        loudness_mean = prosody_summary.get('loudness_mean', 0.0)

        # Projection score: speaking TO audience needs good volume
        projection_score = 1.0
        if loudness_mean < -35:
            projection_score = 0.3  # Too quiet for direct address
        elif loudness_mean < -28:
            projection_score = 0.6  # Moderate
        elif loudness_mean < -20:
            projection_score = 0.9  # Good direct address
        else:
            projection_score = 1.0  # Strong direct address

        # Clarity score: clear voicing = wanting to be understood
        voicing_probs = [p.voicing_probability for p in prosody_timeline]
        clarity_score = np.mean(voicing_probs)

        # Consistency score: maintaining connection throughout
        consistency_score = self._calc_projection_consistency(prosody_timeline)

        # Combine scores
        direct_address = (
            projection_score * 0.40 +
            clarity_score * 0.35 +
            consistency_score * 0.25
        )
        return direct_address

    def _calculate_pacing(
        self,
        word_segments: List[WordSegment],
        prosody_summary: Dict[str, float]
    ) -> float:
        """
        Calculate pacing score (20% of Audience).

        Evaluates strategic timing for audience comprehension:
        - Pause usage (giving audience time to process)
        - Speech rate variation (emphasis through pace)
        - Overall pace (not too fast to follow)
        """
        # Detect pauses
        pauses = []
        for i in range(len(word_segments) - 1):
            gap = word_segments[i + 1].start_time - word_segments[i].end_time
            if gap > 0.2:  # Significant pause
                pauses.append(gap)

        # Pause usage score: good performers use pauses strategically
        if pauses:
            avg_pause = np.mean(pauses)
            pause_count = len(pauses)
            total_duration = word_segments[-1].end_time - word_segments[0].start_time
            pause_frequency = pause_count / (total_duration / 60)  # Pauses per minute

            # Ideal: 8-12 pauses per minute, average 0.5-1.5s
            frequency_score = 1.0
            if pause_frequency < 5:
                frequency_score = 0.6  # Too few pauses
            elif pause_frequency < 8:
                frequency_score = 0.8
            elif pause_frequency <= 12:
                frequency_score = 1.0  # Ideal
            elif pause_frequency <= 15:
                frequency_score = 0.9
            else:
                frequency_score = 0.7  # Too many pauses

            duration_score = 1.0
            if avg_pause < 0.3:
                duration_score = 0.7  # Too brief
            elif avg_pause <= 1.5:
                duration_score = 1.0  # Good duration
            else:
                duration_score = 0.8  # Slightly long

            pause_score = (frequency_score + duration_score) / 2
        else:
            pause_score = 0.4  # No pauses is problematic

        # Speech rate score
        speech_rate = prosody_summary.get('speech_rate_mean', 0.0)
        rate_score = 1.0
        if speech_rate < 1.5:
            rate_score = 0.7  # Too slow for engagement
        elif speech_rate < 2.0:
            rate_score = 0.9  # Slightly slow
        elif speech_rate <= 3.0:
            rate_score = 1.0  # Good pace
        elif speech_rate <= 3.5:
            rate_score = 0.8  # Slightly fast
        else:
            rate_score = 0.5  # Too fast to follow

        # Variation score
        speech_rate_var = prosody_summary.get('speech_rate_var', 0.0)
        variation_score = min(1.0, speech_rate_var / 0.6)

        # Combine scores
        pacing = (
            pause_score * 0.45 +
            rate_score * 0.35 +
            variation_score * 0.20
        )
        return pacing

    def _calculate_emotional_invitation(
        self,
        prosody_timeline: List[ProsodyFeatures],
        vocal_emotions: List[EmotionSegment] = None
    ) -> float:
        """
        Calculate emotional invitation score (25% of Audience).

        Measures how well the performer invites audience into their emotional journey:
        - Emotional clarity (clear emotional expression)
        - Emotional arc (building and releasing)
        - Dynamic space (room for audience to feel)
        """
        if not vocal_emotions:
            # Without emotion data, use prosody dynamics
            dynamic_range = np.std([p.loudness_db for p in prosody_timeline if p.loudness_db > -100])
            return min(1.0, dynamic_range / 8.0)

        # Emotional clarity: strong, confident emotions
        emotion_intensities = [e.intensity for e in vocal_emotions]
        emotion_confidences = [e.confidence for e in vocal_emotions]

        clarity_score = np.mean(emotion_intensities) * np.mean(emotion_confidences)

        # Emotional arc: variety of emotions creating a journey
        unique_emotions = len(set(e.emotion for e in vocal_emotions))
        arc_score = min(1.0, unique_emotions / 5)  # 5+ emotions = full arc

        # Dynamic space: pauses and variation allow audience to feel
        # Check for transitions between emotions
        transitions = []
        for i in range(len(vocal_emotions) - 1):
            if vocal_emotions[i].emotion != vocal_emotions[i + 1].emotion:
                gap = vocal_emotions[i + 1].start_time - vocal_emotions[i].end_time
                transitions.append(gap)

        if transitions:
            avg_transition_gap = np.mean(transitions)
            # Ideal: 0.5-2.0 second gaps for audience to transition with you
            space_score = 1.0
            if avg_transition_gap < 0.3:
                space_score = 0.6  # Too rushed
            elif avg_transition_gap < 0.5:
                space_score = 0.8
            elif avg_transition_gap <= 2.0:
                space_score = 1.0  # Good space
            else:
                space_score = 0.8  # Slightly long
        else:
            space_score = 0.5

        # Combine scores
        emotional_invitation = (
            clarity_score * 0.40 +
            arc_score * 0.35 +
            space_score * 0.25
        )
        return emotional_invitation

    def _calculate_engagement_patterns(
        self,
        prosody_timeline: List[ProsodyFeatures],
        prosody_summary: Dict[str, float],
        vocal_emotions: List[EmotionSegment] = None
    ) -> float:
        """
        Calculate engagement patterns score (25% of Audience).

        Measures sustained attention through:
        - Dynamic variety (keeping attention through change)
        - Attention sustainability (not losing energy)
        - Engagement hooks (moments that grab attention)
        """
        # Dynamic variety: changes keep attention
        loudness_range = prosody_summary.get('loudness_range', 0.0)
        pitch_range = prosody_summary.get('pitch_range', 0.0)

        variety_score = (
            min(1.0, loudness_range / 25) * 0.5 +
            min(1.0, pitch_range / 120) * 0.5
        )

        # Attention sustainability: energy maintained throughout
        sustainability_score = self._calc_attention_sustainability(prosody_timeline)

        # Engagement hooks: moments of high energy/intensity
        hook_score = self._calc_engagement_hooks(prosody_timeline, vocal_emotions)

        # Combine scores
        engagement_patterns = (
            variety_score * 0.35 +
            sustainability_score * 0.35 +
            hook_score * 0.30
        )
        return engagement_patterns

    def _calc_pause_usage(self, word_segments: List[WordSegment]) -> float:
        """Calculate how well pauses are used."""
        if len(word_segments) < 2:
            return 0.5

        pauses = []
        for i in range(len(word_segments) - 1):
            gap = word_segments[i + 1].start_time - word_segments[i].end_time
            if gap > 0.2:
                pauses.append(gap)

        if not pauses:
            return 0.3

        avg_pause = np.mean(pauses)
        # Ideal average pause: 0.5-1.5s
        if 0.5 <= avg_pause <= 1.5:
            return 1.0
        elif 0.3 <= avg_pause < 0.5 or 1.5 < avg_pause <= 2.0:
            return 0.8
        else:
            return 0.6

    def _calc_emotional_arc_strength(self, vocal_emotions: List[EmotionSegment] = None) -> float:
        """Calculate strength of emotional arc."""
        if not vocal_emotions:
            return 0.5

        # Measure variety and intensity of emotions
        unique_emotions = len(set(e.emotion for e in vocal_emotions))
        avg_intensity = np.mean([e.intensity for e in vocal_emotions])

        variety_factor = min(1.0, unique_emotions / 5)
        intensity_factor = avg_intensity

        return (variety_factor + intensity_factor) / 2

    def _calc_attention_sustainability(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate how well attention is sustained throughout."""
        if len(prosody_timeline) < 10:
            return 0.5

        # Divide into segments and check energy retention
        segment_size = len(prosody_timeline) // 5
        segment_energies = []

        for i in range(5):
            start_idx = i * segment_size
            end_idx = start_idx + segment_size if i < 4 else len(prosody_timeline)
            segment = prosody_timeline[start_idx:end_idx]

            avg_energy = np.mean([p.loudness_db for p in segment if p.loudness_db > -100])
            segment_energies.append(avg_energy)

        if not segment_energies:
            return 0.5

        # Check if energy is maintained (not declining)
        first_half_avg = np.mean(segment_energies[:2])
        second_half_avg = np.mean(segment_energies[3:])

        if first_half_avg == 0:
            return 0.5

        retention_ratio = second_half_avg / first_half_avg
        # Ideal: maintain 85%+ of initial energy
        sustainability = min(1.0, max(0.0, (retention_ratio - 0.5) / 0.5))

        return sustainability

    def _calc_engagement_hooks(
        self,
        prosody_timeline: List[ProsodyFeatures],
        vocal_emotions: List[EmotionSegment] = None
    ) -> float:
        """Calculate presence of engagement hooks (attention-grabbing moments)."""
        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]

        if not loudness_values:
            return 0.5

        # Find peaks (moments significantly louder than average)
        mean_loudness = np.mean(loudness_values)
        std_loudness = np.std(loudness_values)

        peaks = [v for v in loudness_values if v > mean_loudness + std_loudness]
        peak_count = len(peaks)

        # Ideal: 3-8 significant peaks in performance
        if peak_count < 2:
            return 0.5  # Too flat
        elif peak_count < 3:
            return 0.7
        elif peak_count <= 8:
            return 1.0  # Good hooks
        elif peak_count <= 12:
            return 0.9
        else:
            return 0.7  # Too many peaks (loses impact)

    def _calc_projection_consistency(self, prosody_timeline: List[ProsodyFeatures]) -> float:
        """Calculate consistency of projection."""
        loudness_values = [p.loudness_db for p in prosody_timeline if p.loudness_db > -100]
        if not loudness_values:
            return 0.5

        consistency = 1.0 - min(1.0, np.std(loudness_values) / 12.0)
        return consistency

    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        score = max(0.0, min(1.0, score))
        return 1.0 + score * 4.0


def analyze_audience(
    audio_path: str,
    word_segments: List[WordSegment],
    vocal_emotions: List[EmotionSegment] = None
) -> AudienceAnalysisResult:
    """
    Convenience function for Audience analysis.

    Args:
        audio_path: Path to audio file
        word_segments: Word-level timing information
        vocal_emotions: Emotion segments (optional)

    Returns:
        AudienceAnalysisResult with complete analysis
    """
    engine = AudienceEngine()
    return engine.analyze(audio_path, word_segments, vocal_emotions)

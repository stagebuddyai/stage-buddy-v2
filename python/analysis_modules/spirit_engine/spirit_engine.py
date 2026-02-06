"""
Stage Buddy V2 - Spirit Engine
Main module that orchestrates emotion analysis and calculates Spirit scores.

The Spirit score measures how well the performer's vocal delivery aligns with
the emotional content of their words. As the POTS guidebook states:
"Until the spirit of a poem is awakened, the performance will forever remain asleep."

Core Scoring Components:
1. Emotion-Word Alignment (30%) - Does vocal emotion match text emotion?
2. Emotional Transition Quality (20%) - Are transitions smooth/intentional?
3. Emotional Range (35%) - Dynamic range of emotions displayed
4. Settling Indicator (15%) - Consistency suggesting piece is "settled"
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import logging

from ..shared.data_structures import (
    EmotionCategory, EmotionSegment, WordSegment, ProsodyFeatures,
    SpiritAnalysisResult, emotions_are_aligned, EMOTION_VA_MAP
)
from .opensmile_extractor import OpenSMILEExtractor, extract_prosody
from .text_emotion_analyzer import TextEmotionAnalyzer, predict_ideal_emotions
from .vocal_emotion_detector import VocalEmotionDetector, detect_vocal_emotions

logger = logging.getLogger(__name__)


class SpiritEngine:
    """
    The Spirit Engine analyzes emotion-word alignment in spoken word performances.
    
    It answers the question: "Does the performer's delivery match the spirit of their piece?"
    
    The engine:
    1. Extracts prosodic features from audio (pitch, loudness, voice quality)
    2. Detects emotions from the vocal performance
    3. Predicts "ideal" emotions from the transcript text
    4. Measures alignment between vocal and ideal emotions
    5. Evaluates transition quality and emotional range
    6. Produces a Spirit score (1-5) with detailed feedback
    """
    
    def __init__(
        self,
        opensmile_feature_set: str = "eGeMAPSv02",
        text_emotion_model: str = "SamLowe/roberta-base-go_emotions",
        vocal_emotion_model: str = "speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        device: str = "auto"
    ):
        """
        Initialize the Spirit Engine.
        
        Args:
            opensmile_feature_set: Feature set for prosody extraction
            text_emotion_model: HuggingFace model for text emotion
            vocal_emotion_model: Model for vocal emotion detection
            device: Compute device ("auto", "cpu", "cuda")
        """
        logger.info("Initializing Spirit Engine...")
        
        # Initialize components
        self.prosody_extractor = OpenSMILEExtractor(
            feature_set=opensmile_feature_set,
            feature_level="LowLevelDescriptors"
        )
        
        self.text_analyzer = TextEmotionAnalyzer(
            model_name=text_emotion_model,
            device=device
        )
        
        self.vocal_detector = VocalEmotionDetector(
            model_source=vocal_emotion_model,
            device=device
        )
        
        # Calibrated weights: 30/20/35/15 (third iteration)
        # Rebalanced: reduced range dominance (was 45%), increased alignment
        # and settling to better reward precise delivery and settled performances
        self.weights = {
            'emotion_alignment': 0.30,
            'transition_quality': 0.20,
            'emotional_range': 0.35,
            'settling': 0.15
        }
        
        logger.info("Spirit Engine initialized")
    
    def analyze(
        self,
        audio_path: str,
        transcript: str,
        word_segments: List[WordSegment],
        segment_duration: float = 3.0
    ) -> SpiritAnalysisResult:
        """
        Perform complete Spirit analysis on a performance.
        
        Args:
            audio_path: Path to audio file
            transcript: Full transcript text
            word_segments: Word-level timing from transcription
            segment_duration: Duration for emotion segments (default 3s)
            
        Returns:
            SpiritAnalysisResult with scores and detailed analysis
        """
        logger.info(f"Starting Spirit analysis for: {audio_path}")
        
        # Step 1: Extract prosodic features
        logger.info("Extracting prosodic features...")
        prosody_result = self.prosody_extractor.extract_features_from_file(audio_path)
        prosody_timeline = prosody_result['prosody_timeline']
        prosody_summary = self.prosody_extractor.get_summary_statistics(prosody_timeline)
        
        # Step 2: Detect vocal emotions
        logger.info("Detecting vocal emotions...")
        vocal_emotions = self.vocal_detector.detect_emotions_from_file(
            audio_path,
            segment_duration=segment_duration
        )
        
        # Step 3: Generate ideal emotional arc from text
        logger.info("Predicting ideal emotional arc...")
        ideal_emotions = self.text_analyzer.analyze_line_by_line(
            transcript,
            word_segments
        )
        
        # If line-by-line fails, fall back to time-based segments
        if not ideal_emotions:
            ideal_emotions = self.text_analyzer.generate_ideal_arc(
                word_segments,
                segment_duration=segment_duration
            )
        
        # Step 4: Calculate alignment scores
        logger.info("Calculating emotion-word alignment...")
        alignment_result = self._calculate_alignment(vocal_emotions, ideal_emotions)
        
        # Step 5: Calculate transition quality
        transition_score = self._calculate_transition_quality(vocal_emotions)
        
        # Step 6: Calculate emotional range
        range_score = self._calculate_emotional_range(vocal_emotions, prosody_summary)
        
        # Step 7: Calculate settling indicator
        settling_score = self._calculate_settling(vocal_emotions, prosody_timeline)
        
        # Step 8: Calculate overall Spirit score
        # Calibrated weights: 30/20/35/15 (third iteration)
        # Rebalanced: reduced range dominance, increased alignment and settling
        component_scores = {
            'emotion_alignment': alignment_result['overall_alignment'],
            'transition_quality': transition_score,
            'emotional_range': range_score,
            'settling': settling_score
        }
        
        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )
        
        # Convert to 1-5 scale and round all scores to nearest tenth
        overall_score = round(self._normalize_to_5_scale(overall_normalized), 1)

        logger.info(f"Spirit analysis complete. Score: {overall_score}/5")

        return SpiritAnalysisResult(
            overall_score=overall_score,
            emotion_alignment_score=alignment_result['overall_alignment'],
            emotional_transition_score=transition_score,
            emotional_range_score=range_score,
            settling_score=settling_score,
            vocal_emotions=vocal_emotions,
            ideal_emotions=ideal_emotions,
            alignment_timeline=alignment_result['timeline'],
            avg_pitch=prosody_summary.get('pitch_mean', 0.0),
            pitch_range=prosody_summary.get('pitch_range', 0.0),
            avg_loudness=prosody_summary.get('loudness_mean', 0.0),
            loudness_range=prosody_summary.get('loudness_range', 0.0),
            speech_rate_avg=prosody_summary.get('speech_rate_mean', 0.0) if 'speech_rate_mean' in prosody_summary else 0.0,
            speech_rate_variance=prosody_summary.get('speech_rate_var', 0.0) if 'speech_rate_var' in prosody_summary else 0.0,
            misalignment_moments=alignment_result['misalignments'],
            strength_moments=alignment_result['strengths'],
            prosody_features=prosody_timeline
        )
    
    def _calculate_alignment(
        self,
        vocal_emotions: List[EmotionSegment],
        ideal_emotions: List[EmotionSegment]
    ) -> Dict[str, Any]:
        """
        Calculate emotion-word alignment between vocal and ideal emotions.
        
        This is the core Spirit metric - it measures whether the performer's
        delivery matches what the text demands.
        """
        if not vocal_emotions or not ideal_emotions:
            return {
                'overall_alignment': 0.5,
                'timeline': [],
                'misalignments': [],
                'strengths': []
            }
        
        timeline = []
        alignment_scores = []
        misalignments = []
        strengths = []
        
        # For each vocal emotion segment, find the best matching ideal segment
        for vocal_seg in vocal_emotions:
            # Find overlapping ideal segments
            overlapping_ideal = [
                ideal for ideal in ideal_emotions
                if self._segments_overlap(vocal_seg, ideal)
            ]
            
            if not overlapping_ideal:
                # No ideal emotion for this segment - use nearest
                nearest = self._find_nearest_segment(vocal_seg, ideal_emotions)
                if nearest:
                    overlapping_ideal = [nearest]
            
            if overlapping_ideal:
                # Calculate alignment with each overlapping ideal
                best_alignment = 0.0
                best_ideal = overlapping_ideal[0]
                
                for ideal in overlapping_ideal:
                    is_aligned, score = emotions_are_aligned(
                        vocal_seg.emotion,
                        ideal.emotion
                    )
                    
                    # Boost score based on intensity match
                    intensity_match = 1.0 - abs(vocal_seg.intensity - ideal.intensity)
                    adjusted_score = score * 0.7 + intensity_match * 0.3
                    
                    if adjusted_score > best_alignment:
                        best_alignment = adjusted_score
                        best_ideal = ideal
                
                alignment_scores.append(best_alignment)
                
                entry = {
                    'start_time': vocal_seg.start_time,
                    'end_time': vocal_seg.end_time,
                    'vocal_emotion': vocal_seg.emotion.value,
                    'ideal_emotion': best_ideal.emotion.value,
                    'alignment_score': best_alignment,
                    'vocal_intensity': vocal_seg.intensity,
                    'ideal_intensity': best_ideal.intensity
                }
                timeline.append(entry)
                
                # Track strengths and misalignments
                if best_alignment >= 0.7:
                    strengths.append({
                        'time': vocal_seg.start_time,
                        'emotion': vocal_seg.emotion.value,
                        'score': best_alignment,
                        'description': f"Strong {vocal_seg.emotion.value} delivery matching text"
                    })
                elif best_alignment < 0.4:
                    misalignments.append({
                        'time': vocal_seg.start_time,
                        'vocal': vocal_seg.emotion.value,
                        'expected': best_ideal.emotion.value,
                        'score': best_alignment,
                        'description': f"Delivered {vocal_seg.emotion.value} but text calls for {best_ideal.emotion.value}"
                    })
        
        overall_alignment = np.mean(alignment_scores) if alignment_scores else 0.5
        
        return {
            'overall_alignment': overall_alignment,
            'timeline': timeline,
            'misalignments': misalignments,
            'strengths': strengths
        }
    
    def _calculate_transition_quality(
        self,
        vocal_emotions: List[EmotionSegment]
    ) -> float:
        """
        Calculate how smooth/intentional emotional transitions are.
        
        Good transitions:
        - Gradual changes in valence/arousal between segments
        - Distinct emotion changes at appropriate moments
        - No jarring jumps without justification
        """
        if len(vocal_emotions) < 2:
            return 0.5  # Can't evaluate transitions with < 2 segments
        
        transition_scores = []
        
        for i in range(1, len(vocal_emotions)):
            prev = vocal_emotions[i - 1]
            curr = vocal_emotions[i]
            
            # Calculate valence-arousal distance
            va_distance = np.sqrt(
                (curr.valence - prev.valence) ** 2 +
                (curr.arousal - prev.arousal) ** 2
            )
            
            # Moderate transitions are good, extreme jumps are bad
            # Optimal transition is ~0.3-0.6 in VA space
            if va_distance < 0.1:
                # Sustained emotion — legitimate artistic choice
                score = 0.85
            elif va_distance < 0.5:
                # Moderate transition - ideal
                score = 1.0
            elif va_distance < 0.8:
                # Larger transition - might be intentional
                score = 0.8
            else:
                # Extreme jump - likely jarring
                score = 0.4
            
            # Check if transition crosses emotion boundary smoothly
            if prev.emotion != curr.emotion:
                # Emotion changed - this is expected at some points
                is_aligned, alignment = emotions_are_aligned(prev.emotion, curr.emotion)
                if is_aligned:
                    score *= 1.0  # Adjacent emotions = smooth
                else:
                    score *= 0.8  # Non-adjacent but could be intentional
            
            transition_scores.append(score)
        
        return np.mean(transition_scores) if transition_scores else 0.5
    
    def _calculate_emotional_range(
        self,
        vocal_emotions: List[EmotionSegment],
        prosody_summary: Dict[str, float]
    ) -> float:
        """
        Calculate the emotional dynamic range of the performance.
        
        A good performance has:
        - Multiple distinct emotions (not monotone)
        - Variation in intensity
        - Appropriate pitch and loudness range
        """
        if not vocal_emotions:
            return 0.5
        
        # Count unique emotions
        unique_emotions = set(e.emotion for e in vocal_emotions)
        emotion_variety_score = min(1.0, len(unique_emotions) / 3)  # 3+ emotions = full score
        
        # Measure intensity range
        intensities = [e.intensity for e in vocal_emotions]
        intensity_range = max(intensities) - min(intensities)
        intensity_score = min(1.0, intensity_range / 0.6)  # 0.6 range = full score
        
        # Measure valence-arousal spread
        valences = [e.valence for e in vocal_emotions]
        arousals = [e.arousal for e in vocal_emotions]
        
        valence_range = max(valences) - min(valences)
        arousal_range = max(arousals) - min(arousals)
        va_spread = (valence_range + arousal_range) / 2
        va_score = min(1.0, va_spread / 0.8)  # 0.8 average range = full score
        
        # Use prosody range as additional signal
        pitch_range = prosody_summary.get('pitch_range', 0)
        loudness_range = prosody_summary.get('loudness_range', 0)
        
        # Normalize prosody scores
        pitch_score = min(1.0, pitch_range / 80)  # 80Hz range = good
        loudness_score = min(1.0, loudness_range / 30)  # 30dB range = good
        
        # Combine scores
        range_score = (
            emotion_variety_score * 0.25 +
            intensity_score * 0.25 +
            va_score * 0.25 +
            pitch_score * 0.15 +
            loudness_score * 0.10
        )
        
        return range_score
    
    def _calculate_settling(
        self,
        vocal_emotions: List[EmotionSegment],
        prosody_timeline: List[ProsodyFeatures]
    ) -> float:
        """
        Calculate the "settling" indicator - how well the performer knows their piece.
        
        A settled performance shows:
        - Consistent timing patterns
        - Confident delivery (high voicing probability)
        - Appropriate pace without rushing or hesitation
        - Low jitter/shimmer (voice quality)
        """
        if not prosody_timeline:
            return 0.5
        
        # Voice quality consistency (jitter/shimmer)
        jitters = [p.jitter for p in prosody_timeline if p.jitter > 0]
        shimmers = [p.shimmer for p in prosody_timeline if p.shimmer > 0]
        
        avg_jitter = np.mean(jitters) if jitters else 0.02
        avg_shimmer = np.mean(shimmers) if shimmers else 0.5
        
        # Lower jitter/shimmer = more controlled voice = more settled
        voice_quality_score = 1.0 - min(1.0, avg_jitter * 10)  # jitter < 0.1 is good
        
        # Voicing consistency
        voicing_probs = [p.voicing_probability for p in prosody_timeline]
        voicing_consistency = np.mean([v > 0.5 for v in voicing_probs])
        
        # Pitch stability (low variance = more settled)
        pitch_vars = [p.pitch_variance for p in prosody_timeline if p.pitch_variance > 0]
        avg_pitch_var = np.mean(pitch_vars) if pitch_vars else 0
        pitch_stability = 1.0 - min(1.0, avg_pitch_var / 50)  # var < 50 is good
        
        # Emotion confidence consistency
        if vocal_emotions:
            confidence_scores = [e.confidence for e in vocal_emotions]
            avg_confidence = np.mean(confidence_scores)
        else:
            avg_confidence = 0.5
        
        settling_score = (
            voice_quality_score * 0.3 +
            voicing_consistency * 0.25 +
            pitch_stability * 0.25 +
            avg_confidence * 0.2
        )
        
        return settling_score
    
    def _segments_overlap(
        self,
        seg1: EmotionSegment,
        seg2: EmotionSegment
    ) -> bool:
        """Check if two segments overlap in time."""
        return seg1.start_time < seg2.end_time and seg2.start_time < seg1.end_time
    
    def _find_nearest_segment(
        self,
        target: EmotionSegment,
        candidates: List[EmotionSegment]
    ) -> Optional[EmotionSegment]:
        """Find the nearest segment by time."""
        if not candidates:
            return None
        
        target_mid = (target.start_time + target.end_time) / 2
        
        nearest = min(
            candidates,
            key=lambda c: abs((c.start_time + c.end_time) / 2 - target_mid)
        )
        return nearest
    
    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        # Ensure score is in 0-1 range
        score = max(0.0, min(1.0, score))
        # Map to 1-5 scale
        return 1.0 + score * 4.0
    
    def generate_feedback(self, result: SpiritAnalysisResult) -> str:
        """
        Generate coach-style feedback based on analysis results.
        
        Uses the POTS guidebook voice - direct, encouraging, focused on growth.
        """
        score = result.overall_score
        
        # Build feedback based on score range
        if score >= 4.5:
            opening = "Your spirit is ALIVE! The emotion in your delivery perfectly matches your words."
        elif score >= 3.5:
            opening = "Good work - your spirit is waking up. There's strong alignment between your words and delivery."
        elif score >= 2.5:
            opening = "Your spirit is stirring, but not fully awake yet. Let's work on making your delivery match your words."
        else:
            opening = "We need to wake the spirit of this piece. Your delivery isn't yet reflecting what your words are saying."
        
        feedback_parts = [opening]
        
        # Add specific feedback on alignment
        if result.misalignment_moments:
            worst_misalign = min(result.misalignment_moments, key=lambda x: x['score'])
            feedback_parts.append(
                f"\nAt {worst_misalign['time']:.1f}s, you delivered '{worst_misalign['vocal']}' "
                f"but the text calls for '{worst_misalign['expected']}'. "
                f"Remember: don't bring your current feelings to the mic - bring the poem's feelings."
            )
        
        # Highlight strengths
        if result.strength_moments:
            best_moment = max(result.strength_moments, key=lambda x: x['score'])
            feedback_parts.append(
                f"\nStrong moment at {best_moment['time']:.1f}s - "
                f"your {best_moment['emotion']} delivery was spot-on. More of that!"
            )
        
        # Add specific component feedback
        if result.emotional_range_score < 0.5:
            feedback_parts.append(
                "\nYour emotional range needs work. The piece has variety - show us more dynamics!"
            )
        
        if result.settling_score < 0.5:
            feedback_parts.append(
                "\nThis piece doesn't feel fully settled yet. Practice until the timing feels natural."
            )
        
        return "\n".join(feedback_parts)


def analyze_spirit(
    audio_path: str,
    transcript: str,
    word_segments: List[WordSegment]
) -> SpiritAnalysisResult:
    """
    Convenience function for Spirit analysis.
    
    Args:
        audio_path: Path to audio file
        transcript: Full transcript text
        word_segments: Word-level timing information
        
    Returns:
        SpiritAnalysisResult with complete analysis
    """
    engine = SpiritEngine()
    return engine.analyze(audio_path, transcript, word_segments)

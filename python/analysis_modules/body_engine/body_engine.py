"""
Stage Buddy V2 - Body Engine
Main module that orchestrates physical performance analysis.

The Body Engine analyzes visual aspects of spoken word performances:
- Gesture intentionality and purposefulness
- Stage presence and use of space
- Eye contact and audience connection
- Physical-vocal alignment

Core Scoring Components:
1. Gesture Intentionality (35%) - Are movements purposeful or nervous fidgeting?
2. Stage Presence (30%) - Use of space, stance, confidence in physicality
3. Eye Contact/Focus (20%) - Connection with audience through gaze
4. Physical-Vocal Alignment (15%) - Do gestures match vocal emphasis?
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
import logging
import time

from ..shared.data_structures import (
    GestureType, GestureEvent, BodySegment, BodyAnalysisResult
)
from .gesture_analyzer import GestureAnalyzer
from .stage_presence_analyzer import StagePresenceAnalyzer
from .eye_contact_detector import EyeContactDetector
from .alignment_scorer import AlignmentScorer

logger = logging.getLogger(__name__)


class BodyEngine:
    """
    The Body Engine analyzes physical performance in spoken word videos.

    It evaluates:
    1. Whether gestures are intentional and serve the piece
    2. How effectively the performer uses the stage space
    3. Eye contact engagement with the audience
    4. Synchronization between physical movement and vocal delivery
    """

    def __init__(
        self,
        fps_target: float = 5.0,
        segment_duration: float = 3.0,
        use_mediapipe: bool = True,
        device: str = "cpu"
    ):
        """
        Initialize the Body Engine.

        Args:
            fps_target: Target frames per second for analysis (5-10 recommended)
            segment_duration: Duration for analysis segments in seconds
            use_mediapipe: Whether to use MediaPipe for pose estimation
            device: Compute device ("cpu" or "cuda")
        """
        logger.info("Initializing Body Engine...")

        self.fps_target = fps_target
        self.segment_duration = segment_duration
        self.device = device

        # Initialize sub-analyzers
        self.gesture_analyzer = GestureAnalyzer(
            use_mediapipe=use_mediapipe,
            device=device
        )

        self.stage_presence_analyzer = StagePresenceAnalyzer(
            use_mediapipe=use_mediapipe
        )

        self.eye_contact_detector = EyeContactDetector(
            use_mediapipe=use_mediapipe
        )

        self.alignment_scorer = AlignmentScorer()

        # Calibrated weights based on POTS criteria
        # Gesture intentionality is weighted highest as it most
        # directly measures "does movement serve the piece"
        self.weights = {
            'gesture': 0.35,
            'stage_presence': 0.30,
            'eye_contact': 0.20,
            'alignment': 0.15
        }

        logger.info("Body Engine initialized")

    def analyze(
        self,
        video_path: str,
        audio_energy_curve: Optional[np.ndarray] = None,
        audio_timestamps: Optional[np.ndarray] = None
    ) -> BodyAnalysisResult:
        """
        Perform complete Body analysis on a video performance.

        Args:
            video_path: Path to video file
            audio_energy_curve: Optional energy curve from Chest Engine for alignment
            audio_timestamps: Timestamps corresponding to energy curve

        Returns:
            BodyAnalysisResult with scores and detailed analysis
        """
        start_time = time.time()
        logger.info(f"Starting Body analysis for: {video_path}")

        # Step 1: Extract frames and video metadata
        logger.info("Extracting video frames...")
        frames_data = self._extract_frames(video_path)

        if not frames_data['frames']:
            logger.warning("No frames extracted - returning minimal result")
            return self._create_minimal_result(video_path, 0.0)

        video_duration = frames_data['duration']
        frames = frames_data['frames']
        timestamps = frames_data['timestamps']

        logger.info(f"Extracted {len(frames)} frames over {video_duration:.1f}s")

        # Step 2: Run pose estimation on all frames
        logger.info("Running pose estimation...")
        pose_data = self.gesture_analyzer.estimate_poses(frames, timestamps)

        # Step 3: Analyze gestures
        logger.info("Analyzing gestures...")
        gesture_result = self.gesture_analyzer.analyze(pose_data, timestamps)

        # Step 4: Analyze stage presence
        logger.info("Analyzing stage presence...")
        stage_result = self.stage_presence_analyzer.analyze(pose_data, timestamps)

        # Step 5: Detect eye contact
        logger.info("Detecting eye contact...")
        eye_result = self.eye_contact_detector.analyze(frames, timestamps)

        # Step 6: Score physical-vocal alignment (if audio data provided)
        logger.info("Scoring physical-vocal alignment...")
        alignment_result = self.alignment_scorer.analyze(
            pose_data,
            timestamps,
            audio_energy_curve,
            audio_timestamps
        )

        # Step 7: Create segment-level analysis
        logger.info("Creating segment analysis...")
        segments = self._create_segments(
            video_duration,
            gesture_result,
            stage_result,
            eye_result,
            alignment_result
        )

        # Step 8: Calculate component scores
        gesture_score = gesture_result['overall_score']
        stage_presence_score = stage_result['overall_score']
        eye_contact_score = eye_result['overall_score']
        alignment_score = alignment_result['overall_score']

        # Step 9: Calculate overall Body score
        component_scores = {
            'gesture': gesture_score,
            'stage_presence': stage_presence_score,
            'eye_contact': eye_contact_score,
            'alignment': alignment_score
        }

        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Convert to 1-5 scale
        overall_score = self._normalize_to_5_scale(overall_normalized)

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(f"Body analysis complete. Score: {overall_score:.2f}/5 ({processing_time_ms:.0f}ms)")

        # Collect feedback moments
        weak_moments = self._identify_weak_moments(segments, gesture_result, eye_result)
        strong_moments = self._identify_strong_moments(segments, gesture_result, eye_result)

        return BodyAnalysisResult(
            overall_score=overall_score,
            gesture_score=gesture_score,
            stage_presence_score=stage_presence_score,
            eye_contact_score=eye_contact_score,
            alignment_score=alignment_score,
            segments=segments,
            gesture_events=gesture_result.get('events', []),
            movement_heatmap=stage_result.get('heatmap'),
            avg_movement=stage_result.get('avg_movement', 0.0),
            movement_variance=stage_result.get('movement_variance', 0.0),
            processing_time_ms=processing_time_ms,
            video_duration=video_duration,
            frames_analyzed=len(frames),
            weak_moments=weak_moments,
            strong_moments=strong_moments,
            fps_analyzed=self.fps_target
        )

    def _extract_frames(self, video_path: str) -> Dict[str, Any]:
        """
        Extract frames from video at target FPS.

        Returns dict with:
            - frames: List of numpy arrays (BGR format)
            - timestamps: List of timestamps in seconds
            - duration: Video duration
            - fps_original: Original video FPS
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available - using fallback")
            return self._fallback_frame_extraction(video_path)

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            logger.error(f"Could not open video: {video_path}")
            return {'frames': [], 'timestamps': [], 'duration': 0.0, 'fps_original': 0.0}

        fps_original = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps_original if fps_original > 0 else 0

        # Calculate frame skip to achieve target FPS
        frame_skip = max(1, int(fps_original / self.fps_target))

        frames = []
        timestamps = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_skip == 0:
                frames.append(frame)
                timestamps.append(frame_idx / fps_original)

            frame_idx += 1

        cap.release()

        logger.debug(f"Extracted {len(frames)} frames (skip={frame_skip}, original_fps={fps_original:.1f})")

        return {
            'frames': frames,
            'timestamps': timestamps,
            'duration': duration,
            'fps_original': fps_original
        }

    def _fallback_frame_extraction(self, video_path: str) -> Dict[str, Any]:
        """Fallback when OpenCV is not available."""
        logger.warning("Using fallback frame extraction - limited functionality")
        # Return empty data - analysis will use fallback scoring
        return {'frames': [], 'timestamps': [], 'duration': 0.0, 'fps_original': 0.0}

    def _create_segments(
        self,
        duration: float,
        gesture_result: Dict,
        stage_result: Dict,
        eye_result: Dict,
        alignment_result: Dict
    ) -> List[BodySegment]:
        """Create time-segmented analysis matching 3-second windows."""
        segments = []

        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            start = i * self.segment_duration
            end = min((i + 1) * self.segment_duration, duration)

            # Get segment-specific metrics from each analyzer
            gesture_seg = gesture_result.get('segments', {}).get(i, {})
            stage_seg = stage_result.get('segments', {}).get(i, {})
            eye_seg = eye_result.get('segments', {}).get(i, {})
            align_seg = alignment_result.get('segments', {}).get(i, {})

            segment = BodySegment(
                start_time=start,
                end_time=end,
                gesture_count=gesture_seg.get('count', 0),
                intentional_ratio=gesture_seg.get('intentional_ratio', 0.5),
                gesture_diversity=gesture_seg.get('diversity', 0.0),
                movement_amount=stage_seg.get('movement', 0.0),
                position_stability=stage_seg.get('stability', 0.5),
                space_usage=stage_seg.get('space_usage', 0.0),
                eye_contact_ratio=eye_seg.get('contact_ratio', 0.0),
                gaze_stability=eye_seg.get('gaze_stability', 0.5),
                physical_energy=align_seg.get('physical_energy', 0.5)
            )
            segments.append(segment)

        return segments

    def _identify_weak_moments(
        self,
        segments: List[BodySegment],
        gesture_result: Dict,
        eye_result: Dict
    ) -> List[Dict[str, Any]]:
        """Identify moments that need improvement for coaching feedback."""
        weak_moments = []

        for i, seg in enumerate(segments):
            # Low intentional gesture ratio
            if seg.intentional_ratio < 0.3:
                weak_moments.append({
                    'time': seg.start_time,
                    'type': 'nervous_gestures',
                    'score': seg.intentional_ratio,
                    'description': f"Segment shows nervous fidgeting (intentionality: {seg.intentional_ratio:.1%})"
                })

            # Poor eye contact
            if seg.eye_contact_ratio < 0.2:
                weak_moments.append({
                    'time': seg.start_time,
                    'type': 'low_eye_contact',
                    'score': seg.eye_contact_ratio,
                    'description': f"Limited audience eye contact ({seg.eye_contact_ratio:.1%} of time)"
                })

            # No movement when standing
            if seg.movement_amount < 0.1 and seg.space_usage < 0.2:
                weak_moments.append({
                    'time': seg.start_time,
                    'type': 'static_position',
                    'score': seg.movement_amount,
                    'description': "Very static - consider using more of the stage"
                })

        return weak_moments

    def _identify_strong_moments(
        self,
        segments: List[BodySegment],
        gesture_result: Dict,
        eye_result: Dict
    ) -> List[Dict[str, Any]]:
        """Identify moments of excellence for positive feedback."""
        strong_moments = []

        for i, seg in enumerate(segments):
            # High intentional gestures
            if seg.intentional_ratio > 0.7 and seg.gesture_count > 0:
                strong_moments.append({
                    'time': seg.start_time,
                    'type': 'intentional_gestures',
                    'score': seg.intentional_ratio,
                    'description': f"Strong, intentional movement (intentionality: {seg.intentional_ratio:.1%})"
                })

            # Strong eye contact
            if seg.eye_contact_ratio > 0.6:
                strong_moments.append({
                    'time': seg.start_time,
                    'type': 'strong_eye_contact',
                    'score': seg.eye_contact_ratio,
                    'description': f"Excellent audience engagement ({seg.eye_contact_ratio:.1%} eye contact)"
                })

            # Good stage usage
            if seg.space_usage > 0.5 and seg.position_stability > 0.6:
                strong_moments.append({
                    'time': seg.start_time,
                    'type': 'good_stage_presence',
                    'score': (seg.space_usage + seg.position_stability) / 2,
                    'description': "Confident use of stage space with controlled movement"
                })

        return strong_moments

    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        score = max(0.0, min(1.0, score))
        return 1.0 + score * 4.0

    def _create_minimal_result(self, video_path: str, duration: float) -> BodyAnalysisResult:
        """Create a minimal result when analysis fails."""
        return BodyAnalysisResult(
            overall_score=1.0,
            gesture_score=0.0,
            stage_presence_score=0.0,
            eye_contact_score=0.0,
            alignment_score=0.0,
            segments=[],
            gesture_events=[],
            movement_heatmap=None,
            avg_movement=0.0,
            movement_variance=0.0,
            processing_time_ms=0.0,
            video_duration=duration,
            frames_analyzed=0,
            weak_moments=[],
            strong_moments=[],
            fps_analyzed=self.fps_target
        )

    def generate_feedback(self, result: BodyAnalysisResult) -> str:
        """
        Generate coach-style feedback based on analysis results.

        Uses the POTS guidebook voice - direct, encouraging, focused on growth.
        """
        score = result.overall_score

        # Build feedback based on score range
        if score >= 4.5:
            opening = "Your body language is COMMANDING the stage! Every gesture serves your piece."
        elif score >= 3.5:
            opening = "Strong physical presence. Your body is engaged with your words."
        elif score >= 2.5:
            opening = "Your body language needs more intentionality. Let's make every movement count."
        else:
            opening = "We need to wake up your body! Your physicality isn't supporting your words yet."

        feedback_parts = [opening]

        # Add specific feedback on gestures
        if result.gesture_score < 0.4:
            feedback_parts.append(
                "\nWatch for nervous fidgeting - hands in pockets, swaying, touching your face. "
                "Each gesture should serve the imagery in your piece."
            )
        elif result.gesture_score > 0.7:
            feedback_parts.append(
                "\nYour gestures are intentional and purposeful - great work!"
            )

        # Stage presence feedback
        if result.stage_presence_score < 0.4:
            feedback_parts.append(
                "\nOwn your space! Don't be rooted to one spot. "
                "Move with purpose and use the full stage."
            )

        # Eye contact feedback
        if result.eye_contact_score < 0.4:
            feedback_parts.append(
                "\nYour eyes need to connect with the audience. "
                "Don't look down or fix on one spot - engage the whole room."
            )
        elif result.eye_contact_score > 0.7:
            feedback_parts.append(
                "\nExcellent eye contact! You're truly connecting with your audience."
            )

        # Add specific weak moment feedback
        if result.weak_moments:
            worst = min(result.weak_moments, key=lambda x: x['score'])
            feedback_parts.append(
                f"\nAt {worst['time']:.1f}s: {worst['description']}"
            )

        # Highlight strengths
        if result.strong_moments:
            best = max(result.strong_moments, key=lambda x: x['score'])
            feedback_parts.append(
                f"\nStrong moment at {best['time']:.1f}s - {best['description']}. More of that!"
            )

        return "\n".join(feedback_parts)


def analyze_body(
    video_path: str,
    audio_energy_curve: Optional[np.ndarray] = None,
    audio_timestamps: Optional[np.ndarray] = None
) -> BodyAnalysisResult:
    """
    Convenience function for Body analysis.

    Args:
        video_path: Path to video file
        audio_energy_curve: Optional energy curve from audio analysis
        audio_timestamps: Timestamps for energy curve

    Returns:
        BodyAnalysisResult with complete analysis
    """
    engine = BodyEngine()
    return engine.analyze(video_path, audio_energy_curve, audio_timestamps)

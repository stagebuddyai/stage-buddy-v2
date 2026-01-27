"""
Stage Buddy V2 - Chest Engine
Main module that orchestrates vocal technique analysis and calculates Chest scores.

The Chest score measures the technical vocal delivery of a spoken word performance:
- Breath Control (35%) - Foundation of vocal technique
- Projection (35%) - Volume and energy to reach the audience
- Pause Technique (20%) - Strategic use of silence (beats, breaths, breaks)
- Vocal Health (10%) - Strain detection and consistency

Based on the POTS S.T.A.R.R. framework for spoken word performance evaluation.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np
import logging
import time

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from ..shared.data_structures import (
    ChestAnalysisResult, ChestSegment, BreathEvent, PauseEvent, PauseType,
    WordSegment, ProsodyFeatures
)

# Import sub-modules (will be created next)
from .breath_analyzer import BreathAnalyzer
from .projection_analyzer import ProjectionAnalyzer
from .pause_detector import PauseDetector
from .vocal_health_monitor import VocalHealthMonitor

logger = logging.getLogger(__name__)


class ChestEngine:
    """
    The Chest Engine analyzes vocal technique in spoken word performances.

    It answers the question: "Does the performer have strong vocal technique?"

    The engine:
    1. Analyzes breath control (invisible breathing, no gasping)
    2. Measures projection (volume, energy, dynamic range)
    3. Evaluates pause technique (strategic beats, breaths, breaks)
    4. Monitors vocal health (strain detection, fatigue)
    5. Produces a Chest score (1-5) with detailed feedback
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        segment_duration: float = 3.0
    ):
        """
        Initialize the Chest Engine.

        Args:
            sample_rate: Audio sample rate for processing
            segment_duration: Duration of analysis segments in seconds
        """
        logger.info("Initializing Chest Engine...")

        self.sample_rate = sample_rate
        self.segment_duration = segment_duration

        # Initialize sub-analyzers
        self.breath_analyzer = BreathAnalyzer(sample_rate=sample_rate)
        self.projection_analyzer = ProjectionAnalyzer(sample_rate=sample_rate)
        self.pause_detector = PauseDetector(sample_rate=sample_rate)
        self.health_monitor = VocalHealthMonitor(sample_rate=sample_rate)

        # Calibrated weights (from CHEST_ENGINE_DESIGN.md)
        # These will be tuned during calibration phase
        self.weights = {
            'breath_control': 0.35,
            'projection': 0.35,
            'pause_technique': 0.20,
            'vocal_health': 0.10
        }

        logger.info("Chest Engine initialized")

    def analyze(
        self,
        audio_path: str,
        transcript: Optional[str] = None,
        word_segments: Optional[List[WordSegment]] = None,
        prosody_features: Optional[List[ProsodyFeatures]] = None
    ) -> ChestAnalysisResult:
        """
        Perform complete Chest analysis on a performance.

        Args:
            audio_path: Path to audio file (or video - will extract audio)
            transcript: Optional transcript text (for pause alignment)
            word_segments: Optional word-level timing (from Spirit Engine)
            prosody_features: Optional pre-extracted prosody (from Spirit Engine)

        Returns:
            ChestAnalysisResult with scores and detailed analysis
        """
        start_time = time.time()
        logger.info(f"Starting Chest analysis for: {audio_path}")

        # Load audio
        audio, sr = self._load_audio(audio_path)
        duration = len(audio) / sr

        logger.info(f"Audio loaded: {duration:.1f}s at {sr}Hz")

        # Step 1: Analyze breath control
        logger.info("Analyzing breath control...")
        breath_result = self.breath_analyzer.analyze(audio, sr)
        breath_events = breath_result['events']
        breath_score = breath_result['score']

        # Step 2: Analyze projection
        logger.info("Analyzing projection...")
        projection_result = self.projection_analyzer.analyze(audio, sr)
        projection_score = projection_result['score']
        energy_curve = projection_result['energy_curve']
        energy_timestamps = projection_result['timestamps']

        # Step 3: Detect and analyze pauses
        logger.info("Analyzing pause technique...")
        pause_result = self.pause_detector.analyze(
            audio, sr, word_segments=word_segments
        )
        pause_events = pause_result['events']
        pause_score = pause_result['score']

        # Step 4: Monitor vocal health
        logger.info("Monitoring vocal health...")
        health_result = self.health_monitor.analyze(
            audio, sr, prosody_features=prosody_features
        )
        health_score = health_result['score']
        fatigue_detected = health_result['fatigue_detected']
        fatigue_onset = health_result.get('fatigue_onset_time')

        # Step 5: Build segment-level analysis
        segments = self._build_segments(
            audio, sr,
            breath_result, projection_result, health_result
        )

        # Step 6: Calculate overall Chest score
        component_scores = {
            'breath_control': breath_score,
            'projection': projection_score,
            'pause_technique': pause_score,
            'vocal_health': health_score
        }

        overall_normalized = sum(
            score * self.weights[component]
            for component, score in component_scores.items()
        )

        # Convert to 1-5 scale
        overall_score = self._normalize_to_5_scale(overall_normalized)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # ms

        logger.info(f"Chest analysis complete. Score: {overall_score:.2f}/5 ({processing_time:.0f}ms)")

        # Build feedback data
        strength_moments, improvement_areas = self._identify_feedback_moments(
            breath_events, pause_events, projection_result, health_result
        )

        return ChestAnalysisResult(
            overall_score=overall_score,
            breath_control_score=breath_score,
            projection_score=projection_score,
            pause_technique_score=pause_score,
            vocal_health_score=health_score,
            segments=segments,
            breath_events=breath_events,
            pause_events=pause_events,
            energy_curve=energy_curve,
            energy_timestamps=energy_timestamps,
            fatigue_detected=fatigue_detected,
            fatigue_onset_time=fatigue_onset,
            strength_moments=strength_moments,
            improvement_areas=improvement_areas,
            processing_time_ms=processing_time,
            audio_duration=duration
        )

    def _load_audio(self, audio_path: str) -> tuple:
        """Load audio from file, extracting from video if necessary."""
        if not LIBROSA_AVAILABLE:
            raise RuntimeError("librosa is required for audio loading")

        path = Path(audio_path)

        # Check if video file - extract audio first
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        if path.suffix.lower() in video_extensions:
            audio_path = self._extract_audio_from_video(audio_path)

        # Load with librosa
        audio, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
        return audio, sr

    def _extract_audio_from_video(self, video_path: str) -> str:
        """Extract audio from video file using ffmpeg."""
        import subprocess
        import tempfile

        # Create temp file for audio
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio.close()

        try:
            cmd = [
                'ffmpeg', '-y', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', str(self.sample_rate),
                '-ac', '1',  # Mono
                temp_audio.name
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return temp_audio.name
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}")

    def _build_segments(
        self,
        audio: np.ndarray,
        sr: int,
        breath_result: Dict,
        projection_result: Dict,
        health_result: Dict
    ) -> List[ChestSegment]:
        """Build segment-level analysis for the performance."""
        segments = []
        duration = len(audio) / sr
        current_time = 0.0

        while current_time < duration:
            segment_end = min(current_time + self.segment_duration, duration)

            # Get segment audio
            start_sample = int(current_time * sr)
            end_sample = int(segment_end * sr)
            segment_audio = audio[start_sample:end_sample]

            if len(segment_audio) < sr * 0.5:
                current_time += self.segment_duration
                continue

            # Calculate segment metrics
            rms = np.sqrt(np.mean(segment_audio ** 2))
            loudness_db = 20 * np.log10(rms + 1e-10)
            energy_var = np.var(segment_audio ** 2)

            # Check for breath events in this segment
            breath_in_segment = [
                e for e in breath_result['events']
                if current_time <= e.timestamp < segment_end
            ]
            breath_detected = len(breath_in_segment) > 0
            breath_type = breath_in_segment[0].breath_quality if breath_in_segment else None

            # Get health metrics for segment (simplified)
            strain_level = health_result.get('strain_level', 0.0)

            segments.append(ChestSegment(
                start_time=current_time,
                end_time=segment_end,
                rms_energy=float(rms),
                loudness_db=float(loudness_db),
                energy_variance=float(energy_var),
                breath_detected=breath_detected,
                breath_type=breath_type,
                voicing_ratio=0.0,  # Will be populated by pause_detector
                pitch_stability=0.0,  # Will be populated by health_monitor
                strain_level=strain_level,
                jitter=0.0,
                shimmer=0.0
            ))

            current_time += self.segment_duration

        return segments

    def _identify_feedback_moments(
        self,
        breath_events: List[BreathEvent],
        pause_events: List[PauseEvent],
        projection_result: Dict,
        health_result: Dict
    ) -> tuple:
        """Identify specific moments for coach feedback."""
        strengths = []
        improvements = []

        # Breath feedback
        controlled_breaths = [e for e in breath_events if e.breath_quality == 'controlled']
        gasping_breaths = [e for e in breath_events if e.breath_quality == 'gasping']

        if controlled_breaths and not gasping_breaths:
            strengths.append({
                'category': 'breath_control',
                'description': 'Excellent breath control - breathing is invisible to audience',
                'score_impact': '+0.2'
            })

        if gasping_breaths:
            worst = max(gasping_breaths, key=lambda e: e.energy_dip)
            improvements.append({
                'category': 'breath_control',
                'time': worst.timestamp,
                'description': f'Audible gasp at {worst.timestamp:.1f}s - practice diaphragmatic breathing',
                'score_impact': '-0.1'
            })

        # Projection feedback
        dynamic_range = projection_result.get('dynamic_range_db', 0)
        if dynamic_range >= 15:
            strengths.append({
                'category': 'projection',
                'description': f'Strong dynamic range ({dynamic_range:.1f}dB) - excellent vocal variety',
                'score_impact': '+0.15'
            })
        elif dynamic_range < 10:
            improvements.append({
                'category': 'projection',
                'description': f'Limited dynamic range ({dynamic_range:.1f}dB) - add more vocal variety',
                'score_impact': '-0.1'
            })

        # Pause feedback
        strategic_pauses = [p for p in pause_events if p.at_punctuation or p.at_line_break]
        if len(strategic_pauses) > len(pause_events) * 0.7:
            strengths.append({
                'category': 'pause_technique',
                'description': 'Strategic pause placement - pauses serve the piece',
                'score_impact': '+0.1'
            })

        # Health feedback
        if health_result.get('fatigue_detected'):
            improvements.append({
                'category': 'vocal_health',
                'time': health_result.get('fatigue_onset_time', 0),
                'description': 'Vocal fatigue detected - pace yourself and support with breath',
                'score_impact': '-0.15'
            })

        return strengths, improvements

    def _normalize_to_5_scale(self, score: float) -> float:
        """Convert a 0-1 score to a 1-5 scale."""
        score = max(0.0, min(1.0, score))
        return 1.0 + score * 4.0

    def generate_feedback(self, result: ChestAnalysisResult) -> str:
        """
        Generate coach-style feedback based on analysis results.

        Uses the POTS guidebook voice - direct, encouraging, focused on growth.
        """
        score = result.overall_score

        # Opening based on score
        if score >= 4.5:
            opening = "Your vocal technique is exceptional! The audience never hears you breathe, your projection fills the space, and your pauses are perfectly placed."
        elif score >= 3.5:
            opening = "Good technical foundation. Your projection and breath control show solid training."
        elif score >= 2.5:
            opening = "Your technique needs work. Let's focus on the fundamentals - breath support is everything."
        else:
            opening = "We need to build your technical foundation. Start with breath control - it's the base of everything else."

        feedback_parts = [opening]

        # Add specific improvements
        for improvement in result.improvement_areas[:3]:  # Top 3 issues
            feedback_parts.append(f"\n- {improvement['description']}")

        # Add encouragement from strengths
        if result.strength_moments:
            best = result.strength_moments[0]
            feedback_parts.append(f"\n\nStrength: {best['description']}")

        # Score breakdown
        feedback_parts.append(f"\n\nScore Breakdown:")
        feedback_parts.append(f"  Breath Control: {result.breath_control_score:.2f}")
        feedback_parts.append(f"  Projection: {result.projection_score:.2f}")
        feedback_parts.append(f"  Pause Technique: {result.pause_technique_score:.2f}")
        feedback_parts.append(f"  Vocal Health: {result.vocal_health_score:.2f}")

        return "\n".join(feedback_parts)


def analyze_chest(
    audio_path: str,
    transcript: Optional[str] = None,
    word_segments: Optional[List[WordSegment]] = None
) -> ChestAnalysisResult:
    """
    Convenience function for Chest analysis.

    Args:
        audio_path: Path to audio/video file
        transcript: Optional transcript text
        word_segments: Optional word-level timing

    Returns:
        ChestAnalysisResult with complete analysis
    """
    engine = ChestEngine()
    return engine.analyze(
        audio_path=audio_path,
        transcript=transcript,
        word_segments=word_segments
    )

"""
S.T.A.R.R. Orchestrator - Main Orchestration Logic

Coordinates all four analysis engines in the correct execution order:
1. Preprocessing: Extract audio, transcribe, generate word segments
2. Parallel analysis: Spirit + Chest + Body run simultaneously
3. Audience analysis: Runs last, receives results from other engines
4. Integration: Merge results into unified timeline and report

Engine weights (POTS methodology):
- Spirit: 30% (emotional authenticity)
- Chest: 25% (vocal technique)
- Body: 25% (physical performance)
- Audience: 20% (audience engagement)
"""

import logging
import time
import os
import subprocess
import tempfile
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

# Engine imports
from python.analysis_modules.spirit_engine import SpiritEngine
from python.analysis_modules.chest_engine import ChestEngine
from python.analysis_modules.body_engine import BodyEngine
from python.analysis_modules.audience_engine import AudienceEngine

# Data structure imports
from python.analysis_modules.shared.data_structures import (
    WordSegment,
    SpiritAnalysisResult,
    ChestAnalysisResult,
    BodyAnalysisResult,
    AudienceAnalysisResult,
    PerformanceTimeline,
    ProsodyFeatures,
)

from .timeline_builder import TimelineBuilder
from .report_generator import ReportGenerator, PerformanceReport
from .coach_feedback import CoachFeedbackGenerator

logger = logging.getLogger(__name__)


# Engine weight constants
ENGINE_WEIGHTS = {
    "spirit": 0.30,
    "chest": 0.25,
    "body": 0.25,
    "audience": 0.20,
}


@dataclass
class PreprocessingResult:
    """Output from the preprocessing stage."""
    audio_path: str
    transcript: str
    word_segments: List[WordSegment]
    duration_seconds: float
    video_path: str


@dataclass
class EngineResults:
    """Collected results from all four engines."""
    spirit: Optional[SpiritAnalysisResult] = None
    chest: Optional[ChestAnalysisResult] = None
    body: Optional[BodyAnalysisResult] = None
    audience: Optional[AudienceAnalysisResult] = None
    errors: Dict[str, str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = {}


class STARROrchestrator:
    """
    Main orchestrator that coordinates all S.T.A.R.R. analysis engines.

    Usage:
        orchestrator = STARROrchestrator()
        report = orchestrator.analyze("performance.mp4")
    """

    def __init__(
        self,
        use_openai: bool = False,
        openai_api_key: Optional[str] = None,
        max_workers: int = 3,
    ):
        """
        Initialize the S.T.A.R.R. Orchestrator.

        Args:
            use_openai: Whether to use OpenAI GPT for coach feedback
            openai_api_key: OpenAI API key (required if use_openai=True)
            max_workers: Max parallel threads for engine execution
        """
        self.max_workers = max_workers

        # Initialize engines
        self.spirit_engine = SpiritEngine()
        self.chest_engine = ChestEngine()
        self.body_engine = BodyEngine()
        self.audience_engine = AudienceEngine()

        # Initialize support modules
        self.timeline_builder = TimelineBuilder()
        self.report_generator = ReportGenerator()
        self.coach = CoachFeedbackGenerator(
            use_openai=use_openai,
            openai_api_key=openai_api_key,
        )

        logger.info("S.T.A.R.R. Orchestrator initialized with all four engines")

    def analyze(
        self,
        video_path: str,
        audio_path: Optional[str] = None,
        transcript: Optional[str] = None,
        word_segments: Optional[List[WordSegment]] = None,
    ) -> PerformanceReport:
        """
        Run the full S.T.A.R.R. analysis pipeline on a performance video.

        Pipeline stages:
        1. Preprocessing - extract audio, transcribe
        2. Parallel engine analysis - Spirit, Chest, Body
        3. Audience analysis - uses results from other engines
        4. Timeline integration - merge all results
        5. Report generation - scores, feedback, key moments

        Args:
            video_path: Path to the performance video file
            audio_path: Optional pre-extracted audio path (skips extraction)
            transcript: Optional pre-generated transcript (skips transcription)
            word_segments: Optional pre-generated word segments

        Returns:
            PerformanceReport with full analysis results
        """
        start_time = time.time()
        logger.info(f"Starting S.T.A.R.R. analysis for: {video_path}")

        # Stage 1: Preprocessing
        preprocessing = self._preprocess(
            video_path, audio_path, transcript, word_segments
        )
        logger.info(
            f"Preprocessing complete: {preprocessing.duration_seconds:.1f}s audio, "
            f"{len(preprocessing.word_segments)} word segments"
        )

        # Stage 2 & 3: Engine analysis (parallel + sequential)
        engine_results = self._run_engines(preprocessing)

        # Stage 4: Build unified timeline
        timeline = self.timeline_builder.build(
            preprocessing=preprocessing,
            engine_results=engine_results,
        )

        # Stage 5: Generate report
        processing_time_ms = (time.time() - start_time) * 1000
        report = self.report_generator.generate(
            timeline=timeline,
            engine_results=engine_results,
            coach=self.coach,
            video_path=video_path,
            processing_time_ms=processing_time_ms,
        )

        logger.info(
            f"S.T.A.R.R. analysis complete: overall={report.overall_score:.2f}/5 "
            f"({report.overall_grade}) in {processing_time_ms:.0f}ms"
        )

        return report

    def _preprocess(
        self,
        video_path: str,
        audio_path: Optional[str] = None,
        transcript: Optional[str] = None,
        word_segments: Optional[List[WordSegment]] = None,
    ) -> PreprocessingResult:
        """
        Extract audio and transcribe the performance.

        If audio_path, transcript, or word_segments are provided,
        those steps are skipped (useful for re-analysis).
        """
        # Step 1: Extract audio if not provided
        if audio_path is None:
            audio_path = self._extract_audio(video_path)

        # Step 2: Get audio duration
        duration = self._get_audio_duration(audio_path)

        # Step 3: Transcribe if not provided
        if transcript is None or word_segments is None:
            transcript, word_segments = self._transcribe(audio_path)

        return PreprocessingResult(
            audio_path=audio_path,
            transcript=transcript,
            word_segments=word_segments,
            duration_seconds=duration,
            video_path=video_path,
        )

    def _extract_audio(self, video_path: str) -> str:
        """Extract audio from video using FFmpeg."""
        audio_path = tempfile.mktemp(suffix=".wav")
        try:
            subprocess.run(
                [
                    "ffmpeg", "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1",
                    "-y", audio_path,
                ],
                capture_output=True,
                check=True,
                timeout=120,
            )
            logger.info(f"Audio extracted to: {audio_path}")
        except FileNotFoundError:
            logger.error("FFmpeg not found. Install ffmpeg for audio extraction.")
            raise RuntimeError(
                "FFmpeg is required for audio extraction. "
                "Install with: apt install ffmpeg"
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr.decode()}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")
        return audio_path

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            import librosa
            duration = librosa.get_duration(path=audio_path)
            return duration
        except ImportError:
            pass

        # Fallback: use ffprobe
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            logger.warning("Could not determine audio duration, estimating from file size")
            # Rough estimate: 16kHz, 16-bit mono = 32000 bytes/second
            file_size = os.path.getsize(audio_path)
            return file_size / 32000.0

    def _transcribe(self, audio_path: str) -> tuple:
        """
        Transcribe audio using Whisper.

        Returns:
            Tuple of (transcript_text, word_segments)
        """
        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                language="en",
            )

            transcript = result["text"].strip()
            word_segments = []

            for segment in result.get("segments", []):
                for word_info in segment.get("words", []):
                    word_segments.append(WordSegment(
                        word=word_info["word"].strip(),
                        start_time=word_info["start"],
                        end_time=word_info["end"],
                        confidence=word_info.get("probability", 0.9),
                    ))

            logger.info(
                f"Transcription complete: {len(word_segments)} words, "
                f"{len(transcript)} characters"
            )
            return transcript, word_segments

        except ImportError:
            logger.warning(
                "Whisper not available. Provide transcript and word_segments manually."
            )
            raise RuntimeError(
                "openai-whisper is required for transcription. "
                "Install with: pip install openai-whisper"
            )

    def _run_engines(self, preprocessing: PreprocessingResult) -> EngineResults:
        """
        Execute all four analysis engines.

        Execution order:
        - Phase A (parallel): Spirit, Chest, Body
        - Phase B (sequential): Audience (receives results from Phase A)
        """
        results = EngineResults()

        # Phase A: Run Spirit, Chest, and Body in parallel
        logger.info("Phase A: Running Spirit, Chest, and Body engines in parallel")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._run_spirit, preprocessing
                ): "spirit",
                executor.submit(
                    self._run_chest, preprocessing
                ): "chest",
                executor.submit(
                    self._run_body, preprocessing
                ): "body",
            }

            for future in as_completed(futures):
                engine_name = futures[future]
                try:
                    result = future.result()
                    setattr(results, engine_name, result)
                    score = result.overall_score if result else 0
                    logger.info(f"  {engine_name.capitalize()} Engine: {score:.2f}/5")
                except Exception as e:
                    logger.error(f"  {engine_name.capitalize()} Engine failed: {e}")
                    results.errors[engine_name] = str(e)

        # Phase B: Run Audience engine with cross-engine data
        logger.info("Phase B: Running Audience engine with cross-engine data")
        try:
            results.audience = self._run_audience(preprocessing, results)
            score = results.audience.overall_score if results.audience else 0
            logger.info(f"  Audience Engine: {score:.2f}/5")
        except Exception as e:
            logger.error(f"  Audience Engine failed: {e}")
            results.errors["audience"] = str(e)

        return results

    def _run_spirit(self, preprocessing: PreprocessingResult) -> SpiritAnalysisResult:
        """Run Spirit Engine analysis."""
        return self.spirit_engine.analyze(
            audio_path=preprocessing.audio_path,
            transcript=preprocessing.transcript,
            word_segments=preprocessing.word_segments,
        )

    def _run_chest(self, preprocessing: PreprocessingResult) -> ChestAnalysisResult:
        """Run Chest Engine analysis."""
        return self.chest_engine.analyze(
            audio_path=preprocessing.audio_path,
            transcript=preprocessing.transcript,
            word_segments=preprocessing.word_segments,
        )

    def _run_body(self, preprocessing: PreprocessingResult) -> BodyAnalysisResult:
        """Run Body Engine analysis."""
        return self.body_engine.analyze(
            video_path=preprocessing.video_path,
        )

    def _run_audience(
        self,
        preprocessing: PreprocessingResult,
        prior_results: EngineResults,
    ) -> AudienceAnalysisResult:
        """
        Run Audience Engine analysis with cross-engine data.

        The Audience Engine benefits from other engines' outputs:
        - spirit_result: Enhances emotional invitation scoring
        - body_result: Enhances engagement pattern detection
        - pause_events: From Chest Engine, enhances pacing analysis
        - loudness_curve: From Chest Engine, enhances engagement patterns
        """
        # Extract cross-engine data
        pause_events = None
        loudness_curve = None
        prosody_features = None

        if prior_results.chest:
            pause_events = prior_results.chest.pause_events
            loudness_curve = prior_results.chest.energy_curve

        if prior_results.spirit and prior_results.spirit.prosody_features:
            prosody_features = prior_results.spirit.prosody_features

        return self.audience_engine.analyze(
            video_path=preprocessing.video_path,
            audio_path=preprocessing.audio_path,
            transcript=preprocessing.transcript,
            word_segments=preprocessing.word_segments,
            spirit_result=prior_results.spirit,
            body_result=prior_results.body,
            pause_events=pause_events,
            loudness_curve=loudness_curve,
            prosody_features=prosody_features,
        )

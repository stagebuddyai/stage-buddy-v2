"""
Performance Analyzer - Unified Analysis Pipeline

Provides a simplified interface for analyzing performances,
handling file validation, configuration, and result caching.
"""

import logging
import os
from typing import Optional, List

from python.analysis_modules.shared.data_structures import WordSegment

from .starr_orchestrator import STARROrchestrator
from .report_generator import PerformanceReport

logger = logging.getLogger(__name__)

# Supported video/audio formats
SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


class PerformanceAnalyzer:
    """
    High-level interface for performance analysis.

    Wraps STARROrchestrator with input validation and convenience methods.

    Usage:
        analyzer = PerformanceAnalyzer()
        report = analyzer.analyze_video("performance.mp4")
        print(report.to_json())
    """

    def __init__(
        self,
        use_openai: bool = False,
        openai_api_key: Optional[str] = None,
        max_workers: int = 3,
    ):
        self.orchestrator = STARROrchestrator(
            use_openai=use_openai,
            openai_api_key=openai_api_key,
            max_workers=max_workers,
        )

    def analyze_video(
        self,
        video_path: str,
        transcript: Optional[str] = None,
        word_segments: Optional[List[WordSegment]] = None,
    ) -> PerformanceReport:
        """
        Analyze a video performance through the full S.T.A.R.R. pipeline.

        Args:
            video_path: Path to video file (.mp4, .avi, .mov, .mkv, .webm)
            transcript: Optional pre-generated transcript
            word_segments: Optional pre-generated word segments

        Returns:
            PerformanceReport with scores, feedback, and timeline

        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video format is not supported
        """
        self._validate_video(video_path)

        return self.orchestrator.analyze(
            video_path=video_path,
            transcript=transcript,
            word_segments=word_segments,
        )

    def analyze_audio(
        self,
        audio_path: str,
        transcript: Optional[str] = None,
        word_segments: Optional[List[WordSegment]] = None,
    ) -> PerformanceReport:
        """
        Analyze an audio-only performance (no Body Engine analysis).

        Args:
            audio_path: Path to audio file (.wav, .mp3, .flac, .ogg, .m4a)
            transcript: Optional pre-generated transcript
            word_segments: Optional pre-generated word segments

        Returns:
            PerformanceReport (body scores will be defaults)
        """
        self._validate_audio(audio_path)

        return self.orchestrator.analyze(
            video_path=audio_path,  # Body engine will gracefully handle audio-only
            audio_path=audio_path,
            transcript=transcript,
            word_segments=word_segments,
        )

    def analyze_with_preprocessing(
        self,
        video_path: str,
        audio_path: str,
        transcript: str,
        word_segments: List[WordSegment],
    ) -> PerformanceReport:
        """
        Analyze with all preprocessing already done.

        Use this when you've already extracted audio, transcribed,
        and generated word segments (e.g., from a previous analysis
        or external transcription service).

        Args:
            video_path: Path to video file
            audio_path: Path to extracted audio
            transcript: Full transcript text
            word_segments: Word-level timing segments

        Returns:
            PerformanceReport
        """
        return self.orchestrator.analyze(
            video_path=video_path,
            audio_path=audio_path,
            transcript=transcript,
            word_segments=word_segments,
        )

    def _validate_video(self, video_path: str) -> None:
        """Validate video file exists and format is supported."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        ext = os.path.splitext(video_path)[1].lower()
        if ext not in SUPPORTED_VIDEO_FORMATS:
            raise ValueError(
                f"Unsupported video format: {ext}. "
                f"Supported: {', '.join(sorted(SUPPORTED_VIDEO_FORMATS))}"
            )

    def _validate_audio(self, audio_path: str) -> None:
        """Validate audio file exists and format is supported."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        ext = os.path.splitext(audio_path)[1].lower()
        if ext not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {ext}. "
                f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
            )

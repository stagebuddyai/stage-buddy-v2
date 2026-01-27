"""
Stage Buddy V2 - Chest Engine: Pause Detector
Detects and evaluates strategic use of silence in spoken word performances.

Pause technique follows the POTS beat/breath/break system (20% of Chest score):
- MICRO (<0.5s): Natural speech rhythm
- BEAT (0.5-1.0s): Separates ideas/images
- BREATH (1.0-2.0s): Sentence boundary + inhale
- BREAK (3.0+s): Dramatic pause between sections

Excellence: Pauses are strategic - beats separate ideas, breaks create tension
Weakness: Pauses feel accidental, rushed delivery, or awkward silence
"""

from typing import List, Dict, Any, Optional
import numpy as np
import logging

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from ..shared.data_structures import PauseEvent, PauseType, WordSegment

logger = logging.getLogger(__name__)


class PauseDetector:
    """
    Detects and classifies pauses in spoken word performances.

    Detection approach:
    1. Use energy-based voice activity detection
    2. Find silence regions (below energy threshold)
    3. Classify by duration (micro/beat/breath/break)
    4. If transcript available, check pause alignment with punctuation
    5. Score based on strategic placement
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        energy_threshold_percentile: float = 20.0,
        min_pause_duration: float = 0.2
    ):
        """
        Initialize the Pause Detector.

        Args:
            sample_rate: Audio sample rate
            energy_threshold_percentile: Percentile for silence detection
            min_pause_duration: Minimum duration to count as pause
        """
        self.sample_rate = sample_rate
        self.energy_threshold_percentile = energy_threshold_percentile
        self.min_pause_duration = min_pause_duration

        # Frame parameters
        self.frame_length = int(0.025 * sample_rate)  # 25ms
        self.hop_length = int(0.010 * sample_rate)    # 10ms

        # POTS pause durations
        self.pause_thresholds = {
            'micro': (0.0, 0.5),
            'beat': (0.5, 1.0),
            'breath': (1.0, 2.0),
            'break': (3.0, float('inf'))
        }

    def analyze(
        self,
        audio: np.ndarray,
        sr: int,
        word_segments: Optional[List[WordSegment]] = None
    ) -> Dict[str, Any]:
        """
        Analyze pause technique in audio.

        Args:
            audio: Audio signal (mono)
            sr: Sample rate
            word_segments: Optional word-level timing for alignment

        Returns:
            Dict with 'events' (List[PauseEvent]) and 'score' (float 0-1)
        """
        # Step 1: Detect silence regions
        silence_regions = self._detect_silence_regions(audio, sr)

        # Step 2: Convert to pause events with classification
        pause_events = []
        for start_time, duration in silence_regions:
            if duration < self.min_pause_duration:
                continue

            pause_type = self._classify_pause_duration(duration)

            # Check alignment with transcript if available
            at_punctuation = False
            at_line_break = False
            preceding_word = None
            following_word = None

            if word_segments:
                at_punctuation, at_line_break, preceding_word, following_word = \
                    self._check_transcript_alignment(start_time, word_segments)

            pause_events.append(PauseEvent(
                pause_type=pause_type,
                start_time=start_time,
                duration=duration,
                preceding_word=preceding_word,
                following_word=following_word,
                at_punctuation=at_punctuation,
                at_line_break=at_line_break
            ))

        # Step 3: Calculate score
        score = self._calculate_score(pause_events, len(audio) / sr)

        # Count by type
        type_counts = {
            'micro': len([p for p in pause_events if p.pause_type == PauseType.MICRO]),
            'beat': len([p for p in pause_events if p.pause_type == PauseType.BEAT]),
            'breath': len([p for p in pause_events if p.pause_type == PauseType.BREATH]),
            'break': len([p for p in pause_events if p.pause_type == PauseType.BREAK])
        }

        strategic_count = len([p for p in pause_events if p.at_punctuation or p.at_line_break])

        logger.info(
            f"Detected {len(pause_events)} pauses "
            f"(beat={type_counts['beat']}, breath={type_counts['breath']}, break={type_counts['break']}), "
            f"score={score:.2f}"
        )

        return {
            'events': pause_events,
            'score': score,
            'type_counts': type_counts,
            'strategic_count': strategic_count,
            'total_pause_time': sum(p.duration for p in pause_events)
        }

    def _detect_silence_regions(
        self,
        audio: np.ndarray,
        sr: int
    ) -> List[tuple]:
        """Detect regions of silence in the audio."""
        if LIBROSA_AVAILABLE:
            # Use librosa for RMS energy
            rms = librosa.feature.rms(
                y=audio,
                frame_length=self.frame_length,
                hop_length=self.hop_length
            )[0]

            times = librosa.frames_to_time(
                np.arange(len(rms)),
                sr=sr,
                hop_length=self.hop_length
            )
        else:
            # Fallback energy calculation
            rms = []
            times = []
            for i in range(0, len(audio) - self.frame_length, self.hop_length):
                frame = audio[i:i + self.frame_length]
                rms.append(np.sqrt(np.mean(frame ** 2)))
                times.append(i / sr)
            rms = np.array(rms)
            times = np.array(times)

        # Find threshold
        threshold = np.percentile(rms, self.energy_threshold_percentile)

        # Find silence regions
        silence_mask = rms < threshold
        silence_regions = []

        in_silence = False
        silence_start = 0

        for i, is_silent in enumerate(silence_mask):
            if is_silent and not in_silence:
                silence_start = i
                in_silence = True
            elif not is_silent and in_silence:
                in_silence = False
                start_time = times[silence_start]
                end_time = times[i]
                duration = end_time - start_time
                silence_regions.append((start_time, duration))

        # Handle trailing silence
        if in_silence:
            start_time = times[silence_start]
            end_time = times[-1]
            duration = end_time - start_time
            silence_regions.append((start_time, duration))

        return silence_regions

    def _classify_pause_duration(self, duration: float) -> PauseType:
        """Classify pause type based on duration using POTS system."""
        if duration < 0.5:
            return PauseType.MICRO
        elif duration < 1.0:
            return PauseType.BEAT
        elif duration < 2.0:
            return PauseType.BREATH
        else:
            return PauseType.BREAK

    def _check_transcript_alignment(
        self,
        pause_start: float,
        word_segments: List[WordSegment]
    ) -> tuple:
        """Check if pause aligns with punctuation or line break."""
        # Find the word before and after the pause
        preceding_word = None
        following_word = None
        at_punctuation = False
        at_line_break = False

        tolerance = 0.3  # 300ms tolerance for alignment

        for i, word in enumerate(word_segments):
            # Check if this word ends near the pause start
            if abs(word.end_time - pause_start) < tolerance:
                preceding_word = word.word

                # Check for punctuation at end of word
                if word.word and word.word[-1] in '.!?,;:':
                    at_punctuation = True

                # Check for line break indicators
                if word.word and word.word.endswith(('.', '!', '?')):
                    at_line_break = True

            # Check if this word starts after the pause
            if word.start_time > pause_start + 0.1 and following_word is None:
                following_word = word.word
                break

        return at_punctuation, at_line_break, preceding_word, following_word

    def _calculate_score(
        self,
        pause_events: List[PauseEvent],
        total_duration: float
    ) -> float:
        """
        Calculate pause technique score (0-1).

        Scoring:
        - Strategic pauses (at punctuation/breaks): +0.15 each
        - Good variety of pause types: +0.1
        - Too many awkward pauses: -0.1 each
        - No pauses (rushed): -0.2
        - Too many pauses (broken flow): -0.1
        """
        if not pause_events:
            # No pauses - rushed delivery
            return 0.4

        score = 0.5  # Base score

        # Count strategic vs non-strategic
        strategic = [p for p in pause_events if p.at_punctuation or p.at_line_break]
        non_strategic = [p for p in pause_events if not p.at_punctuation and not p.at_line_break]

        # Strategic pause bonus
        strategic_ratio = len(strategic) / len(pause_events) if pause_events else 0
        score += strategic_ratio * 0.3

        # Variety bonus - having different pause types is good
        pause_types = set(p.pause_type for p in pause_events)
        if len(pause_types) >= 3:
            score += 0.1

        # Pause density check
        total_pause_time = sum(p.duration for p in pause_events)
        pause_ratio = total_pause_time / total_duration if total_duration > 0 else 0

        # Ideal pause ratio is 10-25%
        if 0.10 <= pause_ratio <= 0.25:
            score += 0.1
        elif pause_ratio > 0.35:
            # Too much silence
            score -= 0.1
        elif pause_ratio < 0.05:
            # Too rushed
            score -= 0.1

        # Penalize awkward mid-sentence pauses (non-strategic beats)
        awkward_pauses = [
            p for p in non_strategic
            if p.pause_type in [PauseType.BEAT, PauseType.BREATH]
        ]
        awkward_penalty = len(awkward_pauses) * 0.03
        score -= min(0.2, awkward_penalty)

        return max(0.0, min(1.0, score))

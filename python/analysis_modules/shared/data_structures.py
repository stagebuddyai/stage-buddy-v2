"""
Stage Buddy V2 - Shared Data Structures
These dataclasses provide the unified timeline that all modules contribute to and read from.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import numpy as np


class EmotionCategory(Enum):
    """
    Emotion categories based on the Feelings Circle from POTS guidebook.
    Maps to both text sentiment and vocal emotion detection outputs.
    """
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    NEUTRAL = "neutral"
    # Extended emotions for nuance
    CALM = "calm"
    EXCITED = "excited"
    TENDER = "tender"
    DETERMINED = "determined"


class PauseType(Enum):
    """
    Pause classification based on POTS beat/breath/break system.
    """
    BEAT = "beat"        # 0.5-1.0 seconds - separates ideas/images
    BREATH = "breath"    # 1.0-2.0 seconds - sentence boundary + inhale
    BREAK = "break"      # 3.0+ seconds - dramatic pause between sections
    MICRO = "micro"      # < 0.5 seconds - natural speech rhythm
    

@dataclass
class WordSegment:
    """A single word from the transcript with timing information."""
    word: str
    start_time: float  # seconds
    end_time: float    # seconds
    confidence: float  # 0.0 to 1.0 from transcription
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass 
class EmotionSegment:
    """
    An emotional segment detected either from audio (vocal) or text (ideal).
    Used by Spirit Engine for emotion-word alignment scoring.
    """
    emotion: EmotionCategory
    intensity: float          # 0.0 to 1.0, how strong the emotion
    valence: float           # -1.0 (negative) to 1.0 (positive)
    arousal: float           # 0.0 (calm) to 1.0 (excited)
    start_time: float        # seconds
    end_time: float          # seconds
    confidence: float        # 0.0 to 1.0, model confidence
    source: str              # "vocal" (detected from audio) or "text" (predicted from words)
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class PauseEvent:
    """A detected pause in the performance."""
    pause_type: PauseType
    start_time: float
    duration: float
    # Context for scoring
    preceding_word: Optional[str] = None
    following_word: Optional[str] = None
    at_punctuation: bool = False  # Was this pause at a punctuation mark?
    at_line_break: bool = False   # Was this at a line/stanza break?
    
    @property
    def end_time(self) -> float:
        return self.start_time + self.duration


@dataclass
class ProsodyFeatures:
    """
    Low-level prosodic features extracted from audio for a time window.
    Populated by openSMILE feature extraction.
    """
    timestamp: float
    
    # Pitch (F0) features
    pitch_hz: float              # Fundamental frequency
    pitch_variance: float        # Local pitch variation
    
    # Energy/Loudness features
    loudness_db: float           # dB level
    loudness_variance: float     # Local loudness variation
    
    # Voice quality
    voicing_probability: float   # 0-1, is this voiced speech?
    jitter: float               # Pitch perturbation (voice quality)
    shimmer: float              # Amplitude perturbation (voice quality)
    
    # Speech rate indicators
    speech_rate: float          # Syllables per second (estimated)
    

@dataclass
class SpiritAnalysisResult:
    """
    Complete output from the Spirit Engine analysis.
    """
    # Overall Spirit score (1-5 scale)
    overall_score: float
    
    # Sub-component scores (0-1 scale, converted to 1-5 for display)
    emotion_alignment_score: float      # Does vocal match text emotion?
    emotional_transition_score: float   # Are transitions smooth/intentional?
    emotional_range_score: float        # Dynamic range of emotions
    settling_score: float               # Consistency suggesting piece is settled
    
    # Detailed data for coach feedback and cross-module use
    vocal_emotions: List[EmotionSegment]    # What was detected from audio
    ideal_emotions: List[EmotionSegment]    # What should be expressed (from text)
    alignment_timeline: List[Dict[str, Any]]  # Per-segment alignment details
    
    # Prosody summary
    avg_pitch: float
    pitch_range: float
    avg_loudness: float
    loudness_range: float
    speech_rate_avg: float
    speech_rate_variance: float
    
    # Feedback generation helpers
    misalignment_moments: List[Dict[str, Any]]  # Specific moments to highlight
    strength_moments: List[Dict[str, Any]]      # Moments of strong alignment
    
    # Raw features for debugging/calibration
    prosody_features: Optional[List[ProsodyFeatures]] = None


@dataclass
class PerformanceTimeline:
    """
    Master timeline that the orchestrator builds and all modules contribute to.
    This enables cross-module analysis and dependency management.
    """
    # Metadata
    video_path: str
    audio_path: str
    duration_seconds: float
    
    # From transcription (populated first)
    words: List[WordSegment] = field(default_factory=list)
    transcript_text: str = ""
    
    # From Spirit Engine
    vocal_emotions: List[EmotionSegment] = field(default_factory=list)
    ideal_emotions: List[EmotionSegment] = field(default_factory=list)
    spirit_result: Optional[SpiritAnalysisResult] = None
    
    # From Chest Engine (to be implemented)
    pause_events: List[PauseEvent] = field(default_factory=list)
    loudness_curve: Optional[np.ndarray] = None
    
    # From Body Engine (to be implemented)
    facial_emotions: List[EmotionSegment] = field(default_factory=list)
    
    # From Audience Engine (to be implemented)
    engagement_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    
    # Overall scores
    spirit_score: float = 0.0
    chest_score: float = 0.0
    body_score: float = 0.0
    audience_score: float = 0.0
    overall_score: float = 0.0
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score per POTS methodology."""
        self.overall_score = (
            self.spirit_score * 0.30 +
            self.chest_score * 0.25 +
            self.body_score * 0.25 +
            self.audience_score * 0.20
        )
        return self.overall_score


# Emotion adjacency map for "close enough" alignment scoring
# Based on Feelings Circle - adjacent emotions are partially aligned
EMOTION_ADJACENCY = {
    EmotionCategory.HAPPY: [EmotionCategory.EXCITED, EmotionCategory.CALM, EmotionCategory.SURPRISED],
    EmotionCategory.SAD: [EmotionCategory.FEARFUL, EmotionCategory.CALM, EmotionCategory.TENDER],
    EmotionCategory.ANGRY: [EmotionCategory.DISGUSTED, EmotionCategory.DETERMINED, EmotionCategory.FEARFUL],
    EmotionCategory.FEARFUL: [EmotionCategory.SAD, EmotionCategory.SURPRISED, EmotionCategory.ANGRY],
    EmotionCategory.SURPRISED: [EmotionCategory.HAPPY, EmotionCategory.FEARFUL, EmotionCategory.EXCITED],
    EmotionCategory.DISGUSTED: [EmotionCategory.ANGRY, EmotionCategory.SAD],
    EmotionCategory.NEUTRAL: [EmotionCategory.CALM],  # Neutral is close to calm
    EmotionCategory.CALM: [EmotionCategory.NEUTRAL, EmotionCategory.HAPPY, EmotionCategory.SAD, EmotionCategory.TENDER],
    EmotionCategory.EXCITED: [EmotionCategory.HAPPY, EmotionCategory.SURPRISED, EmotionCategory.ANGRY],
    EmotionCategory.TENDER: [EmotionCategory.SAD, EmotionCategory.CALM, EmotionCategory.HAPPY],
    EmotionCategory.DETERMINED: [EmotionCategory.ANGRY, EmotionCategory.EXCITED],
}


# Valence-Arousal mappings for emotions
EMOTION_VA_MAP = {
    EmotionCategory.HAPPY: (0.8, 0.6),      # Positive, moderately aroused
    EmotionCategory.SAD: (-0.7, 0.3),        # Negative, low arousal
    EmotionCategory.ANGRY: (-0.6, 0.9),      # Negative, high arousal
    EmotionCategory.FEARFUL: (-0.7, 0.8),    # Negative, high arousal
    EmotionCategory.SURPRISED: (0.1, 0.8),   # Neutral-positive, high arousal
    EmotionCategory.DISGUSTED: (-0.8, 0.5),  # Very negative, moderate arousal
    EmotionCategory.NEUTRAL: (0.0, 0.3),     # Neutral, low arousal
    EmotionCategory.CALM: (0.4, 0.1),        # Positive, very low arousal
    EmotionCategory.EXCITED: (0.7, 0.9),     # Positive, very high arousal
    EmotionCategory.TENDER: (0.6, 0.2),      # Positive, low arousal
    EmotionCategory.DETERMINED: (0.3, 0.7),  # Slightly positive, high arousal
}


def emotions_are_aligned(vocal: EmotionCategory, ideal: EmotionCategory) -> tuple[bool, float]:
    """
    Check if two emotions are aligned (same or adjacent).
    Returns (is_aligned, alignment_score).
    
    - Exact match: 1.0
    - Adjacent emotion: 0.7
    - Non-adjacent: 0.0
    """
    if vocal == ideal:
        return True, 1.0
    
    adjacent = EMOTION_ADJACENCY.get(ideal, [])
    if vocal in adjacent:
        return True, 0.7
    
    return False, 0.0

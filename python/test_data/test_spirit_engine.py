#!/usr/bin/env python3
"""
Stage Buddy V2 - Spirit Engine Test Script

Usage:
    python test_spirit_engine.py                    # Run all tests
    python test_spirit_engine.py path/to/audio.wav  # Analyze a real file
"""

import sys
import logging
from pathlib import Path
from typing import List

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis_modules.shared.data_structures import (
    WordSegment, EmotionCategory, EmotionSegment, emotions_are_aligned
)


def create_mock_word_segments(transcript: str, duration: float) -> List[WordSegment]:
    """Create mock word segments for testing."""
    words = transcript.split()
    if not words:
        return []
    word_duration = duration / len(words)
    return [
        WordSegment(word=w, start_time=i*word_duration, 
                   end_time=(i+0.9)*word_duration, confidence=0.95)
        for i, w in enumerate(words)
    ]


def test_data_structures():
    """Test data structures."""
    print("\n=== Testing Data Structures ===")
    
    word = WordSegment(word="hello", start_time=0.0, end_time=0.5, confidence=0.95)
    assert word.duration == 0.5
    print("✓ WordSegment works")
    
    emotion = EmotionSegment(
        emotion=EmotionCategory.HAPPY, intensity=0.8, valence=0.7, arousal=0.6,
        start_time=0.0, end_time=3.0, confidence=0.9, source="vocal"
    )
    assert emotion.duration == 3.0
    print("✓ EmotionSegment works")
    
    is_aligned, score = emotions_are_aligned(EmotionCategory.HAPPY, EmotionCategory.HAPPY)
    assert is_aligned and score == 1.0
    print("✓ Same emotions align (score=1.0)")
    
    is_aligned, score = emotions_are_aligned(EmotionCategory.EXCITED, EmotionCategory.HAPPY)
    assert is_aligned and score == 0.7
    print("✓ Adjacent emotions partially align (score=0.7)")
    
    print("✓ All data structure tests passed!")


def test_text_emotion_analyzer():
    """Test text emotion analyzer."""
    print("\n=== Testing Text Emotion Analyzer ===")
    
    from analysis_modules.spirit_engine.text_emotion_analyzer import TextEmotionAnalyzer
    
    analyzer = TextEmotionAnalyzer()
    
    test_texts = [
        "I am so happy and full of joy!",
        "This makes me so angry and frustrated!",
        "I feel sad and alone in the darkness.",
        "The sky is blue.",
    ]
    
    for text in test_texts:
        result = analyzer.analyze_text(text)
        if result:
            top = max(result, key=lambda x: x['score'])
            print(f"  '{text[:35]}...' → {top['label']} ({top['score']:.2f})")
    
    # Test ideal arc generation
    transcript = "I woke up blessed. But then darkness came. Now I rise with fire!"
    words = create_mock_word_segments(transcript, 10.0)
    
    ideal_arc = analyzer.analyze_line_by_line(transcript, words)
    print(f"\n  Generated {len(ideal_arc)} emotion segments for ideal arc")
    for seg in ideal_arc:
        print(f"    {seg.start_time:.1f}s-{seg.end_time:.1f}s: {seg.emotion.value}")
    
    print("✓ Text emotion analyzer works!")


def test_opensmile_extractor():
    """Test OpenSMILE feature extraction."""
    print("\n=== Testing OpenSMILE Extractor ===")
    
    from analysis_modules.spirit_engine.opensmile_extractor import OpenSMILEExtractor
    
    extractor = OpenSMILEExtractor()
    
    if extractor.smile is not None:
        print(f"✓ OpenSMILE initialized with {len(extractor.feature_names)} features")
    else:
        print("⚠ OpenSMILE not available - will use librosa fallback")
    
    print("✓ OpenSMILE extractor initialized!")


def test_vocal_emotion_detector():
    """Test vocal emotion detector."""
    print("\n=== Testing Vocal Emotion Detector ===")
    
    from analysis_modules.spirit_engine.vocal_emotion_detector import VocalEmotionDetector
    
    detector = VocalEmotionDetector()
    
    if detector.classifier is not None:
        print("✓ SpeechBrain emotion model loaded")
    else:
        print("⚠ SpeechBrain not available - will use prosody-based fallback")
    
    print("✓ Vocal emotion detector initialized!")


def test_spirit_engine_mock():
    """Test Spirit Engine with mock data."""
    print("\n=== Testing Spirit Engine (Mock Mode) ===")
    
    from analysis_modules.spirit_engine.spirit_engine import SpiritEngine
    
    engine = SpiritEngine()
    print("✓ Spirit Engine initialized")
    
    # Create mock emotions for alignment test
    vocal_emotions = [
        EmotionSegment(EmotionCategory.HAPPY, 0.8, 0.7, 0.6, 0.0, 3.0, 0.9, "vocal"),
        EmotionSegment(EmotionCategory.SAD, 0.7, -0.6, 0.4, 3.0, 6.0, 0.85, "vocal"),
        EmotionSegment(EmotionCategory.ANGRY, 0.9, -0.5, 0.9, 6.0, 9.0, 0.88, "vocal"),
    ]
    
    ideal_emotions = [
        EmotionSegment(EmotionCategory.HAPPY, 0.8, 0.7, 0.6, 0.0, 3.0, 0.95, "text"),
        EmotionSegment(EmotionCategory.SAD, 0.6, -0.5, 0.3, 3.0, 6.0, 0.92, "text"),
        EmotionSegment(EmotionCategory.DETERMINED, 0.8, 0.3, 0.8, 6.0, 9.0, 0.90, "text"),
    ]
    
    # Test alignment calculation
    alignment = engine._calculate_alignment(vocal_emotions, ideal_emotions)
    print(f"  Alignment score: {alignment['overall_alignment']:.2f}")
    print(f"  Strengths: {len(alignment['strengths'])}")
    print(f"  Misalignments: {len(alignment['misalignments'])}")
    
    # Test transition quality
    transition = engine._calculate_transition_quality(vocal_emotions)
    print(f"  Transition quality: {transition:.2f}")
    
    # Test emotional range
    range_score = engine._calculate_emotional_range(vocal_emotions, {
        'pitch_range': 80, 'loudness_range': 25
    })
    print(f"  Emotional range: {range_score:.2f}")
    
    print("✓ Spirit Engine mock tests passed!")


def analyze_audio_file(audio_path: str):
    """Analyze a real audio file."""
    print(f"\n=== Analyzing: {audio_path} ===")
    
    from analysis_modules.spirit_engine.opensmile_extractor import extract_prosody
    from analysis_modules.spirit_engine.vocal_emotion_detector import detect_vocal_emotions
    
    path = Path(audio_path)
    if not path.exists():
        print(f"Error: File not found: {audio_path}")
        return
    
    print("\n1. Extracting prosodic features...")
    try:
        prosody = extract_prosody(str(path))
        print(f"   Extracted {len(prosody['prosody_timeline'])} frames")
        print(f"   Duration: {prosody['summary'].get('duration_seconds', 0):.1f}s")
        print(f"   Avg pitch: {prosody['summary'].get('pitch_mean', 0):.1f} Hz")
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    print("\n2. Detecting vocal emotions...")
    try:
        emotions = detect_vocal_emotions(str(path))
        print(f"   Detected {len(emotions)} emotion segments:")
        for e in emotions[:5]:
            print(f"     {e.start_time:.1f}s: {e.emotion.value} ({e.confidence:.2f})")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✓ Analysis complete!")


def main():
    print("=" * 60)
    print("Stage Buddy V2 - Spirit Engine Tests")
    print("=" * 60)
    
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        analyze_audio_file(sys.argv[1])
    else:
        test_data_structures()
        test_text_emotion_analyzer()
        test_opensmile_extractor()
        test_vocal_emotion_detector()
        test_spirit_engine_mock()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)


if __name__ == "__main__":
    main()

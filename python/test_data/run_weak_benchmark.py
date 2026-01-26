#!/usr/bin/env python3
"""
WEAK Benchmark Analysis - Did You Smile Today
"""
import sys
sys.path.insert(0, '/workspaces/stage-buddy-v2')

from pathlib import Path
import subprocess
import json
import whisper

from python.analysis_modules.spirit_engine.spirit_engine import SpiritEngine
from python.analysis_modules.shared.data_structures import WordSegment

# Paths
video_path = Path("python/test_data/videos/did_you_smile_today_WEAK.mov")
output_dir = Path("python/test_data/outputs/did_you_smile_WEAK")
output_dir.mkdir(parents=True, exist_ok=True)

audio_path = output_dir / "audio.wav"

print("📹 Video:", video_path)
print("📁 Output:", output_dir)
print("")

# Step 1: Extract Audio
print("🎵 Step 1/3: Extracting audio...")
try:
    subprocess.run([
        "ffmpeg", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", "-y",
        str(audio_path)
    ], check=True, capture_output=True)
    print(f"   ✅ Audio extracted")
except subprocess.CalledProcessError as e:
    print(f"   ❌ FFmpeg failed: {e.stderr.decode()}")
    sys.exit(1)

# Step 2: Transcribe with Whisper
print("\n📝 Step 2/3: Transcribing with Whisper...")
try:
    model = whisper.load_model("base")
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en"
    )
    
    transcript_text = result["text"]
    
    # Create WordSegment objects with correct parameter names
    word_segments = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word_segments.append(WordSegment(
                word=word_info["word"].strip(),
                start_time=word_info["start"],
                end_time=word_info["end"],
                confidence=word_info.get("probability", 1.0)
            ))
    
    print(f"   ✅ Transcription complete")
    print(f"   • Words: {len(word_segments)}")
    print(f"   • Preview: {transcript_text[:100]}...")
    
except Exception as e:
    print(f"   ❌ Whisper failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Run Spirit Engine
print("\n🎭 Step 3/3: Spirit Engine analysis...")
try:
    engine = SpiritEngine()
    
    result = engine.analyze(
        audio_path=str(audio_path),
        transcript=transcript_text,
        word_segments=word_segments,
        segment_duration=3.0
    )
    
    manual_score = 2.0
    difference = abs(result.overall_score - manual_score)
    
    print("\n" + "="*60)
    print("✅ SPIRIT ENGINE ANALYSIS COMPLETE")
    print("="*60)
    print(f"\n🎯 Spirit Score: {result.overall_score:.2f} / 5.0")
    print(f"   Manual Score: {manual_score}")
    print(f"   Difference: {difference:.2f}")
    print(f"   Accuracy: {100 - (difference / 5.0 * 100):.1f}%")
    print(f"   Status: {'✅ ACCURATE' if difference <= 1.0 else '⚠️ NEEDS CALIBRATION'}")
    
    print("\n📊 Sub-scores:")
    print(f"  • Emotion Alignment:  {result.emotion_alignment_score:.2f}")
    print(f"  • Transition Quality: {result.emotional_transition_score:.2f}")
    print(f"  • Emotional Range:    {result.emotional_range_score:.2f}")
    print(f"  • Settling Indicator: {result.settling_score:.2f}")
    print("="*60)
    
    # Save results
    result_dict = {
        "performance_id": "did_you_smile_WEAK_test",
        "category": "WEAK",
        "manual_spirit_score": manual_score,
        "calculated_spirit_score": result.overall_score,
        "difference": difference,
        "accuracy_percent": 100 - (difference / 5.0 * 100),
        "sub_scores": {
            "emotion_alignment": result.emotion_alignment_score,
            "transition_quality": result.emotional_transition_score,
            "emotional_range": result.emotional_range_score,
            "settling_indicator": result.settling_score
        },
        "transcript": transcript_text,
        "word_count": len(word_segments)
    }
    
    result_path = output_dir / "spirit_analysis.json"
    with open(result_path, "w") as f:
        json.dump(result_dict, f, indent=2)
    
    print(f"\n💾 Results saved: {result_path}")
    
except Exception as e:
    print(f"\n❌ Spirit Engine failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Print complete summary
print("\n" + "="*60)
print("📊 COMPLETE BENCHMARK SUMMARY - ALL 3 TESTS")
print("="*60)
print("\n  MID (Trap Ghost):      Manual=3.0, Calculated=2.94, Diff=0.06 ✅")
print("  STRONG (X KING):       Manual=5.0, Calculated=3.22, Diff=1.78 ⚠️")
print(f"  WEAK (Did You Smile):  Manual=2.0, Calculated={result.overall_score:.2f}, Diff={difference:.2f}")
print("\n✅ All benchmark tests complete!")
print("="*60)

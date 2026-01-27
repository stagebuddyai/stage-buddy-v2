#!/usr/bin/env python3
"""
Stage Buddy V2 - Chest Engine Benchmark Runner

Runs the Chest Engine on benchmark videos and compares to manual scores.
Benchmark videos must be placed in python/test_data/videos/

Expected Chest Scores (from benchmark_scores.json):
- STRONG (x_king_city_winery): 5/5
- MID (trap_ghost): 4/5
- WEAK (did_you_smile_today): 3/5

Usage:
    python run_chest_benchmark.py                    # Run all benchmarks
    python run_chest_benchmark.py --video STRONG    # Run specific benchmark
    python run_chest_benchmark.py --synthetic       # Run synthetic test
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import json
import argparse
import numpy as np
import time

# Benchmark configuration
BENCHMARKS = {
    "STRONG": {
        "filename": "x_king_city_winery_STRONG.mp4",
        "manual_chest_score": 5.0,
        "notes": "Masterful breath control, 3 distinct voices, fills venue"
    },
    "MID": {
        "filename": "trap_ghost_MID.mov",
        "manual_chest_score": 4.0,
        "notes": "Clear articulation, good projection, hyper delivery"
    },
    "WEAK": {
        "filename": "did_you_smile_today_WEAK.mov",
        "manual_chest_score": 3.0,
        "notes": "Monotone, sitting position, adequate but uninspired"
    }
}

TEST_DATA_DIR = Path(__file__).parent
VIDEOS_DIR = TEST_DATA_DIR / "videos"
OUTPUTS_DIR = TEST_DATA_DIR / "outputs"


def run_synthetic_test():
    """Run Chest Engine on synthetic audio to verify it works."""
    print("=" * 60)
    print("🧪 SYNTHETIC TEST - Verifying Chest Engine")
    print("=" * 60)

    try:
        from analysis_modules.chest_engine import ChestEngine

        # Create synthetic audio (3 seconds of varying sine wave)
        sr = 16000
        duration = 5.0
        t = np.linspace(0, duration, int(sr * duration))

        # Simulate speech-like audio with pauses
        audio = np.zeros_like(t)

        # Segment 1: Speaking (0-1.5s) - moderate energy
        mask1 = (t >= 0) & (t < 1.5)
        audio[mask1] = 0.3 * np.sin(2 * np.pi * 200 * t[mask1]) * (1 + 0.5 * np.sin(2 * np.pi * 5 * t[mask1]))

        # Segment 2: Pause (1.5-2.0s) - low energy
        mask2 = (t >= 1.5) & (t < 2.0)
        audio[mask2] = 0.01 * np.random.randn(np.sum(mask2))

        # Segment 3: Speaking louder (2.0-4.0s) - higher energy
        mask3 = (t >= 2.0) & (t < 4.0)
        audio[mask3] = 0.5 * np.sin(2 * np.pi * 180 * t[mask3]) * (1 + 0.3 * np.sin(2 * np.pi * 8 * t[mask3]))

        # Segment 4: Quiet ending (4.0-5.0s)
        mask4 = (t >= 4.0)
        audio[mask4] = 0.2 * np.sin(2 * np.pi * 160 * t[mask4])

        # Add some noise
        audio += 0.02 * np.random.randn(len(audio))

        print("\n📊 Synthetic audio created:")
        print(f"   Duration: {duration}s")
        print(f"   Sample rate: {sr}Hz")
        print(f"   Segments: speech -> pause -> loud -> quiet")

        # Initialize engine
        print("\n🔧 Initializing Chest Engine...")
        engine = ChestEngine(sample_rate=sr)

        # Analyze directly with audio array (bypass file loading)
        print("🔍 Running analysis...")
        start_time = time.time()

        # Run sub-analyzers directly
        breath_result = engine.breath_analyzer.analyze(audio, sr)
        projection_result = engine.projection_analyzer.analyze(audio, sr)
        pause_result = engine.pause_detector.analyze(audio, sr)
        health_result = engine.health_monitor.analyze(audio, sr)

        elapsed = (time.time() - start_time) * 1000

        # Calculate overall score
        overall = (
            breath_result['score'] * 0.35 +
            projection_result['score'] * 0.35 +
            pause_result['score'] * 0.20 +
            health_result['score'] * 0.10
        )
        overall_5_scale = 1.0 + overall * 4.0

        print("\n" + "=" * 60)
        print("✅ SYNTHETIC TEST RESULTS")
        print("=" * 60)
        print(f"\n🎯 Chest Score: {overall_5_scale:.2f} / 5.0")
        print(f"   Processing time: {elapsed:.0f}ms")

        print("\n📊 Sub-scores (0-1 normalized):")
        print(f"   • Breath Control:  {breath_result['score']:.3f}")
        print(f"   • Projection:      {projection_result['score']:.3f}")
        print(f"   • Pause Technique: {pause_result['score']:.3f}")
        print(f"   • Vocal Health:    {health_result['score']:.3f}")

        print("\n📈 Detailed metrics:")
        print(f"   • Breaths detected: {len(breath_result['events'])}")
        print(f"   • Dynamic range: {projection_result['dynamic_range_db']:.1f} dB")
        print(f"   • Pauses detected: {len(pause_result['events'])}")
        print(f"   • Fatigue detected: {health_result['fatigue_detected']}")

        print("\n" + "=" * 60)
        print("✅ Synthetic test PASSED - Chest Engine is working!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Synthetic test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_benchmark(category: str):
    """Run Chest Engine benchmark for a specific category."""
    if category not in BENCHMARKS:
        print(f"❌ Unknown category: {category}")
        return None

    config = BENCHMARKS[category]
    video_path = VIDEOS_DIR / config["filename"]

    print("=" * 60)
    print(f"🎬 CHEST ENGINE BENCHMARK - {category}")
    print("=" * 60)
    print(f"\n📹 Video: {video_path}")
    print(f"🎯 Target: {config['manual_chest_score']}/5")
    print(f"📝 Notes: {config['notes']}")

    if not video_path.exists():
        print(f"\n❌ Video file not found: {video_path}")
        print("   Please place benchmark videos in python/test_data/videos/")
        return None

    try:
        from analysis_modules.chest_engine import ChestEngine

        # Create output directory
        output_dir = OUTPUTS_DIR / f"{category.lower()}_chest"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize and run
        print("\n🔧 Initializing Chest Engine...")
        engine = ChestEngine()

        print("🔍 Running analysis...")
        start_time = time.time()
        result = engine.analyze(audio_path=str(video_path))
        elapsed = time.time() - start_time

        # Calculate accuracy
        manual_score = config["manual_chest_score"]
        difference = abs(result.overall_score - manual_score)
        accuracy = 100 - (difference / 5.0 * 100)

        print("\n" + "=" * 60)
        print(f"✅ {category} BENCHMARK COMPLETE")
        print("=" * 60)
        print(f"\n🎯 Chest Score: {result.overall_score:.2f} / 5.0")
        print(f"   Manual Score: {manual_score}")
        print(f"   Difference: {difference:.2f}")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Status: {'✅ ACCURATE' if difference <= 1.0 else '⚠️ NEEDS CALIBRATION'}")
        print(f"   Time: {elapsed:.1f}s")

        print("\n📊 Sub-scores (0-1 normalized):")
        print(f"   • Breath Control:  {result.breath_control_score:.3f}")
        print(f"   • Projection:      {result.projection_score:.3f}")
        print(f"   • Pause Technique: {result.pause_technique_score:.3f}")
        print(f"   • Vocal Health:    {result.vocal_health_score:.3f}")

        # Save results
        result_dict = {
            "performance_id": f"{category.lower()}_chest_benchmark",
            "category": category,
            "manual_chest_score": manual_score,
            "calculated_chest_score": result.overall_score,
            "difference": difference,
            "accuracy_percent": accuracy,
            "sub_scores": {
                "breath_control": result.breath_control_score,
                "projection": result.projection_score,
                "pause_technique": result.pause_technique_score,
                "vocal_health": result.vocal_health_score
            },
            "breath_events": len(result.breath_events),
            "pause_events": len(result.pause_events),
            "fatigue_detected": result.fatigue_detected,
            "processing_time_seconds": elapsed
        }

        result_path = output_dir / "chest_analysis.json"
        with open(result_path, "w") as f:
            json.dump(result_dict, f, indent=2)

        print(f"\n💾 Results saved: {result_path}")

        return result_dict

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all_benchmarks():
    """Run all benchmarks and show summary."""
    print("\n" + "=" * 60)
    print("🚀 CHEST ENGINE - FULL BENCHMARK SUITE")
    print("=" * 60)

    results = {}

    for category in ["STRONG", "MID", "WEAK"]:
        print(f"\n{'='*60}")
        result = run_benchmark(category)
        if result:
            results[category] = result
        print()

    # Summary
    if results:
        print("\n" + "=" * 60)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 60)

        total_diff = 0
        for category, result in results.items():
            status = "✅" if result["difference"] <= 1.0 else "⚠️"
            print(f"   {category:8} Manual={result['manual_chest_score']:.1f}, "
                  f"Calc={result['calculated_chest_score']:.2f}, "
                  f"Diff={result['difference']:.2f} {status}")
            total_diff += result["difference"]

        avg_diff = total_diff / len(results)
        print(f"\n   Average Difference: {avg_diff:.2f}")
        print(f"   Target: < 1.0")
        print(f"   Status: {'✅ CALIBRATED' if avg_diff < 1.0 else '⚠️ NEEDS TUNING'}")

        print("=" * 60)
    else:
        print("\n⚠️ No benchmarks completed. Please add videos to test_data/videos/")


def main():
    parser = argparse.ArgumentParser(description="Chest Engine Benchmark Runner")
    parser.add_argument("--video", choices=["STRONG", "MID", "WEAK"],
                       help="Run specific benchmark")
    parser.add_argument("--synthetic", action="store_true",
                       help="Run synthetic audio test")
    parser.add_argument("--all", action="store_true",
                       help="Run all benchmarks")

    args = parser.parse_args()

    if args.synthetic:
        run_synthetic_test()
    elif args.video:
        run_benchmark(args.video)
    elif args.all:
        run_all_benchmarks()
    else:
        # Default: run synthetic test first, then all benchmarks
        print("Running synthetic test first to verify engine...")
        if run_synthetic_test():
            print("\n" + "=" * 60)
            print("Now attempting benchmark videos...")
            run_all_benchmarks()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Body Engine Benchmark - All Three Videos
Tests the Body Engine against manual scores for STRONG, MID, and WEAK performances.

Expected scores (body component from benchmark_scores.json):
- STRONG (x_king_city_winery): 5/5 - Full body engagement, character embodiment
- MID (trap_ghost): 3/5 - Excessive gestures, hyper movement, lacks grounding
- WEAK (did_you_smile_today): 1/5 - Sitting position, no body language, static

Success Criteria: Average difference from manual scores < 1.0
"""
import sys
sys.path.insert(0, '/home/user/stage-buddy-v2')

from pathlib import Path
import json
import time

# Import Body Engine
from python.analysis_modules.body_engine.body_engine import BodyEngine


def run_benchmark():
    """Run Body Engine benchmark on all three test videos."""

    # Paths
    video_dir = Path("python/test_data/videos")
    output_dir = Path("python/test_data/outputs/body_benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Benchmark videos and expected scores
    benchmarks = {
        "x_king_city_winery_STRONG.mp4": {
            "category": "STRONG",
            "manual_body_score": 5.0,
            "notes": "Full body engagement, character embodiment, stage ownership"
        },
        "trap_ghost_MID.mov": {
            "category": "MID",
            "manual_body_score": 3.0,
            "notes": "Excessive gestures, hyper movement, lacks grounding"
        },
        "did_you_smile_today_WEAK.mov": {
            "category": "WEAK",
            "manual_body_score": 1.0,
            "notes": "Sitting position, no body language, static"
        }
    }

    print("=" * 70)
    print("BODY ENGINE BENCHMARK")
    print("=" * 70)
    print()

    # Initialize Body Engine
    print("Initializing Body Engine...")
    try:
        engine = BodyEngine(
            fps_target=5.0,
            segment_duration=3.0,
            use_mediapipe=True
        )
        print("Body Engine initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Body Engine: {e}")
        sys.exit(1)

    print()

    # Run analysis on each video
    results = {}
    total_difference = 0.0
    videos_analyzed = 0

    for video_name, benchmark_info in benchmarks.items():
        video_path = video_dir / video_name

        print("-" * 70)
        print(f"Video: {video_name}")
        print(f"Category: {benchmark_info['category']}")
        print(f"Expected Score: {benchmark_info['manual_body_score']}/5")
        print(f"Notes: {benchmark_info['notes']}")
        print()

        if not video_path.exists():
            print(f"  [SKIP] Video file not found: {video_path}")
            print()
            results[video_name] = {
                "status": "skipped",
                "reason": "Video file not found"
            }
            continue

        # Run Body Engine
        print(f"  [RUNNING] Analyzing video...")
        start_time = time.time()

        try:
            result = engine.analyze(str(video_path))
            elapsed = time.time() - start_time

            calculated_score = result.overall_score
            manual_score = benchmark_info['manual_body_score']
            difference = abs(calculated_score - manual_score)
            accuracy = 100 - (difference / 5.0 * 100)

            print(f"  [DONE] Analysis complete in {elapsed:.1f}s")
            print()
            print(f"  Body Score:      {calculated_score:.2f} / 5.0")
            print(f"  Manual Score:    {manual_score}")
            print(f"  Difference:      {difference:.2f}")
            print(f"  Accuracy:        {accuracy:.1f}%")
            print(f"  Status:          {'PASS' if difference <= 1.0 else 'NEEDS CALIBRATION'}")
            print()
            print(f"  Sub-scores:")
            print(f"    - Gesture:        {result.gesture_score:.2f}")
            print(f"    - Stage Presence: {result.stage_presence_score:.2f}")
            print(f"    - Eye Contact:    {result.eye_contact_score:.2f}")
            print(f"    - Alignment:      {result.alignment_score:.2f}")
            print()
            print(f"  Metadata:")
            print(f"    - Frames analyzed: {result.frames_analyzed}")
            print(f"    - Video duration:  {result.video_duration:.1f}s")
            print(f"    - Segments:        {len(result.segments)}")
            print(f"    - Gesture events:  {len(result.gesture_events)}")

            results[video_name] = {
                "status": "success",
                "category": benchmark_info['category'],
                "manual_score": manual_score,
                "calculated_score": calculated_score,
                "difference": difference,
                "accuracy_percent": accuracy,
                "sub_scores": {
                    "gesture": result.gesture_score,
                    "stage_presence": result.stage_presence_score,
                    "eye_contact": result.eye_contact_score,
                    "alignment": result.alignment_score
                },
                "frames_analyzed": result.frames_analyzed,
                "video_duration": result.video_duration,
                "processing_time_sec": elapsed
            }

            total_difference += difference
            videos_analyzed += 1

        except Exception as e:
            print(f"  [ERROR] Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            results[video_name] = {
                "status": "error",
                "error": str(e)
            }

        print()

    # Summary
    print("=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print()

    if videos_analyzed > 0:
        avg_difference = total_difference / videos_analyzed
        avg_accuracy = 100 - (avg_difference / 5.0 * 100)

        print(f"Videos Analyzed:    {videos_analyzed}")
        print(f"Average Difference: {avg_difference:.2f}")
        print(f"Average Accuracy:   {avg_accuracy:.1f}%")
        print()

        success = avg_difference <= 1.0
        if success:
            print("RESULT: PASS - Body Engine meets calibration target")
        else:
            print("RESULT: NEEDS CALIBRATION - Average difference > 1.0")

        # Per-video summary
        print()
        print("Per-Video Results:")
        for video_name, result in results.items():
            if result.get('status') == 'success':
                diff = result['difference']
                calc = result['calculated_score']
                manual = result['manual_score']
                status = "PASS" if diff <= 1.0 else "FAIL"
                print(f"  {result['category']:6s}: Manual={manual}, Calc={calc:.2f}, Diff={diff:.2f} [{status}]")
            elif result.get('status') == 'skipped':
                print(f"  {benchmarks[video_name]['category']:6s}: SKIPPED - {result.get('reason', 'Unknown')}")
            else:
                print(f"  {benchmarks[video_name]['category']:6s}: ERROR - {result.get('error', 'Unknown')}")
    else:
        print("No videos were analyzed. Make sure video files exist in:")
        print(f"  {video_dir}")
        print()
        print("Expected files:")
        for video_name in benchmarks:
            print(f"  - {video_name}")

    print()
    print("=" * 70)

    # Save results
    results_path = output_dir / "body_benchmark_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved: {results_path}")

    return results


if __name__ == "__main__":
    run_benchmark()

# Body Engine Design Document

**Version:** 1.0
**Status:** Production-Ready
**Last Updated:** January 2026

## Overview

The Body Engine is the third component of the S.T.A.R.R. analysis framework for Stage Buddy V2. It evaluates physical performance aspects visible in video, contributing 25% to the overall STARR score.

## STARR Framework Position

```
Overall STARR Score =
    30% Spirit Engine (emotional authenticity) +
    25% Chest Engine (vocal technique) +
    25% Body Engine (physical performance) ← THIS MODULE
    20% Audience Engine (audience engagement)
```

## Core Scoring Components

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| **Gesture Intentionality** | 35% | Are movements purposeful or nervous fidgeting? |
| **Stage Presence** | 30% | Use of space, stance, confidence in physicality |
| **Eye Contact/Focus** | 20% | Connection with audience through gaze |
| **Physical-Vocal Alignment** | 15% | Do gestures match vocal emphasis? |

## Architecture

```
body_engine/
├── __init__.py                    # Module exports
├── body_engine.py                 # Main orchestrator (BodyEngine class)
├── gesture_analyzer.py            # Pose detection + gesture classification
├── stage_presence_analyzer.py     # Movement tracking + space usage
├── eye_contact_detector.py        # Face/gaze detection
└── alignment_scorer.py            # Physical-vocal synchronization
```

### Data Flow

```
Video Input
    │
    ├─→ Frame Extraction (5 FPS)
    │       │
    │       ├─→ Gesture Analyzer ──────→ GestureEvents + gesture_score
    │       │      (Pose estimation or motion detection)
    │       │
    │       ├─→ Stage Presence ────────→ Movement metrics + stage_presence_score
    │       │      (Position tracking)
    │       │
    │       └─→ Eye Contact ───────────→ Gaze metrics + eye_contact_score
    │              (Face/gaze detection)
    │
    └─→ Alignment Scorer ─────────────→ alignment_score
           (Correlation with audio energy if available)
                    │
                    ▼
            BodyAnalysisResult
```

## Scoring Methodology

### Final Score Calculation

```python
overall_normalized = (
    gesture_score * 0.35 +
    stage_presence_score * 0.30 +
    eye_contact_score * 0.20 +
    alignment_score * 0.15
)

# Convert 0-1 normalized score to 1-5 scale
overall_score = 1.0 + overall_normalized * 4.0
```

### Sub-Component Scoring

#### 1. Gesture Intentionality (35%)

**POTS Excellence Indicators (scores 0.8-1.0):**
- Gestures are intentional, serving the piece's imagery
- Movement is controlled and purposeful
- Emphatic gestures align with emotional moments

**POTS Weak Indicators (scores 0.0-0.3):**
- Nervous fidgeting, hands in pockets
- Swaying or repetitive self-soothing movements
- No gestures at all (static)

**Classification:**
- `EMPHATIC`: Fast, controlled movements (high intentionality)
- `ILLUSTRATIVE`: Movements that paint imagery
- `NERVOUS`: Fidgeting, erratic patterns
- `TRANSITIONAL`: Movement between positions
- `NONE`: No significant gesture

#### 2. Stage Presence (30%)

**POTS Excellence Indicators:**
- Owns the stage, uses space effectively
- Stance is grounded and confident
- Movement is purposeful, not nervous pacing

**POTS Weak Indicators:**
- Rooted to one spot, no movement
- Nervous pacing back and forth
- Hunched posture, closed body language

**Key Metrics:**
- `movement_amount`: Total movement magnitude (optimal: 0.02-0.08)
- `position_stability`: How controlled position is
- `space_usage`: Use of available stage space

#### 3. Eye Contact (20%)

**POTS Excellence Indicators:**
- Engaging the audience, not fixed on one spot
- Natural eye movement
- Not reading from paper

**POTS Weak Indicators:**
- Eyes down, avoiding audience
- Fixed stare at one point
- Looking at paper/script

**Key Metrics:**
- `forward_ratio`: Time looking toward audience
- `gaze_stability`: Steadiness (not darting)
- `downward_ratio`: Time looking down (penalty)

#### 4. Physical-Vocal Alignment (15%)

**When audio energy curve is available:**
- Correlate physical energy with vocal energy
- High correlation = gestures match vocal emphasis
- Measures whether body supports voice

**Without audio data:**
- Analyze physical energy consistency
- Moderate, varied movement scores well
- Static or constant high energy scores poorly

## Benchmark Calibration

| Video | Target | Tolerance | Notes |
|-------|--------|-----------|-------|
| STRONG (x_king) | 5.0 | ±0.5 | Full body engagement, character embodiment |
| MID (trap_ghost) | 3.0 | ±0.5 | Excessive gestures, hyper movement |
| WEAK (did_you_smile) | 1.0 | ±0.5 | Sitting, no body language, static |

**Success Criteria:** Average difference from manual scores < 1.0

## Technical Implementation

### Pose Estimation

**Primary Method:** MediaPipe Pose (when available)
- Full skeletal tracking (33 landmarks)
- High accuracy gesture detection
- Real-time capable

**Fallback Method:** Motion-based detection
- Frame differencing for movement detection
- Face cascade for basic face detection
- Works offline without ML models

### Performance Optimization

- **Frame sampling:** Process at 5 FPS (vs. typical 30 FPS)
- **Segment analysis:** 3-second windows
- **Target processing time:** < 30 seconds for 60-second video

### Dependencies

```
opencv-python>=4.8.0     # Video processing
mediapipe>=0.10.0        # Pose estimation (optional)
numpy>=1.24.0            # Numerical computation
```

## Feedback Generation

The engine generates POTS-style coaching feedback:

```python
def generate_feedback(result: BodyAnalysisResult) -> str:
    if score >= 4.5:
        "Your body language is COMMANDING the stage!"
    elif score >= 3.5:
        "Strong physical presence. Your body is engaged with your words."
    elif score >= 2.5:
        "Your body language needs more intentionality."
    else:
        "We need to wake up your body! Your physicality isn't supporting your words."
```

Specific feedback on:
- Nervous fidgeting patterns
- Stage space usage
- Eye contact engagement
- Physical-vocal synchronization

## Integration

### With Chest Engine (audio energy)

```python
# When Chest Engine provides audio energy curve
result = body_engine.analyze(
    video_path="performance.mp4",
    audio_energy_curve=chest_result.loudness_curve,
    audio_timestamps=chest_result.timestamps
)
```

### With Spirit Engine (emotion alignment)

The Body Engine's segment timeline aligns with Spirit Engine's 3-second segments, enabling cross-module analysis of emotion-gesture alignment.

### With Performance Timeline

```python
timeline = PerformanceTimeline(...)
timeline.body_score = body_result.overall_score
timeline.calculate_overall_score()  # Includes 25% body contribution
```

## Known Limitations

1. **MediaPipe 0.10+ Compatibility:** Uses motion fallback on newer versions
2. **Synthetic faces:** Cannot detect non-human faces
3. **Camera angle dependency:** Best with front-facing camera
4. **Lighting sensitivity:** Low light reduces detection accuracy

## Future Enhancements

1. **MediaPipe Tasks API:** Migrate to new API for MediaPipe 0.10+
2. **GPU acceleration:** Add CUDA support for faster processing
3. **Emotion-gesture mapping:** Link specific gestures to emotions
4. **Multi-person tracking:** Support for performances with multiple people

## Testing

Run the benchmark:

```bash
python python/test_data/run_body_benchmark.py
```

Expected output includes per-video scores and overall accuracy.

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2026 | Initial release with motion fallback |

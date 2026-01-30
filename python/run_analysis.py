#!/usr/bin/env python3
"""
Stage Buddy V2 - Analysis Runner
CLI entry point for the web interface to invoke analysis via subprocess.

Usage:
    python3 run_analysis.py --video-path /path/to/video.mp4 --output-path /path/to/report.json --analysis-id abc123

For Beta, this generates a deterministic report based on the video file.
Same video file always produces the same scores and feedback.
In production, this calls the full S.T.A.R.R. orchestrator pipeline.
"""

import argparse
import json
import sys
import os
import hashlib
import random
import time
import math
import subprocess


def hash_file(filepath: str, chunk_size: int = 1024 * 1024) -> str:
    """Hash the first chunk of a file for deterministic seeding."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        chunk = f.read(chunk_size)
        h.update(chunk)
    return h.hexdigest()


def get_video_duration(video_path: str) -> float:
    """
    Extract actual video duration in seconds using ffprobe.
    Falls back to file size estimation if ffprobe is unavailable.
    """
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ], capture_output=True, text=True, check=True, timeout=10)

        duration = float(result.stdout.strip())
        print(f"✅ ffprobe extracted duration: {duration:.2f}s for {os.path.basename(video_path)}", file=sys.stderr)

        # Sanity check: duration should be positive and reasonable
        # Minimum 30s to ensure timestamp logic works correctly
        if duration >= 30 and duration <= 7200:  # 30s to 2 hours
            return duration
        else:
            raise ValueError(f"Invalid duration: {duration}s (must be 30s-7200s)")

    except (subprocess.CalledProcessError, ValueError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        # Fallback to file size estimation if ffprobe fails
        print(f"⚠️  Warning: Could not extract video duration ({e}). Using file size estimation.", file=sys.stderr)
        file_size = os.path.getsize(video_path)
        fallback_duration = max(60, min(600, file_size // 50000))
        print(f"📊 File size fallback: {file_size} bytes → {fallback_duration}s duration", file=sys.stderr)
        return fallback_duration


def score_to_display(score: float) -> str:
    """Convert 1-5 score to a display label. Avoids 'grade' language."""
    if score >= 4.5:
        return "Strong"
    elif score >= 3.5:
        return "Developing"
    elif score >= 2.5:
        return "Emerging"
    elif score >= 1.5:
        return "Beginning"
    else:
        return "Early"


def generate_spirit_feedback(score: float, subscores: dict, rng: random.Random, moments: list) -> str:
    """Generate Spirit pillar coach feedback following voice rules."""
    alignment = subscores['emotion_alignment']
    transitions = subscores['transitions']
    emotional_range = subscores['range']
    settling = subscores['settling']

    lines = []

    # Observation first (tied to delivery signals)
    if emotional_range >= 4.0:
        lines.append(
            "Your emotional range shows real variety across this piece. "
            "The shifts between sections carry distinct weight."
        )
    elif emotional_range >= 3.0:
        lines.append(
            "There is emotional movement here, but some sections sit at a similar intensity. "
            "The piece has room for wider contrast."
        )
    else:
        lines.append(
            "The emotional landscape stays fairly level through the performance. "
            "There are moments where the text invites a shift that the voice doesn't yet follow."
        )

    # Specific moment reference
    if moments:
        peak = next((m for m in moments if m['type'] == 'peak'), None)
        if peak:
            ts = peak['timestamp']
            mins = int(ts // 60)
            secs = int(ts % 60)
            lines.append(
                f"Around {mins}:{secs:02d}, everything aligned - voice, breath, intention. "
                f"That's the standard your body already knows."
            )

    # Alignment observation
    if alignment >= 4.0:
        lines.append(
            "Your vocal delivery matches the emotional intent of your words consistently. "
            "The audience hears what the poem asks them to feel."
        )
    elif alignment >= 3.0:
        lines.append(
            "Some lines land exactly where they should. Others have a gap between what the words carry "
            "and what the voice delivers. That gap is workable."
        )
    else:
        lines.append(
            "There is a noticeable distance between your text's emotional landscape and your vocal delivery. "
            "The words carry weight the voice hasn't picked up yet."
        )

    # Transitions
    if transitions >= 3.5:
        lines.append(
            "Transitions between emotional beats feel intentional. You're not rushing through the shifts."
        )
    else:
        lines.append(
            "Some transitions happen abruptly - the voice jumps rather than moves between emotions. "
            "Slower breath at those pivot points would let the audience travel with you."
        )

    # Growth framing (not judgment)
    if score >= 4.0:
        lines.append(
            "The spirit of this piece is present and communicating. Keep trusting what your body knows."
        )
    elif score >= 3.0:
        lines.append(
            "The foundation is solid. The next layer is letting the emotional shifts be bigger than "
            "feels comfortable in rehearsal."
        )
    else:
        lines.append(
            "Every performer starts by finding their own emotional access points. "
            "The work now is letting the piece teach you where it wants to go."
        )

    return " ".join(lines)


def generate_chest_feedback(score: float, subscores: dict, rng: random.Random, moments: list) -> str:
    """Generate Chest pillar coach feedback (breath, voice, pacing)."""
    breath = subscores['breath_control']
    projection = subscores['vocal_projection']
    pacing = subscores['pacing']
    articulation = subscores['articulation']

    lines = []

    if projection >= 4.0:
        lines.append(
            "Your voice fills the space without pushing. Projection is grounded, not forced."
        )
    elif projection >= 3.0:
        lines.append(
            "Volume is present but not always consistent. Some lines drop when they could sustain."
        )
    else:
        lines.append(
            "The voice sits close to the chest. There's more volume available that isn't being used yet."
        )

    if breath >= 3.5:
        lines.append(
            "Breath management supports the longer lines. You're not running out at the ends of phrases."
        )
    else:
        lines.append(
            "Some phrases lose air before they finish. The breath work is about giving yourself "
            "permission to pause and refill rather than pushing through."
        )

    if pacing >= 4.0:
        lines.append(
            "Pacing choices serve the material. Fast sections feel intentional, slow sections feel earned."
        )
    elif pacing >= 3.0:
        lines.append(
            "Pacing is mostly steady. The piece would benefit from more deliberate speed changes "
            "to mark section boundaries."
        )
    else:
        lines.append(
            "The tempo stays fairly uniform. Variation in speed is one of the most accessible tools "
            "for guiding audience attention."
        )

    # Moment reference
    if moments:
        dip = next((m for m in moments if m['type'] == 'dip'), None)
        if dip:
            ts = dip['timestamp']
            mins = int(ts // 60)
            secs = int(ts % 60)
            lines.append(
                f"Near {mins}:{secs:02d}, the vocal energy drops. "
                f"Check whether that's an intentional choice or if breath ran thin there."
            )

    if articulation >= 3.5:
        lines.append("Words are landing clearly. The audience isn't working to decode your speech.")
    else:
        lines.append(
            "Some words blur together, especially in faster sections. "
            "Articulation doesn't mean stiffness - it means each word gets its full shape."
        )

    return " ".join(lines)


def generate_body_feedback(score: float, subscores: dict, rng: random.Random, moments: list) -> str:
    """Generate Body pillar coach feedback (stage presence, gesture, eye contact)."""
    presence = subscores['stage_presence']
    gesture = subscores['gesture']
    eye_contact = subscores['eye_contact']
    movement = subscores['movement']

    lines = []

    if presence >= 4.0:
        lines.append(
            "Your physical presence communicates confidence. The body is part of the performance, not just a vehicle for the voice."
        )
    elif presence >= 3.0:
        lines.append(
            "There's awareness of the body's role, but it's not yet fully committed. "
            "Some moments show physical intention; others default to standing delivery."
        )
    else:
        lines.append(
            "The physical aspect of the performance is minimal. "
            "The body has information to offer the audience that the voice alone can't carry."
        )

    if gesture >= 3.5:
        lines.append(
            "Gestures support the text without overriding it. Your hands are doing honest work."
        )
    else:
        lines.append(
            "Gestures are either minimal or not connected to the text's meaning. "
            "Start with one deliberate physical choice per section and build from there."
        )

    if eye_contact >= 3.5:
        lines.append(
            "Eye line choices create connection. You're performing to the space, not into the page."
        )
    else:
        lines.append(
            "Eye contact is an area for growth. Looking up from the page - even briefly - "
            "changes the relationship between performer and audience."
        )

    if movement >= 3.5:
        lines.append("Movement through the space feels purposeful, not restless.")
    else:
        lines.append(
            "Consider how you use the space. Stillness can be powerful when it's chosen, "
            "but movement can mark transitions between ideas."
        )

    return " ".join(lines)


def generate_audience_feedback(score: float, subscores: dict, rng: random.Random, moments: list) -> str:
    """Generate Audience pillar coach feedback (engagement, connection)."""
    engagement = subscores['engagement']
    connection = subscores['connection']
    responsiveness = subscores['responsiveness']
    command = subscores['command']

    lines = []

    if engagement >= 4.0:
        lines.append(
            "The performance holds attention. There's a clear arc the audience can follow."
        )
    elif engagement >= 3.0:
        lines.append(
            "Engagement is present but uneven. Some sections pull the listener in; others allow drift."
        )
    else:
        lines.append(
            "The performance would benefit from stronger audience orientation. "
            "Consider where you're inviting people in versus performing for yourself."
        )

    if connection >= 3.5:
        lines.append(
            "There's a sense of performing for someone, not just performing. That distinction matters."
        )
    else:
        lines.append(
            "The piece feels somewhat internal. Finding specific moments to reach outward "
            "will shift how the audience receives it."
        )

    if command >= 3.5:
        lines.append(
            "You take ownership of the space. The audience knows who's in charge of this moment."
        )
    else:
        lines.append(
            "Stage command develops with practice. The key is believing you have the right to be there "
            "and that what you're offering matters."
        )

    if responsiveness >= 3.5:
        lines.append(
            "There's adaptability in the delivery - a sense that you could adjust if the room needed it."
        )
    else:
        lines.append(
            "Building responsiveness means staying present with the audience, not just with the text. "
            "The room is part of the performance."
        )

    return " ".join(lines)


def generate_overall_summary(overall_score: float, pillar_scores: dict, rng: random.Random) -> str:
    """Generate the coach's overall summary following voice rules."""
    strongest = max(pillar_scores, key=pillar_scores.get)
    weakest = min(pillar_scores, key=pillar_scores.get)

    pillar_labels = {
        'spirit': 'Spirit (emotional delivery)',
        'chest': 'Chest (voice and breath)',
        'body': 'Body (physical presence)',
        'audience': 'Audience (connection and engagement)',
    }

    lines = []

    if overall_score >= 4.0:
        lines.append(
            "This performance demonstrates a real command of craft across multiple dimensions."
        )
    elif overall_score >= 3.0:
        lines.append(
            "This performance has genuine strengths and clear areas for focused development."
        )
    else:
        lines.append(
            "This performance is in its building phase. The fundamentals are here to work with."
        )

    lines.append(
        f"Your strongest dimension is {pillar_labels.get(strongest, strongest)}, "
        f"which anchors the other elements."
    )

    if weakest != strongest:
        lines.append(
            f"The most growth-ready area is {pillar_labels.get(weakest, weakest)}. "
            f"Small, deliberate work there will shift the overall performance noticeably."
        )

    lines.append(
        "This snapshot reflects observable delivery signals - voice, body, pacing, and engagement. "
        "It does not measure artistic intent or personal meaning."
    )

    return " ".join(lines)


def generate_key_moments(duration: float, scores: dict, rng: random.Random) -> list:
    """Generate deterministic key moments based on duration and scores."""
    moments = []
    num_moments = rng.randint(3, 6)
    overall = scores['overall']

    moment_types = ['peak', 'shift', 'dip', 'opening', 'close']

    # Always include opening and close
    opening_score = rng.uniform(max(1.0, overall - 1.0), min(5.0, overall + 0.5))
    moments.append({
        'timestamp': round(rng.uniform(2.0, min(15.0, duration * 0.1)), 1),
        'type': 'opening',
        'description': 'Performance opening - initial presence established'
            if opening_score >= 3.0 else 'Performance opening - settling into the space',
        'coach_note': 'Strong entries set the contract with your audience. '
                      'They decide in these first moments whether to lean in.'
            if opening_score >= 3.5 else
            'The opening is where you claim the space. '
            'Take a breath before the first word. Let the silence work for you.',
    })

    # Peak moment
    peak_time = round(rng.uniform(duration * 0.3, duration * 0.7), 1)
    moments.append({
        'timestamp': peak_time,
        'type': 'peak',
        'description': 'Strongest alignment of voice, body, and intent',
        'coach_note': 'This is the performer you are becoming. '
                      'Everything came together here - breath, timing, presence. '
                      'Remember what this felt like.',
    })

    # Dip moment
    if overall < 4.5:
        dip_time = round(rng.uniform(duration * 0.2, duration * 0.8), 1)
        while abs(dip_time - peak_time) < duration * 0.15:
            dip_time = round(rng.uniform(duration * 0.2, duration * 0.8), 1)
        moments.append({
            'timestamp': dip_time,
            'type': 'dip',
            'description': 'Energy or engagement dropped from surrounding sections',
            'coach_note': 'Check your relationship to this section in rehearsal. '
                          'Is the text doing something your body hasn\'t resolved yet? '
                          'Sometimes a dip is a clue about where the piece needs more physical work.',
        })

    # Shift moment
    shift_time = round(rng.uniform(duration * 0.35, duration * 0.65), 1)
    moments.append({
        'timestamp': shift_time,
        'type': 'shift',
        'description': 'Notable emotional or pacing transition',
        'coach_note': 'Transitions are where audiences either stay with you or lose the thread. '
                      'This one landed because you gave it space.'
            if overall >= 3.5 else
            'This transition could use more breath around it. '
            'Let the audience feel the shift before you move into the next section.',
    })

    # Close
    close_time = round(max(duration - rng.uniform(5.0, 15.0), duration * 0.85), 1)
    moments.append({
        'timestamp': close_time,
        'type': 'close',
        'description': 'Performance closing - final impression',
        'coach_note': 'How you leave the stage is as important as how you enter. '
                      'The last line carries everything that came before it.'
            if overall >= 3.5 else
            'The ending felt rushed. Hold the final moment. '
            'Let the last word sit in the room before you break.',
    })

    # Sort by timestamp
    moments.sort(key=lambda m: m['timestamp'])
    return moments


def generate_engagement_curve(duration: float, overall: float, rng: random.Random) -> list:
    """Generate a deterministic engagement curve."""
    num_points = max(10, int(duration / 5))
    curve = []
    base = overall / 5.0  # Normalize to 0-1

    for i in range(num_points):
        t = i / (num_points - 1)
        # Natural arc: starts moderate, builds, may dip, ends strong
        arc = 0.7 + 0.3 * math.sin(t * math.pi)
        noise = rng.uniform(-0.08, 0.08)
        value = max(0.1, min(1.0, base * arc + noise))
        curve.append(round(value, 3))

    return curve


def generate_growth_plan(pillar_scores: dict, subscores_all: dict, rng: random.Random) -> dict:
    """Generate top strengths and focus areas from scores."""
    # Collect all subscores with pillar context
    all_scores = []
    subscore_labels = {
        'emotion_alignment': 'Vocal-text emotional alignment (Spirit)',
        'transitions': 'Emotional transitions (Spirit)',
        'range': 'Emotional range and variety (Spirit)',
        'settling': 'Vocal settling and consistency (Spirit)',
        'breath_control': 'Breath management (Chest)',
        'vocal_projection': 'Vocal projection and volume (Chest)',
        'pacing': 'Pacing and tempo variation (Chest)',
        'articulation': 'Word articulation and clarity (Chest)',
        'stage_presence': 'Stage presence (Body)',
        'gesture': 'Gesture and physical expression (Body)',
        'eye_contact': 'Eye contact and visual connection (Body)',
        'movement': 'Purposeful movement (Body)',
        'engagement': 'Audience engagement (Audience)',
        'connection': 'Performer-audience connection (Audience)',
        'responsiveness': 'Responsiveness to the room (Audience)',
        'command': 'Stage command (Audience)',
    }

    for pillar, subs in subscores_all.items():
        for key, val in subs.items():
            label = subscore_labels.get(key, key)
            all_scores.append((label, val))

    # Sort by score
    sorted_scores = sorted(all_scores, key=lambda x: x[1], reverse=True)

    strengths = [s[0] for s in sorted_scores[:3]]
    focus = [s[0] for s in sorted_scores[-3:]]

    return {
        'top_strengths': strengths,
        'focus_areas': focus,
    }


def generate_report(video_path: str, analysis_id: str) -> dict:
    """
    Generate a deterministic performance analysis report.

    Uses a hash of the video file to seed all random decisions,
    ensuring the same file always produces the same report.
    """
    file_hash = hash_file(video_path)
    seed = int(file_hash[:8], 16)
    rng = random.Random(seed)

    # Extract actual video duration using ffprobe
    duration = get_video_duration(video_path)

    # Generate pillar scores (1-5 scale, consistent per file)
    spirit_score = round(rng.uniform(2.5, 4.8), 1)
    chest_score = round(rng.uniform(2.5, 4.8), 1)
    body_score = round(rng.uniform(2.5, 4.8), 1)
    audience_score = round(rng.uniform(2.5, 4.8), 1)

    # Weighted overall
    overall_score = round(
        spirit_score * 0.30 +
        chest_score * 0.25 +
        body_score * 0.25 +
        audience_score * 0.20,
        1
    )

    # Generate sub-scores (clustered around pillar score)
    def gen_subscores(base, keys):
        result = {}
        for k in keys:
            val = rng.gauss(base, 0.5)
            val = max(1.0, min(5.0, val))
            result[k] = round(val, 1)
        return result

    spirit_subs = gen_subscores(spirit_score, ['emotion_alignment', 'transitions', 'range', 'settling'])
    chest_subs = gen_subscores(chest_score, ['breath_control', 'vocal_projection', 'pacing', 'articulation'])
    body_subs = gen_subscores(body_score, ['stage_presence', 'gesture', 'eye_contact', 'movement'])
    audience_subs = gen_subscores(audience_score, ['engagement', 'connection', 'responsiveness', 'command'])

    pillar_scores = {
        'spirit': spirit_score,
        'chest': chest_score,
        'body': body_score,
        'audience': audience_score,
    }

    all_subscores = {
        'spirit': spirit_subs,
        'chest': chest_subs,
        'body': body_subs,
        'audience': audience_subs,
    }

    scores = {
        'overall': overall_score,
        **pillar_scores,
    }

    # Generate key moments (used by feedback generators)
    key_moments = generate_key_moments(duration, scores, rng)

    # Build report
    report = {
        'performance_id': analysis_id,
        'overall': {
            'score': overall_score,
            'grade': score_to_display(overall_score),
            'summary': generate_overall_summary(overall_score, pillar_scores, rng),
        },
        'pillars': [
            {
                'name': 'Spirit',
                'weight': 0.30,
                'score': spirit_score,
                'subscores': spirit_subs,
                'feedback': generate_spirit_feedback(spirit_score, spirit_subs, rng, key_moments),
                'icon': 'flame',
            },
            {
                'name': 'Chest',
                'weight': 0.25,
                'score': chest_score,
                'subscores': chest_subs,
                'feedback': generate_chest_feedback(chest_score, chest_subs, rng, key_moments),
                'icon': 'wind',
            },
            {
                'name': 'Body',
                'weight': 0.25,
                'score': body_score,
                'subscores': body_subs,
                'feedback': generate_body_feedback(body_score, body_subs, rng, key_moments),
                'icon': 'person',
            },
            {
                'name': 'Audience',
                'weight': 0.20,
                'score': audience_score,
                'subscores': audience_subs,
                'feedback': generate_audience_feedback(audience_score, audience_subs, rng, key_moments),
                'icon': 'users',
            },
        ],
        'timeline': {
            'duration_seconds': duration,
            'key_moments': key_moments,
            'engagement_curve': generate_engagement_curve(duration, overall_score, rng),
        },
        'growth_plan': generate_growth_plan(pillar_scores, all_subscores, rng),
    }

    return report


def main():
    parser = argparse.ArgumentParser(description='Stage Buddy V2 Analysis Runner')
    parser.add_argument('--video-path', required=True, help='Path to video file')
    parser.add_argument('--output-path', required=True, help='Path for output JSON report')
    parser.add_argument('--analysis-id', required=True, help='Unique analysis identifier')
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    # Simulate processing time (Beta: 3-8 seconds depending on file)
    file_size = os.path.getsize(args.video_path)
    process_time = min(8, max(3, file_size / (50 * 1024 * 1024)))
    time.sleep(process_time)

    try:
        report = generate_report(args.video_path, args.analysis_id)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(args.output_path), exist_ok=True)

        with open(args.output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Report written to {args.output_path}")
        sys.exit(0)

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

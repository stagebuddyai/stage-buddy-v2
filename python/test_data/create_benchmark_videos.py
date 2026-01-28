"""
Create synthetic benchmark videos for Body Engine calibration.

These videos simulate the three benchmark categories:
- STRONG (5/5): Dynamic, intentional gestures, stage usage, forward gaze
- MID (3/5): Excessive/hyperactive movement, less controlled
- WEAK (1/5): Static/sitting, minimal movement, looking down
"""

import numpy as np
import cv2
import os

VIDEO_DIR = os.path.dirname(os.path.abspath(__file__)) + "/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)


def create_strong_video(duration=10.0, fps=30):
    """
    STRONG performance (target: 5/5):
    - Full body engagement, character embodiment
    - Stage ownership, uses space effectively
    - Intentional gestures that serve the piece
    - Strong eye contact with audience
    """
    output_path = os.path.join(VIDEO_DIR, "synthetic_STRONG.mp4")
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = int(duration * fps)

    for i in range(frame_count):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 220
        progress = i / frame_count

        # STAGE MOVEMENT: Performer moves across stage purposefully
        # Moves from left to center to right and back
        stage_position = int(150 + 340 * (0.5 + 0.4 * np.sin(progress * 2 * np.pi)))

        # INTENTIONAL GESTURES: Controlled, purposeful arm movements
        # Arms move with clear intent, not random
        gesture_phase = progress * 8 * np.pi
        left_arm_angle = 0.6 * np.sin(gesture_phase) if (i // 30) % 3 != 2 else 0
        right_arm_angle = 0.6 * np.sin(gesture_phase + np.pi) if (i // 30) % 3 != 1 else 0

        # Body position (standing tall, confident)
        body_x = stage_position
        body_y = 120
        body_width = 60
        body_height = 160

        # Draw body (standing tall)
        cv2.rectangle(frame, (body_x, body_y),
                     (body_x + body_width, body_y + body_height),
                     (80, 80, 80), -1)

        # Draw head (looking forward at audience)
        head_x = body_x + body_width // 2
        head_y = body_y - 25
        cv2.circle(frame, (head_x, head_y), 25, (120, 120, 120), -1)

        # Draw eyes LOOKING FORWARD (strong eye contact)
        eye_y = head_y - 3
        cv2.circle(frame, (head_x - 8, eye_y), 4, (40, 40, 40), -1)
        cv2.circle(frame, (head_x + 8, eye_y), 4, (40, 40, 40), -1)

        # Draw arms with INTENTIONAL gestures
        shoulder_y = body_y + 20

        # Left arm
        left_arm_end_x = body_x - int(60 * np.cos(left_arm_angle))
        left_arm_end_y = shoulder_y + int(60 * np.sin(left_arm_angle)) + 40
        cv2.line(frame, (body_x, shoulder_y), (left_arm_end_x, left_arm_end_y), (80, 80, 80), 8)

        # Right arm
        right_arm_end_x = body_x + body_width + int(60 * np.cos(right_arm_angle))
        right_arm_end_y = shoulder_y + int(60 * np.sin(right_arm_angle)) + 40
        cv2.line(frame, (body_x + body_width, shoulder_y),
                (right_arm_end_x, right_arm_end_y), (80, 80, 80), 8)

        # Draw legs (stable stance)
        leg_top = body_y + body_height
        cv2.line(frame, (body_x + 15, leg_top), (body_x + 10, leg_top + 80), (80, 80, 80), 8)
        cv2.line(frame, (body_x + body_width - 15, leg_top),
                (body_x + body_width - 10, leg_top + 80), (80, 80, 80), 8)

        writer.write(frame)

    writer.release()
    print(f"Created STRONG video: {output_path}")
    return output_path


def create_mid_video(duration=10.0, fps=30):
    """
    MID performance (target: 3/5):
    - Excessive gestures, hyper movement
    - Lacks grounding, too much energy
    - Good eye contact but unfocused movement
    - Movement doesn't serve the piece
    """
    output_path = os.path.join(VIDEO_DIR, "synthetic_MID.mp4")
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = int(duration * fps)

    for i in range(frame_count):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 220
        progress = i / frame_count

        # EXCESSIVE MOVEMENT: Rapid, erratic position changes
        # Bouncing/swaying constantly
        x_jitter = int(30 * np.sin(progress * 20 * np.pi))
        y_jitter = int(15 * np.sin(progress * 25 * np.pi))

        body_x = 290 + x_jitter
        body_y = 120 + y_jitter
        body_width = 60
        body_height = 160

        # Draw body (constant motion)
        cv2.rectangle(frame, (body_x, body_y),
                     (body_x + body_width, body_y + body_height),
                     (80, 80, 80), -1)

        # Draw head
        head_x = body_x + body_width // 2
        head_y = body_y - 25
        cv2.circle(frame, (head_x, head_y), 25, (120, 120, 120), -1)

        # Eyes forward (good eye contact)
        eye_y = head_y - 3
        cv2.circle(frame, (head_x - 8, eye_y), 4, (40, 40, 40), -1)
        cv2.circle(frame, (head_x + 8, eye_y), 4, (40, 40, 40), -1)

        # EXCESSIVE ARM MOVEMENT: Constant, rapid gestures
        # High frequency, lacks intentionality
        gesture_phase = progress * 30 * np.pi  # Very fast
        left_arm_angle = 0.8 * np.sin(gesture_phase)
        right_arm_angle = 0.8 * np.sin(gesture_phase + 0.5)

        shoulder_y = body_y + 20

        # Flailing arms
        left_arm_end_x = body_x - int(70 * np.cos(left_arm_angle))
        left_arm_end_y = shoulder_y + int(70 * np.sin(left_arm_angle)) + 30
        cv2.line(frame, (body_x, shoulder_y), (left_arm_end_x, left_arm_end_y), (80, 80, 80), 8)

        right_arm_end_x = body_x + body_width + int(70 * np.cos(right_arm_angle))
        right_arm_end_y = shoulder_y + int(70 * np.sin(right_arm_angle)) + 30
        cv2.line(frame, (body_x + body_width, shoulder_y),
                (right_arm_end_x, right_arm_end_y), (80, 80, 80), 8)

        # Legs (less stable)
        leg_top = body_y + body_height
        leg_sway = int(5 * np.sin(progress * 15 * np.pi))
        cv2.line(frame, (body_x + 15, leg_top),
                (body_x + 10 + leg_sway, leg_top + 80), (80, 80, 80), 8)
        cv2.line(frame, (body_x + body_width - 15, leg_top),
                (body_x + body_width - 10 - leg_sway, leg_top + 80), (80, 80, 80), 8)

        writer.write(frame)

    writer.release()
    print(f"Created MID video: {output_path}")
    return output_path


def create_weak_video(duration=10.0, fps=30):
    """
    WEAK performance (target: 1/5):
    - Sitting position, no body language
    - Static, minimal movement
    - Eyes looking down (reading or avoiding)
    - No stage presence
    """
    output_path = os.path.join(VIDEO_DIR, "synthetic_WEAK.mp4")
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = int(duration * fps)

    for i in range(frame_count):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 220
        progress = i / frame_count

        # STATIC POSITION: Sitting, almost no movement
        # Very minimal micro-movements
        x_micro = int(2 * np.sin(progress * 3 * np.pi))

        # Sitting position (lower in frame, compressed body)
        body_x = 290 + x_micro
        body_y = 200  # Lower - sitting
        body_width = 70
        body_height = 100  # Shorter - sitting

        # Draw seated body
        cv2.rectangle(frame, (body_x, body_y),
                     (body_x + body_width, body_y + body_height),
                     (80, 80, 80), -1)

        # Draw chair/seat indication
        cv2.rectangle(frame, (body_x - 10, body_y + body_height - 20),
                     (body_x + body_width + 10, body_y + body_height + 40),
                     (100, 80, 60), -1)

        # Draw head (looking DOWN - poor eye contact)
        head_x = body_x + body_width // 2
        head_y = body_y - 20
        cv2.circle(frame, (head_x, head_y), 22, (120, 120, 120), -1)

        # Eyes LOOKING DOWN (reading/avoiding)
        eye_y = head_y + 5  # Eyes lower on face = looking down
        cv2.circle(frame, (head_x - 7, eye_y), 3, (40, 40, 40), -1)
        cv2.circle(frame, (head_x + 7, eye_y), 3, (40, 40, 40), -1)

        # STATIC ARMS: Hands in lap, no gestures
        shoulder_y = body_y + 15
        # Arms down, hands together (in lap)
        cv2.line(frame, (body_x, shoulder_y), (body_x + 20, body_y + 70), (80, 80, 80), 6)
        cv2.line(frame, (body_x + body_width, shoulder_y),
                (body_x + body_width - 20, body_y + 70), (80, 80, 80), 6)

        # Optional: Draw paper/script being read
        paper_x = body_x + 15
        paper_y = body_y + 50
        cv2.rectangle(frame, (paper_x, paper_y), (paper_x + 40, paper_y + 30),
                     (255, 255, 255), -1)
        cv2.rectangle(frame, (paper_x, paper_y), (paper_x + 40, paper_y + 30),
                     (150, 150, 150), 1)

        writer.write(frame)

    writer.release()
    print(f"Created WEAK video: {output_path}")
    return output_path


if __name__ == "__main__":
    print("Creating synthetic benchmark videos...")
    print()
    create_strong_video()
    create_mid_video()
    create_weak_video()
    print()
    print("All videos created in:", VIDEO_DIR)

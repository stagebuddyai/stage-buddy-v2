"""
Stage Buddy V2 - Gesture Analyzer
Detects and classifies gestures from pose estimation data.

This module:
1. Uses MediaPipe for pose estimation (with fallback to motion-based detection)
2. Classifies gestures as emphatic, illustrative, nervous, or none
3. Scores gesture intentionality based on movement patterns
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

from ..shared.data_structures import GestureType, GestureEvent

logger = logging.getLogger(__name__)


# MediaPipe pose landmark indices
class PoseLandmarks:
    """MediaPipe pose landmark indices for body parts."""
    # Upper body
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    # Face
    LEFT_EYE = 2
    RIGHT_EYE = 5
    LEFT_EAR = 7
    RIGHT_EAR = 8


class GestureAnalyzer:
    """
    Analyzes gestures from video frames using pose estimation.

    Gesture types based on POTS criteria:
    - EMPHATIC: Strong, purposeful movements that emphasize words
    - ILLUSTRATIVE: Gestures that paint/illustrate imagery
    - NERVOUS: Fidgeting, self-soothing, aimless movement
    - TRANSITIONAL: Movement between positions
    - NONE: No significant gesture
    """

    def __init__(
        self,
        use_mediapipe: bool = True,
        device: str = "cpu",
        movement_threshold: float = 0.02,
        gesture_min_duration: float = 0.2
    ):
        """
        Initialize the gesture analyzer.

        Args:
            use_mediapipe: Whether to use MediaPipe for pose estimation
            device: Compute device
            movement_threshold: Minimum movement to register (normalized)
            gesture_min_duration: Minimum gesture duration in seconds
        """
        self.use_mediapipe = use_mediapipe
        self.device = device
        self.movement_threshold = movement_threshold
        self.gesture_min_duration = gesture_min_duration

        # MediaPipe components (lazy loaded)
        self._pose = None
        self._mp_pose = None

        # Gesture classification thresholds
        self.emphatic_velocity_threshold = 0.15  # Fast, purposeful
        self.nervous_frequency_threshold = 0.5   # High frequency, low amplitude

        logger.info("GestureAnalyzer initialized")

    def _init_mediapipe(self):
        """Lazy-load MediaPipe to avoid import errors when not needed."""
        if self._pose is None:
            try:
                import mediapipe as mp
                # Try the legacy solutions API first (MediaPipe < 0.10)
                if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'pose'):
                    self._mp_pose = mp.solutions.pose
                    self._pose = self._mp_pose.Pose(
                        static_image_mode=False,
                        model_complexity=1,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    logger.info("MediaPipe Pose (legacy API) initialized successfully")
                else:
                    # MediaPipe 0.10+ uses task-based API
                    # For now, fall back to motion detection
                    logger.warning("MediaPipe 0.10+ detected - using motion-based fallback")
                    logger.info("Note: Legacy mp.solutions.pose not available in this version")
                    self._pose = None
            except ImportError:
                logger.warning("MediaPipe not available - using fallback motion detection")
                self._pose = None
            except Exception as e:
                logger.warning(f"MediaPipe initialization failed: {e} - using fallback")
                self._pose = None

    def estimate_poses(
        self,
        frames: List[np.ndarray],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Run pose estimation on video frames.

        Args:
            frames: List of BGR frames from video
            timestamps: Corresponding timestamps

        Returns:
            Dict with pose data for each frame
        """
        if self.use_mediapipe:
            self._init_mediapipe()

        if self._pose is not None:
            return self._estimate_with_mediapipe(frames, timestamps)
        else:
            return self._estimate_with_motion(frames, timestamps)

    def _estimate_with_mediapipe(
        self,
        frames: List[np.ndarray],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Estimate poses using MediaPipe."""
        import cv2

        poses = []

        for i, frame in enumerate(frames):
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run pose estimation
            results = self._pose.process(rgb_frame)

            if results.pose_landmarks:
                # Extract key landmarks
                landmarks = results.pose_landmarks.landmark

                pose_data = {
                    'timestamp': timestamps[i],
                    'detected': True,
                    'landmarks': {
                        'nose': self._landmark_to_point(landmarks[PoseLandmarks.NOSE]),
                        'left_shoulder': self._landmark_to_point(landmarks[PoseLandmarks.LEFT_SHOULDER]),
                        'right_shoulder': self._landmark_to_point(landmarks[PoseLandmarks.RIGHT_SHOULDER]),
                        'left_elbow': self._landmark_to_point(landmarks[PoseLandmarks.LEFT_ELBOW]),
                        'right_elbow': self._landmark_to_point(landmarks[PoseLandmarks.RIGHT_ELBOW]),
                        'left_wrist': self._landmark_to_point(landmarks[PoseLandmarks.LEFT_WRIST]),
                        'right_wrist': self._landmark_to_point(landmarks[PoseLandmarks.RIGHT_WRIST]),
                        'left_hip': self._landmark_to_point(landmarks[PoseLandmarks.LEFT_HIP]),
                        'right_hip': self._landmark_to_point(landmarks[PoseLandmarks.RIGHT_HIP]),
                    },
                    'visibility': self._get_visibility(landmarks)
                }
            else:
                pose_data = {
                    'timestamp': timestamps[i],
                    'detected': False,
                    'landmarks': None,
                    'visibility': 0.0
                }

            poses.append(pose_data)

        return {
            'poses': poses,
            'method': 'mediapipe',
            'frame_count': len(frames)
        }

    def _estimate_with_motion(
        self,
        frames: List[np.ndarray],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Fallback: Estimate motion using frame differencing.

        This provides a simpler motion-based analysis when MediaPipe
        is not available. It detects movement but cannot identify
        specific body parts.
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available for fallback motion detection")
            return self._create_empty_pose_data(timestamps)

        poses = []
        prev_gray = None

        for i, frame in enumerate(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is not None:
                # Calculate frame difference
                frame_diff = cv2.absdiff(prev_gray, gray)
                _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)

                # Calculate motion amount
                motion_pixels = np.sum(thresh > 0)
                total_pixels = thresh.shape[0] * thresh.shape[1]
                motion_ratio = motion_pixels / total_pixels

                # Find motion centroid
                if motion_pixels > 0:
                    ys, xs = np.where(thresh > 0)
                    centroid_x = np.mean(xs) / frame.shape[1]
                    centroid_y = np.mean(ys) / frame.shape[0]
                else:
                    centroid_x, centroid_y = 0.5, 0.5

                pose_data = {
                    'timestamp': timestamps[i],
                    'detected': True,
                    'motion_ratio': motion_ratio,
                    'centroid': (centroid_x, centroid_y),
                    'method': 'motion'
                }
            else:
                pose_data = {
                    'timestamp': timestamps[i],
                    'detected': False,
                    'motion_ratio': 0.0,
                    'centroid': (0.5, 0.5),
                    'method': 'motion'
                }

            prev_gray = gray
            poses.append(pose_data)

        return {
            'poses': poses,
            'method': 'motion',
            'frame_count': len(frames)
        }

    def _create_empty_pose_data(self, timestamps: List[float]) -> Dict[str, Any]:
        """Create empty pose data when no detection method is available."""
        poses = [{
            'timestamp': ts,
            'detected': False,
            'landmarks': None,
            'visibility': 0.0
        } for ts in timestamps]

        return {
            'poses': poses,
            'method': 'none',
            'frame_count': len(timestamps)
        }

    def analyze(
        self,
        pose_data: Dict[str, Any],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze pose data to detect and classify gestures.

        Args:
            pose_data: Pose estimation results from estimate_poses()
            timestamps: Frame timestamps

        Returns:
            Dict with gesture analysis results
        """
        poses = pose_data.get('poses', [])
        method = pose_data.get('method', 'none')

        if not poses:
            return self._create_empty_analysis()

        if method == 'mediapipe':
            return self._analyze_mediapipe_poses(poses, timestamps)
        elif method == 'motion':
            return self._analyze_motion_data(poses, timestamps)
        else:
            return self._create_empty_analysis()

    def _analyze_mediapipe_poses(
        self,
        poses: List[Dict],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Analyze gestures from MediaPipe pose data."""
        gesture_events = []
        segment_data = {}

        # Calculate hand/arm velocities
        velocities = self._calculate_velocities(poses)

        # Detect gesture events
        gesture_events = self._detect_gesture_events(poses, velocities, timestamps)

        # Calculate segment-level metrics
        segment_data = self._calculate_segment_metrics(poses, gesture_events, timestamps)

        # Calculate overall score
        overall_score = self._calculate_overall_gesture_score(
            poses, gesture_events, velocities
        )

        return {
            'overall_score': overall_score,
            'events': gesture_events,
            'segments': segment_data,
            'method': 'mediapipe',
            'detection_rate': sum(1 for p in poses if p['detected']) / len(poses) if poses else 0
        }

    def _analyze_motion_data(
        self,
        poses: List[Dict],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze gestures from motion-based data (fallback).

        Calibration Notes (Jan 2026):
        - STRONG: High space usage + controlled movement = high intentionality
        - MID: High motion variance + low space usage = erratic/nervous
        - WEAK: No movement = very low intentionality
        """
        # Extract motion ratios and centroids
        motion_ratios = [p.get('motion_ratio', 0.0) for p in poses]
        centroids = [p.get('centroid', (0.5, 0.5)) for p in poses]

        # Calculate basic motion stats
        avg_motion = np.mean(motion_ratios) if motion_ratios else 0.0
        motion_variance = np.var(motion_ratios) if motion_ratios else 0.0

        # Calculate SPACE USAGE from centroid positions
        # High variance in centroid = using the stage
        if len(centroids) > 1:
            centroid_xs = [c[0] for c in centroids]
            centroid_ys = [c[1] for c in centroids]
            space_usage_x = np.std(centroid_xs) * 4  # Scale to 0-1 range
            space_usage_y = np.std(centroid_ys) * 4
            space_usage = min(1.0, (space_usage_x + space_usage_y) / 2)
        else:
            space_usage = 0.0

        # Calculate movement CONSISTENCY (inverse of high-frequency variance)
        # Smooth, controlled movement = low high-freq variance
        if len(motion_ratios) > 3:
            # High frequency variance (frame-to-frame changes)
            motion_diffs = np.diff(motion_ratios)
            hf_variance = np.var(motion_diffs)

            # Consistency is inverse of high-frequency jitter
            consistency = max(0, 1.0 - hf_variance * 50)
        else:
            consistency = 0.5

        # CALIBRATED SCORING LOGIC
        if avg_motion < 0.005:
            # WEAK: Very little movement - static/sitting
            intentionality = 0.05
            overall_score = 0.05
        elif space_usage > 0.3 and consistency > 0.5:
            # STRONG: Uses stage space with controlled movement
            # Intentional performance - moving with purpose
            intentionality = 0.85 + space_usage * 0.15
            overall_score = 0.80 + space_usage * 0.20
        elif motion_variance > avg_motion * 0.5 or consistency < 0.4:
            # MID/WEAK: High variance OR low consistency = erratic/nervous
            # "Excessive gestures" that don't serve the piece
            intentionality = 0.25 + consistency * 0.25
            overall_score = 0.30 + consistency * 0.20
        elif avg_motion > 0.02:
            # Moderate movement with some space usage
            intentionality = 0.50 + space_usage * 0.30
            overall_score = 0.50 + space_usage * 0.30
        else:
            # Minimal movement
            intentionality = 0.20
            overall_score = 0.20

        # Create segment data
        segment_duration = 3.0
        segment_data = {}

        if timestamps:
            duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
            segment_count = max(1, int(duration / segment_duration))

            for i in range(segment_count):
                seg_start = i * segment_duration
                seg_end = (i + 1) * segment_duration

                # Get motion in this segment
                seg_indices = [j for j, t in enumerate(timestamps)
                              if seg_start <= t < seg_end]

                if seg_indices:
                    seg_motion = np.mean([motion_ratios[j] for j in seg_indices])

                    # Segment-level space usage
                    seg_centroids = [centroids[j] for j in seg_indices]
                    if len(seg_centroids) > 1:
                        seg_space = np.std([c[0] for c in seg_centroids]) * 4
                    else:
                        seg_space = 0.0

                    # Estimate gesture count from motion peaks
                    gesture_count = self._count_motion_peaks(
                        [motion_ratios[j] for j in seg_indices]
                    )

                    # Segment intentionality based on space usage
                    seg_intentionality = intentionality * (0.7 + 0.3 * min(1, seg_space))
                else:
                    seg_motion = 0.0
                    gesture_count = 0
                    seg_intentionality = 0.0

                segment_data[i] = {
                    'count': gesture_count,
                    'intentional_ratio': seg_intentionality,
                    'diversity': min(1.0, gesture_count / 3) if gesture_count > 0 else 0.0
                }

        return {
            'overall_score': overall_score,
            'events': [],  # Cannot detect specific events with motion method
            'segments': segment_data,
            'method': 'motion',
            'avg_motion': avg_motion,
            'motion_variance': motion_variance,
            'space_usage': space_usage,
            'consistency': consistency
        }

    def _calculate_velocities(self, poses: List[Dict]) -> Dict[str, List[float]]:
        """Calculate velocities of key body parts between frames."""
        velocities = {
            'left_wrist': [],
            'right_wrist': [],
            'left_elbow': [],
            'right_elbow': [],
            'head': []
        }

        for i in range(1, len(poses)):
            prev = poses[i - 1]
            curr = poses[i]

            if not prev.get('detected') or not curr.get('detected'):
                for key in velocities:
                    velocities[key].append(0.0)
                continue

            dt = curr['timestamp'] - prev['timestamp']
            if dt <= 0:
                dt = 0.1  # Fallback

            prev_lm = prev.get('landmarks', {})
            curr_lm = curr.get('landmarks', {})

            # Calculate velocities for each body part
            for key in ['left_wrist', 'right_wrist', 'left_elbow', 'right_elbow']:
                if key in prev_lm and key in curr_lm:
                    p1 = prev_lm[key]
                    p2 = curr_lm[key]
                    dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                    velocities[key].append(dist / dt)
                else:
                    velocities[key].append(0.0)

            # Head velocity (from nose)
            if 'nose' in prev_lm and 'nose' in curr_lm:
                p1 = prev_lm['nose']
                p2 = curr_lm['nose']
                dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                velocities['head'].append(dist / dt)
            else:
                velocities['head'].append(0.0)

        return velocities

    def _detect_gesture_events(
        self,
        poses: List[Dict],
        velocities: Dict[str, List[float]],
        timestamps: List[float]
    ) -> List[GestureEvent]:
        """Detect distinct gesture events from velocity data."""
        events = []

        # Combine hand velocities for overall arm activity
        if not velocities['left_wrist'] or not velocities['right_wrist']:
            return events

        hand_activity = [
            max(l, r) for l, r in
            zip(velocities['left_wrist'], velocities['right_wrist'])
        ]

        # Find gesture peaks
        in_gesture = False
        gesture_start = 0
        gesture_max_velocity = 0.0

        for i, (velocity, timestamp) in enumerate(zip(hand_activity, timestamps[1:])):
            if velocity > self.movement_threshold and not in_gesture:
                # Start of gesture
                in_gesture = True
                gesture_start = i
                gesture_max_velocity = velocity
            elif in_gesture:
                gesture_max_velocity = max(gesture_max_velocity, velocity)

                if velocity < self.movement_threshold * 0.5:
                    # End of gesture
                    in_gesture = False
                    duration = timestamps[i + 1] - timestamps[gesture_start + 1]

                    if duration >= self.gesture_min_duration:
                        # Classify the gesture
                        gesture_type, intentionality = self._classify_gesture(
                            poses[gesture_start:i + 1],
                            velocities,
                            gesture_start,
                            i
                        )

                        events.append(GestureEvent(
                            timestamp=timestamps[gesture_start + 1],
                            duration=duration,
                            gesture_type=gesture_type,
                            intentionality=intentionality,
                            body_region=self._determine_body_region(
                                velocities, gesture_start, i
                            ),
                            confidence=min(1.0, gesture_max_velocity / 0.2)
                        ))

        return events

    def _classify_gesture(
        self,
        pose_sequence: List[Dict],
        velocities: Dict[str, List[float]],
        start_idx: int,
        end_idx: int
    ) -> Tuple[GestureType, float]:
        """
        Classify a gesture based on its characteristics.

        Returns (gesture_type, intentionality_score)
        """
        # Get velocities for this gesture
        gesture_velocities = {
            key: vals[start_idx:end_idx] if vals else []
            for key, vals in velocities.items()
        }

        # Calculate characteristics
        max_velocity = max(
            max(gesture_velocities.get('left_wrist', [0])),
            max(gesture_velocities.get('right_wrist', [0]))
        )

        # Check for head movement (often indicates nervous gesture)
        head_movement = np.mean(gesture_velocities.get('head', [0]))

        # Check velocity variance (smooth vs jerky)
        all_hand_vel = (
            gesture_velocities.get('left_wrist', []) +
            gesture_velocities.get('right_wrist', [])
        )
        velocity_variance = np.var(all_hand_vel) if all_hand_vel else 0

        # Classification logic
        if max_velocity > self.emphatic_velocity_threshold:
            # High velocity = emphatic or illustrative
            if velocity_variance < 0.01:
                # Smooth, controlled = emphatic
                return GestureType.EMPHATIC, 0.9
            else:
                # More varied = illustrative
                return GestureType.ILLUSTRATIVE, 0.7
        elif head_movement > self.movement_threshold:
            # Head swaying often indicates nervousness
            return GestureType.NERVOUS, 0.3
        elif velocity_variance > 0.02:
            # High variance, low velocity = nervous fidgeting
            return GestureType.NERVOUS, 0.2
        else:
            # Moderate, controlled movement
            return GestureType.TRANSITIONAL, 0.5

    def _determine_body_region(
        self,
        velocities: Dict[str, List[float]],
        start_idx: int,
        end_idx: int
    ) -> str:
        """Determine which body region was most active in the gesture."""
        max_movement = {
            'hands': max(
                np.mean(velocities.get('left_wrist', [0])[start_idx:end_idx] or [0]),
                np.mean(velocities.get('right_wrist', [0])[start_idx:end_idx] or [0])
            ),
            'arms': max(
                np.mean(velocities.get('left_elbow', [0])[start_idx:end_idx] or [0]),
                np.mean(velocities.get('right_elbow', [0])[start_idx:end_idx] or [0])
            ),
            'head': np.mean(velocities.get('head', [0])[start_idx:end_idx] or [0])
        }

        # Return the most active region
        if max_movement['hands'] > max_movement['arms'] * 1.5:
            return 'hands'
        elif max_movement['hands'] > max_movement['head'] and max_movement['arms'] > max_movement['head']:
            return 'arms' if max_movement['arms'] > max_movement['hands'] * 0.5 else 'hands'
        elif max_movement['head'] > max_movement['hands']:
            return 'head'
        else:
            return 'full_body' if max_movement['arms'] > self.movement_threshold else 'hands'

    def _calculate_segment_metrics(
        self,
        poses: List[Dict],
        gesture_events: List[GestureEvent],
        timestamps: List[float]
    ) -> Dict[int, Dict[str, Any]]:
        """Calculate per-segment gesture metrics."""
        segment_data = {}
        segment_duration = 3.0

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / segment_duration))

        for i in range(segment_count):
            seg_start = i * segment_duration
            seg_end = (i + 1) * segment_duration

            # Get events in this segment
            seg_events = [
                e for e in gesture_events
                if seg_start <= e.timestamp < seg_end
            ]

            # Calculate metrics
            gesture_count = len(seg_events)

            if gesture_count > 0:
                intentional_events = [
                    e for e in seg_events
                    if e.gesture_type in [GestureType.EMPHATIC, GestureType.ILLUSTRATIVE]
                ]
                intentional_ratio = len(intentional_events) / gesture_count

                # Gesture type diversity
                types_present = set(e.gesture_type for e in seg_events)
                diversity = len(types_present) / 4  # Max 4 types
            else:
                intentional_ratio = 0.5  # Neutral if no gestures
                diversity = 0.0

            segment_data[i] = {
                'count': gesture_count,
                'intentional_ratio': intentional_ratio,
                'diversity': diversity
            }

        return segment_data

    def _calculate_overall_gesture_score(
        self,
        poses: List[Dict],
        gesture_events: List[GestureEvent],
        velocities: Dict[str, List[float]]
    ) -> float:
        """Calculate overall gesture intentionality score (0-1)."""
        if not poses:
            return 0.0

        # Component 1: Gesture intentionality ratio
        if gesture_events:
            intentional = [
                e for e in gesture_events
                if e.gesture_type in [GestureType.EMPHATIC, GestureType.ILLUSTRATIVE]
            ]
            intentionality_ratio = len(intentional) / len(gesture_events)
        else:
            intentionality_ratio = 0.0

        # Component 2: Movement quality
        # Check for controlled vs erratic movement
        all_velocities = (
            velocities.get('left_wrist', []) +
            velocities.get('right_wrist', [])
        )

        if all_velocities:
            # Good: moderate velocity with low variance = controlled
            avg_velocity = np.mean(all_velocities)
            velocity_var = np.var(all_velocities)

            # Ideal: 0.05-0.15 velocity range with variance < 0.01
            if 0.05 <= avg_velocity <= 0.2 and velocity_var < 0.02:
                movement_quality = 0.8
            elif avg_velocity < 0.02:
                # Very static
                movement_quality = 0.2
            elif velocity_var > 0.05:
                # Very erratic
                movement_quality = 0.3
            else:
                movement_quality = 0.5
        else:
            movement_quality = 0.0

        # Component 3: Detection quality
        detection_rate = sum(1 for p in poses if p.get('detected', False)) / len(poses)

        # Combine scores
        score = (
            intentionality_ratio * 0.5 +
            movement_quality * 0.35 +
            detection_rate * 0.15
        )

        return min(1.0, max(0.0, score))

    def _count_motion_peaks(self, motion_values: List[float]) -> int:
        """Count motion peaks for gesture estimation in fallback mode."""
        if len(motion_values) < 3:
            return 0

        peaks = 0
        for i in range(1, len(motion_values) - 1):
            if (motion_values[i] > motion_values[i-1] and
                motion_values[i] > motion_values[i+1] and
                motion_values[i] > self.movement_threshold):
                peaks += 1

        return peaks

    def _landmark_to_point(self, landmark) -> Tuple[float, float]:
        """Convert MediaPipe landmark to (x, y) tuple."""
        return (landmark.x, landmark.y)

    def _get_visibility(self, landmarks) -> float:
        """Get average visibility score for key landmarks."""
        key_indices = [
            PoseLandmarks.NOSE,
            PoseLandmarks.LEFT_SHOULDER,
            PoseLandmarks.RIGHT_SHOULDER,
            PoseLandmarks.LEFT_WRIST,
            PoseLandmarks.RIGHT_WRIST
        ]
        visibilities = [landmarks[i].visibility for i in key_indices]
        return np.mean(visibilities)

    def _create_empty_analysis(self) -> Dict[str, Any]:
        """Create empty analysis result."""
        return {
            'overall_score': 0.0,
            'events': [],
            'segments': {},
            'method': 'none',
            'detection_rate': 0.0
        }


def analyze_gestures(
    frames: List[np.ndarray],
    timestamps: List[float],
    use_mediapipe: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for gesture analysis.

    Args:
        frames: List of video frames
        timestamps: Frame timestamps
        use_mediapipe: Whether to use MediaPipe

    Returns:
        Gesture analysis results
    """
    analyzer = GestureAnalyzer(use_mediapipe=use_mediapipe)
    pose_data = analyzer.estimate_poses(frames, timestamps)
    return analyzer.analyze(pose_data, timestamps)

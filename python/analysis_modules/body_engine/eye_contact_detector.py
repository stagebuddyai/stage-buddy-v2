"""
Stage Buddy V2 - Eye Contact Detector
Detects and analyzes eye contact with the audience.

This module evaluates:
1. Ratio of time with audience-facing gaze
2. Gaze stability (not darting around nervously)
3. Eye contact engagement patterns
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EyeContactDetector:
    """
    Detects eye contact and gaze patterns from video frames.

    Good eye contact (POTS criteria):
    - Engaging the audience, not fixed on one spot
    - Not reading from paper or looking down
    - Natural movement, not staring

    Weak eye contact:
    - Eyes down, avoiding audience
    - Fixed stare at one point
    - Darting eyes (nervous)
    """

    def __init__(
        self,
        use_mediapipe: bool = True,
        segment_duration: float = 3.0
    ):
        """
        Initialize the eye contact detector.

        Args:
            use_mediapipe: Whether to use MediaPipe face mesh
            segment_duration: Duration for segment analysis
        """
        self.use_mediapipe = use_mediapipe
        self.segment_duration = segment_duration

        # MediaPipe face mesh (lazy loaded)
        self._face_mesh = None
        self._mp_face_mesh = None

        # Gaze thresholds
        self.forward_gaze_threshold = 0.3  # Deviation from forward
        self.downward_gaze_threshold = 0.1  # Looking down

        logger.info("EyeContactDetector initialized")

    def _init_mediapipe(self):
        """Lazy-load MediaPipe Face Mesh."""
        if self._face_mesh is None:
            try:
                import mediapipe as mp
                # Try the legacy solutions API first (MediaPipe < 0.10)
                if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'face_mesh'):
                    self._mp_face_mesh = mp.solutions.face_mesh
                    self._face_mesh = self._mp_face_mesh.FaceMesh(
                        static_image_mode=False,
                        max_num_faces=1,
                        refine_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    logger.info("MediaPipe Face Mesh (legacy API) initialized")
                else:
                    # MediaPipe 0.10+ uses task-based API
                    logger.warning("MediaPipe 0.10+ detected - using face detection fallback")
                    self._face_mesh = None
            except ImportError:
                logger.warning("MediaPipe not available - using fallback detection")
                self._face_mesh = None
            except Exception as e:
                logger.warning(f"MediaPipe initialization failed: {e} - using fallback")
                self._face_mesh = None

    def analyze(
        self,
        frames: List[np.ndarray],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze eye contact from video frames.

        Args:
            frames: List of BGR frames
            timestamps: Frame timestamps

        Returns:
            Eye contact analysis results
        """
        if not frames:
            return self._create_empty_analysis()

        if self.use_mediapipe:
            self._init_mediapipe()

        if self._face_mesh is not None:
            return self._analyze_with_mediapipe(frames, timestamps)
        else:
            return self._analyze_with_fallback(frames, timestamps)

    def _analyze_with_mediapipe(
        self,
        frames: List[np.ndarray],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Analyze eye contact using MediaPipe Face Mesh."""
        import cv2

        gaze_data = []

        for i, frame in enumerate(frames):
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]

                # Analyze gaze direction
                gaze_info = self._analyze_gaze(face_landmarks, frame.shape)
                gaze_info['timestamp'] = timestamps[i]
                gaze_info['face_detected'] = True
            else:
                gaze_info = {
                    'timestamp': timestamps[i],
                    'face_detected': False,
                    'looking_forward': False,
                    'looking_down': False,
                    'gaze_vector': (0, 0),
                    'head_pose': (0, 0, 0)
                }

            gaze_data.append(gaze_info)

        # Calculate metrics
        return self._calculate_eye_contact_metrics(gaze_data, timestamps)

    def _analyze_with_fallback(
        self,
        frames: List[np.ndarray],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Fallback: Use face detection and brightness analysis.

        When MediaPipe is not available, we use simpler heuristics:
        - Face detection to check if performer is facing camera
        - Eye region brightness to detect if eyes are open/visible
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available for fallback")
            return self._create_empty_analysis()

        # Try to use Haar cascade for face detection
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception:
            logger.warning("Face cascade not available")
            return self._create_empty_analysis()

        face_detections = []

        for i, frame in enumerate(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )

            if len(faces) > 0:
                # Face detected - assume looking forward
                x, y, w, h = faces[0]
                face_center_y = (y + h/2) / frame.shape[0]

                # If face is in upper portion of frame, likely looking at camera
                looking_forward = face_center_y < 0.6

                face_detections.append({
                    'timestamp': timestamps[i],
                    'face_detected': True,
                    'looking_forward': looking_forward,
                    'face_position': (x, y, w, h),
                    'face_center_y': face_center_y
                })
            else:
                face_detections.append({
                    'timestamp': timestamps[i],
                    'face_detected': False,
                    'looking_forward': False
                })

        # Calculate metrics from fallback detection
        return self._calculate_fallback_metrics(face_detections, timestamps)

    def _analyze_gaze(
        self,
        face_landmarks,
        frame_shape: Tuple[int, int, int]
    ) -> Dict[str, Any]:
        """Analyze gaze direction from face landmarks."""
        # Key landmarks for gaze estimation
        # Using iris landmarks (468-477 for left, 473-477 for right)

        try:
            landmarks = face_landmarks.landmark

            # Get eye positions
            left_eye = np.array([landmarks[33].x, landmarks[33].y])   # Left eye outer
            right_eye = np.array([landmarks[263].x, landmarks[263].y])  # Right eye outer

            # Get nose tip for head pose
            nose_tip = np.array([landmarks[1].x, landmarks[1].y])

            # Get forehead and chin for head tilt
            forehead = np.array([landmarks[10].x, landmarks[10].y])
            chin = np.array([landmarks[152].x, landmarks[152].y])

            # Calculate head pose (pitch)
            head_vertical = chin[1] - forehead[1]
            head_horizontal = chin[0] - forehead[0]

            # Looking down: chin closer to camera (larger y relative to forehead)
            pitch_estimate = head_vertical
            looking_down = pitch_estimate > 0.15

            # Looking forward: eyes roughly horizontal, nose centered
            eye_line = right_eye[0] - left_eye[0]
            nose_offset = abs(nose_tip[0] - 0.5)  # Deviation from center

            looking_forward = (
                abs(right_eye[1] - left_eye[1]) < 0.05 and  # Eyes level
                nose_offset < self.forward_gaze_threshold and
                not looking_down
            )

            # Estimate gaze vector (simplified)
            gaze_x = nose_offset * (-1 if nose_tip[0] < 0.5 else 1)
            gaze_y = pitch_estimate

            return {
                'looking_forward': looking_forward,
                'looking_down': looking_down,
                'gaze_vector': (gaze_x, gaze_y),
                'head_pose': (pitch_estimate, gaze_x, 0),
                'eye_positions': (left_eye.tolist(), right_eye.tolist())
            }
        except Exception as e:
            logger.debug(f"Gaze analysis error: {e}")
            return {
                'looking_forward': False,
                'looking_down': False,
                'gaze_vector': (0, 0),
                'head_pose': (0, 0, 0)
            }

    def _calculate_eye_contact_metrics(
        self,
        gaze_data: List[Dict],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Calculate eye contact metrics from gaze data."""
        if not gaze_data:
            return self._create_empty_analysis()

        # Calculate detection rate
        faces_detected = sum(1 for g in gaze_data if g.get('face_detected', False))
        detection_rate = faces_detected / len(gaze_data) if gaze_data else 0

        # Calculate forward gaze ratio
        forward_frames = sum(1 for g in gaze_data if g.get('looking_forward', False))
        forward_ratio = forward_frames / faces_detected if faces_detected > 0 else 0

        # Calculate downward gaze ratio (bad)
        downward_frames = sum(1 for g in gaze_data if g.get('looking_down', False))
        downward_ratio = downward_frames / faces_detected if faces_detected > 0 else 0

        # Calculate gaze stability (low variance = stable)
        gaze_vectors = [g.get('gaze_vector', (0, 0)) for g in gaze_data if g.get('face_detected')]
        if gaze_vectors:
            x_variance = np.var([gv[0] for gv in gaze_vectors])
            y_variance = np.var([gv[1] for gv in gaze_vectors])
            # Stability: low variance is good, but not TOO low (staring)
            raw_stability = 1.0 - min(1.0, (x_variance + y_variance) * 10)

            # Penalize if variance is extremely low (fixed stare)
            if x_variance < 0.001 and y_variance < 0.001:
                gaze_stability = raw_stability * 0.7
            else:
                gaze_stability = raw_stability
        else:
            gaze_stability = 0.0

        # Overall eye contact score
        # Good: high forward ratio, low downward, moderate stability
        contact_score = forward_ratio * 0.5 + (1.0 - downward_ratio) * 0.3 + gaze_stability * 0.2

        # Create segment data
        segment_data = self._create_segment_data(gaze_data, timestamps)

        return {
            'overall_score': contact_score,
            'segments': segment_data,
            'forward_ratio': forward_ratio,
            'downward_ratio': downward_ratio,
            'gaze_stability': gaze_stability,
            'detection_rate': detection_rate,
            'method': 'mediapipe'
        }

    def _calculate_fallback_metrics(
        self,
        face_detections: List[Dict],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Calculate metrics from fallback face detection."""
        if not face_detections:
            return self._create_empty_analysis()

        # Detection rate
        faces_detected = sum(1 for f in face_detections if f.get('face_detected', False))
        detection_rate = faces_detected / len(face_detections) if face_detections else 0

        # Forward looking ratio
        forward_frames = sum(1 for f in face_detections if f.get('looking_forward', False))
        forward_ratio = forward_frames / faces_detected if faces_detected > 0 else 0

        # Estimate stability from face position variance
        face_positions = [
            f.get('face_center_y', 0.5) for f in face_detections
            if f.get('face_detected', False)
        ]
        if face_positions:
            position_variance = np.var(face_positions)
            gaze_stability = 1.0 - min(1.0, position_variance * 20)
        else:
            gaze_stability = 0.0

        # Overall score (lower confidence due to fallback method)
        contact_score = (forward_ratio * 0.6 + gaze_stability * 0.4) * 0.8  # 20% penalty for fallback

        # Create segment data
        segment_data = self._create_fallback_segment_data(face_detections, timestamps)

        return {
            'overall_score': contact_score,
            'segments': segment_data,
            'forward_ratio': forward_ratio,
            'downward_ratio': 0.0,  # Can't detect in fallback
            'gaze_stability': gaze_stability,
            'detection_rate': detection_rate,
            'method': 'fallback'
        }

    def _create_segment_data(
        self,
        gaze_data: List[Dict],
        timestamps: List[float]
    ) -> Dict[int, Dict[str, Any]]:
        """Create per-segment eye contact data."""
        segment_data = {}

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            seg_start = i * self.segment_duration
            seg_end = (i + 1) * self.segment_duration

            # Get gaze data in this segment
            seg_gaze = [
                g for g in gaze_data
                if seg_start <= g.get('timestamp', 0) < seg_end
            ]

            if seg_gaze:
                detected = [g for g in seg_gaze if g.get('face_detected', False)]
                forward = [g for g in detected if g.get('looking_forward', False)]

                contact_ratio = len(forward) / len(seg_gaze) if seg_gaze else 0

                # Gaze stability for segment
                gaze_vectors = [g.get('gaze_vector', (0, 0)) for g in detected]
                if gaze_vectors:
                    variance = np.var([gv[0] for gv in gaze_vectors]) + \
                              np.var([gv[1] for gv in gaze_vectors])
                    stability = 1.0 - min(1.0, variance * 10)
                else:
                    stability = 0.0
            else:
                contact_ratio = 0.0
                stability = 0.0

            segment_data[i] = {
                'contact_ratio': contact_ratio,
                'gaze_stability': stability
            }

        return segment_data

    def _create_fallback_segment_data(
        self,
        face_detections: List[Dict],
        timestamps: List[float]
    ) -> Dict[int, Dict[str, Any]]:
        """Create segment data from fallback detection."""
        segment_data = {}

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            seg_start = i * self.segment_duration
            seg_end = (i + 1) * self.segment_duration

            # Get detections in segment
            seg_indices = [
                j for j, t in enumerate(timestamps)
                if seg_start <= t < seg_end
            ]

            if seg_indices:
                seg_detections = [face_detections[j] for j in seg_indices]
                forward = sum(1 for f in seg_detections if f.get('looking_forward', False))
                contact_ratio = forward / len(seg_detections)

                # Stability from position variance
                positions = [
                    f.get('face_center_y', 0.5) for f in seg_detections
                    if f.get('face_detected', False)
                ]
                if positions:
                    stability = 1.0 - min(1.0, np.var(positions) * 20)
                else:
                    stability = 0.0
            else:
                contact_ratio = 0.0
                stability = 0.0

            segment_data[i] = {
                'contact_ratio': contact_ratio,
                'gaze_stability': stability
            }

        return segment_data

    def _create_empty_analysis(self) -> Dict[str, Any]:
        """Create empty analysis result."""
        return {
            'overall_score': 0.0,
            'segments': {},
            'forward_ratio': 0.0,
            'downward_ratio': 0.0,
            'gaze_stability': 0.0,
            'detection_rate': 0.0,
            'method': 'none'
        }


def detect_eye_contact(
    frames: List[np.ndarray],
    timestamps: List[float]
) -> Dict[str, Any]:
    """
    Convenience function for eye contact detection.

    Args:
        frames: List of video frames
        timestamps: Frame timestamps

    Returns:
        Eye contact analysis results
    """
    detector = EyeContactDetector()
    return detector.analyze(frames, timestamps)

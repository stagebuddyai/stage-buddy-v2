"""
Stage Buddy V2 - Stage Presence Analyzer
Analyzes use of space, stance, and physical confidence.

This module evaluates:
1. Movement patterns and stage space usage
2. Position stability vs. nervous pacing
3. Stance confidence (grounded vs. swaying)
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class StagePresenceAnalyzer:
    """
    Analyzes stage presence from pose estimation data.

    Good stage presence (POTS criteria):
    - Uses available space effectively
    - Movement is purposeful, not nervous pacing
    - Stance is grounded and confident
    - Physical presence commands attention

    Weak stage presence:
    - Rooted to one spot OR nervous pacing
    - Swaying, shifting weight nervously
    - Hunched posture, closed body language
    """

    def __init__(
        self,
        use_mediapipe: bool = True,
        segment_duration: float = 3.0
    ):
        """
        Initialize the stage presence analyzer.

        Args:
            use_mediapipe: Whether pose data comes from MediaPipe
            segment_duration: Duration for segment analysis
        """
        self.use_mediapipe = use_mediapipe
        self.segment_duration = segment_duration

        # Thresholds for movement classification
        self.micro_movement_threshold = 0.01   # Below this = static
        self.normal_movement_threshold = 0.05  # Good movement range
        self.pacing_threshold = 0.15           # Above this = nervous pacing

        logger.info("StagePresenceAnalyzer initialized")

    def analyze(
        self,
        pose_data: Dict[str, Any],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze stage presence from pose data.

        Args:
            pose_data: Pose estimation results
            timestamps: Frame timestamps

        Returns:
            Stage presence analysis results
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
        """Analyze stage presence from MediaPipe pose data."""
        # Track body center position over time
        positions = []

        for pose in poses:
            if pose.get('detected') and pose.get('landmarks'):
                lm = pose['landmarks']

                # Body center = midpoint between shoulders
                if 'left_shoulder' in lm and 'right_shoulder' in lm:
                    center_x = (lm['left_shoulder'][0] + lm['right_shoulder'][0]) / 2
                    center_y = (lm['left_shoulder'][1] + lm['right_shoulder'][1]) / 2
                    positions.append((center_x, center_y, pose['timestamp']))
            else:
                # Interpolate or skip
                pass

        if len(positions) < 2:
            return self._create_empty_analysis()

        # Calculate movement metrics
        movement_metrics = self._calculate_movement_metrics(positions)

        # Calculate stance metrics
        stance_metrics = self._calculate_stance_metrics(poses)

        # Calculate space usage
        space_usage = self._calculate_space_usage(positions)

        # Generate segment data
        segment_data = self._create_segment_data(
            positions, movement_metrics, timestamps
        )

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            movement_metrics, stance_metrics, space_usage
        )

        # Generate movement heatmap (optional)
        heatmap = self._generate_heatmap(positions)

        return {
            'overall_score': overall_score,
            'segments': segment_data,
            'avg_movement': movement_metrics['avg_movement'],
            'movement_variance': movement_metrics['movement_variance'],
            'space_usage': space_usage,
            'stance_stability': stance_metrics['stability'],
            'heatmap': heatmap,
            'method': 'mediapipe'
        }

    def _analyze_motion_data(
        self,
        poses: List[Dict],
        timestamps: List[float]
    ) -> Dict[str, Any]:
        """Analyze stage presence from motion-based data (fallback)."""
        # Extract motion and centroid data
        motion_ratios = [p.get('motion_ratio', 0.0) for p in poses]
        centroids = [p.get('centroid', (0.5, 0.5)) for p in poses]

        # Calculate movement from centroid changes
        movements = []
        for i in range(1, len(centroids)):
            dx = centroids[i][0] - centroids[i-1][0]
            dy = centroids[i][1] - centroids[i-1][1]
            movements.append(np.sqrt(dx**2 + dy**2))

        avg_movement = np.mean(movements) if movements else 0.0
        movement_variance = np.var(movements) if movements else 0.0

        # Estimate space usage from centroid range
        if centroids:
            x_coords = [c[0] for c in centroids]
            y_coords = [c[1] for c in centroids]
            x_range = max(x_coords) - min(x_coords)
            y_range = max(y_coords) - min(y_coords)
            space_usage = min(1.0, (x_range + y_range) / 1.0)  # Normalized
        else:
            space_usage = 0.0

        # Score based on movement patterns
        # Very static = weak (sitting, not using body)
        # Excessive movement = weak (nervous pacing)
        # Moderate, controlled = strong

        if avg_movement < 0.01:
            # Very static - likely sitting or rooted
            movement_quality = 0.1
            stability = 0.8  # Stable but not in a good way
        elif avg_movement > 0.1:
            # Excessive movement - nervous pacing
            movement_quality = 0.3
            stability = 0.3
        elif movement_variance > avg_movement:
            # Erratic movement
            movement_quality = 0.4
            stability = 0.4
        else:
            # Controlled, purposeful movement
            movement_quality = 0.7
            stability = 0.7

        overall_score = (
            movement_quality * 0.4 +
            stability * 0.3 +
            space_usage * 0.3
        )

        # Create segment data
        segment_data = self._create_motion_segment_data(
            motion_ratios, centroids, timestamps
        )

        return {
            'overall_score': overall_score,
            'segments': segment_data,
            'avg_movement': avg_movement,
            'movement_variance': movement_variance,
            'space_usage': space_usage,
            'stance_stability': stability,
            'heatmap': None,
            'method': 'motion'
        }

    def _calculate_movement_metrics(
        self,
        positions: List[Tuple[float, float, float]]
    ) -> Dict[str, float]:
        """Calculate movement metrics from position history."""
        movements = []

        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            dt = positions[i][2] - positions[i-1][2]

            if dt > 0:
                # Velocity-based movement
                velocity = np.sqrt(dx**2 + dy**2) / dt
            else:
                velocity = np.sqrt(dx**2 + dy**2)

            movements.append(velocity)

        avg_movement = np.mean(movements) if movements else 0.0
        movement_variance = np.var(movements) if movements else 0.0
        max_movement = max(movements) if movements else 0.0

        # Calculate movement consistency
        # Good: moderate movement with low variance
        # Bad: static OR high variance (nervous)

        return {
            'avg_movement': avg_movement,
            'movement_variance': movement_variance,
            'max_movement': max_movement,
            'movements': movements
        }

    def _calculate_stance_metrics(
        self,
        poses: List[Dict]
    ) -> Dict[str, float]:
        """Calculate stance stability metrics."""
        shoulder_widths = []
        hip_movements = []

        for i, pose in enumerate(poses):
            if not pose.get('detected') or not pose.get('landmarks'):
                continue

            lm = pose['landmarks']

            # Shoulder width (posture indicator)
            if 'left_shoulder' in lm and 'right_shoulder' in lm:
                width = abs(lm['right_shoulder'][0] - lm['left_shoulder'][0])
                shoulder_widths.append(width)

            # Track hip position for stability
            if 'left_hip' in lm and 'right_hip' in lm:
                hip_center = (lm['left_hip'][0] + lm['right_hip'][0]) / 2
                if i > 0:
                    # Compare to previous
                    pass  # Calculate stability

        # Shoulder width consistency indicates stable posture
        if shoulder_widths:
            width_variance = np.var(shoulder_widths)
            # Low variance = stable stance
            stability = 1.0 - min(1.0, width_variance * 100)
        else:
            stability = 0.5

        return {
            'stability': stability,
            'avg_shoulder_width': np.mean(shoulder_widths) if shoulder_widths else 0.0
        }

    def _calculate_space_usage(
        self,
        positions: List[Tuple[float, float, float]]
    ) -> float:
        """Calculate how much of the stage space was used."""
        if not positions:
            return 0.0

        x_coords = [p[0] for p in positions]
        y_coords = [p[1] for p in positions]

        # Calculate the bounding box of movement
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)

        # Normalize: assume performer should use at least 30% of frame width
        # and move somewhat vertically (10% range)
        x_score = min(1.0, x_range / 0.3)
        y_score = min(1.0, y_range / 0.1)

        # Weight x movement more (horizontal stage movement)
        space_usage = x_score * 0.7 + y_score * 0.3

        return space_usage

    def _create_segment_data(
        self,
        positions: List[Tuple[float, float, float]],
        movement_metrics: Dict,
        timestamps: List[float]
    ) -> Dict[int, Dict[str, Any]]:
        """Create per-segment stage presence data."""
        segment_data = {}

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            seg_start = i * self.segment_duration
            seg_end = (i + 1) * self.segment_duration

            # Get positions in this segment
            seg_positions = [
                p for p in positions
                if seg_start <= p[2] < seg_end
            ]

            if seg_positions:
                # Calculate segment-specific metrics
                seg_movements = []
                for j in range(1, len(seg_positions)):
                    dx = seg_positions[j][0] - seg_positions[j-1][0]
                    dy = seg_positions[j][1] - seg_positions[j-1][1]
                    seg_movements.append(np.sqrt(dx**2 + dy**2))

                avg_movement = np.mean(seg_movements) if seg_movements else 0.0

                # Space usage in segment
                x_range = max(p[0] for p in seg_positions) - min(p[0] for p in seg_positions)
                space_usage = min(1.0, x_range / 0.2)

                # Stability
                if seg_movements:
                    variance = np.var(seg_movements)
                    stability = 1.0 - min(1.0, variance * 50)
                else:
                    stability = 0.5
            else:
                avg_movement = 0.0
                space_usage = 0.0
                stability = 0.5

            segment_data[i] = {
                'movement': avg_movement,
                'space_usage': space_usage,
                'stability': stability
            }

        return segment_data

    def _create_motion_segment_data(
        self,
        motion_ratios: List[float],
        centroids: List[Tuple[float, float]],
        timestamps: List[float]
    ) -> Dict[int, Dict[str, Any]]:
        """Create segment data from motion-based analysis."""
        segment_data = {}

        if not timestamps:
            return segment_data

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        segment_count = max(1, int(duration / self.segment_duration))

        for i in range(segment_count):
            seg_start = i * self.segment_duration
            seg_end = (i + 1) * self.segment_duration

            # Get indices for this segment
            seg_indices = [
                j for j, t in enumerate(timestamps)
                if seg_start <= t < seg_end
            ]

            if seg_indices:
                seg_motion = np.mean([motion_ratios[j] for j in seg_indices])

                # Space usage from centroid movement
                seg_centroids = [centroids[j] for j in seg_indices]
                if len(seg_centroids) > 1:
                    x_range = max(c[0] for c in seg_centroids) - min(c[0] for c in seg_centroids)
                    space_usage = min(1.0, x_range / 0.2)
                else:
                    space_usage = 0.0

                # Stability: inverse of motion variance
                motion_var = np.var([motion_ratios[j] for j in seg_indices])
                stability = 1.0 - min(1.0, motion_var * 10)
            else:
                seg_motion = 0.0
                space_usage = 0.0
                stability = 0.5

            segment_data[i] = {
                'movement': seg_motion,
                'space_usage': space_usage,
                'stability': stability
            }

        return segment_data

    def _calculate_overall_score(
        self,
        movement_metrics: Dict[str, float],
        stance_metrics: Dict[str, float],
        space_usage: float
    ) -> float:
        """Calculate overall stage presence score."""
        avg_movement = movement_metrics['avg_movement']
        movement_variance = movement_metrics['movement_variance']
        stability = stance_metrics['stability']

        # Movement quality score
        # Ideal: moderate movement (0.02-0.1 velocity)
        # Too static (< 0.01) = bad (not using body)
        # Too much (> 0.15) = bad (nervous pacing)

        if avg_movement < 0.01:
            movement_score = 0.2  # Very static
        elif avg_movement > 0.15:
            movement_score = 0.4  # Excessive movement
        elif 0.02 <= avg_movement <= 0.08:
            movement_score = 0.9  # Ideal range
        else:
            movement_score = 0.6  # Acceptable

        # Penalize high variance (erratic movement)
        if movement_variance > avg_movement:
            movement_score *= 0.7

        # Overall score
        overall = (
            movement_score * 0.35 +
            stability * 0.35 +
            space_usage * 0.30
        )

        return min(1.0, max(0.0, overall))

    def _generate_heatmap(
        self,
        positions: List[Tuple[float, float, float]]
    ) -> Optional[np.ndarray]:
        """Generate a movement heatmap for visualization."""
        if not positions or len(positions) < 2:
            return None

        try:
            # Create a small heatmap (20x10 for stage representation)
            heatmap = np.zeros((10, 20), dtype=np.float32)

            for x, y, _ in positions:
                # Convert normalized coords to heatmap indices
                hx = int(min(19, max(0, x * 20)))
                hy = int(min(9, max(0, y * 10)))
                heatmap[hy, hx] += 1

            # Normalize
            if heatmap.max() > 0:
                heatmap = heatmap / heatmap.max()

            return heatmap
        except Exception as e:
            logger.warning(f"Failed to generate heatmap: {e}")
            return None

    def _create_empty_analysis(self) -> Dict[str, Any]:
        """Create empty analysis result."""
        return {
            'overall_score': 0.0,
            'segments': {},
            'avg_movement': 0.0,
            'movement_variance': 0.0,
            'space_usage': 0.0,
            'stance_stability': 0.0,
            'heatmap': None,
            'method': 'none'
        }


def analyze_stage_presence(
    pose_data: Dict[str, Any],
    timestamps: List[float]
) -> Dict[str, Any]:
    """
    Convenience function for stage presence analysis.

    Args:
        pose_data: Pose estimation results
        timestamps: Frame timestamps

    Returns:
        Stage presence analysis results
    """
    analyzer = StagePresenceAnalyzer()
    return analyzer.analyze(pose_data, timestamps)

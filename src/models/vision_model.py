"""
Computer Vision Model for Equipment Analysis

Analyzes equipment images to detect wear, damage, or maintenance needs.
"""

import cv2
import numpy as np
from PIL import Image
import logging
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class EquipmentVisionModel:
    """Computer vision model for analyzing equipment images."""

    def __init__(self):
        self.model = None
        self.classes = [
            'normal', 'wear', 'corrosion', 'crack', 'leak',
            'loose_connection', 'overheating', 'vibration_damage'
        ]
        # For simplicity, use basic image processing
        # In production, load a trained CNN model

    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        Analyze equipment image for potential issues.

        Args:
            image_path: Path to the image file

        Returns:
            Dict with analysis results
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"Image not found: {image_path}")
                return None

            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to load image: {image_path}")
                return None

            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Basic analysis techniques
            issues = []

            # 1. Check for corrosion (rough texture)
            roughness = self._calculate_roughness(gray)
            if roughness > 0.7:
                issues.append({
                    'type': 'corrosion',
                    'confidence': min(0.9, roughness),
                    'severity': 'high' if roughness > 0.8 else 'medium'
                })

            # 2. Check for cracks (edge detection)
            crack_score = self._detect_cracks(gray)
            if crack_score > 0.6:
                issues.append({
                    'type': 'crack',
                    'confidence': crack_score,
                    'severity': 'high'
                })

            # 3. Check for overheating (color analysis)
            heat_score = self._detect_overheating(image)
            if heat_score > 0.7:
                issues.append({
                    'type': 'overheating',
                    'confidence': heat_score,
                    'severity': 'high'
                })

            # 4. Check for loose connections (irregular shapes)
            connection_score = self._detect_loose_connections(gray)
            if connection_score > 0.5:
                issues.append({
                    'type': 'loose_connection',
                    'confidence': connection_score,
                    'severity': 'medium'
                })

            # Overall assessment
            if not issues:
                return {
                    'status': 'normal',
                    'issues': [],
                    'confidence': 0.8,
                    'recommendation': 'Equipment appears normal'
                }

            # Sort by confidence and severity
            issues.sort(key=lambda x: (x['severity'] == 'high', x['confidence']), reverse=True)

            severity_levels = {'high': 3, 'medium': 2, 'low': 1}
            overall_severity = max(issues, key=lambda x: severity_levels.get(x['severity'], 1))['severity']

            return {
                'status': 'issues_detected',
                'issues': issues,
                'overall_severity': overall_severity,
                'confidence': issues[0]['confidence'] if issues else 0.5,
                'recommendation': self._generate_recommendation(issues)
            }

        except Exception as e:
            logger.error(f"Failed to analyze image {image_path}: {e}")
            return None

    def _calculate_roughness(self, gray_image: np.ndarray) -> float:
        """Calculate surface roughness score."""
        # Use variance of Laplacian as roughness measure
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        variance = laplacian.var()
        # Normalize to 0-1 scale (rough guess)
        return min(1.0, variance / 500.0)

    def _detect_cracks(self, gray_image: np.ndarray) -> float:
        """Detect cracks using edge detection."""
        # Apply Canny edge detection
        edges = cv2.Canny(gray_image, 50, 150)
        # Calculate ratio of edge pixels
        edge_ratio = np.sum(edges > 0) / edges.size
        return min(1.0, edge_ratio * 5)  # Scale up for sensitivity

    def _detect_overheating(self, image: np.ndarray) -> float:
        """Detect overheating from color analysis."""
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Look for red/yellow hues (hot colors)
        red_mask = cv2.inRange(hsv, (0, 50, 50), (10, 255, 255))
        yellow_mask = cv2.inRange(hsv, (20, 50, 50), (40, 255, 255))
        hot_pixels = np.sum(red_mask > 0) + np.sum(yellow_mask > 0)
        hot_ratio = hot_pixels / image.size
        return min(1.0, hot_ratio * 10)

    def _detect_loose_connections(self, gray_image: np.ndarray) -> float:
        """Detect irregular shapes that might indicate loose connections."""
        # Use contour analysis
        contours, _ = cv2.findContours(gray_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.0

        # Calculate average circularity
        circularities = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 100:  # Skip small contours
                continue
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                circularities.append(circularity)

        if not circularities:
            return 0.0

        # Low circularity indicates irregular shapes
        avg_circularity = np.mean(circularities)
        return max(0.0, 1.0 - avg_circularity)

    def _generate_recommendation(self, issues: List[Dict]) -> str:
        """Generate maintenance recommendation based on detected issues."""
        primary_issue = issues[0]['type']
        severity = issues[0]['severity']

        recommendations = {
            'corrosion': 'Clean and apply protective coating',
            'crack': 'Inspect for structural integrity, possible repair needed',
            'overheating': 'Check cooling system and electrical connections',
            'loose_connection': 'Tighten connections and check for wear'
        }

        base_rec = recommendations.get(primary_issue, 'Schedule professional inspection')

        if severity == 'high':
            return f"URGENT: {base_rec}"
        elif severity == 'medium':
            return f"Schedule maintenance: {base_rec}"
        else:
            return f"Monitor: {base_rec}"

# Global instance
vision_model = EquipmentVisionModel()
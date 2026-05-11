"""
Anomaly Detection Service

This module provides basic anomaly detection for events based on content analysis.
"""

import re
from typing import List


class AnomalyDetector:
    """Service for detecting anomalous content in events."""

    def __init__(self):
        # Keywords that might indicate suspicious activity
        self.suspicious_keywords = {
            'high': ['hack', 'breach', 'exploit', 'malware', 'ransomware', 'phishing', 'scam', 'fraud'],
            'medium': ['suspicious', 'unusual', 'anomaly', 'threat', 'risk', 'alert', 'warning'],
            'low': ['error', 'failure', 'timeout', 'exception', 'crash']
        }

        # Weight for each keyword category
        self.weights = {'high': 0.8, 'medium': 0.5, 'low': 0.2}

    def detect_anomaly(self, content: str, event_type: str) -> float:
        """
        Detect anomaly score for the given content.

        Args:
            content: The text content to analyze
            event_type: The type of event

        Returns:
            Anomaly score between 0 (normal) and 1 (highly anomalous)
        """
        score = 0.0
        content_lower = content.lower()

        # Check for suspicious keywords
        for category, keywords in self.suspicious_keywords.items():
            weight = self.weights[category]
            for keyword in keywords:
                if keyword in content_lower:
                    score += weight
                    break  # Only count once per category

        # Adjust based on content length (very short or very long might be anomalous)
        content_length = len(content.split())
        if content_length < 5:
            score += 0.3  # Very short content
        elif content_length > 500:
            score += 0.2  # Very long content

        # Check for unusual patterns (all caps, excessive punctuation)
        if content.isupper() and len(content) > 10:
            score += 0.4

        punctuation_count = len(re.findall(r'[!?]{2,}', content))
        if punctuation_count > 3:
            score += 0.3

        # Normalize score to 0-1 range
        score = min(score, 1.0)

        return score


# Global instance
detector = AnomalyDetector()


def detect_anomaly(content: str, event_type: str) -> float:
    """
    Convenience function to detect anomaly in content.

    Args:
        content: The text content to analyze
        event_type: The type of event

    Returns:
        Anomaly score between 0 and 1
    """
    return detector.detect_anomaly(content, event_type)
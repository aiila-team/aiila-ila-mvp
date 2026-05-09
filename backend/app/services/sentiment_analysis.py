"""
Sentiment Analysis Service

This module provides sentiment analysis for text content using TextBlob.
"""

from textblob import TextBlob


def analyze_sentiment(text: str) -> float:
    """
    Analyze the sentiment of the given text.

    Args:
        text: The text content to analyze

    Returns:
        Sentiment polarity score between -1 (negative) and 1 (positive)
    """
    try:
        blob = TextBlob(text)
        # Return the polarity score
        return blob.sentiment.polarity
    except Exception:
        # Return neutral sentiment on error
        return 0.0
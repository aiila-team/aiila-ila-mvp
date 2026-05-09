"""
Entity Extraction Service

This module provides regex-based extraction of entities from text content,
including phone numbers, emails, URLs, crypto wallets, usernames, and social handles.
"""

import re
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Service for extracting various types of entities from text."""

    def __init__(self):
        # Regex patterns for entity extraction
        self.patterns = {
            "phone": re.compile(
                r'(\+?\d{1,3}[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
                re.IGNORECASE
            ),
            "email": re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                re.IGNORECASE
            ),
            "url": re.compile(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                re.IGNORECASE
            ),
            "crypto_wallet": re.compile(
                r'\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b',
                re.IGNORECASE
            ),
            "telegram_handle": re.compile(
                r'@([a-zA-Z0-9_]{5,32})',
                re.IGNORECASE
            ),
            "twitter_handle": re.compile(
                r'@([a-zA-Z0-9_]{1,15})(?=\s|$|[^a-zA-Z0-9_@])',
                re.IGNORECASE
            ),
            "username": re.compile(
                r'\b[a-zA-Z0-9_]{3,30}\b',
                re.IGNORECASE
            ),
        }

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from the given text.

        Args:
            text: The text content to analyze

        Returns:
            List of extracted entities with type, value, and confidence
        """
        entities = []

        # Extract phone numbers
        for match in self.patterns["phone"].findall(text):
            phone = ''.join(match).strip()
            if phone and len(phone) >= 10:
                entities.append({
                    "type": "phone",
                    "value": phone,
                    "confidence": 0.95
                })

        # Extract emails
        for match in self.patterns["email"].findall(text):
            entities.append({
                "type": "email",
                "value": match,
                "confidence": 0.98
            })

        # Extract URLs
        for match in self.patterns["url"].findall(text):
            try:
                parsed = urlparse(match)
                if parsed.netloc:
                    entities.append({
                        "type": "url",
                        "value": match,
                        "confidence": 0.90
                    })
            except:
                continue

        # Extract crypto wallets
        for match in self.patterns["crypto_wallet"].findall(text):
            entities.append({
                "type": "crypto_wallet",
                "value": match,
                "confidence": 0.99
            })

        # Extract Telegram handles
        for match in self.patterns["telegram_handle"].findall(text):
            entities.append({
                "type": "telegram_handle",
                "value": f"@{match}",
                "confidence": 0.85
            })

        # Extract Twitter handles
        for match in self.patterns["twitter_handle"].findall(text):
            entities.append({
                "type": "twitter_handle",
                "value": f"@{match}",
                "confidence": 0.85
            })

        # Extract usernames (lower confidence, only if not already captured)
        existing_values = {e["value"] for e in entities}
        for match in self.patterns["username"].findall(text):
            if match not in existing_values and not match.isdigit():
                entities.append({
                    "type": "username",
                    "value": match,
                    "confidence": 0.60
                })

        # Remove duplicates based on value
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity["type"], entity["value"])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        logger.info(f"Extracted {len(unique_entities)} unique entities")
        return unique_entities


# Global instance for easy import
extractor = EntityExtractor()


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Convenience function to extract entities from text.

    Args:
        text: The text content to analyze

    Returns:
        List of extracted entities
    """
    return extractor.extract_entities(text)
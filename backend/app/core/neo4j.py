"""
core/neo4j.py
──────────────────────────────────────────────────────────────────────────────
Neo4j Graph Database Connection Layer for ILA

This module provides the Neo4j driver singleton and connection management.
It handles connection lifecycle, error handling, and provides a clean interface
for graph operations throughout the application.

Configuration:
  - NEO4J_URI: bolt://neo4j:7687 (or neo4j://neo4j:7687 for clusters)
  - NEO4J_USER: neo4j
  - NEO4J_PASSWORD: <password from environment>

Usage:
  from app.core.neo4j import get_neo4j_driver

  driver = get_neo4j_driver()
  with driver.session() as session:
      result = session.run("MATCH (n) RETURN count(n) as count")
      print(result.single()["count"])

Error Handling:
  - Connection failures are logged and re-raised
  - Driver is thread-safe and can be shared across requests
  - Connection pooling is handled automatically by the driver

Shutdown:
  Call close_neo4j_driver() during application shutdown to clean up resources.
──────────────────────────────────────────────────────────────────────────────
"""

import logging
from typing import Optional

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global driver instance
_neo4j_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    """
    Get or create the Neo4j driver singleton.

    Returns:
        Neo4j driver instance

    Raises:
        ConnectionError: If unable to connect to Neo4j
        ValueError: If configuration is missing
    """
    global _neo4j_driver

    if _neo4j_driver is None:
        try:
            # Validate configuration
            if not settings.NEO4J_URI:
                raise ValueError("NEO4J_URI is not configured")
            if not settings.NEO4J_USER:
                raise ValueError("NEO4J_USER is not configured")
            if not settings.NEO4J_PASSWORD:
                raise ValueError("NEO4J_PASSWORD is not configured")

            # Create driver
            _neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                # Connection pool settings
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,  # 60 seconds
            )

            # Test connection
            _neo4j_driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {settings.NEO4J_URI}")

        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise ConnectionError("Failed to authenticate with Neo4j") from e
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise ConnectionError("Neo4j service is unavailable") from e
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise ConnectionError("Failed to connect to Neo4j") from e

    return _neo4j_driver


def close_neo4j_driver() -> None:
    """
    Close the Neo4j driver and clean up resources.
    Should be called during application shutdown.
    """
    global _neo4j_driver

    if _neo4j_driver is not None:
        _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j driver closed")


def health_check() -> bool:
    """
    Check if Neo4j is accessible.

    Returns:
        True if healthy, False otherwise
    """
    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        return True
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return False
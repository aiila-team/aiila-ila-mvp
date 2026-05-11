from .celery_worker import celery

import redis
import json
import random

from datetime import datetime

from loguru import logger


# Redis Connection
redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)


@celery.task(bind=True, max_retries=3)
def generate_risk_alert(self):

    try:

        logger.info("Generating risk alert")

        # Fake risk data
        alert = {

            "risk_score": random.randint(50, 100),

            "message": "High risk transaction detected",

            "timestamp": str(datetime.utcnow())
        }

        # Publish to Redis Pub/Sub
        redis_client.publish(
            "risk-alerts",
            json.dumps(alert)
        )

        logger.info(f"Alert Published: {alert}")

        return alert

    except Exception as e:

        logger.error(f"Task failed: {e}")

        raise self.retry(
            exc=e,
            countdown=5
        )
from .celery_worker import celery

import redis
import json
import random
from datetime import datetime

redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True
)

@celery.task(bind=True, max_retries=3)
def generate_risk_alert(self):

    try:

        alert = {
            "risk_score": random.randint(50, 100),
            "message": "High risk transaction detected",
            "timestamp": str(datetime.utcnow())
        }

        redis_client.publish(
            "risk-alerts",
            json.dumps(alert)
        )

        print("Alert Published:", alert)

        return alert

    except Exception as e:

        raise self.retry(exc=e, countdown=5)
from fastapi import FastAPI
from .websocket import router as websocket_router
from .tasks import generate_risk_alert

app = FastAPI()

app.include_router(websocket_router)

@app.get("/api/health")
async def health():

    return {
        "status": "running"
    }

@app.post("/api/send-alert")
async def send_alert():

    task = generate_risk_alert.delay()

    return {
        "message": "Alert task queued",
        "task_id": task.id
    }
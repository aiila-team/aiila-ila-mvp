from fastapi import FastAPI

app = FastAPI(
    title="ILA Backend",
    version="0.1.0"
)

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "ILA Backend"
    }
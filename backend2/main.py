from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Backend Service 2")

@app.get("/data")
async def get_data():
    return {
        "service": "backend-2",
        "message": "Here is your data",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend-2"}
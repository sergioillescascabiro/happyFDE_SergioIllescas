from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import require_dashboard_token

app = FastAPI(title="HappyFDE API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/health/auth")
async def health_auth(token: str = Depends(require_dashboard_token)):
    return {"status": "ok", "authenticated": True}

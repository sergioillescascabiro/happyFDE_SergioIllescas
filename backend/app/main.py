from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.auth import require_dashboard_token
from app.routers import loads as loads_router
from app.routers import carriers as carriers_router
from app.routers import calls as calls_router
from app.routers import shippers as shippers_router
from app.routers import metrics as metrics_router
from app.routers import quotes as quotes_router
from app.routers.agent import carriers as agent_carriers_router
from app.routers.agent import loads as agent_loads_router
from app.routers.agent import negotiations as agent_negotiations_router
from app.routers.agent import calls as agent_calls_router
from app.routers import webhooks as webhooks_router

app = FastAPI(title="HappyFDE API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(loads_router.router)
app.include_router(carriers_router.router)
app.include_router(calls_router.router)
app.include_router(shippers_router.router)
app.include_router(metrics_router.router)
app.include_router(quotes_router.router)
app.include_router(agent_carriers_router.router)
app.include_router(agent_loads_router.router)
app.include_router(agent_negotiations_router.router)
app.include_router(agent_calls_router.router)
app.include_router(webhooks_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/health/auth")
async def health_auth(token: str = Depends(require_dashboard_token)):
    return {"status": "ok", "authenticated": True}

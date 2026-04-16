from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import settings
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

# Setup logging for production observability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HappyFDE API",
    description="Integrated Freight Brokerage Operations Engine",
    version="1.1.0"
)

# CORS Configuration
# In production, we allow the frontend URL and HappyRobot origins
origins = [
    "http://localhost:3000",
    "https://happyrobot.ai",
    "https://app.happyrobot.ai",
]

# Add wildcards for cloud run domains or specific production URL if known
# For the challenge, we allow broad access if in production to ensure connectivity from platform
if settings.APP_ENV == "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
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

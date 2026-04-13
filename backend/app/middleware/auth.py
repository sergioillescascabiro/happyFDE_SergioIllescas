from fastapi import HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from typing import Optional
from app.config import settings

# Header schemes
agent_key_header = APIKeyHeader(name="X-Agent-Key", auto_error=False)
dashboard_token_header = APIKeyHeader(name="X-Dashboard-Token", auto_error=False)


def require_agent_key(x_agent_key: Optional[str] = Security(agent_key_header)):
    """Dependency: validates X-Agent-Key header for agent endpoints."""
    if not x_agent_key or x_agent_key != settings.AGENT_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing agent API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_agent_key


def require_dashboard_token(x_dashboard_token: Optional[str] = Security(dashboard_token_header)):
    """Dependency: validates X-Dashboard-Token header for dashboard endpoints."""
    if not x_dashboard_token or x_dashboard_token != settings.DASHBOARD_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing dashboard token",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_dashboard_token

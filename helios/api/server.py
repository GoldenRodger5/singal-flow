"""Helios control plane — FastAPI app.

Deliberately minimal in Phase 1:
  GET  /health            liveness
  GET  /health/detailed   component status
  GET  /v2/config         read-only config snapshot
  POST /v2/kill           activate kill switch (requires auth token)
  POST /v2/resume         deactivate kill switch (requires auth token)
  GET  /v2/state          current portfolio state snapshot

Strategy/execution endpoints arrive in later phases. The control plane is
deliberately decoupled from the trade loop — even if FastAPI is down, the
orchestrator can still trade. If the kill-switch endpoint is down, the
orchestrator's local kill-switch file watcher is the backup.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from helios import __version__

KILL_SWITCH_PATH = os.getenv("HELIOS_KILL_SWITCH_PATH", "/tmp/helios.kill")
CONTROL_PLANE_TOKEN = os.getenv("HELIOS_CONTROL_TOKEN", "")  # required for write endpoints


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_token(token: str | None) -> None:
    if not CONTROL_PLANE_TOKEN:
        raise HTTPException(503, "HELIOS_CONTROL_TOKEN not configured on server")
    if token != CONTROL_PLANE_TOKEN:
        raise HTTPException(401, "Invalid control-plane token")


app = FastAPI(title="Helios Control Plane", version=__version__)


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    kill_switch_active: bool


class KillResponse(BaseModel):
    status: str
    kill_switch_active: bool
    timestamp: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        timestamp=_now_iso(),
        kill_switch_active=os.path.exists(KILL_SWITCH_PATH),
    )


@app.get("/health/detailed")
def health_detailed() -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "timestamp": _now_iso(),
        "components": {
            "kill_switch": {
                "active": os.path.exists(KILL_SWITCH_PATH),
                "path": KILL_SWITCH_PATH,
            },
            "control_token_configured": bool(CONTROL_PLANE_TOKEN),
        },
    }


@app.post("/v2/kill", response_model=KillResponse)
def kill(x_helios_token: str | None = Header(default=None)) -> KillResponse:
    _check_token(x_helios_token)
    with open(KILL_SWITCH_PATH, "w") as f:
        f.write(_now_iso())
    return KillResponse(status="killed", kill_switch_active=True, timestamp=_now_iso())


@app.post("/v2/resume", response_model=KillResponse)
def resume(x_helios_token: str | None = Header(default=None)) -> KillResponse:
    _check_token(x_helios_token)
    try:
        os.remove(KILL_SWITCH_PATH)
    except FileNotFoundError:
        pass
    return KillResponse(status="resumed", kill_switch_active=False, timestamp=_now_iso())


@app.get("/v2/config")
def get_config() -> dict[str, object]:
    """Read-only snapshot of risk config. No secrets."""
    from helios.risk import RiskConfig
    cfg = RiskConfig()
    return {
        "max_drawdown_flat_pct": cfg.max_drawdown_flat_pct,
        "max_daily_loss_pct": cfg.max_daily_loss_pct,
        "max_weekly_loss_pct": cfg.max_weekly_loss_pct,
        "max_monthly_loss_pct": cfg.max_monthly_loss_pct,
        "max_position_pct_of_nav": cfg.max_position_pct_of_nav,
        "max_leverage_overall": cfg.max_leverage_overall,
        "nav_gate_options": str(cfg.nav_gate_options),
    }

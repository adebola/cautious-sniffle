"""Workspace Service - FastAPI application entry point."""

import logging

from fastapi import FastAPI

from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.routers import internal, sessions, templates, workspaces

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.DEBUG),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)

app = FastAPI(
    title="ChatCraft Workspace Service",
    description="Manages workspaces, members, documents, sessions, and messages.",
    version="1.0.0",
)

# Routers
app.include_router(health_router)
app.include_router(workspaces.router)
app.include_router(templates.router)
app.include_router(sessions.router)
app.include_router(internal.router)


@app.on_event("startup")
async def on_startup():
    logger.info(
        "Workspace Service starting on port %s (env=%s)",
        settings.service_port,
        settings.environment,
    )


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Workspace Service shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
    )

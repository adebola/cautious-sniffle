"""FastAPI application entry point for the Organization Service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chatcraft_common.health import router as health_router

from app.config import get_settings
from app.routers import internal, organizations, users


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    from chatcraft_common.database import create_db_engine, create_session_factory

    settings = get_settings()

    engine = create_db_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    session_factory = create_session_factory(engine)

    application.state.engine = engine
    application.state.session_factory = session_factory

    yield

    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="ChatCraft Organization Service",
        description="Manages organizations, users, and invitations for ChatCraft Professional",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    origins = [origin.strip() for origin in settings.cors_origins.split(",")]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    application.include_router(health_router)
    application.include_router(organizations.router)
    application.include_router(users.router)
    application.include_router(internal.router)

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=get_settings().service_port,
        reload=True,
    )

"""ARIA FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    yield


app = FastAPI(
    title="ARIA",
    description="AI-Driven Analytics Platform",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}

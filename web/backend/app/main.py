import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db

# Resolve frontend build directory (web/frontend/dist relative to this file)
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
STATIC_DIR = Path(os.environ.get("UPLINK_STATIC_DIR", str(_FRONTEND_DIST)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.game.game_loop import game_loop
    await game_loop.start()
    yield
    await game_loop.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Uplink Web", version="0.1.0", lifespan=lifespan)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from app.api.auth import router as auth_router
    from app.api.game import router as game_router
    from app.api.shop import router as shop_router
    from app.api.player import router as player_router

    app.include_router(auth_router)
    app.include_router(game_router)
    app.include_router(shop_router)
    app.include_router(player_router)

    @app.get("/")
    async def root():
        return {"status": "ok", "game": "Uplink"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        from app.ws.handler import websocket_handler
        await websocket_handler(websocket)

    # Serve built frontend as static files (must be mounted after API routes)
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import system, docker, torrents, media, recommendations, files, actions, streaming
from app.services import qbittorrent as qbit_svc
from app.services import system as system_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start bandwidth collector (polls qBittorrent every 5s)
    system_svc.start_bandwidth_collector(qbit_svc.request)
    # Prefetch storage cache
    threading.Thread(target=system_svc.get_storage, daemon=True).start()
    print(f"Jarvis Dashboard running on http://{settings.host}:{settings.port}")
    yield


app = FastAPI(
    title="Jarvis Dashboard",
    version="2.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.include_router(system.router)
app.include_router(docker.router)
app.include_router(torrents.router)
app.include_router(media.router)
app.include_router(recommendations.router)
app.include_router(files.router)
app.include_router(actions.router)
app.include_router(streaming.router)

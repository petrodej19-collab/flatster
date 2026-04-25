import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.favorites import router as favorites_router
from app.api.listings import router as listings_router
from app.api.projects import router as projects_router
from app.config import settings
from app.database import async_session
from app.scheduler import init_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = await init_scheduler(async_session)
    app.state.scheduler = scheduler
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Scheduler shut down")


app = FastAPI(title="NepremicnineTracker", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(listings_router, prefix="/api/projects", tags=["listings"])
app.include_router(favorites_router, prefix="/api/favorites", tags=["favorites"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}

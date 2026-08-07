from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db import bootstrap_admin
from backend.app.routers.admin import router as admin_router
from backend.app.routers.appointments import router as appointments_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.services import availability_router
from backend.app.routers.services import router as services_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bootstrap_admin()
    yield


app = FastAPI(title="Temujanji KJRI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}

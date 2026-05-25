import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings
from app.db.mongodb import close_db, init_db
from app.kpi.router import router as kpi_router
from app.tickets.router import public_router, router as bugs_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="BugTriage API",
    description="Agentic bug triage pipeline with Email OTP MFA",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(bugs_router)
app.include_router(public_router)
app.include_router(kpi_router)


@app.get("/")
async def root():
    return {
        "service": "BugTriage API",
        "health": f"{settings.public_api_base.rstrip('/')}/health",
        "frontend": settings.app_public_url,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/config")
async def public_config():
    return {
        "api_base": settings.public_api_base,
        "app_url": settings.app_public_url,
        "allow_public_register": settings.allow_public_register,
    }

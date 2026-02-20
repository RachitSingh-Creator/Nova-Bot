import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.user_routes import router as user_router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("nova-bot")


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(user_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {"service": settings.app_name, "status": "ok"}

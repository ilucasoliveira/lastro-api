import asyncio

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.routers import documents

DESCRIPTION = """Ask questions about Brazilian financial regulation (Pix, bank fees,
consumer rights) and get answers grounded in the official documents.

Every answer cites the document and page it came from. When the documents
do not cover a question, the API says so instead of guessing."""

app = FastAPI(
    title="Lastro API",
    description=DESCRIPTION,
    version="0.1.0",
    contact={
        "name": "Lucas de Oliveira Pimentel",
        "email": "lucasoliveirapimentel.dev@gmail.com",
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")


PROBE_TIMEOUT_SECONDS = 3


@app.get("/health", tags=["health"], status_code=200)
async def health_check() -> dict:
    """Liveness: is this process running and able to answer at all.

    Touches nothing external, so a database hiccup cannot make the platform
    restart a perfectly healthy container.
    """
    return {"status": "OK"}


@app.get("/health/ready", tags=["health"])
async def readiness_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Readiness: can this instance actually serve a request.

    Answers 503 when the database is down, which is the only signal an uptime
    monitor can act on.
    """
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=PROBE_TIMEOUT_SECONDS)
        database = "ok"
    except TimeoutError:
        database = "timeout"
    except Exception:
        database = "unreachable"

    ready = database == "ok"
    return JSONResponse(
        {"status": "ok" if ready else "degraded", "database": database},
        status_code=200 if ready else 503,
    )


app.include_router(documents.router)

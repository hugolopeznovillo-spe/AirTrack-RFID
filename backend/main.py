"""main.py — Punto de entrada de la API AirTrack RFID."""

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import create_tables, seed_data, get_db, settings, Scan, Flight, Location
from schemas import StatsOut
from auth import get_current_user, CurrentUser
from routers import scans, flights, locations, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_tables()
    db = next(get_db())
    seed_data(db)
    db.close()
    yield
    # Shutdown (noop)


app = FastAPI(
    title="AirTrack RFID API",
    description="API de control de equipaje de aeropuerto con lectores RFID HT518-R501",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(scans.router,     prefix=PREFIX)
app.include_router(flights.router,   prefix=PREFIX)
app.include_router(locations.router, prefix=PREFIX)
app.include_router(users.router,     prefix=PREFIX)


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.get(f"{PREFIX}/stats", response_model=StatsOut, tags=["stats"])
def get_stats(
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Resumen global para el dashboard."""
    total     = db.query(Scan).count()
    checkin   = db.query(Scan).filter(Scan.action == "CHECK-IN").count()
    embarked  = db.query(Scan).filter(Scan.action.in_(["EMBARCADO", "EN BODEGA"])).count()
    reclaimed = db.query(Scan).filter(Scan.action == "RECLAMADO").count()
    incidents = db.query(Scan).filter(Scan.action == "INCIDENCIA").count()
    lost      = db.query(Scan).filter(Scan.action == "PERDIDO").count()
    fl        = db.query(Flight).filter(Flight.active == True).count()
    lc        = db.query(Location).count()
    return StatsOut(
        total=total, checkin=checkin, embarked=embarked,
        reclaimed=reclaimed, incidents=incidents, lost=lost,
        flights=fl, locations=lc,
    )


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "airtrack-rfid-api"}

"""routers/flights.py — Gestión de vuelos."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Flight, Scan, get_db
from schemas import FlightCreate, FlightOut
from auth import get_current_user, CurrentUser

router = APIRouter(prefix="/flights", tags=["flights"])


def _enrich(flight: Flight, db: Session) -> FlightOut:
    bags = db.query(Scan).filter(Scan.flight_id == flight.id).count()
    out = FlightOut.model_validate(flight)
    out.bags = bags
    return out


@router.get("", response_model=List[FlightOut])
def get_flights(
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    flights = db.query(Flight).filter(Flight.active == True).order_by(Flight.departure).all()
    return [_enrich(f, db) for f in flights]


@router.post("", response_model=FlightOut, status_code=201)
def create_flight(
    body: FlightCreate,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")
    flight = Flight(**body.model_dump())
    db.add(flight)
    db.commit()
    db.refresh(flight)
    return _enrich(flight, db)


@router.put("/{flight_id}", response_model=FlightOut)
def update_flight(
    flight_id: int,
    body: FlightCreate,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin", "operator")
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Vuelo no encontrado")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(flight, k, v)
    db.commit()
    db.refresh(flight)
    return _enrich(flight, db)


@router.delete("/{flight_id}", status_code=204)
def delete_flight(
    flight_id: int,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")
    flight = db.get(Flight, flight_id)
    if flight:
        flight.active = False
        db.commit()

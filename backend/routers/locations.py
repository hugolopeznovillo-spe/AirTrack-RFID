"""routers/locations.py — Ubicaciones (puertas, cintas, terminales…)."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Location, get_db
from schemas import LocationCreate, LocationOut
from auth import get_current_user, CurrentUser

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=List[LocationOut])
def get_locations(
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return db.query(Location).order_by(Location.name).all()


@router.post("", response_model=LocationOut, status_code=201)
def create_location(
    body: LocationCreate,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")
    loc = Location(**body.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.put("/{location_id}", response_model=LocationOut)
def update_location(
    location_id: int,
    body: LocationCreate,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")
    loc = db.get(Location, location_id)
    if not loc:
        raise HTTPException(404, "Ubicación no encontrada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(loc, k, v)
    db.commit()
    db.refresh(loc)
    return loc


@router.delete("/{location_id}", status_code=204)
def delete_location(
    location_id: int,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")
    loc = db.get(Location, location_id)
    if loc:
        db.delete(loc)
        db.commit()

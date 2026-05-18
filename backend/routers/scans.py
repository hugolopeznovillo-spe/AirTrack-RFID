"""routers/scans.py — Endpoints de escaneo RFID de equipaje."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import Scan, Flight, Location, get_db
from schemas import ScanCreate, ScanOut, ScanBatchCreate
from auth import get_current_user, CurrentUser

router = APIRouter(prefix="/scans", tags=["scans"])


def _enrich(scan: Scan) -> ScanOut:
    """Añade campos calculados al objeto de salida."""
    out = ScanOut.model_validate(scan)
    out.flight_code   = scan.flight.code  if scan.flight   else None
    out.location_name = scan.location.name if scan.location else None
    return out


@router.post("", response_model=ScanOut, status_code=201)
def register_scan(
    body: ScanCreate,
    db:   Session      = Depends(get_db),
    user: CurrentUser  = Depends(get_current_user),
):
    """Registra una lectura RFID individual."""
    user.require_role("admin", "operator")

    scan = Scan(
        epc         = body.epc,
        type        = body.type,
        reader_id   = body.reader_id,
        flight_id   = body.flight_id,
        location_id = body.location_id,
        passenger   = body.passenger,
        belt        = body.belt,
        action      = body.action,
        rssi        = body.rssi,
        notes       = body.notes,
        created_by  = user.username,
    )
    db.add(scan)

    # Actualiza el conteo de la ubicación si aplica
    if body.location_id:
        loc = db.get(Location, body.location_id)
        if loc:
            loc.item_count = db.query(Scan).filter(
                Scan.location_id == body.location_id
            ).count() + 1

    db.commit()
    db.refresh(scan)
    return _enrich(scan)


@router.post("/batch", response_model=List[ScanOut], status_code=201)
def register_batch(
    body: ScanBatchCreate,
    db:   Session     = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Registra múltiples lecturas en una sola petición (modo offline sync)."""
    user.require_role("admin", "operator")

    results = []
    for item in body.scans:
        scan = Scan(
            epc         = item.epc,
            type        = item.type,
            reader_id   = item.reader_id,
            flight_id   = item.flight_id,
            location_id = item.location_id,
            passenger   = item.passenger,
            belt        = item.belt,
            action      = item.action,
            rssi        = item.rssi,
            notes       = item.notes,
            created_by  = user.username,
        )
        db.add(scan)
        results.append(scan)

    db.commit()
    for s in results:
        db.refresh(s)
    return [_enrich(s) for s in results]


@router.get("", response_model=List[ScanOut])
def get_scans(
    epc:        Optional[str] = Query(None),
    action:     Optional[str] = Query(None),
    flight_id:  Optional[int] = Query(None),
    type:       Optional[str] = Query(None),
    limit:      int           = Query(100, le=500),
    db:         Session       = Depends(get_db),
    user:       CurrentUser   = Depends(get_current_user),
):
    """Consulta el historial de lecturas con filtros opcionales."""
    user.require_role("admin", "operator")
    q = db.query(Scan)
    if epc:       q = q.filter(Scan.epc.ilike(f"%{epc}%"))
    if action:    q = q.filter(Scan.action == action)
    if flight_id: q = q.filter(Scan.flight_id == flight_id)
    if type:      q = q.filter(Scan.type == type)
    scans = q.order_by(Scan.created_at.desc()).limit(limit).all()
    return [_enrich(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(
    scan_id: int,
    db:      Session     = Depends(get_db),
    user:    CurrentUser = Depends(get_current_user),
):
    user.require_role("admin", "operator")
    scan = db.get(Scan, scan_id)
    if not scan:
        from fastapi import HTTPException
        raise HTTPException(404, "Scan no encontrado")
    return _enrich(scan)


@router.delete("/{scan_id}", status_code=204)
def delete_scan(
    scan_id: int,
    db:      Session     = Depends(get_db),
    user:    CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")
    scan = db.get(Scan, scan_id)
    if scan:
        db.delete(scan)
        db.commit()

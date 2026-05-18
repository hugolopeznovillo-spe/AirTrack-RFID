"""schemas.py — Pydantic models para validación de entrada/salida."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


# ── Scan ──────────────────────────────────────────────────────────────────────

class ScanCreate(BaseModel):
    epc:         str
    type:        str = "maleta"        # maleta | caja | fragil | exceso
    reader_id:   str = "HT518-R501"
    flight_id:   Optional[int]  = None
    location_id: Optional[int]  = None
    passenger:   Optional[str]  = None
    belt:        Optional[str]  = None
    action:      str = "CHECK-IN"      # CHECK-IN | EMBARCADO | EN BODEGA | RECLAMADO | INCIDENCIA | PERDIDO
    rssi:        Optional[float] = None
    notes:       Optional[str]  = None

    @field_validator("epc")
    @classmethod
    def epc_uppercase(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("passenger")
    @classmethod
    def passenger_uppercase(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else None


class ScanOut(BaseModel):
    id:           int
    epc:          str
    type:         str
    reader_id:    str
    flight_id:    Optional[int]
    location_id:  Optional[int]
    passenger:    Optional[str]
    belt:         Optional[str]
    action:       str
    rssi:         Optional[float]
    notes:        Optional[str]
    created_at:   datetime
    created_by:   Optional[str]
    flight_code:  Optional[str] = None
    location_name:Optional[str] = None

    class Config:
        from_attributes = True


class ScanBatchCreate(BaseModel):
    scans: List[ScanCreate]


# ── Flight ────────────────────────────────────────────────────────────────────

class FlightCreate(BaseModel):
    code:      str
    dest:      Optional[str] = None
    origin:    Optional[str] = None
    gate:      Optional[str] = None
    belt:      Optional[str] = None
    departure: Optional[str] = None
    arrival:   Optional[str] = None
    status:    str = "PREVISTO"


class FlightOut(BaseModel):
    id:        int
    code:      str
    dest:      Optional[str]
    origin:    Optional[str]
    gate:      Optional[str]
    belt:      Optional[str]
    departure: Optional[str]
    arrival:   Optional[str]
    status:    str
    bags:      int = 0

    class Config:
        from_attributes = True


# ── Location ──────────────────────────────────────────────────────────────────

class LocationCreate(BaseModel):
    name:        str
    code:        Optional[str] = None
    description: Optional[str] = None


class LocationOut(BaseModel):
    id:          int
    name:        str
    code:        Optional[str]
    description: Optional[str]
    item_count:  int

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username:  str
    password:  str
    email:     Optional[str] = None
    firstName: Optional[str] = None
    lastName:  Optional[str] = None
    role:      str


class UserOut(BaseModel):
    id:        str
    username:  str
    email:     Optional[str] = None
    firstName: Optional[str] = None
    lastName:  Optional[str] = None
    role:      str


class UserRoleUpdate(BaseModel):
    role:      str


# ── Stats ─────────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    total:     int
    checkin:   int
    embarked:  int
    reclaimed: int
    incidents: int
    lost:      int
    flights:   int
    locations: int

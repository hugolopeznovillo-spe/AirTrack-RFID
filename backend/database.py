from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, ForeignKey, Boolean, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://airtrack:airtrack_secret@localhost:5432/airtrack"
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "airport-rfid"
    keycloak_client_id: str = "rfid-backend"
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = "admin"
    cors_origins: str = "http://localhost,http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── ORM Models ────────────────────────────────────────────────────────────────

class Flight(Base):
    __tablename__ = "flights"

    id         = Column(Integer, primary_key=True, index=True)
    code       = Column(String(10), nullable=False, index=True)   # IB3456
    dest       = Column(String(100))                              # MADRID (MAD)
    origin     = Column(String(100))
    gate       = Column(String(10))                               # B22
    belt       = Column(String(10))                               # C3
    departure  = Column(String(10))                               # 08:35
    arrival    = Column(String(10))
    status     = Column(String(30), default="PREVISTO")           # CHECK-IN / EMBARQUE / CERRADO
    active     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scans = relationship("Scan", back_populates="flight")


class Location(Base):
    __tablename__ = "locations"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False)
    code        = Column(String(20))
    description = Column(Text)
    item_count  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    scans = relationship("Scan", back_populates="location")


class Scan(Base):
    __tablename__ = "scans"

    id          = Column(Integer, primary_key=True, index=True)
    epc         = Column(String(64), nullable=False, index=True)
    type        = Column(String(20), default="maleta")   # maleta / caja / fragil / exceso
    reader_id   = Column(String(50), default="HT518-R501")
    flight_id   = Column(Integer, ForeignKey("flights.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    passenger   = Column(String(100))                    # GARCIA/JUAN
    belt        = Column(String(10))
    action      = Column(String(30), default="CHECK-IN") # CHECK-IN / EMBARCADO / EN BODEGA / RECLAMADO / INCIDENCIA / PERDIDO
    rssi        = Column(Float, nullable=True)
    notes       = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)
    created_by  = Column(String(100))                    # Keycloak username

    flight   = relationship("Flight",   back_populates="scans")
    location = relationship("Location", back_populates="scans")


# ── Create tables ─────────────────────────────────────────────────────────────

def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Seed data ─────────────────────────────────────────────────────────────────

def seed_data(db):
    if db.query(Flight).count() > 0:
        return  # Already seeded

    flights = [
        Flight(code="IB3456", dest="MADRID (MAD)",    origin="BCN", gate="B22", belt="C3", departure="08:35", status="EMBARQUE"),
        Flight(code="VY1234", dest="BARCELONA (BCN)", origin="PMI", gate="A14", belt="C1", departure="09:10", status="CHECK-IN"),
        Flight(code="FR9012", dest="PARIS (CDG)",     origin="BCN", gate="C05", belt="C4", departure="10:00", status="CERRADO"),
        Flight(code="U24567", dest="ROMA (FCO)",      origin="BCN", gate="B17", belt="C2", departure="11:25", status="CHECK-IN"),
        Flight(code="LH8901", dest="BERLIN (BER)",    origin="BCN", gate="A03", belt="C5", departure="13:45", status="PREVISTO"),
    ]
    db.add_all(flights)

    locations = [
        Location(name="Terminal 1 — Check-in", code="T1-CI"),
        Location(name="Terminal 2 — Check-in", code="T2-CI"),
        Location(name="Cinta C1",              code="BELT-C1"),
        Location(name="Cinta C2",              code="BELT-C2"),
        Location(name="Cinta C3",              code="BELT-C3"),
        Location(name="Bodega — Vuelo IB3456", code="HOLD-IB3456"),
        Location(name="Zona de incidencias",   code="INCIDENT-ZONE"),
    ]
    db.add_all(locations)
    db.commit()

    # Refresh to get IDs
    for f in flights:
        db.refresh(f)

    scans_seed = [
        Scan(epc="E2003412013F0100B55E57C3", type="maleta", flight_id=flights[0].id, passenger="GARCIA/JUAN",    action="EMBARCADO", rssi=-52.0, reader_id="HT518-R501"),
        Scan(epc="E2003412013F0101C66F68D4", type="caja",   flight_id=flights[0].id, passenger="MARTINEZ/ANA",   action="EN BODEGA", rssi=-61.0, reader_id="HT518-R501"),
        Scan(epc="E2003412013F0102D77G79E5", type="maleta", flight_id=flights[1].id, passenger="LOPEZ/PEDRO",    action="CHECK-IN",  rssi=-48.0, reader_id="HT518-R501"),
        Scan(epc="E2003412013F0103E88H80F6", type="fragil", flight_id=flights[1].id, passenger="FERNANDEZ/MARTA",action="CHECK-IN",  rssi=-55.0, reader_id="HT518-R501"),
        Scan(epc="E2003412013F0104F99I91G7", type="exceso", flight_id=flights[2].id, passenger="SANCHEZ/LUIS",   action="RECLAMADO", rssi=-59.0, reader_id="HT518-R501"),
        Scan(epc="E2003412013F0105G00J02H8", type="caja",   flight_id=flights[2].id, passenger="RUIZ/ELENA",     action="INCIDENCIA",rssi=-70.0, reader_id="HT518-R501"),
        Scan(epc="E2003412013F0106H11K13I9", type="maleta", flight_id=flights[0].id, passenger="MORENO/CARLOS",  action="PERDIDO",   rssi=None,  reader_id="HT518-R501"),
    ]
    db.add_all(scans_seed)
    db.commit()

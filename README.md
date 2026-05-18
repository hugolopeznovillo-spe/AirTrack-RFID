<<<<<<< HEAD
# AirTrack RFID — Sistema de Control de Equipaje

Sistema completo de trazabilidad RFID de maletas y cajas en aeropuerto.  
Stack: **FastAPI + PostgreSQL + Keycloak + Nginx + Bulma**

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│  Docker Compose                                      │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Keycloak │  │ FastAPI  │  │  Nginx + Frontend │   │
│  │  :8080   │  │  :8000   │  │      :80          │   │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘   │
│       │              │                 │              │
│  ┌────▼─────────────▼─────────────────▼──────────┐  │
│  │                 PostgreSQL :5432               │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

Pistola HT518-R501 (Android App) ──► POST /api/v1/scans
```

---

## Inicio rápido

### Requisitos
- Docker + Docker Compose

### 1. Clonar y levantar
```bash
git clone <repo>
cd airtrack-rfid
docker compose up --build
```

### 2. Acceder
| Servicio   | URL                          |
|------------|------------------------------|
| Frontend   | http://localhost             |
| API Docs   | http://localhost:8000/api/docs |
| Keycloak   | http://localhost:8080        |

### 3. Credenciales predefinidas (Keycloak realm `airport-rfid`)

| Usuario    | Contraseña    | Rol      |
|------------|---------------|----------|
| admin      | admin123      | admin    |
| Hlopez     | hlopez123     | operator |
| Mvillegas  | mvillegas123  | operator |

> Admin de Keycloak (consola de administración): `admin / admin`

---

## API Endpoints

```
POST   /api/v1/scans              Registrar lectura RFID
POST   /api/v1/scans/batch        Batch offline sync
GET    /api/v1/scans              Consultar historial
GET    /api/v1/scans/{id}         Detalle de lectura
DELETE /api/v1/scans/{id}         Eliminar (admin)

GET    /api/v1/flights            Listar vuelos
POST   /api/v1/flights            Crear vuelo (admin)
PUT    /api/v1/flights/{id}       Actualizar vuelo
DELETE /api/v1/flights/{id}       Desactivar vuelo (admin)

GET    /api/v1/locations          Listar ubicaciones
POST   /api/v1/locations          Crear ubicación (admin)
PUT    /api/v1/locations/{id}     Actualizar
DELETE /api/v1/locations/{id}     Eliminar (admin)

GET    /api/v1/stats              Resumen del dashboard
GET    /health                    Health check
```

---

## Tipos de acción (action)

| Valor       | Descripción                      |
|-------------|----------------------------------|
| CHECK-IN    | Maleta registrada en mostrador   |
| EMBARCADO   | Maleta cargada en avión          |
| EN BODEGA   | Confirmada en bodega             |
| RECLAMADO   | Recogida por el pasajero         |
| INCIDENCIA  | Problema detectado               |
| PERDIDO     | No localizada                    |

---

## Tipos de pieza (type)

| Valor  | Icono | Descripción           |
|--------|-------|-----------------------|
| maleta | 🧳    | Maleta estándar       |
| caja   | 📦    | Caja / bulto          |
| fragil | ⚠️   | Equipaje frágil       |
| exceso | 🏋️  | Exceso de equipaje    |

---

## Roles Keycloak

| Rol      | Permisos                                  |
|----------|-------------------------------------------|
| admin    | CRUD completo + borrar scans              |
| operator | Leer todo + crear/editar scans y vuelos   |
| viewer   | Solo lectura (GET)                        |

---

## Configuración del Android App (HT518-R501)

En `gradle.properties` (o `local.properties`) añade:
```properties
API_BASE_URL=http://<IP_SERVIDOR>:8000/api/v1/
```

La app Android usa Keycloak para obtener un Bearer token y lo incluye
en cada petición `Authorization: Bearer <token>`.

---

## Variables de entorno (backend)

| Variable              | Valor por defecto                          |
|-----------------------|--------------------------------------------|
| DATABASE_URL          | postgresql://airtrack:...@postgres/airtrack|
| KEYCLOAK_URL          | http://keycloak:8080                       |
| KEYCLOAK_REALM        | airport-rfid                               |
| KEYCLOAK_CLIENT_ID    | rfid-backend                               |
| CORS_ORIGINS          | http://localhost,...                       |

---

## Desarrollo local sin Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
DATABASE_URL=sqlite:///./dev.db \
KEYCLOAK_URL=http://localhost:8080 \
uvicorn main:app --reload --port 8000

# Frontend (cualquier servidor estático)
cd frontend
python -m http.server 3000
```

Para desarrollo sin Keycloak, usa el botón **"Modo demo"** en la pantalla de login.
=======
# AirTrack-RFID
>>>>>>> 915e2a21f9ecd60e9d204bede6d4cfa69d1e4e8a

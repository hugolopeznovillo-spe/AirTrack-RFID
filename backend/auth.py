"""
auth.py — Validación de tokens Keycloak

El token JWT viene en el header Authorization: Bearer <token>
Se valida la firma usando las claves públicas del endpoint JWKS de Keycloak.
"""

import httpx
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from database import settings

security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Descarga las claves públicas JWKS de Keycloak (se cachean)."""
    url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    try:
        resp = httpx.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo obtener las claves de Keycloak: {e}"
        )


def _decode_token(token: str) -> dict:
    """Decodifica y verifica el token JWT con las claves JWKS."""
    jwks = _get_jwks()
    try:
        # Decodificamos sin verificar primero para obtener el kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Buscamos la clave con ese kid
        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "n":   key["n"],
                    "e":   key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clave pública no encontrada en JWKS"
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            options={"verify_aud": False},   # audience flexible para frontend/backend
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class CurrentUser:
    """Usuario autenticado extraído del token JWT."""

    def __init__(self, payload: dict):
        self.username    = payload.get("preferred_username") or payload.get("sub")
        self.email       = payload.get("email", "")
        self.name        = payload.get("name", self.username)
        self.roles: list = payload.get("realm_access", {}).get("roles", [])
        self.sub         = payload.get("sub")

    def has_role(self, *roles) -> bool:
        return any(r in self.roles for r in roles)

    def require_role(self, *roles):
        if not self.has_role(*roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de estos roles: {list(roles)}"
            )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """
    Dependencia FastAPI. Extrae y valida el token Bearer.
    Si no hay token lanza 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    return CurrentUser(payload)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """Como get_current_user pero no lanza error si no hay token (útil en dev)."""
    if not credentials:
        return None
    try:
        payload = _decode_token(credentials.credentials)
        return CurrentUser(payload)
    except HTTPException:
        return None

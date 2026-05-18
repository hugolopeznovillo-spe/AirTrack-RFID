"""Integración mínima con la API de administración de Keycloak."""

import json
import httpx
from fastapi import HTTPException, status

from database import settings


class KeycloakAdmin:
    def __init__(self):
        self.url = settings.keycloak_url.rstrip("/")
        self.realm = settings.keycloak_realm
        self.admin_user = settings.keycloak_admin_user
        self.admin_password = settings.keycloak_admin_password

    def _token(self) -> str:
        url = f"{self.url}/realms/master/protocol/openid-connect/token"
        data = {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": self.admin_user,
            "password": self.admin_password,
        }
        try:
            resp = httpx.post(url, data=data, timeout=10)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo autenticar con Keycloak Admin: {exc.response.text}",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error de red al autenticar Keycloak Admin: {exc}",
            )

        payload = resp.json()
        return payload.get("access_token")

    def _headers(self) -> dict:
        token = self._token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get_role(self, role_name: str) -> dict:
        """Obtiene la definición de un rol desde Keycloak."""
        url = f"{self.url}/admin/realms/{self.realm}/roles/{role_name}"
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El rol '{role_name}' no existe en Keycloak",
                )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No se pudo obtener el rol '{role_name}': {resp.text}",
                )
            return resp.json()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al obtener el rol: {exc}",
            )

    def _get_roles(self, role: str) -> list[dict]:
        """Obtiene las definiciones de roles para asignar según el rol principal."""
        role_hierarchy = {
            "viewer": ["viewer"],
            "operator": ["operator", "viewer"],
            "admin": ["admin", "operator", "viewer"],
        }
        roles_to_assign = role_hierarchy.get(role, [role])  # fallback al rol único si no está definido
        role_defs = []
        for r in roles_to_assign:
            role_defs.append(self._get_role(r))
        return role_defs

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> str:
        url = f"{self.url}/admin/realms/{self.realm}/users"
        payload = {
            "username": username,
            "enabled": True,
            "emailVerified": True,
            "credentials": [
                {"type": "password", "value": password, "temporary": False}
            ],
        }
        if email:
            payload["email"] = email
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name

        resp = httpx.post(url, json=payload, headers=self._headers(), timeout=10)
        if resp.status_code == 409:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya existe en Keycloak",
            )
        if resp.status_code not in (201, 204):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No se pudo crear el usuario en Keycloak: {resp.text}",
            )

        # Keycloak responde con Location: .../users/{id}
        location = resp.headers.get("Location")
        if not location:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No se recibió el identificador del usuario creado",
            )
        user_id = location.rstrip("/").split("/")[-1]

        # Asignar roles al usuario
        role_defs = self._get_roles(role)
        assign_url = f"{self.url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm"
        assign_resp = httpx.post(assign_url, json=role_defs, headers=self._headers(), timeout=10)
        if assign_resp.status_code not in (204,):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No se pudo asignar los roles al usuario: {assign_resp.text}",
            )

        return user_id

    def get_user_by_username(self, username: str) -> dict | None:
        """Obtiene los detalles de un usuario por nombre de usuario."""
        url = f"{self.url}/admin/realms/{self.realm}/users"
        params = {"username": username}
        try:
            resp = httpx.get(url, params=params, headers=self._headers(), timeout=10)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No se pudo obtener el usuario: {resp.text}",
                )
            users = resp.json()
            if not users:
                return None
            return users[0]  # Retorna el primer usuario encontrado
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al obtener el usuario: {exc}",
            )

    def change_user_role(self, username: str, new_role: str) -> None:
        """Cambia el rol de un usuario existente."""
        if new_role not in {"admin", "operator", "viewer"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol inválido. Elija admin, operator o viewer.",
            )

        # Obtener usuario
        user = self.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El usuario '{username}' no existe",
            )

        user_id = user.get("id")

        # Obtener roles actuales del usuario
        url_current_roles = f"{self.url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm"
        try:
            resp = httpx.get(url_current_roles, headers=self._headers(), timeout=10)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No se pudo obtener los roles actuales: {resp.text}",
                )
            current_roles = resp.json()

            # Eliminar todos los roles actuales
            if current_roles:
                remove_resp = httpx.request(
                    "DELETE",
                    url_current_roles,
                    content=json.dumps(current_roles).encode(),
                    headers=self._headers(),
                    timeout=10,
                )
                if remove_resp.status_code not in (204,):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"No se pudieron eliminar los roles actuales: {remove_resp.text}",
                    )

            # Asignar nuevos roles
            new_role_defs = self._get_roles(new_role)
            assign_resp = httpx.post(
                url_current_roles,
                json=new_role_defs,
                headers=self._headers(),
                timeout=10,
            )
            if assign_resp.status_code not in (204,):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No se pudo asignar el nuevo rol: {assign_resp.text}",
                )

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al cambiar el rol del usuario: {exc}",
            )

    def get_all_users(self) -> list[dict]:
        """Obtiene la lista de todos los usuarios con sus roles."""
        url = f"{self.url}/admin/realms/{self.realm}/users"
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=10)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"No se pudo obtener la lista de usuarios: {resp.text}",
                )
            users = resp.json()
            
            # Para cada usuario, obtener su rol principal
            result = []
            for user in users:
                user_id = user.get("id")
                roles_url = f"{self.url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm"
                try:
                    roles_resp = httpx.get(roles_url, headers=self._headers(), timeout=10)
                    if roles_resp.status_code == 200:
                        roles = [r.get("name") for r in roles_resp.json()]
                        # Determinar el rol principal (jerarquía: admin > operator > viewer)
                        primary_role = "viewer"  # default
                        if "admin" in roles:
                            primary_role = "admin"
                        elif "operator" in roles:
                            primary_role = "operator"
                        
                        result.append({
                            "id": user_id,
                            "username": user.get("username"),
                            "email": user.get("email"),
                            "firstName": user.get("firstName"),
                            "lastName": user.get("lastName"),
                            "role": primary_role,
                            "enabled": user.get("enabled", False),
                        })
                except Exception:
                    # Si hay error obteniendo roles, asignar viewer por defecto
                    result.append({
                        "id": user_id,
                        "username": user.get("username"),
                        "email": user.get("email"),
                        "firstName": user.get("firstName"),
                        "lastName": user.get("lastName"),
                        "role": "viewer",
                        "enabled": user.get("enabled", False),
                    })
            
            return result
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al obtener la lista de usuarios: {exc}",
            )

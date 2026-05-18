"""routers/users.py — Gestión de usuarios de Keycloak desde el backend."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user, CurrentUser
from keycloak import KeycloakAdmin
from schemas import UserCreate, UserOut, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserOut])
def list_users(
    user: CurrentUser = Depends(get_current_user),
):
    """Lista todos los usuarios. Solo disponible para administradores."""
    user.require_role("admin")

    kc = KeycloakAdmin()
    users = kc.get_all_users()

    return [
        UserOut(
            id=u["id"],
            username=u["username"],
            email=u["email"],
            firstName=u["firstName"],
            lastName=u["lastName"],
            role=u["role"],
        )
        for u in users
    ]


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    user: CurrentUser = Depends(get_current_user),
):
    user.require_role("admin")

    if body.role not in {"admin", "operator", "viewer"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol inválido. Elija admin, operator o viewer.",
        )

    kc = KeycloakAdmin()
    user_id = kc.create_user(
        username=body.username,
        password=body.password,
        role=body.role,
        email=body.email,
        first_name=body.firstName,
        last_name=body.lastName,
    )

    return UserOut(
        id=user_id,
        username=body.username,
        email=body.email,
        firstName=body.firstName,
        lastName=body.lastName,
        role=body.role,
    )


@router.put("/{username}/role", response_model=dict, status_code=200)
def change_user_role(
    username: str,
    body: UserRoleUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Cambia el rol de un usuario existente. Solo disponible para administradores."""
    user.require_role("admin")

    kc = KeycloakAdmin()
    kc.change_user_role(username, body.role)

    return {
        "message": f"El rol del usuario '{username}' ha sido actualizado a '{body.role}'",
        "username": username,
        "role": body.role,
    }

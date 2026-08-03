# services/auth_service.py
import hashlib
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from database.models import Usuario


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def authenticate_user(db: Session, username: str, password: str):
    if not username or not password:
        return None

    value = username.strip().lower()
    user = db.query(Usuario).filter(
        or_(
            func.lower(Usuario.correo) == value,
            func.lower(Usuario.nombre) == value,
        )
    ).first()

    if user and verify_password(password, user.contraseña):
        return user
    return None


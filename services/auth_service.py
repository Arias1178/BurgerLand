# services/auth_service.py
import hashlib
from sqlalchemy.orm import Session
from database.models import Usuario

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def authenticate_user(db: Session,username: str, password: str):
    user = db.query(Usuario).filter(Usuario.correo == username).first()
    if user and verify_password(password, user.contraseña):
        return user
    return None


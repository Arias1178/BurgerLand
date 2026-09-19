# services/auth_service.py
import hashlib
<<<<<<< HEAD
from sqlalchemy.orm import Session
from database.models import User
=======
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from database.models import Usuario

>>>>>>> Burguerland_V_1.0

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

<<<<<<< HEAD
def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def authenticate_user(db: Session,username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
=======

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
>>>>>>> Burguerland_V_1.0
        return user
    return None


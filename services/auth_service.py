# services/auth_service.py
import hashlib
from sqlalchemy.orm import Session
from database.models import Usuario

# Genera un hash seguro de la contraseña para almacenarla en la base de datos.
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Compara la contraseña ingresada contra el hash almacenado para validar el acceso.
def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

# Busca al usuario por correo y valida sus credenciales para permitir el login.
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(Usuario).filter(Usuario.correo == username).first()
    if user and verify_password(password, user.contraseña):
        return user
    return None


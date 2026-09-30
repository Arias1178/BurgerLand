# services/auth_service.py
import base64
import hashlib
import hmac
import os

from sqlalchemy.orm import Session

from database.models import Usuario


_ITERATIONS = 200_000
_ALGORITHM = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{_ALGORITHM}${_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False

    if hashed.startswith(f"{_ALGORITHM}$"):
        try:
            _, iterations, salt_b64, digest_b64 = hashed.split("$", 3)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(digest_b64)
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                int(iterations),
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed


def authenticate_user(db: Session, correo: str, password: str):
    if not correo or not password:
        return None

    value = correo.strip().lower()
    user = db.query(Usuario).filter(Usuario.correo == value).first()

    return user if user and verify_password(password, user.contraseña) else None

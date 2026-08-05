from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Define la ruta y la URL de la base de datos SQLite para el proyecto.
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "burguerland.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Crea el motor de SQLAlchemy y la sesión que se usará en toda la aplicación.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
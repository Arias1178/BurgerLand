from sqlalchemy.orm import Session

from database.models import mesas


NUMERO_MESAS = 17
ESTADO_MESA_LIBRE = "LIBRE"
ESTADO_MESA_OCUPADA = "OCUPADA"
ESTADO_MESA_POR_PAGAR = "POR_PAGAR"


def sembrar_mesas(db: Session) -> int:
    """Crea las mesas configuradas sin modificar su estado actual."""
    existentes = {
        numero for (numero,) in db.query(mesas.numero).all()
    }
    creadas = 0
    for numero in range(1, NUMERO_MESAS + 1):
        if numero not in existentes:
            db.add(mesas(numero=numero, estado=ESTADO_MESA_LIBRE))
            creadas += 1
    return creadas


def obtener_mesas(db: Session) -> list[mesas]:
    return db.query(mesas).order_by(mesas.numero.asc()).all()


def validar_mesa_disponible(db: Session, mesa_id: int | None) -> mesas | None:
    if mesa_id is None:
        return None

    mesa = db.get(mesas, mesa_id)
    if mesa is None:
        raise ValueError("La mesa seleccionada no existe.")
    if mesa.estado != ESTADO_MESA_LIBRE:
        raise ValueError(f"La mesa {mesa.numero} no está disponible.")
    return mesa

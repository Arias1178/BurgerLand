from sqlalchemy.orm import Session

from database.models import Usuario, rol


ROLES_ADMINISTRABLES = {"ADMIN", "VENDEDOR"}


def _obtener_usuario_admin(db: Session, actor_id: int) -> Usuario:
    actor = db.get(Usuario, actor_id)
    if actor is None:
        raise ValueError("No se encontró el usuario administrador.")
    perfil = db.get(rol, actor.id_rol)
    if perfil is None or perfil.nombre != "ADMIN":
        raise ValueError("Solo un administrador puede gestionar los roles.")
    return actor


def listar_usuarios_para_administracion(
    db: Session,
    actor_id: int,
) -> list[dict]:
    _obtener_usuario_admin(db, actor_id)
    registros = (
        db.query(Usuario, rol.nombre)
        .join(rol, rol.id_rol == Usuario.id_rol)
        .order_by(Usuario.nombre.asc(), Usuario.id_usuario.asc())
        .all()
    )
    return [
        {
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": nombre_rol,
        }
        for usuario, nombre_rol in registros
    ]


def cambiar_rol_usuario(
    db: Session,
    actor_id: int,
    usuario_id: int,
    nuevo_rol: str,
) -> Usuario:
    _obtener_usuario_admin(db, actor_id)
    if actor_id == usuario_id:
        raise ValueError("No puedes cambiar tu propio rol desde esta sesión.")

    nuevo_rol = (nuevo_rol or "").strip().upper()
    if nuevo_rol not in ROLES_ADMINISTRABLES:
        raise ValueError("El rol debe ser ADMIN o VENDEDOR.")

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("No se encontró el usuario que deseas actualizar.")
    rol_actual = db.get(rol, usuario.id_rol)
    if rol_actual is None:
        raise ValueError("El usuario no tiene un rol válido asignado.")
    if rol_actual.nombre == nuevo_rol:
        return usuario

    if rol_actual.nombre == "ADMIN" and nuevo_rol == "VENDEDOR":
        administradores = (
            db.query(Usuario)
            .join(rol, rol.id_rol == Usuario.id_rol)
            .filter(rol.nombre == "ADMIN")
            .count()
        )
        if administradores <= 1:
            raise ValueError(
                "No puedes quitar el último rol ADMIN del sistema."
            )

    rol_destino = db.query(rol).filter(rol.nombre == nuevo_rol).first()
    if rol_destino is None:
        raise ValueError(f"No existe el rol {nuevo_rol} en el sistema.")

    try:
        usuario.id_rol = rol_destino.id_rol
        db.commit()
        db.refresh(usuario)
        return usuario
    except Exception:
        db.rollback()
        raise

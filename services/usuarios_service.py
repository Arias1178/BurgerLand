from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import (
    Orden,
    Usuario,
    caja,
    consolidaciones_contables,
    cuentas_abiertas,
    estado_usuarios,
    gastos,
    historial_domicilios,
    informes,
    retiros_caja,
    rol,
    ventas,
)
from services.auth_service import hash_password


ROLES_ADMINISTRABLES = {"ADMIN", "VENDEDOR"}


def _obtener_usuario_admin(db: Session, actor_id: int) -> Usuario:
    actor = db.get(Usuario, actor_id)
    if actor is None:
        raise ValueError("No se encontró el usuario administrador.")
    perfil = db.get(rol, actor.id_rol)
    if perfil is None or perfil.nombre != "ADMIN":
        raise ValueError("Solo un administrador puede gestionar los roles.")
    if not _esta_activo(db, actor):
        raise ValueError("El usuario administrador está inhabilitado.")
    return actor


def _esta_activo(db: Session, usuario: Usuario) -> bool:
    if usuario.id_estado is None:
        return True
    estado = db.get(estado_usuarios, usuario.id_estado)
    return bool(estado and estado.nombre.upper() == "ACTIVO")


def _nombre_estado(db: Session, usuario: Usuario) -> str:
    if usuario.id_estado is None:
        return "ACTIVO"
    estado = db.get(estado_usuarios, usuario.id_estado)
    return estado.nombre.upper() if estado else "INACTIVO"


def _obtener_estado(db: Session, nombre: str) -> estado_usuarios:
    estado = (
        db.query(estado_usuarios)
        .filter(estado_usuarios.nombre == nombre)
        .first()
    )
    if estado is None:
        raise ValueError(f"No existe el estado de usuario {nombre}.")
    return estado


def _contar_admins_activos(db: Session, excluir_id: int | None = None) -> int:
    administradores = (
        db.query(Usuario)
        .join(rol, rol.id_rol == Usuario.id_rol)
        .filter(rol.nombre == "ADMIN")
        .all()
    )
    return sum(
        usuario.id_usuario != excluir_id and _esta_activo(db, usuario)
        for usuario in administradores
    )


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
            "estado": _nombre_estado(db, usuario),
        }
        for usuario, nombre_rol in registros
    ]


def crear_usuario(
    db: Session,
    actor_id: int,
    nombre: str,
    correo: str,
    password: str,
    nuevo_rol: str,
) -> Usuario:
    _obtener_usuario_admin(db, actor_id)
    nombre = (nombre or "").strip()
    correo = (correo or "").strip().lower()
    nuevo_rol = (nuevo_rol or "").strip().upper()
    if not nombre:
        raise ValueError("El nombre es obligatorio.")
    if (
        correo.count("@") != 1
        or correo.startswith("@")
        or correo.endswith("@")
        or any(caracter.isspace() for caracter in correo)
    ):
        raise ValueError("Ingresa un correo electrónico válido.")
    if not password:
        raise ValueError("La contraseña es obligatoria.")
    if nuevo_rol not in ROLES_ADMINISTRABLES:
        raise ValueError("El rol debe ser ADMIN o VENDEDOR.")

    rol_destino = db.query(rol).filter(rol.nombre == nuevo_rol).first()
    if rol_destino is None:
        raise ValueError(f"No existe el rol {nuevo_rol} en el sistema.")
    if db.query(Usuario).filter(func.lower(Usuario.correo) == correo).first():
        raise ValueError("Ya existe un usuario con ese correo.")

    usuario = Usuario(
        nombre=nombre,
        correo=correo,
        contraseña=hash_password(password),
        id_rol=rol_destino.id_rol,
        id_estado=_obtener_estado(db, "ACTIVO").id_estado,
    )
    try:
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    except IntegrityError as error:
        db.rollback()
        raise ValueError("Ya existe un usuario con ese correo.") from error
    except Exception:
        db.rollback()
        raise


def editar_usuario(
    db: Session,
    actor_id: int,
    usuario_id: int,
    nombre: str,
    correo: str,
    nueva_contrasena: str | None = None,
) -> Usuario:
    _obtener_usuario_admin(db, actor_id)
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("No se encontró el usuario que deseas editar.")

    nombre = (nombre or "").strip()
    correo = (correo or "").strip().lower()
    if not nombre:
        raise ValueError("El nombre es obligatorio.")
    if (
        correo.count("@") != 1
        or correo.startswith("@")
        or correo.endswith("@")
        or any(caracter.isspace() for caracter in correo)
    ):
        raise ValueError("Ingresa un correo electrónico válido.")
    duplicado = (
        db.query(Usuario)
        .filter(
            func.lower(Usuario.correo) == correo,
            Usuario.id_usuario != usuario_id,
        )
        .first()
    )
    if duplicado:
        raise ValueError("Ya existe un usuario con ese correo.")

    usuario.nombre = nombre
    usuario.correo = correo
    if nueva_contrasena:
        usuario.contraseña = hash_password(nueva_contrasena)
    try:
        db.commit()
        db.refresh(usuario)
        return usuario
    except IntegrityError as error:
        db.rollback()
        raise ValueError("Ya existe un usuario con ese correo.") from error
    except Exception:
        db.rollback()
        raise


def cambiar_estado_usuario(
    db: Session,
    actor_id: int,
    usuario_id: int,
    activo: bool,
) -> Usuario:
    _obtener_usuario_admin(db, actor_id)
    if actor_id == usuario_id and not activo:
        raise ValueError("No puedes inhabilitar tu propia cuenta.")
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("No se encontró el usuario que deseas actualizar.")

    estado_destino = _obtener_estado(db, "ACTIVO" if activo else "INACTIVO")
    if _esta_activo(db, usuario) == activo:
        return usuario

    perfil = db.get(rol, usuario.id_rol)
    if not activo and perfil and perfil.nombre == "ADMIN":
        if _contar_admins_activos(db, excluir_id=usuario_id) == 0:
            raise ValueError("No puedes inhabilitar al último administrador activo.")

    usuario.id_estado = estado_destino.id_estado
    try:
        db.commit()
        db.refresh(usuario)
        return usuario
    except Exception:
        db.rollback()
        raise


def _tiene_registros_asociados(db: Session, usuario_id: int) -> bool:
    modelos = (
        cuentas_abiertas,
        caja,
        ventas,
        historial_domicilios,
        retiros_caja,
        informes,
        gastos,
        consolidaciones_contables,
        Orden,
    )
    return any(
        db.query(modelo)
        .filter(modelo.id_usuario == usuario_id)
        .first()
        is not None
        for modelo in modelos
    )


def eliminar_usuario(db: Session, actor_id: int, usuario_id: int) -> None:
    _obtener_usuario_admin(db, actor_id)
    if actor_id == usuario_id:
        raise ValueError("No puedes eliminar tu propia cuenta.")
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("No se encontró el usuario que deseas eliminar.")

    perfil = db.get(rol, usuario.id_rol)
    if perfil and perfil.nombre == "ADMIN":
        if _contar_admins_activos(db, excluir_id=usuario_id) == 0:
            raise ValueError("No puedes eliminar al último administrador activo.")
    if _tiene_registros_asociados(db, usuario_id):
        raise ValueError(
            "El usuario tiene actividad registrada y no puede eliminarse. "
            "Puedes inhabilitarlo en su lugar."
        )

    try:
        db.delete(usuario)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError(
            "El usuario tiene registros asociados y no puede eliminarse. "
            "Puedes inhabilitarlo en su lugar."
        ) from error
    except Exception:
        db.rollback()
        raise


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
        if _contar_admins_activos(db, excluir_id=usuario_id) == 0:
            raise ValueError(
                "No puedes quitar el último rol ADMIN activo del sistema."
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

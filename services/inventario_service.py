import re
import unicodedata

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    categorias,
    categorias_inventario,
    detalles_compras,
    inventario,
    productos,
    catalogo_proveedores,
    proveedores,
)


def sincronizar_categorias_inventario(db_session: Session):
    nombres = {
        nombre.strip()
        for nombre, in db_session.query(inventario.categoria).distinct().all()
        if nombre and nombre.strip()
    }
    existentes = {
        nombre
        for nombre, in db_session.query(categorias_inventario.nombre).all()
    }
    for nombre in nombres - existentes:
        db_session.add(categorias_inventario(nombre=nombre))


def sincronizar_inventario_catalogo_bebidas(db_session: Session) -> int:
    """Create one zero-stock inventory SKU for each catalog item supplied as a beverage."""
    catalogo = (
        db_session.query(catalogo_proveedores, proveedores)
        .join(proveedores, proveedores.id_proveedor == catalogo_proveedores.id_proveedor)
        .filter(func.lower(func.trim(proveedores.que_provee)) == "bebidas")
        .order_by(proveedores.id_proveedor, catalogo_proveedores.id_producto_proveedor)
        .all()
    )
    existentes = {
        (id_proveedor, _normalizar_nombre(nombre))
        for id_proveedor, nombre in db_session.query(
            inventario.id_proveedor,
            inventario.nombre,
        )
        .filter(inventario.id_proveedor.isnot(None))
        .all()
    }
    creados = 0
    for articulo, proveedor in catalogo:
        clave = (proveedor.id_proveedor, _normalizar_nombre(articulo.nombre))
        if clave in existentes:
            continue
        db_session.add(
            inventario(
                nombre=articulo.nombre.strip(),
                categoria="Bebidas",
                unidad_medida="unidad",
                cantidad=0,
                stock_minimo=0,
                costo_unitario=articulo.precio_unitario or 0,
                id_proveedor=proveedor.id_proveedor,
                estado="ACTIVO",
            )
        )
        existentes.add(clave)
        creados += 1
    return creados


def obtener_o_crear_categoria_inventario(db_session: Session, nombre: str):
    nombre = nombre.strip()
    categoria = (
        db_session.query(categorias_inventario)
        .filter(categorias_inventario.nombre == nombre)
        .first()
    )
    if categoria is None:
        categoria = categorias_inventario(nombre=nombre)
        db_session.add(categoria)
        db_session.flush()
    return categoria


def contar_insumos_categoria(db_session: Session, nombre_categoria: str) -> int:
    return (
        db_session.query(inventario)
        .filter(func.trim(inventario.categoria) == nombre_categoria)
        .count()
    )


def cambiar_estado_categoria_inventario(
    db_session: Session, id_categoria: int, nuevo_estado: str
):
    categoria = db_session.get(categorias_inventario, id_categoria)
    if categoria is None:
        raise ValueError("La categoría ya no existe.")
    if nuevo_estado not in {"ACTIVO", "INACTIVO", "ELIMINADO"}:
        raise ValueError("El estado solicitado para la categoría no es válido.")
    categoria.estado = nuevo_estado
    db_session.commit()


def eliminar_categoria_inventario(db_session: Session, id_categoria: int):
    categoria = db_session.get(categorias_inventario, id_categoria)
    if categoria is None:
        raise ValueError("La categoría ya no existe.")
    if categoria.estado == "ACTIVO":
        raise ValueError("Elimina o inhabilita la categoría antes del borrado definitivo.")
    if contar_insumos_categoria(db_session, categoria.nombre):
        raise ValueError(
            "Elimina primero todos los insumos de esta categoría."
        )
    db_session.delete(categoria)
    db_session.commit()


def cambiar_estado_insumo_inventario(
    db_session: Session, id_inventario: int, nuevo_estado: str
):
    item = db_session.get(inventario, id_inventario)
    if item is None:
        raise ValueError("El insumo ya no existe.")
    if nuevo_estado not in {"ACTIVO", "INACTIVO", "ELIMINADO"}:
        raise ValueError("El estado solicitado para el insumo no es válido.")
    item.estado = nuevo_estado
    db_session.commit()


def eliminar_insumo_inventario(db_session: Session, id_inventario: int):
    item = db_session.get(inventario, id_inventario)
    if item is None:
        raise ValueError("El insumo ya no existe.")
    if item.estado == "ACTIVO":
        raise ValueError("Elimina o inhabilita el insumo antes del borrado definitivo.")

    productos_vinculados = (
        db_session.query(productos)
        .filter(productos.id_inventario == id_inventario)
        .count()
    )
    if productos_vinculados:
        raise ValueError(
            "No se puede eliminar: está vinculado a uno o más productos del menú."
        )

    compras_vinculadas = (
        db_session.query(detalles_compras)
        .filter(detalles_compras.id_inventario == id_inventario)
        .count()
    )
    if compras_vinculadas:
        raise ValueError(
            "No se puede eliminar: tiene compras asociadas en el historial."
        )

    db_session.delete(item)
    db_session.commit()


def _normalizar_texto(valor):
    normalizado = unicodedata.normalize("NFKD", (valor or "").strip().casefold())
    sin_tildes = "".join(
        caracter for caracter in normalizado if not unicodedata.combining(caracter)
    )
    return " ".join(re.sub(r"[^\w]+", " ", sin_tildes).split())


def _normalizar_nombre(valor):
    return _normalizar_texto(valor).replace(" ", "")


def extraer_variantes_producto(nombre_producto):
    variantes = []
    for grupo in re.findall(r"\(([^)]*)\)", nombre_producto or ""):
        variantes.extend(
            variante.strip()
            for variante in re.split(r"[,;/|]|\s+y\s+", grupo)
            if variante.strip()
        )
    return variantes


def _puntaje_coincidencia(nombre_inventario, nombre_menu):
    inventario_normalizado = _normalizar_nombre(nombre_inventario)
    menu_normalizado = _normalizar_nombre(nombre_menu)
    if not inventario_normalizado or not menu_normalizado:
        return 0
    if inventario_normalizado == menu_normalizado:
        return 3

    if any(
        _normalizar_nombre(variante) == inventario_normalizado
        for variante in extraer_variantes_producto(nombre_menu)
    ):
        return 2

    inventario_como_texto = _normalizar_texto(nombre_inventario)
    menu_como_texto = _normalizar_texto(nombre_menu)
    if f" {inventario_como_texto} " in f" {menu_como_texto} ":
        return 1
    return 0


def _seleccionar_coincidencia(coincidencias, nombre_menu, nombre_categoria):
    puntajes = [
        (item, _puntaje_coincidencia(item.nombre, nombre_menu))
        for item in coincidencias
    ]
    puntaje_maximo = max((puntaje for _, puntaje in puntajes), default=0)
    mejores = [item for item, puntaje in puntajes if puntaje == puntaje_maximo and puntaje]
    if len(mejores) <= 1:
        return mejores[0] if mejores else None

    categoria_normalizada = _normalizar_nombre(nombre_categoria)
    mejores_categoria = [
        item
        for item in mejores
        if _normalizar_nombre(item.categoria) == categoria_normalizada
    ]
    return mejores_categoria[0] if len(mejores_categoria) == 1 else None


def buscar_inventario_para_producto(db_session: Session, nombre_producto, nombre_categoria=None):
    nombre_normalizado = _normalizar_nombre(nombre_producto)
    if not nombre_normalizado:
        return None

    return _seleccionar_coincidencia(
        db_session.query(inventario).filter(inventario.id_proveedor.is_(None)).all(),
        nombre_producto,
        nombre_categoria,
    )

def vincular_producto_menu(db_session: Session, item_inventario):
    if item_inventario.id_proveedor is not None:
        return False
    nombre_normalizado = _normalizar_nombre(item_inventario.nombre)
    if not nombre_normalizado:
        return False

    inventarios_disponibles = (
        db_session.query(inventario)
        .filter(inventario.id_proveedor.is_(None))
        .all()
    )
    productos_coincidentes = [
        producto
        for producto in db_session.query(productos).all()
        if _puntaje_coincidencia(item_inventario.nombre, producto.nombre)
        and _seleccionar_coincidencia(
            inventarios_disponibles,
            producto.nombre,
            item_inventario.categoria,
        )
        is item_inventario
    ]
    if not productos_coincidentes:
        return False

    puntajes = [
        (producto, _puntaje_coincidencia(item_inventario.nombre, producto.nombre))
        for producto in productos_coincidentes
    ]
    puntaje_maximo = max((puntaje for _, puntaje in puntajes), default=0)
    mejores_productos = [
        producto for producto, puntaje in puntajes if puntaje == puntaje_maximo and puntaje
    ]
    if len(mejores_productos) > 1:
        categorias_coincidentes = [
            categoria
            for categoria in db_session.query(categorias).all()
            if _normalizar_nombre(categoria.nombre)
            == _normalizar_nombre(item_inventario.categoria)
        ]
        if len(categorias_coincidentes) == 1:
            productos_categoria = [
                producto
                for producto in mejores_productos
                if producto.id_categoria == categorias_coincidentes[0].id_categoria
            ]
            if len(productos_categoria) == 1:
                mejores_productos = productos_categoria
    if len(mejores_productos) != 1:
        return False

    producto = mejores_productos[0]
    if producto.id_inventario not in (None, item_inventario.id_inventario):
        return False

    producto.id_inventario = item_inventario.id_inventario
    return True

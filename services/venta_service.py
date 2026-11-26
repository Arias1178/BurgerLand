import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from database.models import (
    categorias,
    consumo_inventario_venta,
    detalle_ventas,
    historial_domicilios,
    inventario,
    movimiento_caja,
    productos,
    receta_producto,
    ventas,
)
from services.inventario_service import buscar_inventario_para_producto
from services.mesa_service import (
    ESTADO_MESA_OCUPADA,
    validar_mesa_disponible,
)
from database.models import mesas
from services.domicilios_service import normalizar_datos_domicilio


def _normalizar_item_venta(item):
    if not isinstance(item, dict):
        raise ValueError("Cada producto del carrito debe ser un registro válido.")

    item_id = item.get("id_producto")
    if item_id is None:
        raise ValueError("Falta el identificador del producto en el carrito.")

    cantidad = item.get("cantidad")
    precio = item.get("precio")
    nombre = item.get("nombre", "el producto")

    try:
        cantidad_int = int(cantidad)
    except (TypeError, ValueError):
        raise ValueError(f"La cantidad para '{nombre}' debe ser un número entero.")

    if cantidad_int <= 0:
        raise ValueError(f"La cantidad para '{nombre}' debe ser mayor que 0.")

    try:
        precio_valor = float(precio)
    except (TypeError, ValueError):
        raise ValueError(f"El precio para '{nombre}' debe ser numérico.")

    if precio_valor < 0:
        raise ValueError(f"El precio para '{nombre}' no puede ser negativo.")

    inventario_id = item.get("id_inventario")
    if inventario_id is not None:
        try:
            inventario_id = int(inventario_id)
        except (TypeError, ValueError):
            raise ValueError(f"El inventario seleccionado para '{nombre}' no es válido.")

    return {
        "id_producto": int(item_id),
        "cantidad": cantidad_int,
        "precio": precio_valor,
        "nombre": nombre,
        "id_inventario": inventario_id,
        "personalizacion": str(item.get("personalizacion") or "").strip() or None,
    }


def validar_item_venta(item):
    return _normalizar_item_venta(item)


def _opcion_receta_seleccionada(grupo, personalizacion):
    personalizacion = (personalizacion or "").strip()
    if grupo == "proteina_burger":
        for parte in personalizacion.split(";"):
            clave, separador, valor = parte.partition(":")
            if separador and clave.strip().casefold() == "carne":
                return valor.strip()
        return "Carne de la casa (140 g, 100 % res)"
    if grupo == "opcion_infantil":
        for opcion in (
            "6 Nuggets",
            "Hamburguesa con carne Koller",
            "Hamburguesa con pollo apanado",
        ):
            if opcion.casefold() in personalizacion.casefold():
                return opcion
        return "6 Nuggets"
    return None


def _consumos_personalizados(db_session, item, consumos):
    personalizacion = (item.get("personalizacion") or "").casefold()
    todos_los_insumos = {
        registro.nombre.strip().casefold(): registro
        for registro in db_session.query(inventario).all()
    }

    def agregar(nombre, cantidad):
        insumo = todos_los_insumos.get(nombre.casefold())
        if insumo is None:
            raise ValueError(
                f"No se encontró el insumo {nombre} requerido por la personalización."
            )
        consumos[insumo.id_inventario] = (
            consumos.get(insumo.id_inventario, 0) + cantidad
        )

    if "arepa artesanal" in personalizacion:
        for id_inventario in list(consumos):
            insumo = db_session.get(inventario, id_inventario)
            if insumo and insumo.nombre.casefold() == "pan de hamburguesa":
                consumos[id_inventario] -= item["cantidad"]
                if consumos[id_inventario] <= 0:
                    del consumos[id_inventario]
                break
        agregar("Arepa de maíz", 1)

    if "con tocineta" in personalizacion:
        agregar("Tocineta", 1)

    if "combo agrandado" in personalizacion:
        agregar("Papas a la francesa", 250)
        agregar("Gaseosa", 350)
    elif "combo (" in personalizacion:
        agregar("Papas a la francesa", 150)
        agregar("Gaseosa", 250)

    acompanamientos = personalizacion.partition("acompañamientos:")[2]
    if acompanamientos:
        elegidos = [nombre.strip() for nombre in acompanamientos.split(" y ")]
        equivalencias = {
            "papas francesas": (("Papas a la francesa", 150),),
            "papas criollas": (("Papas criollas", 150),),
            "casquitos de papa": (("Casquitos de papa", 300),),
            "ensalada primavera": (("Ensalada Primavera", 1),),
            "ensalada zanahoria": (("Ensalada Zanahoria", 1),),
            "arepa con queso": (("Arepa de maíz", 1), ("Queso", 1)),
        }
        for nombre in elegidos:
            for ingrediente, cantidad in equivalencias.get(nombre, ()):
                agregar(ingrediente, cantidad)


def _cargar_inventario_venta(db_session: Session, carrito_local):
    inventarios_por_id = {}
    cantidades_por_inventario = {}

    for item in carrito_local:
        producto_id = item["id_producto"]
        cantidad = item["cantidad"]
        producto = db_session.query(productos).filter(productos.id_producto == producto_id).first()
        if not producto:
            raise ValueError(f"No se encontró el producto con id {producto_id}.")

        receta = (
            db_session.query(receta_producto)
            .filter(receta_producto.id_producto == producto_id)
            .all()
        )
        if receta:
            consumos_item = {}
            grupos = {}
            for ingrediente in receta:
                if ingrediente.grupo_opcion:
                    grupos.setdefault(ingrediente.grupo_opcion, []).append(
                        ingrediente
                    )
                else:
                    consumos_item[ingrediente.id_inventario] = (
                        consumos_item.get(ingrediente.id_inventario, 0)
                        + ingrediente.cantidad
                    )

            for grupo, opciones in grupos.items():
                seleccion = _opcion_receta_seleccionada(
                    grupo, item.get("personalizacion")
                )
                opcion_elegida = next(
                    (
                        ingrediente.opcion
                        for ingrediente in opciones
                        if ingrediente.opcion
                        and ingrediente.opcion.casefold()
                        == (seleccion or "").casefold()
                    ),
                    opciones[0].opcion,
                )
                for ingrediente in opciones:
                    if ingrediente.opcion == opcion_elegida:
                        consumos_item[ingrediente.id_inventario] = (
                            consumos_item.get(ingrediente.id_inventario, 0)
                            + ingrediente.cantidad
                        )

            _consumos_personalizados(
                db_session, item, consumos_item
            )
            for inventario_id, cantidad_ingrediente in consumos_item.items():
                cantidades_por_inventario[inventario_id] = (
                    cantidades_por_inventario.get(inventario_id, 0)
                    + cantidad_ingrediente * cantidad
                )
            continue

        inventario_id = item.get("id_inventario") or producto.id_inventario
        if inventario_id is None:
            categoria = db_session.query(categorias).filter(
                categorias.id_categoria == producto.id_categoria
            ).first()
            insumo_coincidente = buscar_inventario_para_producto(
                db_session,
                producto.nombre,
                categoria.nombre if categoria else None,
            )
            if insumo_coincidente:
                inventario_id = insumo_coincidente.id_inventario
                producto.id_inventario = inventario_id

        if inventario_id is not None:
            cantidades_por_inventario[inventario_id] = (
                cantidades_por_inventario.get(inventario_id, 0) + cantidad
            )

    for inventario_id, cantidad_total in cantidades_por_inventario.items():
        if cantidad_total <= 0:
            continue
        insumo = (
            db_session.query(inventario)
            .filter(inventario.id_inventario == inventario_id)
            .with_for_update()
            .first()
        )
        if not insumo:
            raise ValueError(f"El insumo de inventario {inventario_id} no existe.")
        if insumo.estado != "ACTIVO":
            raise ValueError(
                f"No se puede vender: el insumo {insumo.nombre} "
                "está inhabilitado o eliminado."
            )
        inventarios_por_id[inventario_id] = insumo

    for inventario_id, cantidad_total in cantidades_por_inventario.items():
        if cantidad_total <= 0:
            continue
        insumo = inventarios_por_id[inventario_id]
        if insumo.cantidad < cantidad_total:
            raise ValueError(
                f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
            )

    return inventarios_por_id, cantidades_por_inventario


def _guardar_consumos_inventario(db_session, venta_id, cantidades):
    db_session.add_all(
        [
            consumo_inventario_venta(
                id_venta=venta_id,
                id_inventario=inventario_id,
                cantidad=cantidad,
            )
            for inventario_id, cantidad in cantidades.items()
            if cantidad > 0
        ]
    )


def validar_stock_disponible(db_session: Session, carrito_local: Iterable[dict]):
    carrito_list = list(carrito_local)
    if not carrito_list:
        raise ValueError("Debes agregar al menos un producto para registrar la venta.")

    _cargar_inventario_venta(db_session, carrito_list)
    return True


def registrar_venta(
    db_session: Session,
    carrito,
    metodo_id,
    usuario_actual=None,
    caja_actual=None,
    mesa_id: int | None = None,
    commit: bool = True,
    mesa_cuenta_abierta: bool = False,
    domicilio: dict | None = None,
):
    if not carrito:
        raise ValueError("Agrega al menos un producto para registrar la venta.")
    if metodo_id is None:
        raise ValueError("Debes seleccionar un método de pago.")
    if caja_actual is None:
        raise ValueError("Debes abrir caja antes de registrar la venta.")

    if mesa_cuenta_abierta and mesa_id is not None:
        mesa = db_session.get(mesas, mesa_id)
        if mesa is None or mesa.estado != ESTADO_MESA_OCUPADA:
            raise ValueError("La mesa asociada a esta cuenta ya no está ocupada.")
    else:
        mesa = validar_mesa_disponible(db_session, mesa_id)
    domicilio_normalizado = (
        normalizar_datos_domicilio(domicilio) if domicilio is not None else None
    )
    if domicilio_normalizado and mesa is not None:
        raise ValueError("Un pedido a domicilio no puede asociarse a una mesa.")
    carrito_validado = [_normalizar_item_venta(item) for item in carrito]
    inventarios_por_id, cantidades_por_inventario = _cargar_inventario_venta(
        db_session, carrito_validado
    )

    subtotal = sum(
        float(item["precio"]) * int(item["cantidad"])
        for item in carrito_validado
    )
    valor_domicilio = (
        domicilio_normalizado["valor_domicilio"]
        if domicilio_normalizado
        else 0
    )
    total = subtotal + valor_domicilio
    try:
        nueva_venta = ventas(
            fecha_hora=datetime.datetime.now(),
            total=float(total),
            id_metodos_pagos=metodo_id,
            id_usuario=getattr(usuario_actual, "id_usuario", None),
            id_caja=getattr(caja_actual, "id_caja", None),
            id_estado_ventas=1,
            id_mesa=mesa.id_mesa if mesa else None,
            tipo_pedido=(
                "DOMICILIO"
                if domicilio_normalizado
                else "MESA"
                if mesa is not None
                else "MOSTRADOR"
            ),
            **(domicilio_normalizado or {}),
        )
        db_session.add(nueva_venta)
        db_session.flush()
        _guardar_consumos_inventario(
            db_session,
            nueva_venta.id_venta,
            cantidades_por_inventario,
        )

        for item in carrito_validado:
            db_session.add(
                detalle_ventas(
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio"],
                    subtotal=float(item["precio"] * item["cantidad"]),
                    nombre_producto=item["nombre"],
                    personalizacion=item["personalizacion"],
                    id_venta=nueva_venta.id_venta,
                    id_producto=item["id_producto"],
                    id_inventario=(
                        item["id_inventario"]
                        or db_session.get(productos, item["id_producto"]).id_inventario
                    ),
                )
            )

        if domicilio_normalizado:
            db_session.add(
                historial_domicilios(
                    id_venta=nueva_venta.id_venta,
                    id_usuario=getattr(usuario_actual, "id_usuario", None),
                    estado="RECIBIDO",
                )
            )

        for inventario_id, cantidad_total in cantidades_por_inventario.items():
            inventarios_por_id[inventario_id].cantidad -= cantidad_total

        db_session.add(
            movimiento_caja(
                fecha=datetime.datetime.now(),
                tipo="INGRESO",
                valor=float(total),
                descripcion=f"Venta #{nueva_venta.id_venta}",
                id_caja=caja_actual.id_caja,
            )
        )

        if commit:
            db_session.commit()
        else:
            db_session.flush()
        db_session.refresh(nueva_venta)
        return nueva_venta
    except Exception:
        db_session.rollback()
        raise

import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from database.models import detalle_ventas, inventario, movimiento_caja, productos, ventas


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

    return {
        "id_producto": int(item_id),
        "cantidad": cantidad_int,
        "precio": precio_valor,
        "nombre": nombre,
    }


def validar_item_venta(item):
    return _normalizar_item_venta(item)


def _cantidad_total_por_producto(carrito_local: Iterable[dict]):
    cantidades = {}
    for item in carrito_local:
        item_validado = _normalizar_item_venta(item)
        producto_id = item_validado["id_producto"]
        cantidades[producto_id] = cantidades.get(producto_id, 0) + item_validado["cantidad"]
    return cantidades


def validar_stock_disponible(db_session: Session, carrito_local: Iterable[dict]):
    carrito_list = list(carrito_local)
    if not carrito_list:
        raise ValueError("Debes agregar al menos un producto para registrar la venta.")

    cantidades_por_producto = _cantidad_total_por_producto(carrito_list)
    for producto_id, cantidad_total in cantidades_por_producto.items():
        producto = db_session.query(productos).filter(productos.id_producto == producto_id).first()
        if not producto:
            raise ValueError(f"No se encontró el producto con id {producto_id}.")
        if not producto.id_inventario:
            continue

        insumo = (
            db_session.query(inventario)
            .filter(inventario.id_inventario == producto.id_inventario)
            .with_for_update()
            .first()
        )
        if not insumo:
            raise ValueError(f"El inventario de {producto.nombre} no está configurado.")
        if insumo.cantidad < cantidad_total:
            raise ValueError(
                f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
            )
    return True


def registrar_venta(db_session: Session, carrito, metodo_id, usuario_actual=None, caja_actual=None, proveedores_seleccionados=None):
    proveedores_seleccionados = proveedores_seleccionados or []
    if not carrito:
        raise ValueError("Agrega al menos un producto para registrar la venta.")
    if metodo_id is None:
        raise ValueError("Debes seleccionar un método de pago.")
    if caja_actual is None:
        raise ValueError("Debes abrir caja antes de registrar la venta.")

    carrito_validado = [_normalizar_item_venta(item) for item in carrito]
    validar_stock_disponible(db_session, carrito_validado)

    total = sum(float(item["precio"]) * int(item["cantidad"]) for item in carrito_validado)
    total_proveedores = sum(float(item.get("costo", 0)) for item in proveedores_seleccionados)
    id_proveedor = proveedores_seleccionados[0]["id"] if len(proveedores_seleccionados) == 1 else None
    proveedores_texto = ", ".join(item["nombre"] for item in proveedores_seleccionados) if proveedores_seleccionados else None

    try:
        nueva_venta = ventas(
            fecha_hora=datetime.datetime.now(),
            total=float(total),
            id_metodos_pagos=metodo_id,
            id_usuario=getattr(usuario_actual, "id_usuario", None),
            id_caja=getattr(caja_actual, "id_caja", None),
            id_estado_ventas=1,
            id_proveedor=id_proveedor,
            proveedores_texto=proveedores_texto,
            costo_proveedor=float(total_proveedores),
        )
        db_session.add(nueva_venta)
        db_session.flush()

        cantidades_por_producto = _cantidad_total_por_producto(carrito_validado)
        for producto_id, cantidad_total in cantidades_por_producto.items():
            producto = db_session.query(productos).filter(productos.id_producto == producto_id).first()
            if not producto:
                raise ValueError(f"No se encontró el producto con id {producto_id}.")

            if producto.id_inventario:
                insumo = (
                    db_session.query(inventario)
                    .filter(inventario.id_inventario == producto.id_inventario)
                    .with_for_update()
                    .first()
                )
                if not insumo:
                    raise ValueError(f"El inventario de {producto.nombre} no está configurado.")
                if insumo.cantidad < cantidad_total:
                    raise ValueError(
                        f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
                    )
                insumo.cantidad -= cantidad_total

            subtotal_producto = sum(
                float(item["precio"]) * int(item["cantidad"]) for item in carrito_validado if int(item["id_producto"]) == producto_id
            )
            precio_unitario = next(float(item["precio"]) for item in carrito_validado if int(item["id_producto"]) == producto_id)
            db_session.add(
                detalle_ventas(
                    cantidad=cantidad_total,
                    precio_unitario=precio_unitario,
                    subtotal=float(subtotal_producto),
                    id_venta=nueva_venta.id_venta,
                    id_producto=producto_id,
                )
            )

        db_session.add(
            movimiento_caja(
                fecha=datetime.datetime.now(),
                tipo="INGRESO",
                valor=float(total),
                descripcion=f"Venta #{nueva_venta.id_venta}",
                id_caja=caja_actual.id_caja,
            )
        )

        db_session.commit()
        db_session.refresh(nueva_venta)
        return nueva_venta
    except Exception:
        db_session.rollback()
        raise

import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from database.models import (
    categorias,
    detalle_ventas,
    historial_domicilios,
    inventario,
    movimiento_caja,
    productos,
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


def _cargar_inventario_venta(db_session: Session, carrito_local):
    inventarios_por_id = {}
    cantidades_por_inventario = {}

    for item in carrito_local:
        producto_id = item["id_producto"]
        cantidad = item["cantidad"]
        producto = db_session.query(productos).filter(productos.id_producto == producto_id).first()
        if not producto:
            raise ValueError(f"No se encontró el producto con id {producto_id}.")

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

        if inventario_id is None:
            continue

        if inventario_id not in inventarios_por_id:
            insumo = (
                db_session.query(inventario)
                .filter(inventario.id_inventario == inventario_id)
                .with_for_update()
                .first()
            )
            if not insumo:
                raise ValueError(f"El inventario seleccionado para {producto.nombre} no existe.")
            if insumo.estado != "ACTIVO":
                raise ValueError(
                    f"No se puede vender {producto.nombre}: "
                    f"el insumo {insumo.nombre} está inhabilitado o eliminado."
                )
            inventarios_por_id[inventario_id] = insumo
            cantidades_por_inventario[inventario_id] = 0

        cantidades_por_inventario[inventario_id] += cantidad

    for inventario_id, cantidad_total in cantidades_por_inventario.items():
        insumo = inventarios_por_id[inventario_id]
        if insumo.cantidad < cantidad_total:
            raise ValueError(
                f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
            )

    return inventarios_por_id, cantidades_por_inventario


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
    proveedores_seleccionados=None,
    mesa_id: int | None = None,
    commit: bool = True,
    mesa_cuenta_abierta: bool = False,
    whatsapp_cliente: str | None = None,
    domicilio: dict | None = None,
):
    proveedores_seleccionados = proveedores_seleccionados or []
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
    total_proveedores = sum(float(item.get("costo", 0)) for item in proveedores_seleccionados)
    id_proveedor = proveedores_seleccionados[0]["id"] if len(proveedores_seleccionados) == 1 else None
    proveedores_texto = ", ".join(item["nombre"] for item in proveedores_seleccionados) if proveedores_seleccionados else None
    if whatsapp_cliente:
        from services.whatsapp_service import validar_numero_colombiano

        whatsapp_cliente = validar_numero_colombiano(whatsapp_cliente)

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
            id_mesa=mesa.id_mesa if mesa else None,
            tipo_pedido=(
                "DOMICILIO"
                if domicilio_normalizado
                else "MESA"
                if mesa is not None
                else "MOSTRADOR"
            ),
            **(domicilio_normalizado or {}),
            whatsapp_cliente=whatsapp_cliente,
            whatsapp_estado_envio="PENDIENTE" if whatsapp_cliente else None,
        )
        db_session.add(nueva_venta)
        db_session.flush()

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

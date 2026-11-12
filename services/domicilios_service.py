import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy.orm import Session

from database.models import (
    Transaction,
    detalle_ventas,
    historial_domicilios,
    inventario,
    metodos_pago,
    movimiento_caja,
    productos,
    ventas,
)
from services.whatsapp_service import validar_numero_colombiano


ESTADOS_DOMICILIO = (
    "RECIBIDO",
    "EN_PREPARACION",
    "EN_CAMINO",
    "ENTREGADO",
    "CANCELADO",
)
ESTADOS_DOMICILIO_ACTIVOS = ("RECIBIDO", "EN_PREPARACION", "EN_CAMINO")


def normalizar_datos_domicilio(datos: dict) -> dict:
    if not isinstance(datos, dict):
        raise ValueError("Completa los datos del domicilio.")
    cliente = str(datos.get("cliente") or "").strip()
    direccion = str(datos.get("direccion") or "").strip()
    barrio = str(datos.get("barrio_referencia") or "").strip()
    domiciliario = str(datos.get("domiciliario") or "").strip()
    if not cliente:
        raise ValueError("El nombre del cliente es obligatorio para el domicilio.")
    if not direccion:
        raise ValueError("La dirección es obligatoria para el domicilio.")
    try:
        telefono = validar_numero_colombiano(str(datos.get("telefono") or ""))
    except ValueError as error:
        raise ValueError(f"El teléfono del domicilio no es válido: {error}") from error
    try:
        costo = Decimal(str(datos.get("valor_domicilio", 0)))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("El valor del domicilio debe ser numérico.") from error
    if not costo.is_finite() or costo < 0:
        raise ValueError("El valor del domicilio debe ser un monto no negativo.")
    costo = costo.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return {
        "cliente": cliente,
        "telefono_cliente": telefono,
        "direccion_domicilio": direccion,
        "barrio_referencia": barrio or None,
        "valor_domicilio": float(costo),
        "domiciliario": domiciliario or None,
        "estado_domicilio": "RECIBIDO",
    }


def listar_domicilios_activos(db: Session) -> list[ventas]:
    return (
        db.query(ventas)
        .filter(
            ventas.tipo_pedido == "DOMICILIO",
            ventas.estado_domicilio.in_(ESTADOS_DOMICILIO_ACTIVOS),
        )
        .order_by(ventas.fecha_hora.asc(), ventas.id_venta.asc())
        .all()
    )


def cambiar_estado_domicilio(
    db: Session,
    venta_id: int,
    nuevo_estado: str,
    usuario_id: int | None = None,
    motivo: str | None = None,
) -> ventas:
    nuevo_estado = (nuevo_estado or "").strip().upper()
    if nuevo_estado not in ESTADOS_DOMICILIO:
        raise ValueError("El estado seleccionado para el domicilio no es válido.")
    venta = db.get(ventas, venta_id)
    if venta is None or venta.tipo_pedido != "DOMICILIO":
        raise ValueError("No se encontró el domicilio seleccionado.")
    estado_actual = venta.estado_domicilio or "RECIBIDO"
    if estado_actual == nuevo_estado:
        raise ValueError("El domicilio ya se encuentra en ese estado.")
    transiciones = {
        "RECIBIDO": {"EN_PREPARACION", "CANCELADO"},
        "EN_PREPARACION": {"EN_CAMINO", "CANCELADO"},
        "EN_CAMINO": {"ENTREGADO", "CANCELADO"},
        "ENTREGADO": set(),
        "CANCELADO": set(),
    }
    if nuevo_estado not in transiciones[estado_actual]:
        raise ValueError(
            f"No se puede cambiar el domicilio de {estado_actual} a {nuevo_estado}."
        )
    motivo_normalizado = (motivo or "").strip()
    if nuevo_estado == "CANCELADO" and not motivo_normalizado:
        raise ValueError("Indica el motivo de cancelación del domicilio.")
    fecha_cambio = datetime.datetime.now()

    try:
        if nuevo_estado == "CANCELADO":
            metodo = db.get(metodos_pago, venta.id_metodos_pagos)
            es_efectivo = bool(metodo and metodo.nombre.upper() == "EFECTIVO")
            db.add(
                Transaction(
                    tipo="reembolso_venta",
                    monto=float(venta.total),
                    fecha=fecha_cambio,
                    categoria=f"Cancelación de domicilio #{venta.id_venta}",
                    centro_de_costo_id=venta.id_venta,
                    pagado=es_efectivo,
                )
            )
            if es_efectivo:
                db.add(
                    movimiento_caja(
                        fecha=fecha_cambio,
                        tipo="EGRESO",
                        valor=float(venta.total),
                        descripcion=f"Devolución domicilio #{venta.id_venta}",
                        id_caja=venta.id_caja,
                    )
                )
            else:
                db.add(
                    movimiento_caja(
                        fecha=fecha_cambio,
                        tipo="REEMBOLSO_NO_EFECTIVO",
                        valor=float(venta.total),
                        descripcion=f"Devolución no efectiva domicilio #{venta.id_venta}",
                        id_caja=venta.id_caja,
                    )
                )

            detalles = (
                db.query(detalle_ventas)
                .filter(detalle_ventas.id_venta == venta.id_venta)
                .all()
            )
            for detalle in detalles:
                inventario_id = detalle.id_inventario
                if inventario_id is None and detalle.id_producto is not None:
                    producto = db.get(productos, detalle.id_producto)
                    inventario_id = producto.id_inventario if producto else None
                if inventario_id is not None:
                    item = db.get(inventario, inventario_id)
                    if item is None:
                        raise ValueError(
                            "No se puede cancelar: falta un insumo asociado al "
                            "producto vendido."
                        )
                    item.cantidad += detalle.cantidad
            venta.id_estado_ventas = _id_estado_venta(db, "ANULADA")

        venta.estado_domicilio = nuevo_estado
        db.add(
            historial_domicilios(
                id_venta=venta.id_venta,
                id_usuario=usuario_id,
                estado=nuevo_estado,
                motivo=motivo_normalizado or None,
            )
        )
        db.commit()
        db.refresh(venta)
        return venta
    except Exception:
        db.rollback()
        raise


def _id_estado_venta(db: Session, nombre: str) -> int:
    from database.models import estado_ventas

    estado = (
        db.query(estado_ventas)
        .filter(estado_ventas.nombre == nombre)
        .first()
    )
    if estado is None:
        raise ValueError(f"No existe el estado de venta {nombre}.")
    return estado.id_estado_venta

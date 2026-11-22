from datetime import datetime

from sqlalchemy.orm import Session

from database.models import compras, detalles_compras, inventario, proveedores


def registrar_compra(db: Session, proveedor_id: int, lineas: list[dict]) -> compras:
    proveedor = (
        db.query(proveedores)
        .filter(
            proveedores.id_proveedor == proveedor_id,
            proveedores.estado == "ACTIVO",
        )
        .first()
    )
    if not proveedor:
        raise ValueError("Selecciona un proveedor activo.")
    if not lineas:
        raise ValueError("Agrega al menos un ítem a la compra.")

    compra = compras(fecha=datetime.now(), total=0, id_proveedor=proveedor_id)
    detalles = []
    total = 0.0
    try:
        for linea in lineas:
            item = (
                db.query(inventario)
                .filter(inventario.id_inventario == linea["id_inventario"])
                .with_for_update()
                .first()
            )
            if not item:
                raise ValueError(
                    "El ítem seleccionado no existe en inventario. Regístralo primero desde Inventario."
                )
            if item.estado != "ACTIVO":
                raise ValueError(
                    f"El ítem {item.nombre} está inhabilitado o eliminado."
                )
            if item.id_proveedor not in (None, proveedor_id):
                raise ValueError(
                    f"El ítem {item.nombre} pertenece a otro proveedor."
                )

            cantidad = int(linea["cantidad"])
            precio = float(linea["precio"])
            if cantidad <= 0 or precio < 0:
                raise ValueError("La cantidad debe ser mayor que cero y el precio no puede ser negativo.")

            subtotal = cantidad * precio
            total += subtotal
            cantidad_anterior = item.cantidad
            cantidad_total = cantidad_anterior + cantidad
            item.costo_unitario = (
                (
                    cantidad_anterior * item.costo_unitario
                    + cantidad * precio
                )
                / cantidad_total
                if cantidad_total
                else 0
            )
            item.cantidad = cantidad_total
            detalles.append(
                detalles_compras(
                    cantidad=cantidad,
                    precio=precio,
                    subtotal=subtotal,
                    id_inventario=item.id_inventario,
                )
            )

        compra.total = total
        db.add(compra)
        db.flush()
        for detalle in detalles:
            detalle.id_compra = compra.id_compra
            db.add(detalle)
        db.commit()
        db.refresh(compra)
        return compra
    except Exception:
        db.rollback()
        raise

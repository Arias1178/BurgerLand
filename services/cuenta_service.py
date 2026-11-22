import datetime
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import (
    asignaciones_subcuenta,
    cuentas_abiertas,
    detalle_ventas,
    items_cuenta,
    metodos_pago,
    movimiento_caja,
    mesas,
    productos,
    subcuentas,
    ventas,
)
from services.mesa_service import (
    ESTADO_MESA_LIBRE,
    ESTADO_MESA_OCUPADA,
    validar_mesa_disponible,
)
from services.whatsapp_service import validar_numero_colombiano


class CuentaModificadaError(ValueError):
    """Señala que otra sesión guardó la cuenta primero."""


def _normalizar_items(carrito: list[dict]) -> list[dict]:
    if not carrito:
        raise ValueError("Agrega al menos un producto antes de guardar la cuenta.")

    resultado = []
    for item in carrito:
        try:
            id_producto = int(item["id_producto"])
            cantidad = int(item["cantidad"])
            precio = float(item["precio"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Hay un producto del carrito con datos inválidos.")
        if id_producto <= 0 or cantidad <= 0 or precio < 0:
            raise ValueError("Revisa el producto, la cantidad y el precio del carrito.")

        id_inventario = item.get("id_inventario")
        if id_inventario is not None:
            try:
                id_inventario = int(id_inventario)
            except (TypeError, ValueError):
                raise ValueError("El inventario asociado a un producto no es válido.")

        agregado_en = item.get("agregado_en") or datetime.datetime.now()
        if isinstance(agregado_en, str):
            try:
                agregado_en = datetime.datetime.fromisoformat(agregado_en)
            except ValueError as error:
                raise ValueError("La fecha de agregado de un producto no es válida.") from error

        resultado.append(
            {
                "id_producto": id_producto,
                "id_inventario": id_inventario,
                "nombre": str(item.get("nombre") or "Producto"),
                "precio_unitario": precio,
                "cantidad": cantidad,
                "personalizacion": str(item.get("personalizacion") or "").strip() or None,
                "agregado_en": agregado_en,
            }
        )
    return resultado


def obtener_cuenta_abierta(db: Session, cuenta_id: int) -> cuentas_abiertas:
    cuenta = db.get(cuentas_abiertas, cuenta_id)
    if cuenta is None or cuenta.estado != "ABIERTA":
        raise ValueError("La cuenta ya no está abierta.")
    return cuenta


def obtener_items_cuenta(db: Session, cuenta_id: int) -> list[items_cuenta]:
    return (
        db.query(items_cuenta)
        .filter(items_cuenta.id_cuenta == cuenta_id)
        .order_by(items_cuenta.agregado_en, items_cuenta.id_item_cuenta)
        .all()
    )


def listar_subcuentas(db: Session, cuenta_id: int) -> list[dict]:
    filas = (
        db.query(subcuentas)
        .filter(subcuentas.id_cuenta == cuenta_id)
        .order_by(subcuentas.id_subcuenta)
        .all()
    )
    resultado = []
    for subcuenta in filas:
        asignaciones = (
            db.query(asignaciones_subcuenta, items_cuenta)
            .join(
                items_cuenta,
                asignaciones_subcuenta.id_item_cuenta == items_cuenta.id_item_cuenta,
            )
            .filter(asignaciones_subcuenta.id_subcuenta == subcuenta.id_subcuenta)
            .order_by(items_cuenta.agregado_en, items_cuenta.id_item_cuenta)
            .all()
        )
        resultado.append(
            {
                "subcuenta": subcuenta,
                "items": [
                    {"asignacion": asignacion, "item": item}
                    for asignacion, item in asignaciones
                ],
            }
        )
    return resultado


def actualizar_estado_whatsapp_cuenta(
    db: Session,
    cuenta_id: int,
    estado: str,
) -> None:
    if estado not in {"PENDIENTE", "ENVIADO", "ERROR"}:
        raise ValueError("El estado de WhatsApp no es válido.")
    resultado = db.execute(
        update(cuentas_abiertas)
        .where(
            cuentas_abiertas.id_cuenta == cuenta_id,
            cuentas_abiertas.estado == "ABIERTA",
        )
        .values(whatsapp_estado_envio=estado)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise ValueError("No se encontró la cuenta abierta para actualizar WhatsApp.")
    db.commit()


def actualizar_contacto_subcuenta(
    db: Session,
    subcuenta_id: int,
    version: int,
    whatsapp_cliente: str,
    whatsapp_en_confirmar: bool,
) -> subcuentas:
    numero = validar_numero_colombiano(whatsapp_cliente)
    resultado = db.execute(
        update(subcuentas)
        .where(
            subcuentas.id_subcuenta == subcuenta_id,
            subcuentas.estado == "ABIERTA",
            subcuentas.version == version,
        )
        .values(
            whatsapp_cliente=numero,
            whatsapp_estado_envio="PENDIENTE",
            whatsapp_en_confirmar=bool(whatsapp_en_confirmar),
            version=version + 1,
        )
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise CuentaModificadaError(
            "Otro cajero modificó esta subcuenta. Recarga la cuenta."
        )
    db.commit()
    subcuenta = db.get(subcuentas, subcuenta_id)
    if subcuenta is None:
        raise ValueError("No se encontró la subcuenta después de guardar WhatsApp.")
    return subcuenta


def actualizar_estado_whatsapp_subcuenta(
    db: Session,
    subcuenta_id: int,
    estado: str,
) -> None:
    if estado not in {"PENDIENTE", "ENVIADO", "ERROR"}:
        raise ValueError("El estado de WhatsApp no es válido.")
    resultado = db.execute(
        update(subcuentas)
        .where(subcuentas.id_subcuenta == subcuenta_id)
        .values(whatsapp_estado_envio=estado)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise ValueError("No se encontró la subcuenta para actualizar WhatsApp.")
    db.commit()


def _etiquetas_subcuenta(cantidad: int) -> list[str]:
    if cantidad < 2:
        raise ValueError("La división debe tener al menos dos subcuentas.")
    if cantidad > 26 * 26:
        raise ValueError("No se pueden crear más de 676 subcuentas.")

    etiquetas = []
    for indice in range(cantidad):
        numero = indice + 1
        etiqueta = ""
        while numero:
            numero, resto = divmod(numero - 1, 26)
            etiqueta = chr(65 + resto) + etiqueta
        etiquetas.append(etiqueta)
    return etiquetas


def _prorratear_proveedores(proveedores: list[dict], totales: list[float]) -> list[list[dict]]:
    suma_totales = sum(totales)
    por_subcuenta = [[] for _ in totales]
    for proveedor in proveedores:
        try:
            costo = float(proveedor.get("costo", 0))
        except (TypeError, ValueError):
            raise ValueError("El costo asociado a un proveedor no es válido.")
        if costo < 0:
            raise ValueError("El costo asociado a un proveedor no puede ser negativo.")
        acumulado = 0.0
        for indice, total in enumerate(totales):
            if indice == len(totales) - 1:
                costo_parte = round(costo - acumulado, 2)
            elif suma_totales:
                costo_parte = round(costo * total / suma_totales, 2)
                acumulado += costo_parte
            else:
                costo_parte = round(costo / len(totales), 2)
                acumulado += costo_parte
            por_subcuenta[indice].append({**proveedor, "costo": costo_parte})
    return por_subcuenta


def _crear_subcuentas(
    db: Session,
    cuenta: cuentas_abiertas,
    version: int,
    modo: str,
    cantidades_por_item: list[list[int]] | None = None,
    numero_partes: int | None = None,
    totales_personalizados: list[float] | None = None,
) -> list[subcuentas]:
    cuenta = obtener_cuenta_abierta(db, cuenta.id_cuenta)
    if cuenta.version != version:
        raise CuentaModificadaError(
            "Otro cajero modificó esta cuenta. Recárgala antes de dividirla."
        )
    if db.query(subcuentas).filter(subcuentas.id_cuenta == cuenta.id_cuenta).first():
        raise ValueError("Esta cuenta ya está dividida.")

    items = obtener_items_cuenta(db, cuenta.id_cuenta)
    unidades = sum(item.cantidad for item in items)
    if unidades < 2 and modo != "VALORES":
        raise ValueError("La cuenta necesita al menos dos unidades para dividirse.")

    if modo == "IGUALES":
        if numero_partes is None:
            raise ValueError("Indica en cuántas partes deseas dividir la cuenta.")
        etiquetas = _etiquetas_subcuenta(numero_partes)
        total_pesos = int(
            Decimal(str(cuenta.total)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        if abs(float(total_pesos) - float(cuenta.total)) > 1e-6:
            raise ValueError("El total debe estar expresado en pesos enteros.")
        base, residuo = divmod(total_pesos, numero_partes)
        totales = [base] * (numero_partes - 1) + [base + residuo]
        cuentas_creadas = [
            subcuentas(
                id_cuenta=cuenta.id_cuenta,
                etiqueta=etiqueta,
                total=total,
                estado="ABIERTA",
                version=1,
            )
            for etiqueta, total in zip(etiquetas, totales)
        ]
    elif modo == "VALORES":
        if not totales_personalizados:
            raise ValueError("Indica el valor de cada subcuenta.")
        etiquetas = _etiquetas_subcuenta(len(totales_personalizados))
        try:
            totales = [
                int(
                    Decimal(str(total)).quantize(
                        Decimal("1"),
                        rounding=ROUND_HALF_UP,
                    )
                )
                for total in totales_personalizados
            ]
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Los valores de las subcuentas deben ser numéricos.") from error
        if any(total <= 0 for total in totales):
            raise ValueError("Cada subcuenta debe tener un valor mayor que cero.")
        total_original = int(
            Decimal(str(cuenta.total)).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        if sum(totales) != total_original:
            raise ValueError(
                "La suma de los valores personalizados debe coincidir con el total "
                f"de la cuenta (${total_original:,.0f}).".replace(",", ".")
            )
        cuentas_creadas = [
            subcuentas(
                id_cuenta=cuenta.id_cuenta,
                etiqueta=etiqueta,
                total=total,
                estado="ABIERTA",
                version=1,
            )
            for etiqueta, total in zip(etiquetas, totales)
        ]
    elif modo == "ITEMS":
        if cantidades_por_item is None:
            raise ValueError("Debes asignar las unidades de cada producto.")
        numero_partes = len(cantidades_por_item[0]) if cantidades_por_item else 0
        etiquetas = _etiquetas_subcuenta(numero_partes)
        if len(cantidades_por_item) != len(items):
            raise ValueError("La lista de productos cambió. Recarga la cuenta e inténtalo.")

        totales = [0.0] * numero_partes
        asignaciones_pendientes = []
        for indice, (item, cantidades) in enumerate(zip(items, cantidades_por_item)):
            if len(cantidades) != numero_partes:
                raise ValueError("La asignación de productos está incompleta.")
            if any(not isinstance(cantidad, int) or cantidad < 0 for cantidad in cantidades):
                raise ValueError("Las cantidades asignadas deben ser enteros no negativos.")
            if sum(cantidades) != item.cantidad:
                raise ValueError(
                    f"Distribuye las {item.cantidad} unidades de «{item.nombre}» "
                    "entre las subcuentas."
                )
            for posicion, cantidad in enumerate(cantidades):
                if cantidad:
                    totales[posicion] += item.precio_unitario * cantidad
                    asignaciones_pendientes.append((posicion, item.id_item_cuenta, cantidad))
        if any(total <= 0 for total in totales):
            raise ValueError("Cada subcuenta debe recibir al menos una unidad.")
        if abs(sum(totales) - float(cuenta.total)) > 1e-6:
            raise ValueError("La suma de los productos no coincide con el total de la cuenta.")
        cuentas_creadas = [
            subcuentas(
                id_cuenta=cuenta.id_cuenta,
                etiqueta=etiqueta,
                total=total,
                estado="ABIERTA",
                version=1,
            )
            for etiqueta, total in zip(etiquetas, totales)
        ]
    else:
        raise ValueError("El modo de división no es válido.")

    proveedores = json.loads(cuenta.proveedores_json or "[]")
    proveedores_por_subcuenta = _prorratear_proveedores(proveedores, totales)
    resultado = db.execute(
        update(cuentas_abiertas)
        .where(
            cuentas_abiertas.id_cuenta == cuenta.id_cuenta,
            cuentas_abiertas.estado == "ABIERTA",
            cuentas_abiertas.version == version,
            cuentas_abiertas.modo_division.is_(None),
        )
        .values(
            modo_division=modo,
            version=version + 1,
            fecha_actualizacion=datetime.datetime.now(),
        )
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise CuentaModificadaError(
            "Otro cajero modificó esta cuenta. Recárgala antes de dividirla."
        )
    cuenta.modo_division = modo
    cuenta.version = version + 1
    cuenta.fecha_actualizacion = datetime.datetime.now()
    for indice, subcuenta in enumerate(cuentas_creadas):
        subcuenta.costo_proveedor = sum(
            proveedor["costo"] for proveedor in proveedores_por_subcuenta[indice]
        )
        db.add(subcuenta)
    db.flush()
    if modo == "ITEMS":
        for posicion, id_item, cantidad in asignaciones_pendientes:
            db.add(
                asignaciones_subcuenta(
                    id_subcuenta=cuentas_creadas[posicion].id_subcuenta,
                    id_item_cuenta=id_item,
                    cantidad=cantidad,
                )
            )
    db.commit()
    return cuentas_creadas


def dividir_cuenta_en_partes_iguales(
    db: Session, cuenta_id: int, version: int, numero_partes: int
) -> list[subcuentas]:
    try:
        return _crear_subcuentas(
            db,
            obtener_cuenta_abierta(db, cuenta_id),
            version,
            "IGUALES",
            numero_partes=numero_partes,
        )
    except Exception:
        db.rollback()
        raise


def dividir_cuenta_por_items(
    db: Session,
    cuenta_id: int,
    version: int,
    cantidades_por_item: list[list[int]],
) -> list[subcuentas]:
    try:
        return _crear_subcuentas(
            db,
            obtener_cuenta_abierta(db, cuenta_id),
            version,
            "ITEMS",
            cantidades_por_item=cantidades_por_item,
        )
    except Exception:
        db.rollback()
        raise


def dividir_cuenta_por_valores(
    db: Session,
    cuenta_id: int,
    version: int,
    totales_personalizados: list[float],
) -> list[subcuentas]:
    try:
        return _crear_subcuentas(
            db,
            obtener_cuenta_abierta(db, cuenta_id),
            version,
            "VALORES",
            totales_personalizados=totales_personalizados,
        )
    except Exception:
        db.rollback()
        raise


def listar_cuentas_abiertas(db: Session) -> list[dict]:
    cuentas = (
        db.query(cuentas_abiertas, mesas.numero)
        .outerjoin(mesas, mesas.id_mesa == cuentas_abiertas.id_mesa)
        .filter(cuentas_abiertas.estado == "ABIERTA")
        .order_by(cuentas_abiertas.fecha_apertura.asc())
        .all()
    )
    resultado = []
    for cuenta, numero_mesa in cuentas:
        resultado.append(
            {
                "cuenta": cuenta,
                "mesa_numero": numero_mesa,
                "cantidad_items": sum(
                    item.cantidad for item in obtener_items_cuenta(db, cuenta.id_cuenta)
                ),
                "subcuentas_pagadas": sum(
                    subcuenta.estado == "PAGADA"
                    for subcuenta in db.query(subcuentas)
                    .filter(subcuentas.id_cuenta == cuenta.id_cuenta)
                    .all()
                ),
                "total_subcuentas": db.query(subcuentas)
                .filter(subcuentas.id_cuenta == cuenta.id_cuenta)
                .count(),
            }
        )
    return resultado


def guardar_cuenta_abierta(
    db: Session,
    carrito: list[dict],
    mesa_id: int | None,
    proveedores_seleccionados: list[dict] | None = None,
    usuario_id: int | None = None,
    cuenta_id: int | None = None,
    version: int | None = None,
    whatsapp_cliente: str | None = None,
    whatsapp_en_confirmar: bool = False,
) -> cuentas_abiertas:
    items = _normalizar_items(carrito)
    proveedores = proveedores_seleccionados or []
    whatsapp_cliente = (
        validar_numero_colombiano(whatsapp_cliente)
        if whatsapp_cliente and whatsapp_cliente.strip()
        else None
    )
    for item in items:
        if db.get(productos, item["id_producto"]) is None:
            raise ValueError(
                f"El producto «{item['nombre']}» ya no está disponible en el menú."
            )
    proveedores_json = json.dumps(proveedores, ensure_ascii=False)
    total = sum(item["precio_unitario"] * item["cantidad"] for item in items)
    ahora = datetime.datetime.now()

    try:
        if cuenta_id is None:
            mesa = validar_mesa_disponible(db, mesa_id)
            cuenta = cuentas_abiertas(
                id_mesa=mesa.id_mesa if mesa else None,
                estado="ABIERTA",
                fecha_apertura=ahora,
                fecha_actualizacion=ahora,
                total=total,
                id_usuario=usuario_id,
                proveedores_json=proveedores_json,
                version=1,
                whatsapp_cliente=whatsapp_cliente,
                whatsapp_estado_envio=(
                    "PENDIENTE" if whatsapp_cliente else None
                ),
                whatsapp_en_confirmar=bool(whatsapp_en_confirmar),
            )
            db.add(cuenta)
            db.flush()
        else:
            cuenta = obtener_cuenta_abierta(db, cuenta_id)
            if cuenta.modo_division is not None:
                raise ValueError(
                    "No se puede editar una cuenta dividida. Cobra sus subcuentas por separado."
                )
            mesa_anterior_id = cuenta.id_mesa
            if version is None:
                raise ValueError("Falta la versión de la cuenta para guardarla.")
            if mesa_anterior_id != mesa_id:
                validar_mesa_disponible(db, mesa_id)

            resultado = db.execute(
                update(cuentas_abiertas)
                .where(
                    cuentas_abiertas.id_cuenta == cuenta_id,
                    cuentas_abiertas.estado == "ABIERTA",
                    cuentas_abiertas.version == version,
                )
                .values(
                    id_mesa=mesa_id,
                    total=total,
                    proveedores_json=proveedores_json,
                    whatsapp_cliente=whatsapp_cliente,
                    whatsapp_estado_envio=(
                        "PENDIENTE" if whatsapp_cliente else None
                    ),
                    whatsapp_en_confirmar=bool(whatsapp_en_confirmar),
                    fecha_actualizacion=ahora,
                    version=version + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if resultado.rowcount != 1:
                raise CuentaModificadaError(
                    "Otro cajero modificó esta cuenta. Recárgala antes de continuar."
                )
            db.flush()
            cuenta.id_mesa = mesa_id
            cuenta.total = total
            cuenta.proveedores_json = proveedores_json
            cuenta.whatsapp_cliente = whatsapp_cliente
            cuenta.whatsapp_estado_envio = (
                "PENDIENTE" if whatsapp_cliente else None
            )
            cuenta.whatsapp_en_confirmar = bool(whatsapp_en_confirmar)
            cuenta.fecha_actualizacion = ahora
            cuenta.version = version + 1
            db.query(items_cuenta).filter(
                items_cuenta.id_cuenta == cuenta_id
            ).delete(synchronize_session=False)
            if mesa_anterior_id != mesa_id:
                mesa_anterior = db.get(mesas, mesa_anterior_id) if mesa_anterior_id else None
                if mesa_anterior:
                    mesa_anterior.estado = ESTADO_MESA_LIBRE

        for item in items:
            db.add(items_cuenta(id_cuenta=cuenta.id_cuenta, **item))

        if cuenta.id_mesa is not None:
            mesa_actual = db.get(mesas, cuenta.id_mesa)
            if mesa_actual is None:
                raise ValueError("La mesa asociada a la cuenta ya no existe.")
            mesa_actual.estado = ESTADO_MESA_OCUPADA

        db.commit()
        db.refresh(cuenta)
        return cuenta
    except IntegrityError:
        db.rollback()
        raise ValueError("Ya existe una cuenta abierta para esa mesa.")
    except Exception:
        db.rollback()
        raise


def cobrar_cuenta_abierta(
    db: Session,
    cuenta_id: int,
    version: int,
    metodo_id: int,
    usuario_actual,
    caja_actual,
    carrito: list[dict] | None = None,
    proveedores_seleccionados: list[dict] | None = None,
    whatsapp_cliente: str | None = None,
    whatsapp_en_confirmar: bool | None = None,
):
    from services.venta_service import registrar_venta

    cuenta = obtener_cuenta_abierta(db, cuenta_id)
    if cuenta.modo_division is not None:
        raise ValueError("Cobra las subcuentas por separado.")
    if carrito is None:
        items_cuenta_abierta = obtener_items_cuenta(db, cuenta_id)
        carrito_venta = [
            {
                "id_producto": item.id_producto,
                "id_inventario": item.id_inventario,
                "nombre": item.nombre,
                "precio": item.precio_unitario,
                "cantidad": item.cantidad,
                "personalizacion": item.personalizacion,
            }
            for item in items_cuenta_abierta
        ]
    else:
        items_normalizados = _normalizar_items(carrito)
        carrito_venta = [
            {
                "id_producto": item["id_producto"],
                "id_inventario": item["id_inventario"],
                "nombre": item["nombre"],
                "precio": item["precio_unitario"],
                "cantidad": item["cantidad"],
                "personalizacion": item["personalizacion"],
            }
            for item in items_normalizados
        ]
        db.query(items_cuenta).filter(
            items_cuenta.id_cuenta == cuenta_id
        ).delete(synchronize_session=False)
        db.add_all(
            [
                items_cuenta(id_cuenta=cuenta_id, **item)
                for item in items_normalizados
            ]
        )

    proveedores_cuenta = (
        proveedores_seleccionados
        if proveedores_seleccionados is not None
        else json.loads(cuenta.proveedores_json or "[]")
    )
    whatsapp_cuenta = (
        validar_numero_colombiano(whatsapp_cliente)
        if whatsapp_cliente and whatsapp_cliente.strip()
        else cuenta.whatsapp_cliente
    )
    valores_actualizacion = {
        "estado": "PAGADA",
        "fecha_cierre": datetime.datetime.now(),
        "version": version + 1,
    }
    if carrito is not None:
        valores_actualizacion["total"] = sum(
            item["precio"] * item["cantidad"] for item in carrito_venta
        )
        valores_actualizacion["proveedores_json"] = json.dumps(
            proveedores_cuenta,
            ensure_ascii=False,
        )
    valores_actualizacion.update(
        whatsapp_cliente=whatsapp_cuenta,
        whatsapp_estado_envio="PENDIENTE" if whatsapp_cuenta else None,
        whatsapp_en_confirmar=(
            cuenta.whatsapp_en_confirmar
            if whatsapp_en_confirmar is None
            else bool(whatsapp_en_confirmar)
        ),
    )
    resultado = db.execute(
        update(cuentas_abiertas)
        .where(
            cuentas_abiertas.id_cuenta == cuenta_id,
            cuentas_abiertas.estado == "ABIERTA",
            cuentas_abiertas.version == version,
        )
        .values(**valores_actualizacion)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise CuentaModificadaError(
            "Otro cajero modificó esta cuenta. Recárgala antes de cobrar."
        )

    try:
        venta = registrar_venta(
            db_session=db,
            carrito=carrito_venta,
            metodo_id=metodo_id,
            usuario_actual=usuario_actual,
            caja_actual=caja_actual,
            proveedores_seleccionados=proveedores_cuenta,
            mesa_id=cuenta.id_mesa,
            commit=False,
            mesa_cuenta_abierta=True,
            whatsapp_cliente=whatsapp_cuenta,
        )
        if cuenta.id_mesa is not None:
            mesa = db.get(mesas, cuenta.id_mesa)
            if mesa:
                mesa.estado = ESTADO_MESA_LIBRE
        db.commit()
        db.refresh(venta)
        return venta
    except Exception:
        db.rollback()
        raise


def anular_cuenta_abierta(db: Session, cuenta_id: int, version: int) -> None:
    cuenta = obtener_cuenta_abierta(db, cuenta_id)
    if db.query(subcuentas).filter(
        subcuentas.id_cuenta == cuenta_id,
        subcuentas.estado == "PAGADA",
    ).first():
        raise ValueError(
            "No se puede anular una cuenta dividida que ya tiene subcuentas pagadas."
        )
    resultado = db.execute(
        update(cuentas_abiertas)
        .where(
            cuentas_abiertas.id_cuenta == cuenta_id,
            cuentas_abiertas.estado == "ABIERTA",
            cuentas_abiertas.version == version,
        )
        .values(
            estado="ANULADA",
            fecha_cierre=datetime.datetime.now(),
            version=version + 1,
        )
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise CuentaModificadaError(
            "Otro cajero modificó esta cuenta. Recarga la lista antes de anular."
        )
    if cuenta.id_mesa is not None:
        mesa = db.get(mesas, cuenta.id_mesa)
        if mesa:
            mesa.estado = ESTADO_MESA_LIBRE
    db.commit()


def cobrar_subcuenta(
    db: Session,
    cuenta_id: int,
    version_cuenta: int,
    subcuenta_id: int,
    version_subcuenta: int,
    metodo_id: int,
    usuario_actual,
    caja_actual,
    whatsapp_cliente: str | None = None,
    whatsapp_en_confirmar: bool | None = None,
):
    from services.venta_service import _cargar_inventario_venta, registrar_venta

    cuenta = obtener_cuenta_abierta(db, cuenta_id)
    if cuenta.modo_division is None:
        raise ValueError("La cuenta no está dividida.")
    if caja_actual is None:
        raise ValueError("Debes abrir caja antes de cobrar una subcuenta.")
    if db.get(metodos_pago, metodo_id) is None:
        raise ValueError("Selecciona un método de pago válido.")
    subcuenta = db.get(subcuentas, subcuenta_id)
    if (
        subcuenta is None
        or subcuenta.id_cuenta != cuenta_id
        or subcuenta.estado != "ABIERTA"
    ):
        raise ValueError("La subcuenta ya no está disponible para cobrar.")
    if subcuenta.version != version_subcuenta:
        raise CuentaModificadaError(
            "Otro cajero modificó esta subcuenta. Recarga la cuenta."
        )
    whatsapp_subcuenta = (
        validar_numero_colombiano(whatsapp_cliente)
        if whatsapp_cliente and whatsapp_cliente.strip()
        else subcuenta.whatsapp_cliente
    )

    otras_pendientes = (
        db.query(subcuentas)
        .filter(
            subcuentas.id_cuenta == cuenta_id,
            subcuentas.id_subcuenta != subcuenta_id,
            subcuentas.estado != "PAGADA",
        )
        .count()
    )
    fecha_pago = datetime.datetime.now()
    valores_cuenta = {
        "version": version_cuenta + 1,
        "fecha_actualizacion": fecha_pago,
    }
    if otras_pendientes == 0:
        valores_cuenta.update(estado="PAGADA", fecha_cierre=fecha_pago)
    actualizacion_cuenta = db.execute(
        update(cuentas_abiertas)
        .where(
            cuentas_abiertas.id_cuenta == cuenta_id,
            cuentas_abiertas.estado == "ABIERTA",
            cuentas_abiertas.version == version_cuenta,
            cuentas_abiertas.modo_division.is_not(None),
        )
        .values(**valores_cuenta)
        .execution_options(synchronize_session=False)
    )
    actualizacion_subcuenta = db.execute(
        update(subcuentas)
        .where(
            subcuentas.id_subcuenta == subcuenta_id,
            subcuentas.id_cuenta == cuenta_id,
            subcuentas.estado == "ABIERTA",
            subcuentas.version == version_subcuenta,
        )
        .values(
            estado="PAGADA",
            id_metodo_pago=metodo_id,
            version=version_subcuenta + 1,
            whatsapp_cliente=whatsapp_subcuenta,
            whatsapp_estado_envio=(
                "PENDIENTE" if whatsapp_subcuenta else None
            ),
            whatsapp_en_confirmar=(
                subcuenta.whatsapp_en_confirmar
                if whatsapp_en_confirmar is None
                else bool(whatsapp_en_confirmar)
            ),
        )
        .execution_options(synchronize_session=False)
    )
    if actualizacion_cuenta.rowcount != 1 or actualizacion_subcuenta.rowcount != 1:
        db.rollback()
        raise CuentaModificadaError(
            "Otro cajero modificó la cuenta. Recárgala antes de cobrar."
        )

    try:
        asignaciones = (
            db.query(asignaciones_subcuenta, items_cuenta)
            .join(
                items_cuenta,
                asignaciones_subcuenta.id_item_cuenta == items_cuenta.id_item_cuenta,
            )
            .filter(asignaciones_subcuenta.id_subcuenta == subcuenta_id)
            .order_by(items_cuenta.agregado_en, items_cuenta.id_item_cuenta)
            .all()
        )
        proveedores = json.loads(cuenta.proveedores_json or "[]")
        proveedores_por_subcuenta = _prorratear_proveedores(
            proveedores,
            [
                fila.total
                for fila in db.query(subcuentas)
                .filter(subcuentas.id_cuenta == cuenta_id)
                .order_by(subcuentas.id_subcuenta)
                .all()
            ],
        )
        subcuentas_ordenadas = (
            db.query(subcuentas)
            .filter(subcuentas.id_cuenta == cuenta_id)
            .order_by(subcuentas.id_subcuenta)
            .all()
        )
        posicion = next(
            indice
            for indice, fila in enumerate(subcuentas_ordenadas)
            if fila.id_subcuenta == subcuenta_id
        )
        proveedores_pago = proveedores_por_subcuenta[posicion]

        if cuenta.modo_division == "ITEMS":
            carrito = [
                {
                    "id_producto": item.id_producto,
                    "id_inventario": item.id_inventario,
                    "nombre": item.nombre,
                    "precio": item.precio_unitario,
                    "cantidad": asignacion.cantidad,
                    "personalizacion": item.personalizacion,
                }
                for asignacion, item in asignaciones
            ]
            total_carrito = sum(
                item["precio"] * item["cantidad"] for item in carrito
            )
            if abs(total_carrito - subcuenta.total) > 1e-6:
                raise ValueError("Los productos asignados no coinciden con el total de la subcuenta.")
            venta = registrar_venta(
                db_session=db,
                carrito=carrito,
                metodo_id=metodo_id,
                usuario_actual=usuario_actual,
                caja_actual=caja_actual,
                proveedores_seleccionados=proveedores_pago,
                mesa_id=cuenta.id_mesa,
                commit=False,
                mesa_cuenta_abierta=True,
                whatsapp_cliente=whatsapp_subcuenta,
            )
        else:
            if not cuenta.inventario_descontado:
                items_cuenta_abierta = obtener_items_cuenta(db, cuenta_id)
                carrito_completo = [
                    {
                        "id_producto": item.id_producto,
                        "id_inventario": item.id_inventario,
                        "nombre": item.nombre,
                        "precio": item.precio_unitario,
                        "cantidad": item.cantidad,
                        "personalizacion": item.personalizacion,
                    }
                    for item in items_cuenta_abierta
                ]
                inventarios, cantidades = _cargar_inventario_venta(
                    db, carrito_completo
                )
                for inventario_id, cantidad in cantidades.items():
                    inventarios[inventario_id].cantidad -= cantidad
                cuenta.inventario_descontado = True

            proveedor_unico = (
                proveedores_pago[0]["id"]
                if len(proveedores_pago) == 1
                else None
            )
            nueva_venta = ventas(
                fecha_hora=fecha_pago,
                total=float(subcuenta.total),
                id_metodos_pagos=metodo_id,
                id_usuario=getattr(usuario_actual, "id_usuario", None),
                id_caja=caja_actual.id_caja,
                id_estado_ventas=1,
                id_proveedor=proveedor_unico,
                proveedores_texto=", ".join(
                    proveedor["nombre"] for proveedor in proveedores_pago
                )
                or None,
                costo_proveedor=float(subcuenta.costo_proveedor),
                id_mesa=cuenta.id_mesa,
                whatsapp_cliente=whatsapp_subcuenta,
                whatsapp_estado_envio=(
                    "PENDIENTE" if whatsapp_subcuenta else None
                ),
            )
            db.add(nueva_venta)
            db.flush()
            db.add(
                detalle_ventas(
                    cantidad=1,
                    precio_unitario=float(subcuenta.total),
                    subtotal=float(subcuenta.total),
                    nombre_producto=(
                        f"División igual {subcuenta.etiqueta} "
                        f"· Cuenta #{cuenta_id}"
                    ),
                    personalizacion="Pago por partes iguales",
                    id_venta=nueva_venta.id_venta,
                    id_producto=None,
                )
            )
            db.add(
                movimiento_caja(
                    fecha=fecha_pago,
                    tipo="INGRESO",
                    valor=float(subcuenta.total),
                    descripcion=f"Venta #{nueva_venta.id_venta}",
                    id_caja=caja_actual.id_caja,
                )
            )
            venta = nueva_venta

        mesa = db.get(mesas, cuenta.id_mesa) if cuenta.id_mesa is not None else None
        if otras_pendientes == 0 and mesa is not None:
            mesa.estado = ESTADO_MESA_LIBRE
        db.commit()
        db.refresh(venta)
        return venta, otras_pendientes == 0
    except Exception:
        db.rollback()
        raise

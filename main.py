import ssl
import certifi
import os
import datetime
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from sqlalchemy import func

os.environ["FLET_RENDERER"] = "software"
ssl._create_default_https_context = ssl.create_default_context
os.environ["SSL_CERT_FILE"] = certifi.where()

import flet as ft
from create_db import init_db
from database.database import SessionLocal
from database.models import (
    Usuario,
    caja,
    cuentas_abiertas,
    estados_caja,
    ventas,
    detalle_ventas,
    metodos_pago,
    informes,
    movimiento_caja,
    rol,
)
from views.login import login_view
from views.inicio import inicio_view
from views.venta import venta_view
from views.navbar import construir_navbar
from views.historial import historial_view
from views.menu import menu_view
from views.inventario import inventario_view
from views.proveedores import proveedores_view
from views.compras import compras_view
from views.informes import informes_view
from views.nueva_venta_view import nueva_venta_view
from views.cuentas_abiertas import cuentas_abiertas_view
from views.contabilidad import contabilidad_view
from views.usuarios import usuarios_view
from services.contabilidad_service import can_process_accounting, obtener_ultima_caja_cerrada, generar_cierre_contable
from services.retiros_caja_service import registrar_retiro

usuario_actual = {"valor": None}  # guardamos el usuario logueado aquí
SALDO_INICIAL_SUGERIDO = 2_000_000
UMBRAL_APERTURA_MULTIPLICADOR = float(
    os.environ.get("CAJA_APERTURA_MULTIPLICADOR", "5")
)


def parsear_valor_cop(valor):
    if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool):
        try:
            saldo = Decimal(str(valor))
        except InvalidOperation as error:
            raise ValueError("El saldo inicial debe ser numérico.") from error
        if not saldo.is_finite():
            raise ValueError("El saldo inicial debe ser numérico.")
        return float(saldo)

    texto = str(valor or "").strip().replace("$", "").replace(" ", "")
    if not texto:
        raise ValueError("El saldo inicial debe ser numérico.")

    if "," in texto:
        entero, decimal = texto.rsplit(",", 1)
        if decimal.isdigit() and len(decimal) <= 2:
            texto = f"{entero.replace('.', '').replace(',', '')}.{decimal}"
        else:
            texto = texto.replace(".", "").replace(",", "")
    else:
        texto = texto.replace(".", "")

    try:
        saldo = Decimal(texto)
    except InvalidOperation as error:
        raise ValueError("El saldo inicial debe ser numérico.") from error
    if not saldo.is_finite():
        raise ValueError("El saldo inicial debe ser numérico.")
    return float(saldo)


def advertencia_apertura(db, saldo_inicial):
    if saldo_inicial <= 0:
        return "El valor de apertura debe ser mayor que cero."

    promedio = (
        db.query(func.avg(caja.saldo_inicial))
        .filter(caja.saldo_inicial > 0)
        .scalar()
    )
    if (
        promedio
        and UMBRAL_APERTURA_MULTIPLICADOR > 0
        and saldo_inicial > float(promedio) * UMBRAL_APERTURA_MULTIPLICADOR
    ):
        return (
            "El valor supera "
            f"{UMBRAL_APERTURA_MULTIPLICADOR:g} veces el promedio histórico "
            f"de aperturas (${float(promedio):,.0f}".replace(",", ".")
            + ")."
        )
    return None


def calcular_saldo_final_caja(saldo_inicial, efectivo, egresos):
    return float(saldo_inicial or 0) + float(efectivo or 0) - float(egresos or 0)


def obtener_estado_caja(db, nombre):
    return db.query(estados_caja).filter(estados_caja.nombre == nombre).first()


def obtener_caja_abierta(db, usuario_id=None):
    estado_abierta = obtener_estado_caja(db, "ABIERTA")
    if not estado_abierta:
        return None

    query = db.query(caja).filter(caja.id_estado_caja == estado_abierta.id_estado_caja)
    if usuario_id is not None:
        query = query.filter(caja.id_usuario == usuario_id)
    return query.order_by(caja.fecha_apertura.desc()).first()


def abrir_caja(usuario, saldo_inicial, confirmar_inusual=False):
    if not usuario:
        return {"ok": False, "mensaje": "Debes iniciar sesión para abrir caja."}

    try:
        saldo_inicial = parsear_valor_cop(saldo_inicial)
    except ValueError:
        return {"ok": False, "mensaje": "El saldo inicial debe ser numérico."}

    db = SessionLocal()
    if obtener_caja_abierta(db, usuario.id_usuario):
        db.close()
        return {"ok": False, "mensaje": "Ya existe una caja abierta para este usuario."}

    estado_abierta = obtener_estado_caja(db, "ABIERTA")
    if not estado_abierta:
        db.close()
        return {"ok": False, "mensaje": "No existe el estado ABIERTA para caja."}

    advertencia = advertencia_apertura(db, saldo_inicial)
    if advertencia and not confirmar_inusual:
        valor_texto = f"${saldo_inicial:,.0f}".replace(",", ".")
        db.close()
        return {
            "ok": False,
            "requiere_confirmacion": True,
            "mensaje": f"El valor ingresado ({valor_texto}) es inusual. {advertencia} ¿Deseas continuar?",
        }

    caja_nueva = caja(
        fecha_apertura=datetime.datetime.now(),
        saldo_inicial=saldo_inicial,
        id_estado_caja=estado_abierta.id_estado_caja,
        id_usuario=usuario.id_usuario,
    )
    db.add(caja_nueva)
    db.commit()
    db.refresh(caja_nueva)
    db.close()
    return {"ok": True, "mensaje": "Caja abierta correctamente.", "caja": caja_nueva}


def cerrar_caja(usuario):
    if not usuario:
        return {"ok": False, "mensaje": "Debes iniciar sesión para cerrar caja."}

    db = SessionLocal()
    caja_actual = obtener_caja_abierta(db, usuario.id_usuario)
    if not caja_actual:
        db.close()
        return {"ok": False, "mensaje": "No hay una caja abierta para cerrar."}

    cuentas_pendientes = db.query(cuentas_abiertas).filter(
        cuentas_abiertas.estado == "ABIERTA"
    ).count()
    if cuentas_pendientes:
        db.close()
        return {
            "ok": False,
            "mensaje": (
                f"No se puede cerrar la caja: hay {cuentas_pendientes} "
                "cuenta(s) abierta(s). Cóbralas o anúlalas antes del cierre."
            ),
        }

    estado_cerrada = obtener_estado_caja(db, "CERRADA")
    if not estado_cerrada:
        db.close()
        return {"ok": False, "mensaje": "No existe el estado CERRADA para caja."}

    metodo_efectivo = db.query(metodos_pago).filter(metodos_pago.nombre == "EFECTIVO").first()
    metodo_tarjeta = db.query(metodos_pago).filter(metodos_pago.nombre == "TARJETA").first()
    metodo_nequi = db.query(metodos_pago).filter(metodos_pago.nombre == "NEQUI").first()

    def total_por_metodo(metodo):
        if not metodo:
            return 0
        return db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
            ventas.id_caja == caja_actual.id_caja,
            ventas.id_metodos_pagos == metodo.id_metodos_pago,
        ).scalar() or 0

    ventas_totales = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
    total_efectivo = total_por_metodo(metodo_efectivo)
    total_tarjeta = total_por_metodo(metodo_tarjeta)
    total_nequi = total_por_metodo(metodo_nequi)
    total_egresos = db.query(func.coalesce(func.sum(movimiento_caja.valor), 0)).filter(
        movimiento_caja.id_caja == caja_actual.id_caja,
        movimiento_caja.tipo.in_(("EGRESO", "GASTO", "CAJA_CHICA")),
    ).scalar() or 0
    total_proveedores = db.query(func.coalesce(func.sum(ventas.costo_proveedor), 0)).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
    productos_vendidos = db.query(func.coalesce(func.sum(detalle_ventas.cantidad), 0)).join(
        ventas, detalle_ventas.id_venta == ventas.id_venta
    ).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
    caja_actual.fecha_cierre = datetime.datetime.now()
    caja_actual.saldo_final = calcular_saldo_final_caja(
        caja_actual.saldo_inicial,
        total_efectivo,
        total_egresos,
    )
    caja_actual.id_estado_caja = estado_cerrada.id_estado_caja

    informe = informes(
        fecha=datetime.date.today(),
        ventas_totales=float(ventas_totales),
        productos_vendidos=int(productos_vendidos),
        clientes_atendidos=0,
        total_efectivo=float(total_efectivo),
        total_tarjeta=float(total_tarjeta),
        total_nequi=float(total_nequi),
        total_proveedores=float(total_proveedores),
        saldo_inicial=float(caja_actual.saldo_inicial),
        saldo_final=float(caja_actual.saldo_final),
        id_caja=caja_actual.id_caja,
        id_usuario=usuario.id_usuario,
    )
    db.add(informe)
    db.commit()
    db.refresh(caja_actual)
    db.refresh(informe)

    informe_data = {
        "id_informe": informe.id_informe,
        "fecha": informe.fecha,
        "ventas_totales": float(informe.ventas_totales),
        "productos_vendidos": int(informe.productos_vendidos),
        "total_efectivo": float(informe.total_efectivo),
        "total_tarjeta": float(informe.total_tarjeta),
        "total_nequi": float(informe.total_nequi),
        "total_proveedores": float(informe.total_proveedores),
        "saldo_inicial": float(informe.saldo_inicial),
        "saldo_final": float(informe.saldo_final),
        "id_caja": informe.id_caja,
        "id_usuario": informe.id_usuario,
    }

    try:
        cierre = generar_cierre_contable(caja_actual.id_caja)
        informe_data["cierre_contable_id"] = cierre.id_cierre
    except Exception:
        pass

    db.close()
    return {"ok": True, "mensaje": "Caja cerrada y reporte generado.", "informe": informe_data}


async def main(page: ft.Page):
    init_db()
    page.title = "BurgerLand - Sistema de Gestión"
    page.window_width = 1200
    page.window_height = 800
    page.bgcolor = "#2C2F3E"

    def navegar(vista):
        page.controls.clear()
        page.update()
        page.add(vista)
        page.update()

    def usuario_es_admin():
        usuario = usuario_actual["valor"]
        if not usuario:
            return False
        db = SessionLocal()
        try:
            usuario_db = db.get(Usuario, usuario.id_usuario)
            if usuario_db is None:
                return False
            usuario.id_rol = usuario_db.id_rol
            perfil = db.get(rol, usuario_db.id_rol)
            return bool(perfil and perfil.nombre == "ADMIN")
        finally:
            db.close()

    def get_navbar(activo):
        db = SessionLocal()
        try:
            estado_cerrada = obtener_estado_caja(db, "CERRADA")
            hay_cierre = bool(estado_cerrada and db.query(caja).filter(caja.id_estado_caja == estado_cerrada.id_estado_caja).count() > 0)
            contabilidad_habilitada = usuario_es_admin() or hay_cierre
        finally:
            db.close()
        return construir_navbar(
            page,
            activo=activo,
            mostrar_inicio=lambda: mostrar_inicio(),
            mostrar_venta=lambda: mostrar_venta(),
            mostrar_historial=lambda: mostrar_historial(),
            mostrar_menu=lambda: mostrar_menu(),
            mostrar_inventario=lambda: mostrar_inventario(),
            mostrar_proveedores=lambda: mostrar_proveedores(),
            mostrar_compras=lambda: mostrar_compras(),
            mostrar_informes=lambda: mostrar_informes(),
            compras_habilitadas=usuario_es_admin(),
            mostrar_contabilidad=lambda: mostrar_contabilidad(),
            contabilidad_habilitada=contabilidad_habilitada,
            mostrar_cuentas_abiertas=lambda: mostrar_cuentas_abiertas(),
            mostrar_usuarios=(
                (lambda: mostrar_gestion_usuarios())
                if usuario_es_admin()
                else None
            ),
        )

    def obtener_caja_para_contabilidad(usuario_id):
        """
        Determina la caja de referencia para Operatividad Contable:
        primero la caja abierta actual (para poder informar por qué está
        bloqueada), y si no existe, la última caja cerrada del usuario.
        """
        db = SessionLocal()
        caja_abierta = obtener_caja_abierta(db, usuario_id)
        db.close()
        if caja_abierta:
            return caja_abierta
        return obtener_ultima_caja_cerrada(usuario_id)

    def cargar_caja_actual():
        db = SessionLocal()
        caja_actual = obtener_caja_abierta(db, usuario_actual["valor"].id_usuario if usuario_actual["valor"] else None)
        db.close()
        return caja_actual

    def registrar_retiro_actual(monto, motivo):
        usuario = usuario_actual["valor"]
        if usuario is None:
            return {"ok": False, "mensaje": "Debes iniciar sesión para retirar dinero."}
        db = SessionLocal()
        try:
            caja_abierta = obtener_caja_abierta(db, usuario.id_usuario)
            if caja_abierta is None:
                return {"ok": False, "mensaje": "Debes tener una caja abierta."}
            registro = registrar_retiro(
                db,
                caja_abierta.id_caja,
                usuario.id_usuario,
                monto,
                motivo,
            )
            return {
                "ok": True,
                "mensaje": f"Retiro #{registro.id_retiro} registrado como pendiente de justificar.",
            }
        except ValueError as error:
            return {"ok": False, "mensaje": str(error)}
        finally:
            db.close()

    def mostrar_venta():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(venta_view(page, get_navbar("venta"), on_nueva_venta=mostrar_nueva_venta))

    def mostrar_nueva_venta(
        mesa_id=None,
        mesa_elegida=False,
        cuenta_id=None,
        tipo_pedido="MOSTRADOR",
    ):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(nueva_venta_view(
            page,
            get_navbar("venta"),
            usuario_actual=usuario_actual["valor"],
            on_venta_completada=mostrar_venta,
            caja_actual=cargar_caja_actual(),
            mesa_id=mesa_id,
            mesa_elegida=mesa_elegida,
            cuenta_id=cuenta_id,
            on_seleccionar_mesa=seleccionar_mesa_venta,
            on_cuenta_guardada=mostrar_cuentas_abiertas,
            on_recargar_cuenta=lambda id_cuenta: mostrar_nueva_venta(
                mesa_elegida=True,
                cuenta_id=id_cuenta,
            ),
            tipo_pedido=tipo_pedido,
            on_volver_a_mesas=(
                mostrar_cuentas_abiertas
                if cuenta_id is not None
                else lambda: mostrar_nueva_venta()
            ),
        ))

    def seleccionar_mesa_venta(mesa_id, cuenta_id=None, tipo_pedido="MOSTRADOR"):
        if cuenta_id is not None:
            mostrar_nueva_venta(mesa_elegida=True, cuenta_id=cuenta_id)
            return
        mostrar_nueva_venta(mesa_id, True, tipo_pedido=tipo_pedido)

    def mostrar_cuentas_abiertas():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(
            cuentas_abiertas_view(
                page,
                get_navbar("cuentas_abiertas"),
                on_abrir_cuenta=lambda id_cuenta: mostrar_nueva_venta(
                    mesa_elegida=True,
                    cuenta_id=id_cuenta,
                ),
            )
        )

    def mostrar_inicio(usuario=None):
        if usuario:
            usuario_actual["valor"] = usuario
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(inicio_view(
            page,
            get_navbar("inicio"),
            usuario_actual=usuario_actual["valor"],
            caja_actual=cargar_caja_actual(),
            on_abrir_caja=lambda saldo, confirmar_inusual=False: abrir_caja(
                usuario_actual["valor"],
                saldo,
                confirmar_inusual=confirmar_inusual,
            ),
            on_cerrar_caja=lambda: cerrar_caja(usuario_actual["valor"]),
            on_refrescar=mostrar_inicio,
            saldo_inicial_sugerido=SALDO_INICIAL_SUGERIDO,
            on_registrar_retiro=registrar_retiro_actual,
        ))

    def mostrar_menu(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(menu_view(page, get_navbar("menu"), usuario_actual=usuario_actual["valor"]))

    def mostrar_proveedores(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(proveedores_view(page, get_navbar("proveedores"), usuario_actual=usuario_actual["valor"]))

    def mostrar_compras(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(compras_view(page, get_navbar("compras"), usuario_actual=usuario_actual["valor"]))

    def mostrar_inventario(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(inventario_view(page, get_navbar("inventario"), usuario_actual=usuario_actual["valor"]))

    def mostrar_informes(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        db = SessionLocal()
        ultimo_informe = db.query(informes).order_by(informes.id_informe.desc()).first()
        caja_actual = obtener_caja_abierta(db, usuario_actual["valor"].id_usuario if usuario_actual["valor"] else None)
        if caja_actual:
            metodo_efectivo = db.query(metodos_pago).filter(metodos_pago.nombre == "EFECTIVO").first()
            metodo_tarjeta = db.query(metodos_pago).filter(metodos_pago.nombre == "TARJETA").first()
            metodo_nequi = db.query(metodos_pago).filter(metodos_pago.nombre == "NEQUI").first()

            def total_por_metodo(metodo):
                if not metodo:
                    return 0
                return db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
                    ventas.id_caja == caja_actual.id_caja,
                    ventas.id_metodos_pagos == metodo.id_metodos_pago,
                ).scalar() or 0

            ventas_totales = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
            total_efectivo = total_por_metodo(metodo_efectivo)
            total_tarjeta = total_por_metodo(metodo_tarjeta)
            total_nequi = total_por_metodo(metodo_nequi)
            total_egresos = db.query(func.coalesce(func.sum(movimiento_caja.valor), 0)).filter(
                movimiento_caja.id_caja == caja_actual.id_caja,
                movimiento_caja.tipo.in_(("EGRESO", "GASTO", "CAJA_CHICA")),
            ).scalar() or 0
            total_proveedores = db.query(func.coalesce(func.sum(ventas.costo_proveedor), 0)).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
            productos_vendidos = db.query(func.coalesce(func.sum(detalle_ventas.cantidad), 0)).join(
                ventas, detalle_ventas.id_venta == ventas.id_venta
            ).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
            clientes_atendidos = db.query(ventas).filter(ventas.id_caja == caja_actual.id_caja).count()
            ultimo_informe = SimpleNamespace(
                fecha=datetime.date.today(),
                ventas_totales=float(ventas_totales),
                productos_vendidos=int(productos_vendidos),
                clientes_atendidos=int(clientes_atendidos),
                total_efectivo=float(total_efectivo),
                total_tarjeta=float(total_tarjeta),
                total_nequi=float(total_nequi),
                total_proveedores=float(total_proveedores),
                saldo_inicial=float(caja_actual.saldo_inicial),
                saldo_final=calcular_saldo_final_caja(
                    caja_actual.saldo_inicial,
                    total_efectivo,
                    total_egresos,
                ),
                id_caja=caja_actual.id_caja,
                id_usuario=caja_actual.id_usuario,
            )
        db.close()
        navegar(informes_view(page, get_navbar("informes"), ultimo_informe=ultimo_informe))

    def mostrar_historial(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(
            historial_view(
                page,
                get_navbar("historial"),
                usuario_actual=usuario or usuario_actual["valor"],
            )
        )

    def mostrar_contabilidad(usuario=None):
        """
        Muestra la vista de Operatividad Contable.

        Se resuelve la caja de referencia (abierta o última cerrada) del
        usuario y se delega en la vista/servicio la validación real de
        si el procesamiento contable puede habilitarse. Si el usuario
        llega aquí con la caja abierta, la vista mostrará el mensaje
        informativo de bloqueo en lugar del formulario.
        """
        if not usuario_es_admin():
            return mostrar_inicio()
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        usuario_id = usuario_actual["valor"].id_usuario if usuario_actual["valor"] else None
        caja_referencia = obtener_caja_para_contabilidad(usuario_id)
        navegar(contabilidad_view(
            page,
            get_navbar("contabilidad"),
            usuario_actual=usuario_actual["valor"],
            caja_actual=caja_referencia,
        ))

    def mostrar_gestion_usuarios(usuario=None):
        if not usuario_es_admin():
            return mostrar_inicio()
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(
            usuarios_view(
                page,
                get_navbar("usuarios"),
                usuario_actual=usuario_actual["valor"],
            )
        )

    def mostrar_login():
        page.horizontal_alignment = "center"
        page.vertical_alignment = "center"
        page.padding = 0
        navegar(login_view(page, on_login_success=mostrar_inicio))

    mostrar_login()

if __name__ == "__main__":
    ft.run(main)
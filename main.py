import ssl
import certifi
import os
import datetime
from sqlalchemy import func

os.environ["FLET_RENDERER"] = "software"
ssl._create_default_https_context = ssl.create_default_context
os.environ["SSL_CERT_FILE"] = certifi.where()

import flet as ft
from create_db import init_db
from database.database import SessionLocal
from database.models import caja, estados_caja, ventas, detalle_ventas, metodos_pago, informes
from views.login import login_view
from views.inicio import inicio_view
from views.venta import venta_view
from views.navbar import construir_navbar
from views.historial import historial_view
from views.menu import menu_view
from views.inventario import inventario_view
from views.informes import informes_view
from views.nueva_venta_view import nueva_venta_view

usuario_actual = {"valor": None}  # guardamos el usuario logueado aquí


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


def abrir_caja(usuario, saldo_inicial):
    if not usuario:
        return {"ok": False, "mensaje": "Debes iniciar sesión para abrir caja."}

    db = SessionLocal()
    if obtener_caja_abierta(db, usuario.id_usuario):
        db.close()
        return {"ok": False, "mensaje": "Ya existe una caja abierta para este usuario."}

    estado_abierta = obtener_estado_caja(db, "ABIERTA")
    if not estado_abierta:
        db.close()
        return {"ok": False, "mensaje": "No existe el estado ABIERTA para caja."}

    try:
        saldo_inicial = float(saldo_inicial)
    except (TypeError, ValueError):
        db.close()
        return {"ok": False, "mensaje": "El saldo inicial debe ser numérico."}

    if saldo_inicial < 0:
        db.close()
        return {"ok": False, "mensaje": "El saldo inicial no puede ser negativo."}

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

    estado_cerrada = obtener_estado_caja(db, "CERRADA")
    if not estado_cerrada:
        db.close()
        return {"ok": False, "mensaje": "No existe el estado CERRADA para caja."}

    metodo_efectivo = db.query(metodos_pago).filter(metodos_pago.nombre == "EFECTIVO").first()
    metodo_tarjeta = db.query(metodos_pago).filter(metodos_pago.nombre == "TARJETA").first()
    metodo_nequi = db.query(metodos_pago).filter(metodos_pago.nombre == "NEQUI").first()

    ventas_totales = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
    total_efectivo = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
        ventas.id_caja == caja_actual.id_caja,
        ventas.id_metodos_pagos == metodo_efectivo.id_metodos_pago if metodo_efectivo else None,
    ).scalar() or 0
    total_tarjeta = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
        ventas.id_caja == caja_actual.id_caja,
        ventas.id_metodos_pagos == metodo_tarjeta.id_metodos_pago if metodo_tarjeta else None,
    ).scalar() or 0
    total_nequi = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
        ventas.id_caja == caja_actual.id_caja,
        ventas.id_metodos_pagos == metodo_nequi.id_metodos_pago if metodo_nequi else None,
    ).scalar() or 0
    productos_vendidos = db.query(func.coalesce(func.sum(detalle_ventas.cantidad), 0)).join(
        ventas, detalle_ventas.id_venta == ventas.id_venta
    ).filter(ventas.id_caja == caja_actual.id_caja).scalar() or 0
    clientes_atendidos = db.query(ventas).filter(ventas.id_caja == caja_actual.id_caja).count()

    caja_actual.fecha_cierre = datetime.datetime.now()
    caja_actual.saldo_final = caja_actual.saldo_inicial + total_efectivo
    caja_actual.id_estado_caja = estado_cerrada.id_estado_caja

    informe = informes(
        fecha=datetime.date.today(),
        ventas_totales=float(ventas_totales),
        productos_vendidos=int(productos_vendidos),
        clientes_atendidos=int(clientes_atendidos),
        total_efectivo=float(total_efectivo),
        total_tarjeta=float(total_tarjeta),
        total_nequi=float(total_nequi),
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
        "clientes_atendidos": int(informe.clientes_atendidos),
        "total_efectivo": float(informe.total_efectivo),
        "total_tarjeta": float(informe.total_tarjeta),
        "total_nequi": float(informe.total_nequi),
        "saldo_inicial": float(informe.saldo_inicial),
        "saldo_final": float(informe.saldo_final),
        "id_caja": informe.id_caja,
        "id_usuario": informe.id_usuario,
    }

    db.close()
    return {"ok": True, "mensaje": "Caja cerrada y reporte generado.", "informe": informe_data}


async def main(page: ft.Page):
    init_db()
    page.title = "Burgerland"
    page.window_width = 1200
    page.window_height = 800
    page.bgcolor = "#2C2F3E"

    def navegar(vista):
        page.controls.clear()
        page.update()
        page.add(vista)
        page.update()

    def get_navbar(activo):
        return construir_navbar(
            page,
            activo=activo,
            mostrar_inicio=lambda: mostrar_inicio(),
            mostrar_venta=lambda: mostrar_venta(),
            mostrar_historial=lambda: mostrar_historial(),
            mostrar_menu=lambda: mostrar_menu(),
            mostrar_inventario=lambda: mostrar_inventario(),
            mostrar_informes=lambda: mostrar_informes(),
        )

    def cargar_caja_actual():
        db = SessionLocal()
        caja_actual = obtener_caja_abierta(db, usuario_actual["valor"].id_usuario if usuario_actual["valor"] else None)
        db.close()
        return caja_actual

    def mostrar_venta():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(venta_view(page, get_navbar("venta"), on_nueva_venta=mostrar_nueva_venta))

    def mostrar_nueva_venta():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(nueva_venta_view(
            page,
            get_navbar("venta"),
            usuario_actual=usuario_actual["valor"],
            on_venta_completada=mostrar_venta,
            caja_actual=cargar_caja_actual(),
        ))

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
            on_abrir_caja=lambda saldo: abrir_caja(usuario_actual["valor"], saldo),
            on_cerrar_caja=lambda: cerrar_caja(usuario_actual["valor"]),
            on_refrescar=mostrar_inicio,
        ))

    def mostrar_menu(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(menu_view(page, get_navbar("menu")))

    def mostrar_inventario(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(inventario_view(page, get_navbar("inventario")))

    def mostrar_informes(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        db = SessionLocal()
        ultimo_informe = db.query(informes).order_by(informes.id_informe.desc()).first()
        db.close()
        navegar(informes_view(page, get_navbar("informes"), ultimo_informe=ultimo_informe))

    def mostrar_historial(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(historial_view(page, get_navbar("historial")))

    def mostrar_login():
        page.horizontal_alignment = "center"
        page.vertical_alignment = "center"
        page.padding = 0
        navegar(login_view(page, on_login_success=mostrar_inicio))

    mostrar_login()

if __name__ == "__main__":
    ft.run(main)
import datetime

import flet as ft

from database.database import SessionLocal
from database.models import ventas, detalle_ventas, productos, metodos_pago, Usuario


def obtener_productos_texto(db, id_venta):
    detalles = db.query(detalle_ventas).filter(detalle_ventas.id_venta == id_venta).all()
    partes = []
    for d in detalles:
        prod = db.query(productos).filter(productos.id_producto == d.id_producto).first()
        nombre = prod.nombre if prod else "Producto eliminado"
        partes.append(f"{nombre} x{d.cantidad}")
    return ", ".join(partes) if partes else "-"


def _badge(texto, color):
    return ft.Container(
        padding=ft.Padding(left=10, right=10, top=4, bottom=4),
        border_radius=999,
        bgcolor=color,
        content=ft.Text(texto, color="white", size=12, weight="bold"),
    )


def _crear_tarjeta_venta(db, venta):
    metodo = db.query(metodos_pago).filter(metodos_pago.id_metodos_pago == venta.id_metodos_pagos).first()
    usuario = db.query(Usuario).filter(Usuario.id_usuario == venta.id_usuario).first()
    productos_texto = obtener_productos_texto(db, venta.id_venta)

    return ft.Container(
        border_radius=16,
        padding=16,
        bgcolor="#2E3344",
        border=ft.Border(
            left=ft.BorderSide(1, "#5A5F72"),
            right=ft.BorderSide(1, "#5A5F72"),
            top=ft.BorderSide(1, "#5A5F72"),
            bottom=ft.BorderSide(1, "#5A5F72"),
        ),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(
                                    venta.fecha_hora.strftime("%d/%m/%Y"),
                                    color="white",
                                    size=13,
                                    weight="bold",
                                ),
                                ft.Text(
                                    venta.fecha_hora.strftime("%H:%M"),
                                    color="#C9CEDB",
                                    size=12,
                                ),
                            ],
                        ),
                        _badge(f"${venta.total:,.0f}".replace(",", "."), "#F2C744"),
                    ],
                ),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        _badge(usuario.nombre if usuario else "Sin usuario", "#5A5F72"),
                        _badge(metodo.nombre if metodo else "Sin pago", "#7ABAFB"),
                    ],
                ),
                ft.Text(
                    productos_texto,
                    color="#E3E7F1",
                    size=13,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
        ),
    )


def _crear_lista_ventas(ventas_lista, db):
    if not ventas_lista:
        return ft.Container(
            padding=20,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("No hay registros para mostrar.", color="white"),
        )

    return ft.Column(
        spacing=12,
        scroll="auto",
        controls=[_crear_tarjeta_venta(db, venta) for venta in ventas_lista],
    )


def historial_view(page: ft.Page, navbar):
    db = SessionLocal()
    hoy = datetime.date.today()
    todas_ventas = db.query(ventas).order_by(ventas.fecha_hora.desc()).all()
    ventas_hoy = [v for v in todas_ventas if v.fecha_hora.date() == hoy]
    ventas_historicas = [v for v in todas_ventas if v.fecha_hora.date() != hoy]

    total_hoy = sum(v.total for v in ventas_hoy)
    total_historicas = sum(v.total for v in ventas_historicas)

    bloque_hoy = _crear_lista_ventas(ventas_hoy, db)
    bloque_historicas = _crear_lista_ventas(ventas_historicas, db)
    db.close()

    panel_hoy = ft.Container(
        bgcolor="#2E3344",
        border_radius=18,
        padding=20,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("Ventas del día", size=20, weight="bold", color="#F2C744"),
                        _badge(f"Total: ${total_hoy:,.0f}".replace(",", "."), "#7AE582"),
                    ],
                ),
                ft.Container(
                    height=300,
                    content=bloque_hoy,
                ),
            ],
        ),
    )

    mostrar_historico = {"valor": False}

    def alternar_historico(e):
        mostrar_historico["valor"] = not mostrar_historico["valor"]
        panel_historico.visible = mostrar_historico["valor"]
        btn_historico.text = "Ocultar historial histórico" if mostrar_historico["valor"] else "Ver historial histórico"
        page.update()

    panel_historico = ft.Container(
        visible=False,
        bgcolor="#2E3344",
        border_radius=18,
        padding=20,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("Ventas históricas", size=20, weight="bold", color="#7AE582"),
                        _badge(f"Total: ${total_historicas:,.0f}".replace(",", "."), "#7ABAFB"),
                    ],
                ),
                ft.Container(
                    height=300,
                    content=bloque_historicas,
                ),
            ],
        ),
    )

    btn_historico = ft.ElevatedButton(
        "Ver historial histórico",
        on_click=alternar_historico,
        bgcolor="#3A3F52",
        color="white",
    )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=30,
        content=ft.Column(
            expand=True,
            spacing=20,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("HISTORIAL DE VENTAS", size=22, weight="bold", color="white"),
                        _badge("Registros ordenados", "#5A5F72"),
                    ],
                ),
                panel_hoy,
                btn_historico,
                panel_historico,
            ],
        ),
    )

    return ft.Column(expand=True, spacing=20, scroll="auto", controls=[navbar, tarjeta])

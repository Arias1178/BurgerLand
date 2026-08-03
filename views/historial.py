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


def _crear_tabla_ventas(ventas_lista, db):
    filas = []
    for v in ventas_lista:
        metodo = db.query(metodos_pago).filter(metodos_pago.id_metodos_pago == v.id_metodos_pagos).first()
        nombre_metodo = metodo.nombre if metodo else "-"

        usuario = db.query(Usuario).filter(Usuario.id_usuario == v.id_usuario).first()
        nombre_usuario = usuario.nombre if usuario else "-"

        productos_texto = obtener_productos_texto(db, v.id_venta)

        filas.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(v.fecha_hora.strftime("%d/%m/%Y"), color="white")),
                ft.DataCell(ft.Text(v.fecha_hora.strftime("%H:%M"), color="white")),
                ft.DataCell(ft.Text(nombre_usuario, color="white")),
                ft.DataCell(ft.Text(f"${v.total:,.0f}".replace(",", "."), color="white")),
                ft.DataCell(ft.Text(nombre_metodo, color="white")),
                ft.DataCell(ft.Text(productos_texto, color="white")),
            ])
        )

    if not filas:
        return ft.Text("No hay ventas registradas.", color="white")

    tabla = ft.DataTable(
        border_radius=10,
        column_spacing=28,
        columns=[
            ft.DataColumn(ft.Text("Fecha", color="white", weight="bold")),
            ft.DataColumn(ft.Text("Hora", color="white", weight="bold")),
            ft.DataColumn(ft.Text("Usuario", color="white", weight="bold")),
            ft.DataColumn(ft.Text("Total", color="white", weight="bold")),
            ft.DataColumn(ft.Text("Pago", color="white", weight="bold")),
            ft.DataColumn(ft.Text("Productos", color="white", weight="bold")),
        ],
        rows=filas,
    )
    return ft.Column(expand=True, scroll="auto", controls=[tabla])


def historial_view(page: ft.Page, navbar):
    db = SessionLocal()
    hoy = datetime.date.today()
    todas_ventas = db.query(ventas).order_by(ventas.fecha_hora.desc()).all()
    ventas_hoy = [v for v in todas_ventas if v.fecha_hora.date() == hoy]
    ventas_historicas = [v for v in todas_ventas if v.fecha_hora.date() != hoy]

    bloque_hoy = _crear_tabla_ventas(ventas_hoy, db)
    bloque_historicas = _crear_tabla_ventas(ventas_historicas, db)

    total_hoy = sum(v.total for v in ventas_hoy)
    total_historicas = sum(v.total for v in ventas_historicas)

    db.close()

    panel_hoy = ft.Container(
        bgcolor="#2E3344",
        border_radius=18,
        padding=20,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("Ventas del día", size=20, weight="bold", color="#F2C744"),
                ft.Text(f"Total: ${total_hoy:,.0f}".replace(",", "."), size=16, color="white", weight="bold"),
                ft.Container(
                    height=260,
                    content=ft.Column(scroll="auto", expand=True, controls=[bloque_hoy]),
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
            spacing=8,
            controls=[
                ft.Text("Ventas históricas", size=20, weight="bold", color="#7AE582"),
                ft.Text(f"Total: ${total_historicas:,.0f}".replace(",", "."), size=16, color="white", weight="bold"),
                ft.Container(
                    height=260,
                    content=ft.Column(scroll="auto", expand=True, controls=[bloque_historicas]),
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
            controls=[
                ft.Text("HISTORIAL DE VENTAS", size=22, weight="bold", color="white"),
                panel_hoy,
                btn_historico,
                panel_historico,
            ],
        ),
    )

    return ft.Column(expand=True, spacing=20, controls=[navbar, tarjeta])

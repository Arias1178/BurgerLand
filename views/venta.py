import flet as ft
import datetime
from database.database import SessionLocal
from database.models import ventas, detalle_ventas, productos, metodos_pago

def obtener_productos_texto(db, id_venta):
    detalles = db.query(detalle_ventas).filter(detalle_ventas.id_venta == id_venta).all()
    partes = []
    for d in detalles:
        prod = db.query(productos).filter(productos.id_producto == d.id_producto).first()
        nombre = prod.nombre if prod else "Producto eliminado"
        partes.append(f"{nombre} x{d.cantidad}")
    return ", ".join(partes) if partes else "-"

def venta_view(page: ft.Page, navbar, on_nueva_venta):
    db = SessionLocal()

    hoy = datetime.date.today()
    todas_ventas = db.query(ventas).order_by(ventas.fecha_hora.desc()).all()
    ventas_hoy = [v for v in todas_ventas if v.fecha_hora.date() == hoy]
    total_dia = sum(v.total for v in ventas_hoy)
    cantidad_pedidos = len(ventas_hoy)

    filas = []
    for v in ventas_hoy:
        metodo = db.query(metodos_pago).filter(
            metodos_pago.id_metodos_pago == v.id_metodos_pagos
        ).first()
        nombre_metodo = metodo.nombre if metodo else "-"
        productos_texto = obtener_productos_texto(db, v.id_venta)

        filas.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(v.fecha_hora.strftime("%H:%M"), color="white", size=12)),
                ft.DataCell(ft.Text(f"${v.total:,.0f}".replace(",", "."), color="#F2C744", weight="bold")),
                ft.DataCell(ft.Text(nombre_metodo, color="white", size=12)),
                ft.DataCell(ft.Text(productos_texto, color="white", size=12)),
            ])
        )

    db.close()

    tarjetas_resumen = [
        ft.Container(
            width=220,
            bgcolor="#2E3344",
            border_radius=16,
            padding=18,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Ventas hoy", size=12, color="#B9C0D0"),
                    ft.Text(str(cantidad_pedidos), size=26, weight="bold", color="white"),
                ]
            ),
        ),
        ft.Container(
            width=220,
            bgcolor="#2E3344",
            border_radius=16,
            padding=18,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Total recaudado", size=12, color="#B9C0D0"),
                    ft.Text(f"${total_dia:,.0f}".replace(",", "."), size=25, weight="bold", color="#F2C744"),
                ]
            ),
        ),
        ft.Container(
            width=220,
            bgcolor="#2E3344",
            border_radius=16,
            padding=18,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Promedio", size=12, color="#B9C0D0"),
                    ft.Text(
                        f"${(total_dia / cantidad_pedidos) if cantidad_pedidos else 0:,.0f}".replace(",", "."),
                        size=25,
                        weight="bold",
                        color="#7AE582",
                    ),
                ]
            ),
        ),
    ]

    if filas:
        tabla = ft.DataTable(
            border_radius=10,
            column_spacing=30,
            columns=[
                ft.DataColumn(ft.Text("Hora", color="white", weight="bold", size=13)),
                ft.DataColumn(ft.Text("Total", color="white", weight="bold", size=13)),
                ft.DataColumn(ft.Text("Pago", color="white", weight="bold", size=13)),
                ft.DataColumn(ft.Text("Productos", color="white", weight="bold", size=13)),
            ],
            rows=filas,
            heading_row_color="#1C1F2B",
            data_row_max_height=50,
        )
        contenido_tabla = ft.Container(
            expand=True,
            bgcolor="#1E2430",
            border_radius=16,
            padding=10,
            content=ft.Column(scroll="auto", expand=True, controls=[tabla]),
        )
    else:
        contenido_tabla = ft.Container(
            bgcolor="#1E2430",
            border_radius=16,
            padding=30,
            content=ft.Text("No hay ventas registradas hoy.", color="#D8DDEB", size=16),
        )

    btn_nueva_venta = ft.Button(
        content=ft.Text("Nueva venta", color="#111111", weight="bold", size=15),
        bgcolor="#F2C744",
        width=180,
        height=48,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
        on_click=lambda e: on_nueva_venta(),
    )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=22,
        padding=25,
        content=ft.Column(
            expand=True,
            spacing=18,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    vertical_alignment="center",
                    controls=[
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text("Ventas", size=28, weight="bold", color="white"),
                                ft.Text(f"{hoy.strftime('%d/%m/%Y')}", size=13, color="#B9C0D0"),
                            ],
                        ),
                        ft.Container(
                            bgcolor="#2E3344",
                            border_radius=12,
                            padding=10,
                            content=ft.Text(
                                f"Total del día: ${total_dia:,.0f}".replace(",", "."),
                                size=16,
                                weight="bold",
                                color="#F2C744",
                            ),
                        ),
                    ],
                ),
                ft.Row(wrap=True, spacing=16, run_spacing=16, controls=tarjetas_resumen),
                ft.Container(
                    expand=True,
                    content=contenido_tabla,
                ),
                ft.Row(alignment="end", controls=[btn_nueva_venta]),
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta],
    )
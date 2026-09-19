import datetime

import flet as ft
from sqlalchemy import func

from database.database import SessionLocal
from database.models import detalle_ventas, metodos_pago, productos, ventas


def obtener_productos_texto(db, id_venta):
    venta = db.query(ventas).filter(ventas.id_venta == id_venta).first()
    detalles = db.query(detalle_ventas).filter(detalle_ventas.id_venta == id_venta).all()
    partes = []
    for d in detalles:
        prod = db.query(productos).filter(productos.id_producto == d.id_producto).first()
        nombre = prod.nombre if prod else "Producto eliminado"
        partes.append(f"{nombre} x{d.cantidad}")
    if partes:
        return ", ".join(partes)
    if venta and venta.proveedores_texto:
        return f"Proveedores: {venta.proveedores_texto}"
    return "-"


def venta_view(page: ft.Page, navbar, on_nueva_venta):
    db = SessionLocal()

    hoy = datetime.date.today()
    todas_ventas = db.query(ventas).order_by(ventas.fecha_hora.desc()).all()
    ventas_hoy = [v for v in todas_ventas if v.fecha_hora.date() == hoy]
    total_dia = sum(v.total for v in ventas_hoy)
    cantidad_pedidos = len(ventas_hoy)

    conteo_productos = db.query(
        productos.nombre,
        func.coalesce(func.sum(detalle_ventas.cantidad), 0).label("vendidas"),
    ).outerjoin(
        detalle_ventas, productos.id_producto == detalle_ventas.id_producto
    ).group_by(
        productos.id_producto
    ).all()

    productos_vendidos = sorted(
        [{"nombre": nombre, "vendidas": int(vendidas)} for nombre, vendidas in conteo_productos],
        key=lambda item: (-item["vendidas"], item["nombre"].lower()),
    )
    max_vendidos = max([item["vendidas"] for item in productos_vendidos], default=0)

    def _barra_producto(item, color):
        porcentaje = (item["vendidas"] / max_vendidos) if max_vendidos else 0
        return ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Container(
                            expand=True,
                            content=ft.Text(item["nombre"], color="white", size=12, no_wrap=True),
                        ),
                        ft.Text(str(item["vendidas"]), color=color, size=12, weight="bold"),
                    ],
                ),
                ft.ProgressBar(value=porcentaje, color=color, bgcolor="#3A3F52", height=10),
            ],
        )

    def _columna_productos(titulo, color_titulo, color_barra, items):
        controles = [ft.Text(titulo, color=color_titulo, weight="bold")]
        if items:
            controles.extend([_barra_producto(item, color_barra) for item in items])
        else:
            controles.append(ft.Text("Sin datos", color="white"))
        return ft.Container(
            expand=True,
            content=ft.Column(spacing=10, controls=controles),
        )

    productos_top = productos_vendidos[:5]
    productos_bottom = sorted(productos_vendidos, key=lambda item: (item["vendidas"], item["nombre"].lower()))[:5]

    conteo_productos_hoy = db.query(
        productos.nombre,
        func.coalesce(func.sum(detalle_ventas.cantidad), 0).label("vendidas"),
    ).join(
        detalle_ventas, productos.id_producto == detalle_ventas.id_producto
    ).join(
        ventas, detalle_ventas.id_venta == ventas.id_venta
    ).filter(
        func.date(ventas.fecha_hora) == hoy.isoformat()
    ).group_by(
        productos.id_producto
    ).all()

    productos_hoy_vendidos = sorted(
        [{"nombre": nombre, "vendidas": int(vendidas)} for nombre, vendidas in conteo_productos_hoy],
        key=lambda item: (-item["vendidas"], item["nombre"].lower()),
    )
    productos_hoy_top = productos_hoy_vendidos[:5]
    productos_hoy_bottom = sorted(
        productos_hoy_vendidos,
        key=lambda item: (item["vendidas"], item["nombre"].lower()),
    )[:5]

    filas = []
    for v in ventas_hoy:
        metodo = db.query(metodos_pago).filter(
            metodos_pago.id_metodos_pago == v.id_metodos_pagos
        ).first()
        nombre_metodo = metodo.nombre if metodo else "-"
        productos_texto = obtener_productos_texto(db, v.id_venta)

        filas.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(v.fecha_hora.strftime("%H:%M"), color="white", size=12)),
                    ft.DataCell(ft.Text(f"${v.total:,.0f}".replace(",", "."), color="#F2C744", weight="bold")),
                    ft.DataCell(ft.Text(nombre_metodo, color="white", size=12)),
                    ft.DataCell(ft.Text(productos_texto, color="white", size=12)),
                    ft.DataCell(ft.Text(f"${v.costo_proveedor:,.0f}".replace(",", "."), color="#F2C744", size=12, weight="bold")),
                ]
            )
        )

    db.close()

    tarjetas_resumen = [
        ft.Container(
            width=205,
            bgcolor="#2E3344",
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Text("Ventas hoy", size=11, color="#B9C0D0"),
                    ft.Text(str(cantidad_pedidos), size=24, weight="bold", color="white"),
                ],
            ),
        ),
        ft.Container(
            width=205,
            bgcolor="#2E3344",
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Text("Total recaudado", size=11, color="#B9C0D0"),
                    ft.Text(f"${total_dia:,.0f}".replace(",", "."), size=23, weight="bold", color="#F2C744"),
                ],
            ),
        ),
        ft.Container(
            width=205,
            bgcolor="#2E3344",
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Text("Promedio", size=11, color="#B9C0D0"),
                    ft.Text(
                        f"${(total_dia / cantidad_pedidos) if cantidad_pedidos else 0:,.0f}".replace(",", "."),
                        size=23,
                        weight="bold",
                        color="#7AE582",
                    ),
                ],
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
                ft.DataColumn(ft.Text("Proveedores", color="white", weight="bold", size=13)),
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

    panel_grafica = ft.Container(
        expand=True,
        bgcolor="#2E3344",
        border_radius=16,
        padding=12,
        height=205,
        content=ft.Column(
            expand=True,
            spacing=10,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("Productos vendidos", size=15, weight="bold", color="white"),
                        ft.Text("Ventas acumuladas", size=12, color="#B9C0D0"),
                    ],
                ),
                _columna_productos("Más vendidos", "#F2C744", "#7AE582", productos_top),
                _columna_productos("Menos vendidos", "#7ABAFB", "#FFB86C", productos_bottom),
            ],
        ),
    )

    panel_grafica_hoy = ft.Container(
        expand=True,
        bgcolor="#2E3344",
        border_radius=16,
        padding=12,
        height=205,
        content=ft.Column(
            expand=True,
            spacing=10,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("Productos del día", size=15, weight="bold", color="white"),
                        ft.Text("Solo hoy", size=12, color="#B9C0D0"),
                    ],
                ),
                _columna_productos("Más vendidos hoy", "#F2C744", "#7AE582", productos_hoy_top),
                _columna_productos("Menos vendidos hoy", "#7ABAFB", "#FFB86C", productos_hoy_bottom),
            ],
        ),
    )

    panel_derecho = ft.Column(
        expand=True,
        spacing=12,
        scroll="auto",
        controls=[panel_grafica, panel_grafica_hoy],
    )

    panel_izquierdo = ft.Column(
        expand=True,
        spacing=12,
        scroll="auto",
        controls=[
            ft.Row(wrap=True, spacing=10, run_spacing=10, controls=tarjetas_resumen),
            ft.Container(height=210, content=contenido_tabla),
        ],
    )

    panel_boton = ft.Container(
        width=190,
        height=56,
        alignment=ft.Alignment(-1, 0),
        content=btn_nueva_venta,
    )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=22,
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=12,
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
                ft.Row(
                    expand=True,
                    spacing=12,
                    controls=[
                        panel_izquierdo,
                        panel_derecho,
                    ],
                ),
                ft.Row(
                    controls=[
                        panel_boton,
                    ],
                ),
            ],
        ),
    )

    return ft.Column(expand=True, spacing=20, scroll="auto", controls=[navbar, tarjeta])

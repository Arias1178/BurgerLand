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

def historial_view(page: ft.Page, navbar):
    db = SessionLocal()

    todas_ventas = db.query(ventas).order_by(ventas.fecha_hora.desc()).all()

    filas = []
    for v in todas_ventas:
        metodo = db.query(metodos_pago).filter(
            metodos_pago.id_metodos_pago == v.id_metodos_pagos
        ).first()
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

    db.close()

    if filas:
        total_general = sum(v.total for v in todas_ventas)
        tabla = ft.DataTable(
            border_radius=10,
            column_spacing=30,
            columns=[
                ft.DataColumn(ft.Text("Fecha", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Hora", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Usuario", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Total", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Pago", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Productos", color="white", weight="bold")),
            ],
            rows=filas
        )
        contenido_tabla = ft.Column(expand=True, scroll="auto", controls=[tabla])
        resumen = ft.Text(
            f"Total histórico: ${total_general:,.0f}".replace(",", "."),
            size=16, weight="bold", color="#F2C744"
        )
    else:
        contenido_tabla = ft.Text("No hay ventas registradas todavía.", color="white")
        resumen = ft.Text("")

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=30,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Text("HISTORIAL DE VENTAS", size=22, weight="bold", color="white"),
                ft.Container(expand=True, content=contenido_tabla),
                resumen
            ]
        )
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta]
    )
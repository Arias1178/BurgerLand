import ssl
import certifi
import os
os.environ["FLET_RENDERER"] = "software"

# Solución para certificados SSL de Flet
ssl._create_default_https_context = ssl.create_default_context
os.environ["SSL_CERT_FILE"] = certifi.where()

import flet as ft
from database.database import SessionLocal
from database.models import ventas, metodos_pago, detalle_ventas, productos

# Punto principal de la aplicación: aquí se construye la interfaz y se define la navegación entre pantallas.
async def main(page: ft.Page):
    page.title = "Sistema de Créditos y Cobranza"
    page.window_width = 1200
    page.window_height = 800

    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"
    page.bgcolor = "#FFFFFFFF"

    # INTERFAZ
    txt_username = ft.TextField(
        label="Escribe tu Usuario aquí",
        width=300,
        color="black"
    )

    txt_password = ft.TextField(
        label="Escribe tu Contraseña aquí",
        password=True,
        width=300,
        color="black"
    )

    lbl_error = ft.Text(
        value="", 
        color="red", 
        weight="bold"
    )

    # Muestra la pantalla de inicio de sesión con los campos para usuario y contraseña.
    def show_login_page():
        page.title = "Sistema de Créditos y Cobranza"
        page.controls.clear()
        page.add(
            ft.Text("INGRESO AL SISTEMA", size=24, weight="bold", color="blue"),
            txt_username,
            txt_password,
            lbl_error,
            ft.ElevatedButton(
                "Iniciar Sesión",
                width=300,
                bgcolor="blue",
                color="white",
                on_click=btn_login_click
            )
        )
        page.update()

    # Consulta las ventas registradas en la base de datos y arma un resumen con el método de pago y los productos.
    def get_sales_data():
        sales = {}
        db = SessionLocal()
        try:
            sales_query = db.query(
                ventas,
                metodos_pago.nombre.label("pago")
            ).join(
                metodos_pago,
                ventas.id_metodos_pagos == metodos_pago.id_metodos_pago
            )

            for sale, pago in sales_query.all():
                sales[sale.id_venta] = {
                    "hora": sale.fecha_hora.strftime("%H:%M") if sale.fecha_hora else "",
                    "total": f"${sale.total:,.2f}",
                    "pago": pago,
                    "productos": []
                }

            if sales:
                details_query = db.query(
                    detalle_ventas,
                    productos.nombre.label("producto")
                ).join(
                    productos,
                    detalle_ventas.id_producto == productos.id_producto
                ).filter(detalle_ventas.id_venta.in_(sales.keys()))

                for detail, producto in details_query.all():
                    sales[detail.id_venta]["productos"].append(producto)

                for sale_id, value in sales.items():
                    value["productos"] = " + ".join(value["productos"]) if value["productos"] else ""

            return list(sales.values())
        finally:
            db.close()

    # Muestra la pantalla de ventas con una tabla que resume las operaciones realizadas.
    def show_sales_page():
        page.title = "Ventas - Burguer Land"
        page.controls.clear()

        sales_data = get_sales_data()

        if not sales_data:
            page.add(
                ft.Column(
                    horizontal_alignment="center",
                    spacing=20,
                    controls=[
                        ft.Text("Ventas", size=28, weight="bold", color="white"),
                        ft.Text("No hay ventas registradas.", size=16, color="white70"),
                        ft.ElevatedButton("Volver", width=200, on_click=lambda e: show_admin_page())
                    ]
                )
            )
            page.update()
            return

        table = ft.DataTable(
            heading_row_color=ft.colors.BLACK12,
            columns=[
                ft.DataColumn(ft.Text("Hora", weight="bold", color="white70")),
                ft.DataColumn(ft.Text("Total", weight="bold", color="white70")),
                ft.DataColumn(ft.Text("Pago", weight="bold", color="white70")),
                ft.DataColumn(ft.Text("Productos", weight="bold", color="white70"))
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row["hora"], color="white")),
                        ft.DataCell(ft.Text(row["total"], color="white")),
                        ft.DataCell(ft.Text(row["pago"], color="white")),
                        ft.DataCell(ft.Text(row["productos"], color="white"))
                    ]
                )
                for row in sales_data
            ],
            width=1040,
            height=420,
            vertical_lines=ft.border.BorderSide(1, "#4B4F58"),
            horizontal_lines=ft.border.BorderSide(1, "#4B4F58")
        )

        page.add(
            ft.Container(
                width=1080,
                bgcolor="#232A34",
                border_radius=20,
                padding=20,
                content=ft.Column(
                    spacing=20,
                    controls=[
                        ft.Row(
                            alignment="spaceBetween",
                            vertical_alignment="center",
                            controls=[
                                ft.Text("Ventas", size=28, weight="bold", color="white"),
                                ft.ElevatedButton("Volver", width=160, on_click=lambda e: show_admin_page())
                            ]
                        ),
                        ft.Row(
                            spacing=12,
                            alignment="center",
                            controls=[
                                ft.FilledButton("Inicio", bgcolor="#2E3746", color="white"),
                                ft.FilledButton("Venta", bgcolor="#4E7BFE", color="white"),
                                ft.FilledButton("Historial", bgcolor="#2E3746", color="white"),
                                ft.FilledButton("Menu", bgcolor="#2E3746", color="white"),
                                ft.FilledButton("Inventario", bgcolor="#2E3746", color="white"),
                                ft.FilledButton("Informes", bgcolor="#2E3746", color="white")
                            ]
                        ),
                        ft.Container(
                            bgcolor="#1F2630",
                            border_radius=12,
                            padding=20,
                            content=table
                        )
                    ]
                )
            )
        )
        page.update()

    # Muestra el panel principal del administrador con accesos a inventario, menú y ventas.
    def show_admin_page():
        page.title = "Bienvenidos a Burguer Land"
        page.controls.clear()
        page.add(
            ft.Column(
                spacing=30,
                horizontal_alignment="center",
                controls=[
                    ft.Container(
                        width=1000,
                        padding=ft.padding.Padding(top=20, bottom=20),
                        alignment=ft.Alignment.TOP_CENTER,
                        content=ft.Text(
                            "Bienvenidos a Burguer Land",
                            size=36,
                            weight="bold",
                            color="blue"
                        )
                    ),
                    ft.Column(
                        expand=True,
                        alignment="center",
                        horizontal_alignment="center",
                        spacing=20,
                        controls=[
                            ft.Row(
                                alignment="center",
                                spacing=20,
                                controls=[
                                    ft.ElevatedButton("Inventario", width=180, height=60),
                                    ft.ElevatedButton("Menú", width=180, height=60),
                                    ft.ElevatedButton("Ventas", width=180, height=60, on_click=lambda e: show_sales_page())
                                ]
                            ),
                            ft.Row(
                                alignment="center",
                                spacing=20,
                                controls=[
                                    ft.ElevatedButton("Historial", width=180, height=60),
                                    ft.ElevatedButton("Reportes", width=180, height=60)
                                ]
                            )
                        ]
                    ),
                    ft.ElevatedButton(
                        "Cerrar sesión",
                        width=200,
                        on_click=lambda e: show_login_page()
                    )
                ]
            )
        )
        page.update()

    # Valida el acceso del usuario y redirige a la pantalla de administración si las credenciales son correctas.
    async def btn_login_click(e):
        lbl_error.value = ""

        if not txt_username.value or not txt_password.value:
            lbl_error.value = "Por favor, llena todos los campos."
            page.update()
            return

        if txt_username.value == "admin" and txt_password.value == "admin123":
            show_admin_page()
        else:
            lbl_error.value = "Usuario o contraseña incorrectos."
            page.update()

    show_login_page()

if __name__ == "__main__":
    ft.run(main)
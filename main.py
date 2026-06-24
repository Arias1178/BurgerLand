import ssl
import certifi
import os
os.environ["FLET_RENDERER"] = "software"

# Solución para certificados SSL de Flet
ssl._create_default_https_context = ssl.create_default_context
os.environ["SSL_CERT_FILE"] = certifi.where()

import flet as ft
from database.database import SessionLocal

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
                                    ft.ElevatedButton("Ventas", width=180, height=60)
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
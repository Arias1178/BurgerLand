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
    page.bgcolor = "#F0F2F5"

    # INTERFAZ
    txt_username = ft.TextField(
        label="Escribe tu Usuario aquí",
        width=300
    )

    txt_password = ft.TextField(
        label="Escribe tu Contraseña aquí",
        password=True,
        width=300
    )

    lbl_error = ft.Text(
        value="", 
        color="red", 
        weight="bold"
    )

    # ACCIÓN DEL BOTÓN
    async def btn_login_click(e):
        lbl_error.value = ""

        if not txt_username.value or not txt_password.value:
            lbl_error.value = "Por favor, llena todos los campos."
            page.update()
            return

        if txt_username.value == "admin" and txt_password.value == "admin123":
            page.controls.clear()
            page.add(
                ft.Text("¡INICIO DE SESIÓN EXITOSO!", size=30, color="green", weight="bold"),
                ft.Text("Bienvenido al panel principal.", size=18)
            )
        else:
            lbl_error.value = "Usuario o contraseña incorrectos."

        page.update()

    btn_login = ft.Button(
        content=ft.Text("Iniciar Sesión", color="white"),
        bgcolor="blue",
        width=300,
        on_click=btn_login_click
    )

    page.add(
        ft.Text("INGRESO AL SISTEMA", size=24, weight="bold", color="black"),
        txt_username,
        txt_password,
        lbl_error, 
        btn_login
    )

    page.update()

if __name__ == "__main__":
    ft.run(main)
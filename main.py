import ssl
import certifi
import os
os.environ["FLET_RENDERER"] = "software"
ssl._create_default_https_context = ssl.create_default_context
os.environ["SSL_CERT_FILE"] = certifi.where()

import flet as ft
from views.login import login_view
from views.inicio import inicio_view
from views.venta import venta_view
from views.navbar import construir_navbar

async def main(page: ft.Page):
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
            mostrar_historial=lambda: print("historial"),
            mostrar_menu=lambda: print("menu"),
            mostrar_inventario=lambda: print("inventario"),
            mostrar_informes=lambda: print("informes"),
        )

    def mostrar_inicio(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(inicio_view(page, get_navbar("inicio")))

    def mostrar_venta():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(venta_view(page, get_navbar("venta")))

    def mostrar_login():
        page.horizontal_alignment = "center"
        page.vertical_alignment = "center"
        page.padding = 0
        navegar(login_view(page, on_login_success=mostrar_inicio))

    mostrar_login()

if __name__ == "__main__":
    ft.run(main)
import ssl
import certifi
import os

ssl._create_default_https_context = ssl.create_default_context
os.environ["SSL_CERT_FILE"] = certifi.where()

import flet as ft
from views.inicio import inicio_view
from views.navbar import construir_navbar
from views.venta import venta_view
from views.login import login_view


async def main(page: ft.Page):
    page.title = "Sistema de Gestión"
    page.window_width = 1200
    page.window_height = 800
    page.horizontal_alignment = ft.MainAxisAlignment.CENTER
    page.vertical_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#F5F5F5"

    active_view = "inicio"

    def show_login_page():
        page.controls.clear()
        try:
            page.add(login_view(page, on_login_success=show_main_page))
        except Exception as e:
            page.controls.clear()
            page.add(
                ft.Column(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Error al cargar login:", color="red"),
                        ft.Text(str(e), color="red"),
                    ],
                )
            )
            import traceback
            traceback.print_exc()
        page.update()

    def render_main_page():
        nonlocal active_view
        page.controls.clear()
        navbar = construir_navbar(
            page,
            active_view,
            mostrar_inicio,
            mostrar_venta,
            lambda: None,
            lambda: None,
            lambda: None,
            lambda: None,
        )

        if active_view == "venta":
            page.add(venta_view(page, navbar))
        else:
            page.add(inicio_view(page, navbar))

        page.update()

    def mostrar_inicio():
        nonlocal active_view
        active_view = "inicio"
        render_main_page()

    def mostrar_venta():
        nonlocal active_view
        active_view = "venta"
        render_main_page()

    async def show_main_page(user=None):
        page.title = "Burguer Land"
        render_main_page()

    show_login_page()


if __name__ == "__main__":
    ft.run(
        main,
        view=ft.AppView.WEB_BROWSER,
        host="127.0.0.1",
        port=0,
        web_renderer=ft.WebRenderer.CANVAS_KIT,
        no_cdn=True,
    )

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
from views.historial import historial_view
from views.menu import menu_view
from views.inventario import inventario_view
from views.informes import informes_view
from views.nueva_venta_view import nueva_venta_view

usuario_actual = {"valor": None}  # guardamos el usuario logueado aquí

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
            mostrar_historial=lambda: mostrar_historial(),
            mostrar_menu=lambda: mostrar_menu(),
            mostrar_inventario=lambda: mostrar_inventario(),
            mostrar_informes=lambda: mostrar_informes(),
        )

    def mostrar_venta():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(venta_view(page, get_navbar("venta"), on_nueva_venta=mostrar_nueva_venta))

    def mostrar_nueva_venta():
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(nueva_venta_view(
            page,
            get_navbar("venta"),
            usuario_actual=usuario_actual["valor"],
            on_venta_completada=mostrar_venta
        ))

    def mostrar_inicio(usuario=None):
        if usuario:
            usuario_actual["valor"] = usuario
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(inicio_view(page, get_navbar("inicio")))

    def mostrar_menu(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(menu_view(page, get_navbar("menu")))

    def mostrar_inventario(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(inventario_view(page, get_navbar("inventario")))

    def mostrar_informes(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(informes_view(page, get_navbar("informes")))
    
    def mostrar_historial(usuario=None):
        page.horizontal_alignment = "start"
        page.vertical_alignment = "start"
        page.padding = 20
        navegar(historial_view(page, get_navbar("historial")))

    def mostrar_login():
        page.horizontal_alignment = "center"
        page.vertical_alignment = "center"
        page.padding = 0
        navegar(login_view(page, on_login_success=mostrar_inicio))

    mostrar_login()

if __name__ == "__main__":
    ft.run(main)
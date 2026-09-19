import datetime
import flet as ft


def inicio_view(page: ft.Page, navbar, usuario_actual=None, caja_actual=None, on_abrir_caja=None, on_cerrar_caja=None, on_refrescar=None):
    saldo_inicial_field = ft.TextField(
        value="0",
        width=420,
        height=60,
        hint_text="Ingresa el saldo inicial",
        bgcolor="#DDE2EA",
        color="#111111",
        border_radius=12,
        border_color="transparent",
        text_style=ft.TextStyle(size=18, color="#111111"),
        content_padding=ft.Padding(left=16, right=16, top=18, bottom=12),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    mensaje = ft.Text("", color="#F2C744", size=14)

    def ejecutar_abrir_caja(_e):
        if not on_abrir_caja:
            return
        resultado = on_abrir_caja(saldo_inicial_field.value)
        if resultado and not resultado.get("ok"):
            mensaje.value = resultado.get("mensaje", "No se pudo abrir la caja.")
            mensaje.color = "#FF7B7B"
        else:
            mensaje.value = resultado.get("mensaje", "Caja abierta correctamente.")
            mensaje.color = "#7AE582"
        page.update()
        if resultado and resultado.get("ok") and on_refrescar:
            on_refrescar()

    def confirmar_abrir_caja(e):
        try:
            valor_texto = f"${float(saldo_inicial_field.value or 0):,.0f}".replace(",", ".")
        except (TypeError, ValueError):
            valor_texto = saldo_inicial_field.value or "0"

        def aceptar(_e):
            page.pop_dialog()
            ejecutar_abrir_caja(_e)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar apertura de caja"),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text("Saldo inicial a registrar:", color="#C9CEDB"),
                    ft.Text(valor_texto, size=20, weight="bold", color="#F2C744"),
                    ft.Text("¿Deseas continuar y abrir la caja con este valor?", color="white"),
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(
                    content="Abrir caja",
                    bgcolor="#4A6741",
                    color="white",
                    on_click=aceptar,
                ),
            ],
        )
        page.show_dialog(dialog)

    def ejecutar_cerrar_caja(e):
        if not on_cerrar_caja:
            return
        resultado = on_cerrar_caja()
        if resultado and not resultado.get("ok"):
            mensaje.value = resultado.get("mensaje", "No se pudo cerrar la caja.")
            mensaje.color = "#FF7B7B"
        else:
            mensaje.value = resultado.get("mensaje", "Caja cerrada correctamente.")
            mensaje.color = "#7AE582"
        page.update()
        if resultado and resultado.get("ok") and on_refrescar:
            on_refrescar()

    def confirmar_cerrar_caja(e):
        def aceptar(_e):
            page.pop_dialog()
            ejecutar_cerrar_caja(_e)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar cierre de caja"),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Saldo inicial: ${caja_actual.saldo_inicial:,.0f}".replace(",", "."), color="#C9CEDB"),
                    ft.Text("Esta acción cerrará el turno actual y no se podrá deshacer.", color="white"),
                    ft.Text("¿Deseas continuar y cerrar la caja?", color="white"),
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(
                    content="Cerrar caja",
                    bgcolor="#8A3A3A",
                    color="white",
                    on_click=aceptar,
                ),
            ],
        )
        page.show_dialog(dialog)

    if caja_actual:
        panel_izquierdo = ft.Container(
            expand=True,
            padding=28,
            bgcolor="#2E3344",
            border_radius=20,
            content=ft.Column(
                expand=True,
                spacing=15,
                controls=[
                    ft.Text("CAJA ABIERTA", size=22, weight="bold", color="white"),
                    ft.Text(f"Fecha apertura: {caja_actual.fecha_apertura.strftime('%d/%m/%Y %H:%M')}", size=16, color="white"),
                    ft.Text("Saldo inicial:", size=16, weight="bold", color="white"),
                    ft.Text(f"${caja_actual.saldo_inicial:,.0f}".replace(",", "."), size=18, color="#F2C744", weight="bold"),
                    ft.Text("Estado:", size=16, weight="bold", color="white"),
                    ft.Text("ABIERTA", size=18, color="#7AE582", weight="bold"),
                    ft.Button(
                        content=ft.Text("Cerrar Caja", color="white", weight="bold"),
                        bgcolor="#8A3A3A",
                        on_click=confirmar_cerrar_caja,
                    ),
                    mensaje,
                ],
            ),
        )
        panel_derecho = ft.Container(
            expand=True,
            padding=28,
            bgcolor="#2E3344",
            border_radius=20,
            content=ft.Column(
                expand=True,
                spacing=15,
                horizontal_alignment="center",
                controls=[
                    ft.Text("Resumen", size=22, weight="bold", color="white"),
                    ft.Text("Ventas del turno", size=16, weight="bold", color="white"),
                    ft.Text("$0", size=18, color="#F2C744", weight="bold"),
                    ft.Text("Efectivo estimado", size=16, weight="bold", color="white"),
                    ft.Text(f"${caja_actual.saldo_inicial:,.0f}".replace(",", "."), size=18, color="white", weight="bold"),
                ],
            ),
        )
    else:
        panel_izquierdo = ft.Container(
            expand=True,
            padding=28,
            bgcolor="#2E3344",
            border_radius=20,
            content=ft.Column(
                expand=True,
                spacing=18,
                controls=[
                    ft.Text("APERTURA DE CAJA", size=22, weight="bold", color="white"),
                    ft.Text(f"Fecha: {datetime.datetime.now().strftime('%d/%m/%Y')}", size=16, color="white"),
                    ft.Text("Saldo inicial en caja:", size=16, weight="bold", color="white"),
                    ft.Container(
                        width=420,
                        height=62,
                        alignment=ft.Alignment(-1, 0),
                        content=saldo_inicial_field,
                    ),
                    ft.Container(
                        width=170,
                        content=ft.Button(
                            content=ft.Text("Abrir Caja", color="white", weight="bold"),
                            bgcolor="#5A5F72",
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)),
                            on_click=confirmar_abrir_caja,
                        ),
                    ),
                    mensaje,
                ],
            ),
        )
        panel_derecho = ft.Container(
            expand=True,
            padding=28,
            bgcolor="#2E3344",
            border_radius=20,
            content=ft.Column(
                expand=True,
                spacing=15,
                horizontal_alignment="center",
                controls=[
                    ft.Text("Sin caja activa", size=22, weight="bold", color="white"),
                    ft.Text("Antes de vender debes abrir caja.", size=16, color="white"),
                    ft.Text("Ventas del día: $0", size=16, weight="bold", color="white"),
                    ft.Text("Efectivo esperado: $0", size=16, color="white"),
                ],
            ),
        )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=30,
        content=ft.Row(
            expand=True,
            alignment="spaceBetween",
            controls=[panel_izquierdo, panel_derecho],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=20,
        scroll="auto",
        controls=[
            navbar,
            ft.Container(margin=ft.Margin(top=8), content=tarjeta),
        ],
    )

import datetime
import re
import flet as ft


def inicio_view(
    page: ft.Page,
    navbar,
    usuario_actual=None,
    caja_actual=None,
    on_abrir_caja=None,
    on_cerrar_caja=None,
    on_refrescar=None,
    saldo_inicial_sugerido=2_000_000,
    on_registrar_retiro=None,
):
    sugerido_texto = f"${saldo_inicial_sugerido:,.0f}".replace(",", ".")
    saldo_inicial_field = ft.TextField(
        value=f"{saldo_inicial_sugerido:,.0f}".replace(",", "."),
        width=420,
        height=60,
        hint_text="Ingresa el saldo inicial en COP",
        bgcolor="#DDE2EA",
        color="#111111",
        border_radius=12,
        border_color="transparent",
        text_style=ft.TextStyle(size=18, color="#111111"),
        content_padding=ft.Padding(left=16, right=16, top=18, bottom=12),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    mensaje = ft.Text("", color="#F2C744", size=14)

    def formatear_saldo(e):
        valor = e.control.value or ""
        negativo = valor.lstrip().startswith("-")
        digitos = re.sub(r"\D", "", valor)
        if digitos:
            formateado = f"{int(digitos):,}".replace(",", ".")
        else:
            formateado = ""
        e.control.value = f"-{formateado}" if negativo else formateado
        e.control.update()

    saldo_inicial_field.on_change = formatear_saldo

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
        resultado = on_abrir_caja(saldo_inicial_field.value)
        if not resultado:
            mensaje.value = "No se pudo abrir la caja."
            mensaje.color = "#FF7B7B"
            page.update()
            return
        if resultado and resultado.get("requiere_confirmacion"):
            abrir_dialogo_confirmacion(resultado["mensaje"])
            return

        mensaje.value = resultado.get("mensaje", "No se pudo abrir la caja.")
        mensaje.color = "#FF7B7B"
        page.update()

    def abrir_dialogo_confirmacion(mensaje_advertencia):
        def aceptar(_e):
            page.pop_dialog()
            resultado = on_abrir_caja(
                saldo_inicial_field.value,
                confirmar_inusual=True,
            )
            if resultado and not resultado.get("ok"):
                mensaje.value = resultado.get("mensaje", "No se pudo abrir la caja.")
                mensaje.color = "#FF7B7B"
            else:
                mensaje.value = resultado.get(
                    "mensaje", "Caja abierta correctamente."
                )
                mensaje.color = "#7AE582"
            page.update()
            if resultado and resultado.get("ok") and on_refrescar:
                on_refrescar()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar apertura de caja"),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(mensaje_advertencia, color="#FFB86C"),
                    ft.Text("Puedes corregir el valor o confirmar la apertura.", color="white"),
                ],
            ),
            actions=[
                ft.TextButton("Corregir", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(
                    content="Confirmar",
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

    def abrir_dialogo_retiro(_e):
        monto_field = ft.TextField(
            label="Monto del retiro (COP)",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        motivo_field = ft.TextField(
            label="Motivo",
            multiline=True,
            min_lines=2,
            max_lines=3,
        )
        error = ft.Text("", color="#FF7B7B", size=12)

        def guardar_retiro(_evento):
            resultado = on_registrar_retiro(
                monto_field.value,
                motivo_field.value,
            )
            if not resultado or not resultado.get("ok"):
                error.value = (
                    resultado.get("mensaje", "No se pudo registrar el retiro.")
                    if resultado
                    else "No se pudo registrar el retiro."
                )
                page.update()
                return
            page.pop_dialog()
            mensaje.value = resultado["mensaje"]
            mensaje.color = "#7AE582"
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Registrar retiro de caja"),
                content=ft.Column(
                    tight=True,
                    controls=[monto_field, motivo_field, error],
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _evento: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Registrar retiro",
                        on_click=guardar_retiro,
                    ),
                ],
            )
        )

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
                    ft.Button(
                        content=ft.Text("Registrar retiro", color="white", weight="bold"),
                        bgcolor="#5A5F72",
                        on_click=abrir_dialogo_retiro,
                        disabled=on_registrar_retiro is None,
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
            padding=30,
            bgcolor="#252A39",
            border=ft.Border.all(1, "#454B60"),
            border_radius=20,
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        controls=[
                            ft.Row(
                                spacing=14,
                                controls=[
                                    ft.Container(
                                        width=50,
                                        height=50,
                                        border_radius=15,
                                        alignment=ft.Alignment.CENTER,
                                        bgcolor="#F2C744",
                                        content=ft.Icon(
                                            ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                                            color="#202433",
                                            size=26,
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=3,
                                        controls=[
                                            ft.Text(
                                                "Abrir caja",
                                                size=23,
                                                weight="bold",
                                                color="white",
                                            ),
                                            ft.Text(
                                                "Inicia el turno registrando el "
                                                "efectivo disponible.",
                                                size=13,
                                                color="#AEB6C9",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Container(
                                padding=ft.Padding.symmetric(
                                    horizontal=12, vertical=8
                                ),
                                border_radius=20,
                                bgcolor="#343B4E",
                                content=ft.Row(
                                    spacing=7,
                                    controls=[
                                        ft.Icon(
                                            ft.Icons.CALENDAR_TODAY_OUTLINED,
                                            size=15,
                                            color="#F2C744",
                                        ),
                                        ft.Text(
                                            datetime.datetime.now().strftime(
                                                "%d/%m/%Y"
                                            ),
                                            size=12,
                                            color="#E5E8EF",
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Divider(height=1, color="#41485B"),
                    ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(
                                "Saldo inicial en caja",
                                size=15,
                                weight="bold",
                                color="white",
                            ),
                            ft.Container(
                                width=420,
                                height=62,
                                alignment=ft.Alignment(-1, 0),
                                content=saldo_inicial_field,
                            ),
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.INFO_OUTLINE,
                                        size=15,
                                        color="#AEB6C9",
                                    ),
                                    ft.Text(
                                        f"Monto sugerido: {sugerido_texto} COP",
                                        size=12,
                                        color="#AEB6C9",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Container(
                        width=220,
                        content=ft.ElevatedButton(
                            content="Iniciar caja",
                            icon=ft.Icons.ARROW_FORWARD,
                            bgcolor="#F2C744",
                            color="#202433",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=ft.Padding.symmetric(
                                    horizontal=20, vertical=16
                                ),
                            ),
                            on_click=confirmar_abrir_caja,
                        ),
                    ),
                    mensaje,
                ],
            ),
        )
        panel_derecho = ft.Container(
            expand=True,
            padding=30,
            bgcolor="#252A39",
            border=ft.Border.all(1, "#454B60"),
            border_radius=20,
            content=ft.Column(
                spacing=14,
                horizontal_alignment="center",
                controls=[
                    ft.Container(
                        width=58,
                        height=58,
                        border_radius=29,
                        alignment=ft.Alignment.CENTER,
                        bgcolor="#343B4E",
                        content=ft.Icon(
                            ft.Icons.LOCK_OPEN_OUTLINED,
                            size=27,
                            color="#F2C744",
                        ),
                    ),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                        border_radius=18,
                        bgcolor="#453F2D",
                        content=ft.Text(
                            "TURNO SIN INICIAR",
                            size=10,
                            weight="bold",
                            color="#F2C744",
                        ),
                    ),
                    ft.Column(
                        spacing=5,
                        horizontal_alignment="center",
                        controls=[
                            ft.Text(
                                "Sin caja activa",
                                size=21,
                                weight="bold",
                                color="white",
                            ),
                            ft.Text(
                                "Abre la caja para empezar a vender y "
                                "controlar el efectivo del turno.",
                                size=13,
                                color="#AEB6C9",
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                    ft.Divider(height=1, color="#41485B"),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                expand=True,
                                padding=14,
                                border_radius=12,
                                bgcolor="#2E3344",
                                content=ft.Column(
                                    spacing=5,
                                    controls=[
                                        ft.Row(
                                            spacing=7,
                                            controls=[
                                                ft.Icon(
                                                    ft.Icons.POINT_OF_SALE_OUTLINED,
                                                    color="#7ABAFB",
                                                    size=17,
                                                ),
                                                ft.Text(
                                                    "Ventas del día",
                                                    size=12,
                                                    color="#AEB6C9",
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            "$0",
                                            size=20,
                                            weight="bold",
                                            color="white",
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                padding=14,
                                border_radius=12,
                                bgcolor="#2E3344",
                                content=ft.Column(
                                    spacing=5,
                                    controls=[
                                        ft.Row(
                                            spacing=7,
                                            controls=[
                                                ft.Icon(
                                                    ft.Icons.PAYMENTS_OUTLINED,
                                                    color="#80C78A",
                                                    size=17,
                                                ),
                                                ft.Text(
                                                    "Efectivo esperado",
                                                    size=12,
                                                    color="#AEB6C9",
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            "$0",
                                            size=20,
                                            weight="bold",
                                            color="white",
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=24,
        content=ft.Row(
            expand=True,
            spacing=18,
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

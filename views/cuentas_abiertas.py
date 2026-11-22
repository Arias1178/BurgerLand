import datetime

import flet as ft

from database.database import SessionLocal
from services.cuenta_service import anular_cuenta_abierta, listar_cuentas_abiertas


def formato_pesos(valor: float) -> str:
    return f"${valor:,.0f}".replace(",", ".")


def formato_transcurrido(fecha_apertura: datetime.datetime) -> str:
    if fecha_apertura.tzinfo:
        ahora = datetime.datetime.now(fecha_apertura.tzinfo)
    else:
        ahora = datetime.datetime.now()
    segundos = max(0, int((ahora - fecha_apertura).total_seconds()))
    horas, resto = divmod(segundos, 3600)
    minutos = resto // 60
    return f"{horas} h {minutos:02d} min"


def cuentas_abiertas_view(
    page: ft.Page,
    navbar,
    on_abrir_cuenta,
) -> ft.Column:
    mensaje = ft.Text("", color="#FF7B7B", size=13)
    lista = ft.Column(spacing=12, scroll="auto", expand=True)

    def refrescar():
        db = SessionLocal()
        try:
            registros = listar_cuentas_abiertas(db)
            filas = []
            for registro in registros:
                cuenta = registro["cuenta"]
                mesa = (
                    f"Mesa {registro['mesa_numero']}"
                    if registro["mesa_numero"] is not None
                    else "Para llevar / Mostrador"
                )
                filas.append(
                    ft.Container(
                        bgcolor="#2C2F3E",
                        border_radius=14,
                        padding=16,
                        content=ft.Row(
                            alignment="spaceBetween",
                            controls=[
                                ft.Column(
                                    expand=True,
                                    spacing=4,
                                    controls=[
                                        ft.Text(
                                            f"{mesa} · Cuenta #{cuenta.id_cuenta}",
                                            color="white",
                                            weight="bold",
                                            size=16,
                                        ),
                                        ft.Text(
                                            f"{registro['cantidad_items']} unidades · "
                                            f"Abierta hace {formato_transcurrido(cuenta.fecha_apertura)}",
                                            color="#C9CEDB",
                                        ),
                                        *(
                                            [
                                                ft.Text(
                                                    f"Subcuentas pagadas: "
                                                    f"{registro['subcuentas_pagadas']}/"
                                                    f"{registro['total_subcuentas']}",
                                                    color="#FFB86C",
                                                )
                                            ]
                                            if registro["total_subcuentas"]
                                            else []
                                        ),
                                        ft.Text(
                                            formato_pesos(cuenta.total),
                                            color="#F2C744",
                                            weight="bold",
                                            size=18,
                                        ),
                                    ],
                                ),
                                ft.Button(
                                    "Abrir cuenta",
                                    bgcolor="#4A6741",
                                    color="white",
                                    on_click=lambda _e, id_cuenta=cuenta.id_cuenta:
                                        on_abrir_cuenta(id_cuenta),
                                ),
                                ft.TextButton(
                                    "Anular",
                                    on_click=lambda _e, id_cuenta=cuenta.id_cuenta,
                                    version=cuenta.version:
                                        confirmar_anulacion(id_cuenta, version),
                                ),
                            ],
                        ),
                    )
                )
            lista.controls = filas or [
                ft.Container(
                    padding=24,
                    content=ft.Text(
                        "No hay cuentas abiertas.",
                        color="#C9CEDB",
                        text_align="center",
                    ),
                )
            ]
        finally:
            db.close()
        page.update()

    def confirmar_anulacion(cuenta_id: int, version: int):
        def aceptar(_e):
            db = SessionLocal()
            try:
                anular_cuenta_abierta(db, cuenta_id, version)
            except ValueError as error:
                db.rollback()
                mensaje.value = str(error)
                page.pop_dialog()
                refrescar()
                return
            finally:
                db.close()
            page.pop_dialog()
            refrescar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Anular cuenta abierta"),
                content=ft.Text(
                    f"¿Seguro que deseas anular la cuenta #{cuenta_id}? "
                    "La mesa quedará libre."
                ),
                actions=[
                    ft.TextButton(
                        "Volver",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Anular cuenta",
                        bgcolor="#8A3A3A",
                        color="white",
                        on_click=aceptar,
                    ),
                ],
            )
        )

    refrescar()
    return ft.Column(
        expand=True,
        spacing=18,
        scroll="auto",
        controls=[
            navbar,
            ft.Container(
                expand=True,
                bgcolor="#3A3F52",
                border_radius=20,
                padding=24,
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    controls=[
                        ft.Text("CUENTAS ABIERTAS", size=22, weight="bold", color="white"),
                        ft.Text(
                            "Continúa una cuenta o confirma su pago desde la pantalla de venta.",
                            color="#C9CEDB",
                        ),
                        mensaje,
                        lista,
                    ],
                ),
            ),
        ],
    )

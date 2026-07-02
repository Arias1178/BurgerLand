import flet as ft

def inicio_view(page: ft.Page, navbar):

    panel_izquierdo = ft.Column(
        expand=True,
        spacing=15,
        controls=[
            ft.Text("APERTURA DE CAJA", size=22, weight="bold", color="white"),
            ft.Text("Fecha: 15/06/2026", size=16, color="white"),
            ft.Text("Saldo de cierre anterior:", size=16, weight="bold", color="white"),
            ft.Text("$150.000", size=16, color="white"),
            ft.Text("Dinero inicial en caja:", size=16, weight="bold", color="white"),
            ft.Text("[ $150.000 ]", size=16, color="white"),
            ft.Button(
                content=ft.Text("[ Abrir Caja ]", color="white"),
                bgcolor="#5A5F72",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20))
            )
        ]
    )

    panel_derecho = ft.Column(
        expand=True,
        spacing=15,
        horizontal_alignment="center",
        controls=[
            ft.Text("Último cierre:", size=22, weight="bold", color="white"),
            ft.Text("14/06/2026", size=16, color="white"),
            ft.Text("Ventas:", size=16, weight="bold", color="white"),
            ft.Text("$1.250.000", size=16, color="white"),
            ft.Text("Efectivo final:", size=16, weight="bold", color="white"),
            ft.Text("$150.000", size=16, color="white"),
        ]
    )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=40,
        content=ft.Row(
            expand=True,
            alignment="spaceBetween",
            controls=[panel_izquierdo, panel_derecho]
        )
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta]
    )
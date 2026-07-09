import flet as ft

def venta_view(page: ft.Page, navbar):

    tabla = ft.DataTable(
    border_radius=10,
    column_spacing=40,
    heading_row_color="#2C2F3E",
    columns=[
        ft.DataColumn(ft.Text("#", color="white", weight="bold")),
        ft.DataColumn(ft.Text("Hora", color="white", weight="bold")),
        ft.DataColumn(ft.Text("Total", color="white", weight="bold")),
        ft.DataColumn(ft.Text("Pago", color="white", weight="bold")),
        ft.DataColumn(ft.Text("Productos", color="white", weight="bold")),
    ],
    rows=[
        ft.DataRow(cells=[
            ft.DataCell(ft.Text("2", color="white")),
            ft.DataCell(ft.Text("10:15", color="white")),
            ft.DataCell(ft.Text("$25.000", color="white")),
            ft.DataCell(ft.Text("Nequi", color="white")),
            ft.DataCell(ft.Text("Hamburguesa + Gaseosa", color="white")),
        ]),
        ft.DataRow(cells=[
            ft.DataCell(ft.Text("3", color="white")),
            ft.DataCell(ft.Text("10:40", color="white")),
            ft.DataCell(ft.Text("$18.000", color="white")),
            ft.DataCell(ft.Text("Efectivo", color="white")),
            ft.DataCell(ft.Text("Perro + Papas", color="white")),
        ]),
        ft.DataRow(cells=[
            ft.DataCell(ft.Text("4", color="white")),
            ft.DataCell(ft.Text("11:00", color="white")),
            ft.DataCell(ft.Text("$32.000", color="white")),
            ft.DataCell(ft.Text("Tarjeta", color="white")),
            ft.DataCell(ft.Text("Combo Doble", color="white")),
        ]),
    ]
)

    btn_nueva_venta = ft.Button(
        content=ft.Text("Venta", color="white", weight="bold"),
        bgcolor="#3A3F52",
        style=ft.ButtonStyle(
            side=ft.BorderSide(2, "white"),
            shape=ft.RoundedRectangleBorder(radius=25)
        ),
        width=150,
        height=50,
        on_click=lambda e: print("nueva venta")
    )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=30,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        scroll="auto",
                        controls=[tabla]
                    )
                ),
                ft.Row(
                    alignment="end",
                    controls=[btn_nueva_venta]
                )
            ]
        )
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta]
    )
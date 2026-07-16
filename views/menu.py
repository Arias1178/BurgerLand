import flet as ft
from database.database import SessionLocal
from database.models import productos, categorias

def menu_view(page: ft.Page, navbar):
    db = SessionLocal()
    lista_categorias = db.query(categorias).all()

    if not lista_categorias:
        db.close()
        return ft.Column(
        expand=True,
        spacing=20,
        controls=[
            navbar,
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("No hay categorías registradas todavía.", color="white", size=18)
            )
        ]
    )

    def construir_tarjeta_producto(producto):
        return ft.Container(
            width=260,
            bgcolor="#3A3F52",
            border_radius=15,
            padding=15,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text(producto.nombre, size=16, weight="bold", color="white"),
                    ft.Text(producto.descripcion or "", size=12, color="#C7C9D9"),
                    ft.Text(
                        f"${producto.precio:,.0f}".replace(",", "."),
                        size=16,
                        weight="bold",
                        color="#F2C744"
                    ),
                ]
            )
        )

    def construir_grid_categoria(id_categoria):
        productos_categoria = db.query(productos).filter(
            productos.id_categoria == id_categoria
        ).all()

        if not productos_categoria:
            return ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=30,
                content=ft.Text("No hay productos en esta categoría.", color="white")
            )

        return ft.Container(
            padding=20,
            content=ft.Row(
                wrap=True,
                spacing=15,
                run_spacing=15,
                controls=[construir_tarjeta_producto(p) for p in productos_categoria]
            )
        )

    tab_bar = ft.TabBar(
        tabs=[ft.Tab(label=ft.Text(cat.nombre, color="white")) for cat in lista_categorias]
    )

    tab_bar_view = ft.TabBarView(
        expand=True,
        controls=[construir_grid_categoria(cat.id_categoria) for cat in lista_categorias]
    )

    tabs = ft.Tabs(
        length=len(lista_categorias),
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[tab_bar, tab_bar_view]
        )
    )

    db.close()

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Text("MENÚ", size=24, weight="bold", color="white"),
                ft.Container(expand=True, content=tabs)
            ]
        )
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta]
    )
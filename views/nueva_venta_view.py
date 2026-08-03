import flet as ft
from database.database import SessionLocal
from database.models import productos, categorias, metodos_pago, ventas, detalle_ventas

def nueva_venta_view(page: ft.Page, navbar, usuario_actual, on_venta_completada, caja_actual=None):
    db = SessionLocal()
    lista_categorias = db.query(categorias).all()
    lista_metodos = db.query(metodos_pago).all()

    if caja_actual is None:
        db.close()
        return ft.Column(
            controls=[
                navbar,
                ft.Container(
                    padding=30,
                    bgcolor="#3A3F52",
                    border_radius=20,
                    content=ft.Column(
                        controls=[
                            ft.Text("Debe abrir caja antes de registrar ventas.", size=22, weight="bold", color="white"),
                            ft.TextButton("Volver al inicio", on_click=lambda e: on_venta_completada()),
                        ]
                    ),
                ),
            ]
        )

    carrito = []  # lista de dicts: {id_producto, nombre, precio, cantidad}
    metodo_seleccionado = {"id": lista_metodos[0].id_metodos_pago if lista_metodos else None,
                            "nombre": lista_metodos[0].nombre if lista_metodos else ""}

    carrito_column = ft.Column(spacing=8, scroll="auto", expand=True)
    total_text = ft.Text("Total: $0", size=20, weight="bold", color="white")
    metodo_text = ft.Text(f"Método: {metodo_seleccionado['nombre']}", color="white")

    # ─── CARRITO ────────────────────────────────────────────
    def actualizar_carrito():
        carrito_column.controls.clear()
        total = 0
        for item in carrito:
            subtotal = item["precio"] * item["cantidad"]
            total += subtotal

            def quitar(e, id_producto=item["id_producto"]):
                carrito[:] = [i for i in carrito if i["id_producto"] != id_producto]
                actualizar_carrito()

            carrito_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Column(
                            expand=True,
                            spacing=0,
                            controls=[
                                ft.Text(f"{item['nombre']}", color="white", weight="bold"),
                                ft.Text(f"{item['cantidad']} x ${item['precio']:,.0f}".replace(",", "."), color="#C7C9D9", size=12),
                            ]
                        ),
                        ft.Text(f"${subtotal:,.0f}".replace(",", "."), color="#F2C744", weight="bold"),
                        ft.Button(
                            content=ft.Text("X", color="white"),
                            bgcolor="#8A3A3A",
                            width=35,
                            height=35,
                            on_click=quitar
                        )
                    ]
                )
            )
        total_text.value = f"Total: ${total:,.0f}".replace(",", ".")
        page.update()

    # ─── SELECTOR DE CANTIDAD ───────────────────────────────
    def abrir_selector_cantidad(producto):
        cantidad_field = ft.TextField(value="1", width=80, text_align="center")

        def confirmar(e):
            try:
                cantidad = int(cantidad_field.value)
                if cantidad <= 0:
                    cantidad = 1
            except ValueError:
                cantidad = 1

            for item in carrito:
                if item["id_producto"] == producto.id_producto:
                    item["cantidad"] += cantidad
                    break
            else:
                carrito.append({
                    "id_producto": producto.id_producto,
                    "nombre": producto.nombre,
                    "precio": producto.precio,
                    "cantidad": cantidad
                })

            page.pop_dialog()
            actualizar_carrito()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(producto.nombre),
            content=ft.Row(
                controls=[ft.Text("Cantidad:"), cantidad_field]
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Agregar", on_click=confirmar),
            ]
        )
        page.show_dialog(dialog)

    # ─── TARJETAS DE PRODUCTO (clicables) ───────────────────
    def construir_tarjeta_producto(producto):
        return ft.Button(
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(producto.nombre, size=14, weight="bold", color="white"),
                    ft.Text(
                        f"${producto.precio:,.0f}".replace(",", "."),
                        size=14, color="#F2C744", weight="bold"
                    ),
                ]
            ),
            bgcolor="#3A3F52",
            width=220,
            height=70,
            on_click=lambda e, p=producto: abrir_selector_cantidad(p)
        )

    def construir_grid_categoria(id_categoria):
        productos_categoria = db.query(productos).filter(
            productos.id_categoria == id_categoria
        ).all()
        return ft.Container(
            padding=15,
            content=ft.Row(
                wrap=True,
                spacing=10,
                run_spacing=10,
                controls=[construir_tarjeta_producto(p) for p in productos_categoria]
            )
        )

    if lista_categorias:
        tab_bar = ft.TabBar(
            tabs=[ft.Tab(label=ft.Text(cat.nombre, color="white")) for cat in lista_categorias]
        )
        tab_bar_view = ft.TabBarView(
            expand=True,
            controls=[construir_grid_categoria(cat.id_categoria) for cat in lista_categorias]
        )
        menu_tabs = ft.Tabs(
            length=len(lista_categorias),
            selected_index=0,
            expand=True,
            content=ft.Column(expand=True, controls=[tab_bar, tab_bar_view])
        )
    else:
        menu_tabs = ft.Text("No hay productos registrados.", color="white")

    # ─── SELECTOR DE MÉTODO DE PAGO ──────────────────────────
    def seleccionar_metodo(m):
        metodo_seleccionado["id"] = m.id_metodos_pago
        metodo_seleccionado["nombre"] = m.nombre
        metodo_text.value = f"Método: {m.nombre}"
        page.update()

    botones_metodo = ft.Row(
        spacing=10,
        controls=[
            ft.Button(
                content=ft.Text(m.nombre, color="white", size=12),
                bgcolor="#5A5F72",
                height=35,
                on_click=lambda e, m=m: seleccionar_metodo(m)
            )
            for m in lista_metodos
        ]
    )

    # ─── CONFIRMAR VENTA ──────────────────────────────────────
    def confirmar_venta(e):
        if not carrito:
            return

        import datetime
        total = sum(item["precio"] * item["cantidad"] for item in carrito)

        nueva_venta = ventas(
            fecha_hora=datetime.datetime.now(),
            total=total,
            id_metodos_pagos=metodo_seleccionado["id"],
            id_usuario=usuario_actual.id_usuario if usuario_actual else None,
            id_caja=caja_actual.id_caja if caja_actual else None,
            id_estado_ventas=1
        )
        db.add(nueva_venta)
        db.commit()
        db.refresh(nueva_venta)

        for item in carrito:
            db.add(detalle_ventas(
                cantidad=item["cantidad"],
                precio_unitario=item["precio"],
                subtotal=item["precio"] * item["cantidad"],
                id_venta=nueva_venta.id_venta,
                id_producto=item["id_producto"]
            ))
        db.commit()

        carrito.clear()
        db.close()
        on_venta_completada()

    btn_confirmar = ft.Button(
        content=ft.Text("Confirmar Venta", color="white", weight="bold"),
        bgcolor="#4A6741",
        width=250,
        height=50,
        on_click=confirmar_venta
    )

    # ─── PANEL CARRITO ────────────────────────────────────────
    panel_carrito = ft.Container(
        width=320,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Text("CARRITO", size=18, weight="bold", color="white"),
                ft.Divider(color="#5A5F72"),
                carrito_column,
                ft.Divider(color="#5A5F72"),
                total_text,
                metodo_text,
                botones_metodo,
                ft.Container(height=15),
                btn_confirmar
            ]
        )
    )

    panel_menu = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            controls=[
                ft.Text("NUEVA VENTA", size=22, weight="bold", color="white"),
                ft.Container(expand=True, content=menu_tabs)
            ]
        )
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[
            navbar,
            ft.Row(
                expand=True,
                controls=[panel_menu, panel_carrito]
            )
        ]
    )
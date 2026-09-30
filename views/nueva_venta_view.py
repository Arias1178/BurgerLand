import datetime

import flet as ft

from database.database import SessionLocal
from database.models import (
    productos,
    categorias,
    estados_productos,
    metodos_pago,
    ventas,
    detalle_ventas,
    proveedores,
    inventario,
)


def nueva_venta_view(page: ft.Page, navbar, usuario_actual, on_venta_completada, caja_actual=None):
    db = SessionLocal()
    lista_categorias = db.query(categorias).all()
    lista_metodos = db.query(metodos_pago).all()
    lista_proveedores = db.query(proveedores).filter(proveedores.estado == "ACTIVO").order_by(proveedores.nombre.asc()).all()
    estado_activo = db.query(estados_productos).filter(estados_productos.nombre == "ACTIVO").first()

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

    carrito = []
    metodo_seleccionado = {
        "id": lista_metodos[0].id_metodos_pago if lista_metodos else None,
        "nombre": lista_metodos[0].nombre if lista_metodos else "",
    }
    proveedores_seleccionados = []
    pestaña_actual = {"indice": 0}
    busqueda = {"texto": ""}

    carrito_column = ft.Column(spacing=8, scroll="auto", expand=True)
    total_text = ft.Text("Total: $0", size=20, weight="bold", color="white")
    metodo_text = ft.Text(f"Método: {metodo_seleccionado['nombre']}", color="white")
    proveedor_text = ft.Text("Proveedores: Sin selección", color="white")
    proveedor_costo_text = ft.Text("Cobro de proveedores: $0", color="#F2C744")
    mensaje_venta_text = ft.Text("", color="#FF7B7B", size=12)
    proveedores_column = ft.Column(spacing=6, expand=True, scroll="auto")
    contenedor_menu = ft.Container(expand=True)

    def validar_item_venta(item):
        if not isinstance(item, dict):
            raise ValueError("Cada producto del carrito debe ser un registro válido.")

        cantidad = item.get("cantidad")
        precio = item.get("precio")
        nombre = item.get("nombre", "el producto")

        try:
            cantidad_int = int(cantidad)
        except (TypeError, ValueError):
            raise ValueError(f"La cantidad para '{nombre}' debe ser un número entero.")

        if cantidad_int <= 0:
            raise ValueError(f"La cantidad para '{nombre}' debe ser mayor que 0.")

        try:
            precio_valor = float(precio)
        except (TypeError, ValueError):
            raise ValueError(f"El precio para '{nombre}' debe ser numérico.")

        if precio_valor < 0:
            raise ValueError(f"El precio para '{nombre}' no puede ser negativo.")

        return cantidad_int, precio_valor

    def validar_stock_disponible(db_session, carrito_local):
        if not carrito_local:
            raise ValueError("Debes agregar al menos un producto para registrar la venta.")

        for item in carrito_local:
            cantidad, _ = validar_item_venta(item)
            producto = db_session.query(productos).filter(productos.id_producto == item["id_producto"]).first()
            if not producto:
                raise ValueError(f"No se encontró el producto {item.get('nombre', 'seleccionado')}.")
            if producto.id_inventario:
                insumo = (
                    db_session.query(inventario)
                    .filter(inventario.id_inventario == producto.id_inventario)
                    .with_for_update()
                    .first()
                )
                if not insumo:
                    raise ValueError(f"El inventario de {producto.nombre} no está configurado.")
                if insumo.cantidad < cantidad:
                    raise ValueError(
                        f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
                    )
        return True

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
                                ft.Text(item["nombre"], color="white", weight="bold"),
                                ft.Text(
                                    f"{item['cantidad']} x ${item['precio']:,.0f}".replace(",", "."),
                                    color="#C7C9D9",
                                    size=12,
                                ),
                            ],
                        ),
                        ft.Text(f"${subtotal:,.0f}".replace(",", "."), color="#F2C744", weight="bold"),
                        ft.Container(
                            width=35,
                            height=35,
                            bgcolor="#8A3A3A",
                            border_radius=18,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text("X", color="white", weight="bold", text_align="center"),
                            on_click=quitar,
                        ),
                    ]
                )
            )
        total_text.value = f"Total: ${total:,.0f}".replace(",", ".")
        page.update()

    def abrir_selector_cantidad(producto):
        cantidad_field = ft.TextField(value="1", width=80, text_align="center")

        def confirmar(e):
            try:
                cantidad = int(cantidad_field.value)
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor que 0.")
            except ValueError:
                mensaje_venta_text.value = "La cantidad debe ser un número entero mayor que 0."
                page.update()
                return

            if producto.id_inventario:
                insumo = db.query(inventario).filter(inventario.id_inventario == producto.id_inventario).first()
                if insumo is not None and insumo.cantidad < cantidad:
                    mensaje_venta_text.value = f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
                    page.update()
                    return

            for item in carrito:
                if item["id_producto"] == producto.id_producto:
                    nuevo_total = item["cantidad"] + cantidad
                    if producto.id_inventario:
                        insumo = db.query(inventario).filter(inventario.id_inventario == producto.id_inventario).first()
                        if insumo is not None and insumo.cantidad < nuevo_total:
                            mensaje_venta_text.value = f"No hay suficiente inventario de {insumo.nombre}. Disponible: {insumo.cantidad:g}."
                            page.update()
                            return
                    item["cantidad"] = nuevo_total
                    break
            else:
                carrito.append(
                    {
                        "id_producto": producto.id_producto,
                        "nombre": producto.nombre,
                        "precio": producto.precio,
                        "cantidad": cantidad,
                    }
                )

            page.pop_dialog()
            actualizar_carrito()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(producto.nombre),
            content=ft.Row(controls=[ft.Text("Cantidad:"), cantidad_field]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Agregar", on_click=confirmar),
            ],
        )
        page.show_dialog(dialog)

    def construir_tarjeta_producto(producto):
        return ft.Button(
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(producto.nombre, size=14, weight="bold", color="white"),
                    ft.Text(
                        f"${producto.precio:,.0f}".replace(",", "."),
                        size=14,
                        color="#F2C744",
                        weight="bold",
                    ),
                ],
            ),
            bgcolor="#3A3F52",
            width=220,
            height=70,
            on_click=lambda e, p=producto: abrir_selector_cantidad(p),
        )

    def productos_visibles():
        texto = busqueda["texto"].strip().lower()
        if estado_activo:
            candidatos = [p for p in db.query(productos).filter(productos.id_estado == estado_activo.id_estado_producto).all()]
        else:
            candidatos = db.query(productos).all()
        if not texto:
            return candidatos
        return [
            p
            for p in candidatos
            if texto in p.nombre.lower() or texto in (p.descripcion or "").lower()
        ]

    def construir_grid_productos(lista_productos_local):
        if not lista_productos_local:
            return ft.Container(
                alignment=ft.Alignment(0, 0),
                padding=20,
                content=ft.Text("No hay productos para mostrar.", color="white"),
            )

        return ft.Container(
            padding=15,
            content=ft.Row(
                wrap=True,
                spacing=10,
                run_spacing=10,
                controls=[construir_tarjeta_producto(p) for p in lista_productos_local],
            ),
        )

    def construir_tarjeta_proveedor(proveedor):
        seleccionado = any(p["id"] == proveedor.id_proveedor for p in proveedores_seleccionados)
        return ft.Button(
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(proveedor.nombre, size=14, weight="bold", color="white"),
                    ft.Text(
                        f"${float(proveedor.cuanto_cobra or 0):,.0f}".replace(",", "."),
                        size=14,
                        color="#F2C744",
                        weight="bold",
                    ),
                ],
            ),
            bgcolor="#4A6741" if seleccionado else "#3A3F52",
            width=220,
            height=70,
            on_click=lambda e, p=proveedor: seleccionar_proveedor(p),
        )

    def construir_grid_proveedores():
        if not lista_proveedores:
            return ft.Container(
                alignment=ft.Alignment(0, 0),
                padding=20,
                content=ft.Text("No hay proveedores activos registrados.", color="white"),
            )

        return ft.Container(
            padding=15,
            content=ft.Row(
                wrap=True,
                spacing=10,
                run_spacing=10,
                controls=[construir_tarjeta_proveedor(p) for p in lista_proveedores],
            ),
        )

    def construir_tabs():
        if not lista_categorias and not lista_proveedores:
            return ft.Text("No hay productos registrados.", color="white")

        tabs = []
        contenidos = []
        candidatos = productos_visibles()

        for cat in lista_categorias:
            tabs.append(ft.Tab(label=ft.Text(cat.nombre, color="white")))
            contenidos.append(
                construir_grid_productos([p for p in candidatos if p.id_categoria == cat.id_categoria])
            )

        tabs.append(ft.Tab(label=ft.Text("Proveedores", color="white")))
        contenidos.append(construir_grid_proveedores())

        return ft.Tabs(
            length=len(tabs),
            selected_index=pestaña_actual["indice"],
            on_change=lambda e: pestaña_actual.__setitem__(
                "indice", getattr(e.control, "selected_index", 0)
            ),
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(tabs=tabs),
                    ft.TabBarView(expand=True, controls=contenidos),
                ],
            ),
        )

    def refrescar_menu():
        texto = busqueda["texto"].strip()
        if texto:
            resultados = productos_visibles()
            contenido = ft.Column(
                expand=True,
                controls=[
                    ft.Text(f"Resultados para: {texto}", color="white", weight="bold"),
                    construir_grid_productos(resultados),
                ],
            )
        else:
            contenido = construir_tabs()
        contenedor_menu.content = contenido
        page.update()

    def actualizar_proveedores_resumen():
        total_proveedores = sum(item["costo"] for item in proveedores_seleccionados)
        if proveedores_seleccionados:
            nombres = ", ".join(item["nombre"] for item in proveedores_seleccionados)
            proveedor_text.value = f"Proveedores: {nombres}"
        else:
            proveedor_text.value = "Proveedores: Sin selección"
        proveedor_costo_text.value = f"Cobro de proveedores: ${total_proveedores:,.0f}".replace(",", ".")

        proveedores_column.controls.clear()
        for item in proveedores_seleccionados:
            proveedores_column.controls.append(
                ft.Row(
                    spacing=8,
                    vertical_alignment="center",
                    controls=[
                        ft.Text(item["nombre"], color="white", size=12),
                        ft.Text(
                            f"${item['costo']:,.0f}".replace(",", "."),
                            color="#F2C744",
                            size=12,
                            weight="bold",
                        ),
                        ft.Container(
                            width=28,
                            height=28,
                            bgcolor="#8A3A3A",
                            border_radius=14,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text("X", color="white", weight="bold", text_align="center"),
                            on_click=lambda e, id_proveedor=item["id"]: quitar_proveedor(id_proveedor),
                        ),
                    ],
                )
            )

    def seleccionar_metodo(m):
        metodo_seleccionado["id"] = m.id_metodos_pago
        metodo_seleccionado["nombre"] = m.nombre
        metodo_text.value = f"Método: {m.nombre}"
        page.update()

    def seleccionar_proveedor(p):
        if any(item["id"] == p.id_proveedor for item in proveedores_seleccionados):
            return
        proveedores_seleccionados.append(
            {
                "id": p.id_proveedor,
                "nombre": p.nombre,
                "costo": float(p.cuanto_cobra or 0),
            }
        )
        actualizar_proveedores_resumen()
        refrescar_menu()

    def quitar_proveedor(id_proveedor):
        proveedores_seleccionados[:] = [item for item in proveedores_seleccionados if item["id"] != id_proveedor]
        actualizar_proveedores_resumen()
        refrescar_menu()

    def limpiar_proveedor():
        proveedores_seleccionados.clear()
        actualizar_proveedores_resumen()
        refrescar_menu()

    actualizar_proveedores_resumen()

    def ejecutar_venta():
        if not carrito:
            mensaje_venta_text.value = "Agrega al menos un producto para registrar la venta."
            page.update()
            return

        if metodo_seleccionado["id"] is None:
            mensaje_venta_text.value = "Debes seleccionar un método de pago antes de confirmar la venta."
            page.update()
            return

        try:
            for item in carrito:
                validar_item_venta(item)
            validar_stock_disponible(db, carrito)
        except ValueError as error:
            mensaje_venta_text.value = str(error)
            page.update()
            return

        try:
            from services.venta_service import registrar_venta

            registrar_venta(
                db_session=db,
                carrito=carrito,
                metodo_id=metodo_seleccionado["id"],
                usuario_actual=usuario_actual,
                caja_actual=caja_actual,
                proveedores_seleccionados=proveedores_seleccionados,
            )
        except ValueError as error:
            db.rollback()
            mensaje_venta_text.value = str(error)
            page.update()
            return
        except Exception:
            db.rollback()
            mensaje_venta_text.value = "No fue posible registrar la venta."
            page.update()
            return

        carrito.clear()
        proveedores_seleccionados.clear()
        actualizar_proveedores_resumen()
        mensaje_venta_text.value = ""
        db.close()
        on_venta_completada()

    def confirmar_venta(e):
        if not carrito and not proveedores_seleccionados:
            mensaje_venta_text.value = "Agrega productos o selecciona al menos un proveedor."
            page.update()
            return

        total = sum(item["precio"] * item["cantidad"] for item in carrito)
        total_proveedores = sum(item["costo"] for item in proveedores_seleccionados)

        def aceptar(_e):
            page.pop_dialog()
            ejecutar_venta()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar venta"),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Productos en el carrito: {len(carrito)}", color="#C9CEDB"),
                    ft.Text(f"Total a cobrar: ${total:,.0f}".replace(",", "."), size=18, weight="bold", color="#F2C744"),
                    ft.Text(f"Método de pago: {metodo_seleccionado.get('nombre', 'No seleccionado')}", color="#C9CEDB"),
                    (
                        ft.Text(f"Costo a proveedores: ${total_proveedores:,.0f}".replace(",", "."), color="#FFB86C")
                        if proveedores_seleccionados
                        else ft.Text("Sin proveedores asociados a esta venta.", color="#A7AEC2")
                    ),
                    ft.Text("¿Deseas confirmar y registrar esta venta?", color="white"),
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(
                    content="Confirmar venta",
                    bgcolor="#4A6741",
                    color="white",
                    on_click=aceptar,
                ),
            ],
        )
        page.show_dialog(dialog)

    if lista_metodos:
        botones_metodo = ft.Row(
            spacing=10,
            controls=[
                ft.Button(
                    content=ft.Text(m.nombre, color="white", size=12),
                    bgcolor="#5A5F72",
                    height=35,
                    on_click=lambda e, m=m: seleccionar_metodo(m),
                )
                for m in lista_metodos
            ],
        )
    else:
        botones_metodo = ft.Text("No hay métodos de pago registrados.", color="white")

    btn_confirmar = ft.Button(
        content=ft.Text("Confirmar Venta", color="white", weight="bold"),
        bgcolor="#4A6741",
        width=250,
        height=50,
        on_click=confirmar_venta,
    )

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
                proveedor_text,
                proveedores_column,
                proveedor_costo_text,
                mensaje_venta_text,
                ft.Container(height=15),
                btn_confirmar,
            ],
        ),
    )

    campo_busqueda = ft.TextField(
        label="Buscar producto",
        hint_text="hamburguesa, papas, coca...",
        on_change=lambda e: (busqueda.__setitem__("texto", e.control.value or ""), refrescar_menu()),
        border_radius=12,
    )

    contenedor_menu.content = construir_tabs()

    panel_menu = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Text("NUEVA VENTA", size=22, weight="bold", color="white"),
                campo_busqueda,
                ft.Container(expand=True, content=contenedor_menu),
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[
            navbar,
            ft.Row(
                expand=True,
                controls=[panel_menu, panel_carrito],
            ),
        ],
    )

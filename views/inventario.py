import flet as ft

from database.database import SessionLocal
from database.models import inventario, rol


def formato_entero(valor):
    return str(int(valor or 0))


def inventario_view(page: ft.Page, navbar, usuario_actual=None):
    db = SessionLocal()
    rol_usuario = None
    if usuario_actual:
        rol_usuario = db.query(rol).filter(rol.id_rol == usuario_actual.id_rol).first()
    es_admin = bool(rol_usuario and rol_usuario.nombre == "ADMIN")
    db.close()

    filtro = {"texto": ""}
    tabla_container = ft.Container(expand=True)

    def obtener_items():
        db = SessionLocal()
        try:
            items = db.query(inventario).order_by(inventario.nombre.asc()).all()
            return items
        finally:
            db.close()

    def obtener_categorias():
        db = SessionLocal()
        try:
            return [
                categoria
                for categoria, in db.query(inventario.categoria)
                .filter(inventario.categoria.isnot(None), inventario.categoria != "")
                .distinct()
                .order_by(inventario.categoria.asc())
                .all()
            ]
        finally:
            db.close()

    def color_estado(item):
        if item.estado != "ACTIVO":
            return "#9AA0B4"
        if item.cantidad <= 0:
            return "#FF7B7B"
        if item.cantidad <= item.stock_minimo:
            return "#F2C744"
        return "#7AE582"

    def texto_estado(item):
        if item.estado != "ACTIVO":
            return "INACTIVO"
        if item.cantidad <= 0:
            return "AGOTADO"
        if item.cantidad <= item.stock_minimo:
            return "BAJO"
        return "OK"

    def abrir_formulario(item=None):
        nombre = ft.TextField(label="Nombre", value=item.nombre if item else "")
        categorias = obtener_categorias()
        categoria_nueva = ft.TextField(label="Nueva categoría", visible=False)
        categoria = ft.Dropdown(
            label="Categoría",
            value=item.categoria if item and item.categoria in categorias else None,
            options=[
                *[ft.dropdown.Option(valor) for valor in categorias],
                ft.dropdown.Option("__nueva__", "Crear nueva categoría..."),
            ],
        )

        def cambiar_categoria(e):
            categoria_nueva.visible = categoria.value == "__nueva__"
            page.update()

        categoria.on_change = cambiar_categoria
        unidad = ft.TextField(label="Unidad de medida", value=item.unidad_medida if item else "")
        cantidad = ft.TextField(label="Cantidad", value=formato_entero(item.cantidad) if item else "0")
        stock_minimo = ft.TextField(label="Stock mínimo", value=formato_entero(item.stock_minimo) if item else "0")
        costo_unitario = ft.TextField(label="Costo unitario", value=str(item.costo_unitario if item else 0))
        estado = ft.Dropdown(
            label="Estado",
            value=item.estado if item else "ACTIVO",
            options=[
                ft.dropdown.Option("ACTIVO"),
                ft.dropdown.Option("INACTIVO"),
            ],
        )
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def guardar(e):
            categoria_valor = (
                categoria_nueva.value.strip()
                if categoria.value == "__nueva__"
                else (categoria.value or "").strip()
            )
            if not nombre.value.strip() or not categoria_valor or not unidad.value.strip():
                mensaje.value = "Completa nombre, categoría y unidad."
                page.update()
                return

            try:
                cantidad_valor = int(cantidad.value)
                stock_minimo_valor = int(stock_minimo.value)
                costo_unitario_valor = float(costo_unitario.value)
            except ValueError:
                mensaje.value = "Cantidad y stock mínimo deben ser enteros; el costo debe ser numérico."
                page.update()
                return

            db = SessionLocal()
            try:
                if item is None:
                    db.add(
                        inventario(
                            nombre=nombre.value.strip(),
                            categoria=categoria_valor,
                            unidad_medida=unidad.value.strip(),
                            cantidad=cantidad_valor,
                            stock_minimo=stock_minimo_valor,
                            costo_unitario=costo_unitario_valor,
                            estado=estado.value or "ACTIVO",
                        )
                    )
                else:
                    registro = db.query(inventario).filter(inventario.id_inventario == item.id_inventario).first()
                    if not registro:
                        mensaje.value = "No fue posible actualizar el registro."
                        page.update()
                        return
                    registro.nombre = nombre.value.strip()
                    registro.categoria = categoria_valor
                    registro.unidad_medida = unidad.value.strip()
                    registro.cantidad = cantidad_valor
                    registro.stock_minimo = stock_minimo_valor
                    registro.costo_unitario = costo_unitario_valor
                    registro.estado = estado.value or "ACTIVO"

                db.commit()
            finally:
                db.close()

            page.pop_dialog()
            refrescar()
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Inventario actualizado", color="#7AE582"),
                    content=ft.Text(f"Ajuste aplicado a {item.nombre}."),
                    actions=[ft.TextButton("Aceptar", on_click=lambda e: page.pop_dialog())],
                )
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar producto" if item else "Agregar producto"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    tight=True,
                    scroll="auto",
                    controls=[
                        nombre,
                        categoria,
                        categoria_nueva,
                        unidad,
                        cantidad,
                        stock_minimo,
                        costo_unitario,
                        estado,
                        mensaje,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Guardar", on_click=guardar),
            ],
        )
        page.show_dialog(dialog)

    def abrir_ajuste(item):
        if not es_admin:
            return
        ajuste = ft.TextField(label="Ajuste de cantidad", value="0")
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def guardar(e):
            try:
                delta = int(ajuste.value)
            except ValueError:
                mensaje.value = "El ajuste debe ser un número entero."
                page.update()
                return

            db = SessionLocal()
            try:
                registro = db.query(inventario).filter(inventario.id_inventario == item.id_inventario).first()
                if not registro:
                    mensaje.value = "No fue posible actualizar el inventario."
                    page.update()
                    return
                registro.cantidad = max(0, registro.cantidad + delta)
                db.commit()
            finally:
                db.close()

            page.pop_dialog()
            refrescar()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Ajustar cantidad: {item.nombre}"),
            content=ft.Column(tight=True, controls=[ft.Text(f"Cantidad actual: {formato_entero(item.cantidad)}"), ajuste, mensaje]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Aplicar", on_click=guardar),
            ],
        )
        page.show_dialog(dialog)

    def construir_tabla(items, categoria=None):
        if not items:
            return ft.Container(
                alignment=ft.Alignment(0, 0),
                padding=30,
                content=ft.Text("No hay productos registrados en inventario.", color="white"),
            )

        columnas = [
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Categoría")),
            ft.DataColumn(ft.Text("Cantidad")),
            ft.DataColumn(ft.Text("Unidad")),
            ft.DataColumn(ft.Text("Stock mínimo")),
            ft.DataColumn(ft.Text("Estado")),
            ft.DataColumn(ft.Text("Acciones")),
        ]

        filas = []
        for item in items:
            acciones = []
            if es_admin:
                acciones = [
                    ft.TextButton("Editar", on_click=lambda e, it=item: abrir_formulario(it)),
                    ft.TextButton("Ajustar", on_click=lambda e, it=item: abrir_ajuste(it)),
                ]
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.nombre, color="white")),
                        ft.DataCell(ft.Text(item.categoria, color="white")),
                        ft.DataCell(ft.Text(formato_entero(item.cantidad), color="white")),
                        ft.DataCell(ft.Text(item.unidad_medida, color="white")),
                        ft.DataCell(ft.Text(formato_entero(item.stock_minimo), color="white")),
                        ft.DataCell(
                            ft.Text(
                                texto_estado(item),
                                color=color_estado(item),
                                weight="bold",
                            )
                        ),
                        ft.DataCell(
                            ft.Row(
                                spacing=8,
                                controls=acciones,
                            )
                        ),
                    ]
                )
            )

        tabla = ft.DataTable(
                columns=columnas,
                rows=filas,
                border=ft.Border(
                    left=ft.BorderSide(1, "#5A5F72"),
                    right=ft.BorderSide(1, "#5A5F72"),
                    top=ft.BorderSide(1, "#5A5F72"),
                    bottom=ft.BorderSide(1, "#5A5F72"),
                ),
                data_row_color={"hovered": "#404659"},
                heading_row_color="#2E3344",
                divider_thickness=1,
                column_spacing=20,
                horizontal_margin=10,
        )
        contenido = ft.Container(
            padding=10,
            content=ft.Column(
                scroll="auto",
                controls=[
                    ft.Row(
                        scroll="auto",
                        controls=[tabla],
                    )
                ],
            ),
        )
        if categoria:
            return ft.Column(
                spacing=6,
                controls=[
                    ft.Text(
                        categoria,
                        size=17,
                        weight="bold",
                        color="#F2C744",
                    ),
                    contenido,
                ],
            )
        return contenido

    def construir_tablas_por_categoria(items):
        grupos = {}
        for item in items:
            grupos.setdefault(item.categoria or "Sin categoría", []).append(item)
        return ft.Column(
            spacing=18,
            scroll="auto",
            controls=[
                construir_tabla(grupo, categoria)
                for categoria, grupo in sorted(grupos.items())
            ],
        )

    def refrescar():
        texto = filtro["texto"].strip().lower()
        items = obtener_items()
        if texto:
            items = [
                item
                for item in items
                if texto in item.nombre.lower()
                or texto in item.categoria.lower()
                or texto in item.unidad_medida.lower()
            ]
        tabla_container.content = construir_tablas_por_categoria(items)
        page.update()

    buscador = ft.TextField(
        label="Buscar en inventario",
        hint_text="nombre, categoría o unidad",
        on_change=lambda e: (filtro.__setitem__("texto", e.control.value or ""), refrescar()),
        border_radius=12,
    )

    tabla_container.content = construir_tablas_por_categoria(obtener_items())

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=15,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("INVENTARIO", size=24, weight="bold", color="white"),
                        ft.Button(
                            content=ft.Text("Agregar producto", color="white", weight="bold"),
                            bgcolor="#5A5F72",
                            on_click=lambda e: abrir_formulario(),
                            visible=es_admin,
                        ) if es_admin else ft.Container(),
                    ],
                ),
                buscador,
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        expand=True,
                        scroll="auto",
                        controls=[tabla_container],
                    ),
                ),
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta],
    )

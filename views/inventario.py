import flet as ft

from database.database import SessionLocal
from database.models import inventario


def inventario_view(page: ft.Page, navbar):
    filtro = {"texto": ""}
    tabla_container = ft.Container(expand=True)

    def obtener_items():
        db = SessionLocal()
        try:
            items = db.query(inventario).order_by(inventario.nombre.asc()).all()
            return items
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
        categoria = ft.TextField(label="Categoría", value=item.categoria if item else "")
        unidad = ft.TextField(label="Unidad de medida", value=item.unidad_medida if item else "")
        cantidad = ft.TextField(label="Cantidad", value=str(item.cantidad if item else 0))
        stock_minimo = ft.TextField(label="Stock mínimo", value=str(item.stock_minimo if item else 0))
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
            if not nombre.value.strip() or not categoria.value.strip() or not unidad.value.strip():
                mensaje.value = "Completa nombre, categoría y unidad."
                page.update()
                return

            try:
                cantidad_valor = float(cantidad.value)
                stock_minimo_valor = float(stock_minimo.value)
                costo_unitario_valor = float(costo_unitario.value)
            except ValueError:
                mensaje.value = "Cantidad, stock mínimo y costo deben ser numéricos."
                page.update()
                return

            db = SessionLocal()
            try:
                if item is None:
                    db.add(
                        inventario(
                            nombre=nombre.value.strip(),
                            categoria=categoria.value.strip(),
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
                    registro.categoria = categoria.value.strip()
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

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar producto" if item else "Agregar producto"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    tight=True,
                    scroll="auto",
                    controls=[nombre, categoria, unidad, cantidad, stock_minimo, costo_unitario, estado, mensaje],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Guardar", on_click=guardar),
            ],
        )
        page.show_dialog(dialog)

    def abrir_ajuste(item):
        ajuste = ft.TextField(label="Ajuste de cantidad", value="0")
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def guardar(e):
            try:
                delta = float(ajuste.value)
            except ValueError:
                mensaje.value = "El ajuste debe ser numérico."
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
            content=ft.Column(tight=True, controls=[ft.Text(f"Cantidad actual: {item.cantidad}"), ajuste, mensaje]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Aplicar", on_click=guardar),
            ],
        )
        page.show_dialog(dialog)

    def construir_tabla(items):
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
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.nombre, color="white")),
                        ft.DataCell(ft.Text(item.categoria, color="white")),
                        ft.DataCell(ft.Text(str(item.cantidad), color="white")),
                        ft.DataCell(ft.Text(item.unidad_medida, color="white")),
                        ft.DataCell(ft.Text(str(item.stock_minimo), color="white")),
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
                                controls=[
                                    ft.TextButton("Editar", on_click=lambda e, it=item: abrir_formulario(it)),
                                    ft.TextButton("Ajustar", on_click=lambda e, it=item: abrir_ajuste(it)),
                                ],
                            )
                        ),
                    ]
                )
            )

        return ft.Container(
            padding=10,
            content=ft.DataTable(
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
            ),
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
        tabla_container.content = construir_tabla(items)
        page.update()

    buscador = ft.TextField(
        label="Buscar en inventario",
        hint_text="nombre, categoría o unidad",
        on_change=lambda e: (filtro.__setitem__("texto", e.control.value or ""), refrescar()),
        border_radius=12,
    )

    tabla_container.content = construir_tabla(obtener_items())

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
                        ),
                    ],
                ),
                buscador,
                ft.Container(expand=True, content=tabla_container),
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=20,
        controls=[navbar, tarjeta],
    )

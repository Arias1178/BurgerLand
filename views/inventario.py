import flet as ft

from database.database import SessionLocal
from database.models import (
    categorias_inventario,
    detalles_compras,
    inventario,
    proveedores,
    rol,
)
from services.inventario_service import (
    cambiar_estado_categoria_inventario,
    cambiar_estado_insumo_inventario,
    contar_insumos_categoria,
    eliminar_categoria_inventario,
    eliminar_insumo_inventario,
    obtener_o_crear_categoria_inventario,
    sincronizar_categorias_inventario,
    vincular_producto_menu,
)


def formato_entero(valor):
    return str(int(valor or 0))


def formato_pesos(valor):
    return f"${float(valor or 0):,.0f}".replace(",", ".")


def inventario_view(page: ft.Page, navbar, usuario_actual=None):
    db = SessionLocal()
    rol_usuario = None
    if usuario_actual:
        rol_usuario = db.query(rol).filter(rol.id_rol == usuario_actual.id_rol).first()
    es_admin = bool(rol_usuario and rol_usuario.nombre == "ADMIN")
    db.close()

    filtro = {"texto": ""}
    mostrar_eliminados = {"valor": False}
    tabla_container = ft.Container(expand=True)

    def obtener_items(incluir_eliminados=False):
        db = SessionLocal()
        try:
            consulta = db.query(inventario)
            if not incluir_eliminados:
                consulta = consulta.filter(inventario.estado != "ELIMINADO")
            items = consulta.order_by(inventario.nombre.asc()).all()
            return items
        finally:
            db.close()

    def obtener_categorias(categoria_actual=None):
        db = SessionLocal()
        try:
            sincronizar_categorias_inventario(db)
            db.commit()
            return [
                categoria.nombre
                for categoria in db.query(categorias_inventario)
                .filter(
                    (categorias_inventario.estado == "ACTIVO")
                    | (categorias_inventario.nombre == categoria_actual)
                )
                .order_by(categorias_inventario.nombre.asc())
                .all()
            ]
        finally:
            db.close()

    def abrir_gestion_categorias():
        db = SessionLocal()
        try:
            sincronizar_categorias_inventario(db)
            db.commit()
            categorias = db.query(categorias_inventario).order_by(
                categorias_inventario.nombre.asc()
            ).all()
            datos = [
                (categoria.id_categoria_inventario, categoria.nombre,
                 categoria.estado,
                 contar_insumos_categoria(db, categoria.nombre))
                for categoria in categorias
            ]
        finally:
            db.close()

        if not datos:
            controles = [ft.Text("No hay categorías registradas.", color="white")]
        else:
            controles = [
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text(
                            f"{nombre} — {estado} ({cantidad} insumos)",
                            color="white",
                            expand=True,
                        ),
                        ft.TextButton(
                            "Restaurar" if estado == "ELIMINADO" else
                            "Habilitar" if estado == "INACTIVO" else "Inhabilitar",
                            on_click=lambda e, cid=id_categoria, n=nombre, actual=estado:
                                confirmar_estado_categoria(
                                    cid, n, actual,
                                    "ACTIVO" if actual in {"INACTIVO", "ELIMINADO"} else "INACTIVO",
                                ),
                        ),
                        ft.TextButton(
                            "Eliminar",
                            on_click=lambda e, cid=id_categoria, n=nombre, actual=estado:
                                confirmar_estado_categoria(cid, n, actual, "ELIMINADO"),
                        ) if estado != "ELIMINADO" else ft.Container(),
                        ft.TextButton(
                            "Eliminar definitivamente",
                            disabled=cantidad > 0,
                            on_click=lambda e, cid=id_categoria, n=nombre:
                                confirmar_eliminar_categoria(cid, n),
                        ) if estado != "ACTIVO" else ft.Container(),
                    ],
                )
                for id_categoria, nombre, estado, cantidad in datos
            ]

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Categorías del inventario"),
                content=ft.Container(
                    width=640,
                    content=ft.Column(tight=True, scroll="auto", controls=controles),
                ),
                actions=[
                    ft.TextButton("Cerrar", on_click=lambda e: page.pop_dialog()),
                ],
            )
        )

    def confirmar_estado_categoria(id_categoria, nombre, estado_actual, nuevo_estado):
        page.pop_dialog()
        acciones = {
            "ACTIVO": "restaurar" if estado_actual == "ELIMINADO" else "habilitar",
            "INACTIVO": "inhabilitar",
            "ELIMINADO": "eliminar",
        }
        accion = acciones[nuevo_estado]
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def cambiar(e):
            db = SessionLocal()
            try:
                cambiar_estado_categoria_inventario(db, id_categoria, nuevo_estado)
            except ValueError as error:
                mensaje.value = str(error)
                page.update()
                return
            finally:
                db.close()
            page.pop_dialog()
            refrescar()
            abrir_gestion_categorias()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"{accion.capitalize()} categoría"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            (
                                f"¿Eliminar la categoría «{nombre}»? Quedará oculta, "
                                "pero podrás restaurarla; no se borrará definitivamente."
                                if nuevo_estado == "ELIMINADO"
                                else f"¿Deseas {accion} la categoría «{nombre}»?"
                            ),
                            color="white",
                        ),
                        mensaje,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton(accion.capitalize(), on_click=cambiar),
                ],
            )
        )

    def confirmar_eliminar_categoria(id_categoria, nombre):
        page.pop_dialog()
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def eliminar(e):
            db = SessionLocal()
            try:
                eliminar_categoria_inventario(db, id_categoria)
            except ValueError as error:
                mensaje.value = str(error)
                page.update()
                return
            finally:
                db.close()
            page.pop_dialog()
            refrescar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar categoría definitivamente"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            f"¿Eliminar la categoría «{nombre}»? "
                            "Esta acción no se puede deshacer.",
                            color="white",
                        ),
                        mensaje,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton("Eliminar definitivamente", on_click=eliminar),
                ],
            )
        )

    def confirmar_estado_insumo(item, nuevo_estado):
        acciones = {
            "ACTIVO": "restaurar" if item.estado == "ELIMINADO" else "habilitar",
            "INACTIVO": "inhabilitar",
            "ELIMINADO": "eliminar",
        }
        accion = acciones[nuevo_estado]
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def cambiar(e):
            db = SessionLocal()
            try:
                cambiar_estado_insumo_inventario(
                    db, item.id_inventario, nuevo_estado
                )
            except ValueError as error:
                mensaje.value = str(error)
                page.update()
                return
            finally:
                db.close()
            page.pop_dialog()
            refrescar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"{accion.capitalize()} insumo"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            (
                                f"¿Eliminar «{item.nombre}»? Quedará oculto, "
                                "pero podrás restaurarlo; no se borrará definitivamente."
                                if nuevo_estado == "ELIMINADO"
                                else f"¿Deseas {accion} «{item.nombre}»?"
                            ),
                            color="white",
                        ),
                        mensaje,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton(accion.capitalize(), on_click=cambiar),
                ],
            )
        )

    def confirmar_eliminar_insumo(item):
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def eliminar(e):
            db = SessionLocal()
            try:
                eliminar_insumo_inventario(db, item.id_inventario)
            except ValueError as error:
                mensaje.value = str(error)
                page.update()
                return
            finally:
                db.close()
            page.pop_dialog()
            refrescar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar insumo definitivamente"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            f"¿Eliminar «{item.nombre}» del inventario? "
                            "Esta acción no se puede deshacer.",
                            color="white",
                        ),
                        mensaje,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton("Eliminar definitivamente", on_click=eliminar),
                ],
            )
        )

    def color_estado(item):
        if item.estado != "ACTIVO":
            return "#9AA0B4"
        if item.cantidad <= 0:
            return "#FF7B7B"
        if item.cantidad <= item.stock_minimo:
            return "#F2C744"
        return "#7AE582"

    def texto_estado(item):
        if item.estado == "ELIMINADO":
            return "ELIMINADO"
        if item.estado != "ACTIVO":
            return "INACTIVO"
        if item.cantidad <= 0:
            return "AGOTADO"
        if item.cantidad <= item.stock_minimo:
            return "BAJO"
        return "OK"

    def abrir_formulario(item=None):
        nombre = ft.TextField(label="Nombre", value=item.nombre if item else "")
        db = SessionLocal()
        try:
            consulta_proveedores = db.query(proveedores)
            if item and item.id_proveedor:
                consulta_proveedores = consulta_proveedores.filter(
                    (proveedores.estado == "ACTIVO")
                    | (proveedores.id_proveedor == item.id_proveedor)
                )
            else:
                consulta_proveedores = consulta_proveedores.filter(
                    proveedores.estado == "ACTIVO"
                )
            proveedores_disponibles = consulta_proveedores.order_by(
                proveedores.nombre.asc()
            ).all()
        finally:
            db.close()
        proveedor = ft.Dropdown(
            label="Proveedor",
            value=(
                str(item.id_proveedor)
                if item and item.id_proveedor
                else "__none__"
            ),
            options=[
                ft.dropdown.Option("__none__", "Sin proveedor específico"),
                *[
                    ft.dropdown.Option(str(registro.id_proveedor), registro.nombre)
                    for registro in proveedores_disponibles
                ],
            ],
        )
        categorias = obtener_categorias(item.categoria if item else None)
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
            categoria_nueva.visible = e.control.value == "__nueva__"
            page.update()

        categoria.on_select = cambiar_categoria
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
                categoria_registro = obtener_o_crear_categoria_inventario(
                    db, categoria_valor
                )
                if categoria_registro.estado != "ACTIVO" and (
                    item is None or categoria_valor != item.categoria
                ):
                    mensaje.value = "No puedes asignar un insumo a una categoría inhabilitada o eliminada."
                    page.update()
                    return
                proveedor_id = (
                    int(proveedor.value)
                    if proveedor.value and proveedor.value != "__none__"
                    else None
                )
                if item is None:
                    registro = inventario(
                        nombre=nombre.value.strip(),
                        categoria=categoria_valor,
                        unidad_medida=unidad.value.strip(),
                        cantidad=cantidad_valor,
                        stock_minimo=stock_minimo_valor,
                        costo_unitario=costo_unitario_valor,
                        id_proveedor=proveedor_id,
                        estado=estado.value or "ACTIVO",
                    )
                    db.add(registro)
                else:
                    registro = db.query(inventario).filter(inventario.id_inventario == item.id_inventario).first()
                    if not registro:
                        mensaje.value = "No fue posible actualizar el registro."
                        page.update()
                        return
                    if (
                        registro.id_proveedor != proveedor_id
                        and db.query(detalles_compras)
                        .filter(
                            detalles_compras.id_inventario
                            == registro.id_inventario
                        )
                        .count()
                    ):
                        mensaje.value = (
                            "No puedes cambiar el proveedor de un artículo con compras "
                            "registradas; conserva su historial y crea otro SKU."
                        )
                        page.update()
                        return
                    registro.nombre = nombre.value.strip()
                    registro.categoria = categoria_valor
                    registro.unidad_medida = unidad.value.strip()
                    registro.cantidad = cantidad_valor
                    registro.stock_minimo = stock_minimo_valor
                    registro.costo_unitario = costo_unitario_valor
                    registro.id_proveedor = proveedor_id
                    registro.estado = estado.value or "ACTIVO"

                db.flush()
                vincular_producto_menu(db, registro)
                db.commit()
            finally:
                db.close()

            page.pop_dialog()
            refrescar()
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        "Producto agregado" if item is None else "Producto actualizado",
                        color="#7AE582",
                    ),
                    content=ft.Text(
                        f"Se {'agregó' if item is None else 'actualizó'} "
                        f"{nombre.value.strip()} correctamente."
                    ),
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
                        proveedor,
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

    def construir_tabla(items, categoria=None, proveedores_por_id=None):
        if not items:
            return ft.Container(
                alignment=ft.Alignment(0, 0),
                padding=30,
                content=ft.Text("No hay productos registrados en inventario.", color="white"),
            )

        columnas = [
            ft.DataColumn(ft.Text("Producto")),
            ft.DataColumn(ft.Text("Categoría")),
            ft.DataColumn(ft.Text("Proveedor")),
            ft.DataColumn(ft.Text("Costo unitario")),
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
                if item.estado == "ELIMINADO":
                    acciones = [
                        ft.TextButton(
                            "Restaurar",
                            on_click=lambda e, it=item:
                                confirmar_estado_insumo(it, "ACTIVO"),
                        ),
                    ]
                else:
                    acciones = [
                        ft.TextButton("Editar", on_click=lambda e, it=item: abrir_formulario(it)),
                        ft.TextButton("Ajustar", on_click=lambda e, it=item: abrir_ajuste(it)),
                        ft.TextButton(
                            "Inhabilitar" if item.estado == "ACTIVO" else "Habilitar",
                            on_click=lambda e, it=item: confirmar_estado_insumo(
                                it,
                                "INACTIVO" if it.estado == "ACTIVO" else "ACTIVO",
                            ),
                        ),
                        ft.TextButton(
                            "Eliminar",
                            on_click=lambda e, it=item:
                                confirmar_estado_insumo(it, "ELIMINADO"),
                        ),
                    ]
                if item.estado != "ACTIVO":
                    acciones.append(
                        ft.TextButton(
                            "Eliminar definitivamente",
                            on_click=lambda e, it=item: confirmar_eliminar_insumo(it),
                        )
                    )
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.nombre, color="white")),
                        ft.DataCell(ft.Text(item.categoria, color="white")),
                        ft.DataCell(
                            ft.Text(
                                (proveedores_por_id or {}).get(item.id_proveedor, "—"),
                                color="white",
                            )
                        ),
                        ft.DataCell(ft.Text(formato_pesos(item.costo_unitario), color="white")),
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
        db = SessionLocal()
        try:
            proveedores_por_id = obtener_proveedores_por_id(db)
            estados_categoria = {
                categoria.nombre: categoria.estado
                for categoria in db.query(categorias_inventario).all()
            }
        finally:
            db.close()
        return ft.Column(
            spacing=18,
            scroll="auto",
            controls=[
                construir_tabla(
                    grupo,
                    categoria + (
                        f" ({estados_categoria[categoria]})"
                        if estados_categoria.get(categoria, "ACTIVO") != "ACTIVO"
                        else ""
                    ),
                    proveedores_por_id,
                )
                for categoria, grupo in sorted(grupos.items())
            ],
        )

    def obtener_proveedores_por_id(db=None):
        cerrar_db = db is None
        if db is None:
            db = SessionLocal()
        try:
            return {
                proveedor.id_proveedor: proveedor.nombre
                for proveedor in db.query(proveedores).all()
            }
        finally:
            if cerrar_db:
                db.close()

    def refrescar():
        texto = filtro["texto"].strip().lower()
        items = obtener_items(mostrar_eliminados["valor"])
        proveedores_por_id = obtener_proveedores_por_id()
        if texto:
            items = [
                item
                for item in items
                if texto in item.nombre.lower()
                or texto in item.categoria.lower()
                or texto in item.unidad_medida.lower()
                or texto in proveedores_por_id.get(item.id_proveedor, "").lower()
            ]
        tabla_container.content = construir_tablas_por_categoria(items)
        page.update()

    buscador = ft.TextField(
        label="Buscar en inventario",
        hint_text="nombre, categoría o unidad",
        on_change=lambda e: (filtro.__setitem__("texto", e.control.value or ""), refrescar()),
        border_radius=12,
    )

    def cambiar_visibilidad_eliminados(e):
        mostrar_eliminados["valor"] = bool(e.control.value)
        refrescar()

    mostrar_eliminados_control = ft.Checkbox(
        label="Mostrar eliminados",
        value=False,
        on_change=cambiar_visibilidad_eliminados,
    ) if es_admin else ft.Container()

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
                        ft.Button(
                            content=ft.Text("Categorías", color="white", weight="bold"),
                            bgcolor="#5A5F72",
                            on_click=lambda e: abrir_gestion_categorias(),
                        ) if es_admin else ft.Container(),
                        mostrar_eliminados_control,
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

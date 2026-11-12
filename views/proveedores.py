import flet as ft

from database.database import SessionLocal
from database.models import (
    catalogo_proveedores,
    categorias_proveedores,
    compras,
    detalles_compras,
    gastos,
    inventario,
    productos,
    proveedores,
    rol,
    ventas,
)


ESTADO_ACTIVO = "ACTIVO"
ESTADO_INACTIVO = "INACTIVO"


def proveedores_view(page: ft.Page, navbar, usuario_actual=None):
    db = SessionLocal()
    rol_usuario = None
    if usuario_actual:
        rol_usuario = db.query(rol).filter(rol.id_rol == usuario_actual.id_rol).first()
    es_admin = bool(rol_usuario and rol_usuario.nombre == "ADMIN")
    db.close()

    contenedor = ft.Container(expand=True)
    filtro = {"texto": ""}

    def badge(texto, color):
        return ft.Container(
            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            border_radius=999,
            bgcolor=color,
            content=ft.Text(texto, color="white", size=12, weight="bold"),
        )

    def tarjeta_resumen(etiqueta, valor, color, icono):
        return ft.Container(
            width=250,
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
            border_radius=14,
            bgcolor="#2E3344",
            border=ft.Border.all(1, "#454B60"),
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Text(str(valor), size=23, weight="bold", color=color),
                    ft.Text(etiqueta, size=12, color="#B7BDCE"),
                ],
            ),
        )

    def obtener_proveedores():
        db_local = SessionLocal()
        try:
            query = db_local.query(proveedores).order_by(proveedores.nombre.asc())
            registros = query.all()
            if es_admin:
                return registros
            categorias_inactivas = {
                categoria.nombre
                for categoria in db_local.query(categorias_proveedores).filter(
                    categorias_proveedores.estado == ESTADO_INACTIVO
                ).all()
            }
            return [
                registro
                for registro in registros
                if registro.estado == ESTADO_ACTIVO
                and (registro.que_provee or "") not in categorias_inactivas
            ]
        finally:
            db_local.close()

    def obtener_categorias():
        db_local = SessionLocal()
        try:
            return [
                categoria.nombre
                for categoria in db_local.query(categorias_proveedores)
                .filter(categorias_proveedores.estado == ESTADO_ACTIVO)
                .order_by(categorias_proveedores.nombre.asc())
                .all()
            ]
        finally:
            db_local.close()

    def cambiar_estado(prov, nuevo_estado):
        db_local = SessionLocal()
        try:
            registro = db_local.query(proveedores).filter(proveedores.id_proveedor == prov.id_proveedor).first()
            if not registro:
                return False
            registro.estado = nuevo_estado
            db_local.commit()
            return True
        finally:
            db_local.close()

    def alternar_estado(prov):
        nuevo_estado = ESTADO_INACTIVO if prov.estado == ESTADO_ACTIVO else ESTADO_ACTIVO
        if cambiar_estado(prov, nuevo_estado):
            recargar()
            return True
        return False

    def eliminar_proveedor(prov):
        db_local = SessionLocal()
        try:
            registro = db_local.query(proveedores).filter(
                proveedores.id_proveedor == prov.id_proveedor
            ).first()
            if not registro:
                return "El proveedor ya no existe."
            tiene_historial = any(
                consulta.count()
                for consulta in (
                    db_local.query(compras).filter(
                        compras.id_proveedor == prov.id_proveedor
                    ),
                    db_local.query(gastos).filter(
                        gastos.id_proveedor == prov.id_proveedor
                    ),
                    db_local.query(ventas).filter(
                        ventas.id_proveedor == prov.id_proveedor
                    ),
                    db_local.query(productos).filter(
                        productos.id_proveedor == prov.id_proveedor
                    ),
                    db_local.query(inventario).filter(
                        inventario.id_proveedor == prov.id_proveedor
                    ),
                )
            )
            if tiene_historial:
                return (
                    "No se puede eliminar porque está asociado a productos del menú, "
                    "inventario, compras, gastos o ventas. Inhabilítalo para conservar esas referencias."
                )
            categoria_nombre = registro.que_provee
            db_local.query(catalogo_proveedores).filter(
                catalogo_proveedores.id_proveedor == prov.id_proveedor
            ).delete(synchronize_session=False)
            db_local.delete(registro)
            categoria = db_local.query(categorias_proveedores).filter(
                categorias_proveedores.nombre == categoria_nombre
            ).first()
            if categoria and not db_local.query(proveedores).filter(
                proveedores.que_provee == categoria_nombre,
                proveedores.id_proveedor != prov.id_proveedor,
            ).count():
                db_local.delete(categoria)
            db_local.commit()
            return None
        finally:
            db_local.close()

    def confirmar_eliminacion_proveedor(prov):
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def eliminar(_):
            error = eliminar_proveedor(prov)
            if error:
                mensaje.value = error
                page.update()
                return
            page.pop_dialog()
            recargar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar proveedor definitivamente"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            f"Se eliminará permanentemente a {prov.nombre} y su catálogo. "
                            "Esta acción no se puede deshacer.",
                            color="white",
                        ),
                        mensaje,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton(
                        "Eliminar definitivamente",
                        on_click=eliminar,
                    ),
                ],
            )
        )

    def gestionar_categoria(nombre_categoria):
        db_local = SessionLocal()
        try:
            categoria = db_local.query(categorias_proveedores).filter(
                categorias_proveedores.nombre == nombre_categoria
            ).first()
            if not categoria:
                return
            estado_categoria = categoria.estado
        finally:
            db_local.close()

        def cerrar(_):
            page.pop_dialog()

        def cambiar_estado_categoria(_):
            db = SessionLocal()
            try:
                categoria = db.query(categorias_proveedores).filter(
                    categorias_proveedores.nombre == nombre_categoria
                ).first()
                if categoria:
                    categoria.estado = (
                        ESTADO_INACTIVO
                        if categoria.estado == ESTADO_ACTIVO
                        else ESTADO_ACTIVO
                    )
                    db.commit()
            finally:
                db.close()
            page.pop_dialog()
            recargar()

        def eliminar_categoria(_):
            db = SessionLocal()
            try:
                if db.query(proveedores).filter(
                    proveedores.que_provee == nombre_categoria
                ).count() > 0:
                    mensaje.value = "Mueve primero los proveedores de esta categoría."
                    page.update()
                    return
                categoria = db.query(categorias_proveedores).filter(
                    categorias_proveedores.nombre == nombre_categoria
                ).first()
                if categoria:
                    db.delete(categoria)
                    db.commit()
            finally:
                db.close()
            page.pop_dialog()
            recargar()

        mensaje = ft.Text("", color="#FF7B7B", size=12)
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Administrar categoría: {nombre_categoria}"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            "Una categoría inhabilitada no estará disponible para usuarios no administradores.",
                            color="#C9CEDB",
                        ),
                        mensaje,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar),
                    ft.TextButton(
                        "Habilitar" if estado_categoria == ESTADO_INACTIVO else "Inhabilitar",
                        on_click=cambiar_estado_categoria,
                    ),
                    ft.TextButton("Eliminar definitivamente", on_click=eliminar_categoria),
                ],
            )
        )

    def ver_compras(prov):
        db_local = SessionLocal()
        try:
            registros = (
                db_local.query(compras)
                .filter(compras.id_proveedor == prov.id_proveedor)
                .order_by(compras.fecha.desc())
                .all()
            )
            contenido = []
            for compra in registros:
                detalles = (
                    db_local.query(detalles_compras, inventario)
                    .join(inventario, detalles_compras.id_inventario == inventario.id_inventario)
                    .filter(detalles_compras.id_compra == compra.id_compra)
                    .all()
                )
                items = ", ".join(
                    f"{detalle.cantidad} {item.nombre}"
                    for detalle, item in detalles
                )
                contenido.append(
                    ft.Text(
                        f"{compra.fecha.strftime('%d/%m/%Y')} — {items or 'Sin ítems'} — "
                        f"${compra.total:,.0f}".replace(",", "."),
                        color="white",
                    )
                )
        finally:
            db_local.close()

        if not contenido:
            contenido = [
                ft.Text(
                    "Aún no hay compras registradas para este proveedor.",
                    color="#C9CEDB",
                )
            ]

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Compras de {prov.nombre}"),
                content=ft.Container(
                    width=620,
                    content=ft.Column(tight=True, spacing=10, controls=contenido),
                ),
                actions=[ft.TextButton("Cerrar", on_click=lambda e: page.pop_dialog())],
            )
        )

    def ver_catalogo(prov):
        def editar_precio_catalogo(articulo):
            precio = ft.TextField(
                label="Precio unitario de compra ($)",
                value=(
                    str(articulo.precio_unitario)
                    if articulo.precio_unitario is not None
                    else ""
                ),
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            mensaje = ft.Text("", color="#FF7B7B", size=12)

            def guardar(_):
                db_local = SessionLocal()
                try:
                    from services.proveedores_service import actualizar_precio_catalogo

                    actualizar_precio_catalogo(
                        db_local,
                        articulo.id_producto_proveedor,
                        precio.value,
                    )
                except ValueError as error:
                    db_local.rollback()
                    mensaje.value = str(error)
                    page.update()
                    return
                finally:
                    db_local.close()
                page.pop_dialog()
                ver_catalogo(prov)

            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(f"Precio de {articulo.nombre}"),
                    content=ft.Column(
                        tight=True,
                        controls=[
                            precio,
                            mensaje,
                        ],
                    ),
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                        ft.TextButton("Guardar", on_click=guardar),
                    ],
                )
            )

        db_local = SessionLocal()
        try:
            registros = (
                db_local.query(catalogo_proveedores)
                .filter(catalogo_proveedores.id_proveedor == prov.id_proveedor)
                .order_by(catalogo_proveedores.grupo.asc(), catalogo_proveedores.nombre.asc())
                .all()
            )
            grupos = {}
            for registro in registros:
                grupos.setdefault(registro.grupo, []).append(registro)
            contenido = []
            for grupo, articulos in grupos.items():
                contenido.append(
                    ft.Text(
                        grupo,
                        color="#F2C744",
                        size=15,
                        weight="bold",
                    )
                )
                contenido.extend(
                    ft.Column(
                        tight=True,
                        spacing=2,
                        controls=[
                            ft.Text(articulo.nombre, color="white", weight="bold"),
                            ft.Text(
                                articulo.detalles or "Sin detalles de presentación.",
                                color="#C9CEDB",
                                size=12,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        (
                                            f"Precio unitario de compra: "
                                            f"${articulo.precio_unitario:,.0f}".replace(",", ".")
                                            if articulo.precio_unitario is not None
                                            else "Precio unitario de compra sin registrar"
                                        ),
                                        color="#F2C744",
                                        size=12,
                                    ),
                                    ft.TextButton(
                                        "Definir precio" if articulo.precio_unitario is None else "Editar precio",
                                        visible=es_admin,
                                        on_click=lambda e, item=articulo: editar_precio_catalogo(item),
                                    ) if es_admin else ft.Container(),
                                ],
                            ),
                        ],
                    )
                    for articulo in articulos
                )
        finally:
            db_local.close()

        if not contenido:
            contenido = [
                ft.Text(
                    "Este proveedor aún no tiene artículos registrados en su catálogo.",
                    color="#C9CEDB",
                )
            ]

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Catálogo de {prov.nombre}"),
                content=ft.Container(
                    width=620,
                    height=520,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        scroll="auto",
                        controls=contenido,
                    ),
                ),
                actions=[
                    ft.TextButton("Cerrar", on_click=lambda e: page.pop_dialog())
                ],
            )
        )

    def abrir_formulario(prov=None):
        nombre = ft.TextField(label="Nombre del proveedor", value=prov.nombre if prov else "")
        categorias = obtener_categorias()
        categoria_nueva = ft.TextField(label="Nueva categoría de suministro", visible=False)
        que_provee = ft.Dropdown(
            label="Categoría de suministro",
            value=prov.que_provee if prov and prov.que_provee in categorias else None,
            options=[
                *[ft.dropdown.Option(valor) for valor in categorias],
                ft.dropdown.Option("__nueva__", "Crear nueva categoría..."),
            ],
        )

        def cambiar_categoria(e):
            categoria_nueva.visible = e.control.value == "__nueva__"
            page.update()

        que_provee.on_select = cambiar_categoria
        telefono = ft.TextField(label="Número de teléfono", value=prov.telefono if prov else "")
        correo = ft.TextField(
            label="Correo (opcional)",
            value=prov.correo or "" if prov else "",
        )
        cuanto_cobra = ft.TextField(label="Cuánto cobra", value=str(prov.cuanto_cobra if prov else 0))
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def guardar(mensaje_local):
            categoria_valor = (
                categoria_nueva.value.strip()
                if que_provee.value == "__nueva__"
                else (que_provee.value or "").strip()
            )
            if not nombre.value.strip() or not categoria_valor:
                mensaje_local.value = "Completa el nombre del proveedor y su categoría de suministro."
                return False

            try:
                cobro = float(cuanto_cobra.value)
            except ValueError:
                mensaje_local.value = "Cuánto cobra debe ser numérico."
                return False

            db_local = SessionLocal()
            try:
                correo_valor = correo.value.strip() or None
                consulta_correo = db_local.query(proveedores).filter(
                    proveedores.correo == correo_valor
                )
                if prov is not None:
                    consulta_correo = consulta_correo.filter(
                        proveedores.id_proveedor != prov.id_proveedor
                    )
                if correo_valor and consulta_correo.first():
                    mensaje_local.value = "Ese correo ya está registrado para otro proveedor."
                    return False
                if not db_local.query(categorias_proveedores).filter(
                    categorias_proveedores.nombre == categoria_valor
                ).first():
                    db_local.add(categorias_proveedores(nombre=categoria_valor, estado=ESTADO_ACTIVO))
                if prov is None:
                    db_local.add(
                        proveedores(
                            nombre=nombre.value.strip(),
                            que_provee=categoria_valor,
                            telefono=telefono.value.strip() or None,
                            correo=correo_valor,
                            cuanto_cobra=cobro,
                            estado=ESTADO_ACTIVO,
                        )
                    )
                else:
                    registro = db_local.query(proveedores).filter(proveedores.id_proveedor == prov.id_proveedor).first()
                    if not registro:
                        mensaje_local.value = "No fue posible actualizar el proveedor."
                        return False
                    registro.nombre = nombre.value.strip()
                    registro.que_provee = categoria_valor
                    registro.telefono = telefono.value.strip() or None
                    registro.correo = correo_valor
                    registro.cuanto_cobra = cobro
                db_local.commit()
                return True
            finally:
                db_local.close()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo proveedor" if prov is None else "Editar proveedor"),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    tight=True,
                    scroll="auto",
                    controls=[
                        nombre,
                        que_provee,
                        categoria_nueva,
                        telefono,
                        correo,
                        cuanto_cobra,
                        mensaje,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Guardar", on_click=lambda e: (page.pop_dialog() if guardar(mensaje) else page.update())),
            ],
        )
        page.show_dialog(dialog)

    def _contar_articulos_catalogo(id_proveedor):
        db_local = SessionLocal()
        try:
            return db_local.query(catalogo_proveedores).filter(
                catalogo_proveedores.id_proveedor == id_proveedor
            ).count()
        finally:
            db_local.close()

    def construir_tabla(items):
        filas = []
        for prov in items:
            estado = prov.estado or ESTADO_ACTIVO
            acciones = [
                ft.TextButton(
                    "Compras",
                    tooltip="Consultar historial de compras",
                    style=ft.ButtonStyle(color="#9CCBFF"),
                    on_click=lambda e, p=prov: ver_compras(p),
                )
            ]
            cantidad_catalogo = _contar_articulos_catalogo(prov.id_proveedor)
            acciones.insert(
                0,
                ft.TextButton(
                    f"Catálogo ({cantidad_catalogo})",
                    tooltip="Consultar artículos que ofrece este proveedor",
                    style=ft.ButtonStyle(color="#9CCBFF"),
                    on_click=lambda e, p=prov: ver_catalogo(p),
                ),
            )
            if es_admin:
                acciones.extend(
                    [
                        ft.TextButton(
                            "Editar",
                            tooltip="Editar proveedor",
                            style=ft.ButtonStyle(color="#F2C744"),
                            on_click=lambda e, p=prov: abrir_formulario(p),
                        ),
                        ft.TextButton(
                            "Habilitar" if estado == ESTADO_INACTIVO else "Inhabilitar",
                            tooltip="Cambiar estado del proveedor",
                            style=ft.ButtonStyle(
                                color="#7AE582" if estado == ESTADO_INACTIVO else "#FF9B9B"
                            ),
                            on_click=lambda e, p=prov: alternar_estado(p),
                        ),
                        ft.TextButton(
                            "Eliminar definitivamente",
                            tooltip="Borra el proveedor y no se puede deshacer",
                            style=ft.ButtonStyle(color="#FF7B7B"),
                            on_click=lambda e, p=prov: confirmar_eliminacion_proveedor(p),
                        ),
                    ]
                )
            filas.append(
                ft.Container(
                    padding=10,
                    bgcolor="#3A3F52",
                    border_radius=8,
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(prov.nombre or "-", color="white", size=16, weight="bold"),
                            ft.Text(
                                f"{prov.que_provee or 'Sin categoría'}  ·  "
                                f"{prov.telefono or 'Sin teléfono'}  ·  {prov.correo or 'Sin correo'}",
                                color="#C9CEDB",
                                size=12,
                            ),
                            ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Text(
                                        f"${prov.cuanto_cobra:,.0f}".replace(",", "."),
                                        color="#F2C744",
                                        weight="bold",
                                    ),
                                    badge(
                                        estado,
                                        "#7AE582" if estado == ESTADO_ACTIVO else "#FF7B7B",
                                    ),
                                    *acciones,
                                ],
                            ),
                        ],
                    ),
                )
            )

        return ft.Column(spacing=8, controls=filas)

    def construir_tablas_por_categoria(items):
        grupos = {}
        for item in items:
            grupos.setdefault(item.que_provee or "Sin categoría", []).append(item)
        return ft.Column(
            spacing=12,
            controls=[
                ft.Container(
                    padding=10,
                    border_radius=14,
                    bgcolor="#34394C",
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment="spaceBetween",
                                controls=[
                                    ft.Row(
                                        spacing=9,
                                        controls=[
                                            ft.Text("Categoría", color="#F2C744", size=13),
                                            ft.Text(categoria, size=16, weight="bold", color="white"),
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Text(
                                                f"{len(grupo)} proveedor{'es' if len(grupo) != 1 else ''}",
                                                size=12,
                                                color="#B7BDCE",
                                            ),
                                            ft.TextButton(
                                                "Administrar categoría",
                                                visible=es_admin,
                                                on_click=lambda e, c=categoria: gestionar_categoria(c),
                                            ) if es_admin else ft.Container(),
                                        ],
                                    ),
                                ],
                            ),
                            construir_tabla(grupo),
                        ],
                    ),
                )
                for categoria, grupo in sorted(grupos.items())
            ],
        )

    def construir_contenido():
        items = obtener_proveedores()
        texto = filtro["texto"].strip().lower()
        if texto:
            items = [
                item
                for item in items
                if texto in (item.nombre or "").lower()
                or texto in (item.que_provee or "").lower()
                or texto in (item.telefono or "").lower()
                or texto in (item.correo or "").lower()
            ]

        total_activos = sum(1 for item in items if item.estado == ESTADO_ACTIVO)
        categorias = len({item.que_provee or "Sin categoría" for item in items})
        acciones_admin = (
            ft.Button(
                content=ft.Text("＋  Nuevo proveedor", color="white", weight="bold"),
                bgcolor="#5A5F72",
                on_click=lambda e: abrir_formulario(),
            )
            if es_admin
            else ft.Container()
        )

        return ft.Column(
            spacing=14,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text("Proveedores", size=27, weight="bold", color="white"),
                                ft.Text("Gestiona tus aliados comerciales y sus compras.", size=13, color="#B7BDCE"),
                            ],
                        ),
                        acciones_admin,
                    ],
                ),
                ft.Row(
                    spacing=12,
                    controls=[
                        tarjeta_resumen("Proveedores visibles", len(items), "#9CCBFF", "groups"),
                        tarjeta_resumen("Activos", total_activos, "#7AE582", "check_circle"),
                        tarjeta_resumen("Categorías", categorias, "#F2C744", "category"),
                    ],
                ),
                ft.Container(
                    padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                    border_radius=14,
                    bgcolor="#34394C",
                    content=ft.TextField(
                        label="Buscar proveedor",
                        hint_text="Nombre, categoría, teléfono o correo",
                        prefix_icon="search",
                        value=filtro["texto"],
                        on_change=lambda e: (
                            filtro.__setitem__("texto", e.control.value or ""),
                            recargar(),
                        ),
                        border_radius=10,
                        border_color="#5A5F72",
                        focused_border_color="#9CCBFF",
                    ),
                ),
                ft.Container(
                    bgcolor="#34394C",
                    border_radius=18,
                    padding=14,
                    content=ft.Column(
                        controls=[construir_tablas_por_categoria(items)],
                    ),
                ),
            ],
        )

    def recargar():
        contenedor.content = construir_contenido()
        page.update()

    contenedor.content = construir_contenido()

    return ft.Column(
        expand=True,
        spacing=20,
        scroll="auto",
        controls=[navbar, contenedor],
    )

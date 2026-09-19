import flet as ft

from database.database import SessionLocal
from database.models import categorias, estados_productos, productos, rol


ESTADO_ACTIVO = "ACTIVO"
ESTADO_INACTIVO = "INACTIVO"


def menu_view(page: ft.Page, navbar, usuario_actual=None):
    db = SessionLocal()
    rol_usuario = None
    if usuario_actual:
        rol_usuario = db.query(rol).filter(rol.id_rol == usuario_actual.id_rol).first()
    es_admin = bool(rol_usuario and rol_usuario.nombre == "ADMIN")
    db.close()

    contenedor = ft.Container(expand=True)

    def badge(texto, color):
        return ft.Container(
            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            border_radius=999,
            bgcolor=color,
            content=ft.Text(texto, color="white", size=12, weight="bold"),
        )

    def obtener_categoria_estado(cat):
        return getattr(cat, "estado", ESTADO_ACTIVO) or ESTADO_ACTIVO

    def obtener_categoria_estado_color(cat):
        return "#7AE582" if obtener_categoria_estado(cat) == ESTADO_ACTIVO else "#FF7B7B"

    def obtener_estado_producto_nombre(prod):
        db_local = SessionLocal()
        try:
            estado = db_local.query(estados_productos).filter(estados_productos.id_estado_producto == prod.id_estado).first()
            return estado.nombre if estado else ESTADO_ACTIVO
        finally:
            db_local.close()

    def obtener_estado_producto_color(prod):
        return "#7AE582" if obtener_estado_producto_nombre(prod) == ESTADO_ACTIVO else "#FF7B7B"

    def obtener_categorias():
        db_local = SessionLocal()
        try:
            query = db_local.query(categorias).order_by(categorias.nombre.asc())
            if not es_admin:
                query = query.filter(categorias.estado == ESTADO_ACTIVO)
            return query.all()
        finally:
            db_local.close()

    def obtener_productos(id_categoria):
        db_local = SessionLocal()
        try:
            query = db_local.query(productos).filter(productos.id_categoria == id_categoria).order_by(productos.nombre.asc())
            if not es_admin:
                query = query.join(estados_productos, productos.id_estado == estados_productos.id_estado_producto).filter(
                    estados_productos.nombre == ESTADO_ACTIVO
                )
            return query.all()
        finally:
            db_local.close()

    def abrir_dialogo(titulo, campos, on_guardar):
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def guardar(e):
            if on_guardar(mensaje):
                page.pop_dialog()
                recargar()
            else:
                page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(titulo),
            content=ft.Container(
                width=520,
                content=ft.Column(tight=True, scroll="auto", controls=campos + [mensaje]),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Guardar", on_click=guardar),
            ],
        )
        page.show_dialog(dialog)

    def obtener_estado_producto_por_nombre(nombre_estado):
        db_local = SessionLocal()
        try:
            estado = db_local.query(estados_productos).filter(estados_productos.nombre == nombre_estado).first()
            return estado.id_estado_producto if estado else None
        finally:
            db_local.close()

    def editar_categoria(cat=None):
        nombre = ft.TextField(label="Nombre", value=cat.nombre if cat else "")
        descripcion = ft.TextField(label="Descripción", value=cat.descripcion if cat else "")
        estado = ft.Dropdown(
            label="Estado",
            value=obtener_categoria_estado(cat) if cat else ESTADO_ACTIVO,
            options=[ft.dropdown.Option(ESTADO_ACTIVO), ft.dropdown.Option(ESTADO_INACTIVO)],
        )

        def guardar(mensaje):
            if not nombre.value.strip():
                mensaje.value = "El nombre de la sección es obligatorio."
                return False

            db_local = SessionLocal()
            try:
                if cat is None:
                    db_local.add(categorias(nombre=nombre.value.strip(), descripcion=descripcion.value.strip() or None, estado=estado.value or ESTADO_ACTIVO))
                else:
                    registro = db_local.query(categorias).filter(categorias.id_categoria == cat.id_categoria).first()
                    if not registro:
                        mensaje.value = "No fue posible actualizar la sección."
                        return False
                    registro.nombre = nombre.value.strip()
                    registro.descripcion = descripcion.value.strip() or None
                    registro.estado = estado.value or ESTADO_ACTIVO
                db_local.commit()
                return True
            finally:
                db_local.close()

        abrir_dialogo("Nueva sección" if cat is None else "Editar sección", [nombre, descripcion, estado], guardar)

    def alternar_categoria(cat):
        db_local = SessionLocal()
        try:
            registro = db_local.query(categorias).filter(categorias.id_categoria == cat.id_categoria).first()
            if not registro:
                return False
            registro.estado = ESTADO_INACTIVO if obtener_categoria_estado(cat) == ESTADO_ACTIVO else ESTADO_ACTIVO
            db_local.commit()
            return True
        finally:
            db_local.close()

    def eliminar_categoria_definitivamente(cat):
        db_local = SessionLocal()
        try:
            db_local.query(productos).filter(productos.id_categoria == cat.id_categoria).delete(synchronize_session=False)
            db_local.query(categorias).filter(categorias.id_categoria == cat.id_categoria).delete(synchronize_session=False)
            db_local.commit()
            return True
        finally:
            db_local.close()

    def editar_producto(prod=None):
        db_local = SessionLocal()
        try:
            categorias_disponibles = db_local.query(categorias).order_by(categorias.nombre.asc()).all()
        finally:
            db_local.close()

        if not categorias_disponibles:
            return

        nombre = ft.TextField(label="Nombre", value=prod.nombre if prod else "")
        precio = ft.TextField(label="Precio", value=str(prod.precio if prod else 0))
        stock = ft.TextField(label="Stock", value=str(prod.stock if prod else 0))
        descripcion = ft.TextField(label="Descripción", value=prod.descripcion if prod else "")
        categoria = ft.Dropdown(
            label="Sección",
            value=str(prod.id_categoria) if prod else str(categorias_disponibles[0].id_categoria),
            options=[ft.dropdown.Option(str(cat.id_categoria), cat.nombre) for cat in categorias_disponibles],
        )
        estado = ft.Dropdown(
            label="Estado",
            value=obtener_estado_producto_nombre(prod) if prod else ESTADO_ACTIVO,
            options=[ft.dropdown.Option(ESTADO_ACTIVO), ft.dropdown.Option(ESTADO_INACTIVO)],
        )

        def guardar(mensaje):
            if not nombre.value.strip():
                mensaje.value = "El nombre del producto es obligatorio."
                return False

            try:
                precio_valor = float(precio.value)
                stock_valor = int(float(stock.value))
            except ValueError:
                mensaje.value = "Precio y stock deben ser numéricos."
                return False

            estado_id = obtener_estado_producto_por_nombre(estado.value or ESTADO_ACTIVO)
            if estado_id is None:
                mensaje.value = "No existe el estado del producto."
                return False

            db_local = SessionLocal()
            try:
                if prod is None:
                    db_local.add(
                        productos(
                            nombre=nombre.value.strip(),
                            precio=precio_valor,
                            stock=stock_valor,
                            descripcion=descripcion.value.strip() or None,
                            id_categoria=int(categoria.value),
                            id_estado=estado_id,
                            id_proveedor=None,
                        )
                    )
                else:
                    registro = db_local.query(productos).filter(productos.id_producto == prod.id_producto).first()
                    if not registro:
                        mensaje.value = "No fue posible actualizar el producto."
                        return False
                    registro.nombre = nombre.value.strip()
                    registro.precio = precio_valor
                    registro.stock = stock_valor
                    registro.descripcion = descripcion.value.strip() or None
                    registro.id_categoria = int(categoria.value)
                    registro.id_estado = estado_id
                db_local.commit()
                return True
            finally:
                db_local.close()

        abrir_dialogo("Nuevo producto" if prod is None else "Editar producto", [nombre, precio, stock, descripcion, categoria, estado], guardar)

    def alternar_producto(prod):
        db_local = SessionLocal()
        try:
            registro = db_local.query(productos).filter(productos.id_producto == prod.id_producto).first()
            if not registro:
                return False
            estado_actual = obtener_estado_producto_nombre(prod)
            estado_id = obtener_estado_producto_por_nombre(ESTADO_INACTIVO if estado_actual == ESTADO_ACTIVO else ESTADO_ACTIVO)
            if estado_id is None:
                return False
            registro.id_estado = estado_id
            db_local.commit()
            return True
        finally:
            db_local.close()

    def eliminar_producto_definitivamente(prod):
        db_local = SessionLocal()
        try:
            db_local.query(productos).filter(productos.id_producto == prod.id_producto).delete(synchronize_session=False)
            db_local.commit()
            return True
        finally:
            db_local.close()

    def construir_tarjeta_producto(prod):
        estado_prod = obtener_estado_producto_nombre(prod)
        es_inactivo = estado_prod == ESTADO_INACTIVO
        botones = []
        if es_admin:
            botones = [
                ft.TextButton("Editar", on_click=lambda e, p=prod: editar_producto(p)),
                ft.TextButton("Restaurar" if es_inactivo else "Eliminar", on_click=lambda e, p=prod: (alternar_producto(p) and recargar())),
                ft.TextButton(
                    "Eliminar definitivamente",
                    on_click=lambda e, p=prod: (eliminar_producto_definitivamente(p) and recargar()),
                ) if es_inactivo else ft.Container(),
            ]

        return ft.Container(
            width=260,
            bgcolor="#262B38" if es_inactivo else "#2E3344",
            border_radius=15,
            padding=15,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Text(prod.nombre, size=16, weight="bold", color="#B9C0D0" if es_inactivo else "white"),
                    ft.Text(prod.descripcion or "", size=12, color="#C7C9D9"),
                    ft.Text(f"${prod.precio:,.0f}".replace(",", "."), size=16, weight="bold", color="#F2C744"),
                    ft.Row(
                        spacing=6,
                        controls=[badge(estado_prod, obtener_estado_producto_color(prod))] + botones,
                    ),
                ],
            ),
        )

    def construir_seccion(cat):
        productos_cat = obtener_productos(cat.id_categoria)
        estado_cat = obtener_categoria_estado(cat)
        es_inactiva = estado_cat == ESTADO_INACTIVO
        controles_productos = [construir_tarjeta_producto(p) for p in productos_cat]
        if not controles_productos:
            controles_productos = [ft.Container(padding=20, content=ft.Text("No hay productos en esta sección.", color="white"))]

        encabezado_botones = [badge(estado_cat, obtener_categoria_estado_color(cat))]
        if es_admin:
            encabezado_botones.extend([
                ft.TextButton("Editar", on_click=lambda e, c=cat: editar_categoria(c)),
                ft.TextButton("Restaurar" if es_inactiva else "Eliminar", on_click=lambda e, c=cat: (alternar_categoria(c) and recargar())),
                ft.TextButton(
                    "Eliminar definitivamente",
                    on_click=lambda e, c=cat: (eliminar_categoria_definitivamente(c) and recargar()),
                ) if es_inactiva else ft.Container(),
            ])

        return ft.Container(
            bgcolor="#3A3F52" if not es_inactiva else "#262B38",
            border_radius=16,
            padding=18,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        vertical_alignment="center",
                        controls=[
                            ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(cat.nombre, size=18, weight="bold", color="white" if not es_inactiva else "#B9C0D0"),
                                    ft.Text(cat.descripcion or "", size=12, color="#C7C9D9"),
                                ],
                            ),
                            ft.Row(spacing=8, controls=encabezado_botones),
                        ],
                    ),
                    ft.Container(
                        padding=10,
                        content=ft.Row(wrap=True, spacing=15, run_spacing=15, controls=controles_productos),
                    ),
                ],
            ),
        )

    def construir_contenido():
        categorias_visibles = obtener_categorias()
        acciones_admin = ft.Row(
            spacing=10,
            controls=[
                ft.Button(content=ft.Text("Agregar sección", color="white"), bgcolor="#5A5F72", on_click=lambda e: editar_categoria()) if es_admin else ft.Container(),
                ft.Button(content=ft.Text("Agregar producto", color="white"), bgcolor="#5A5F72", on_click=lambda e: editar_producto()) if es_admin else ft.Container(),
            ],
        )
        if not es_admin:
            acciones_admin = ft.Container()

        if not categorias_visibles:
            return ft.Column(
                expand=True,
                spacing=20,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        controls=[
                            ft.Text("MENÚ", size=24, weight="bold", color="white"),
                            acciones_admin,
                        ],
                    ),
                    ft.Container(expand=True, alignment=ft.Alignment(0, 0), content=ft.Text("No hay secciones registradas todavía.", color="white", size=18)),
                ],
            )

        return ft.Column(
            expand=True,
            spacing=16,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("MENÚ", size=24, weight="bold", color="white"),
                        acciones_admin,
                    ],
                ),
                ft.Column(
                    spacing=16,
                    controls=[construir_seccion(cat) for cat in categorias_visibles],
                ),
            ],
        )

    def recargar():
        contenedor.content = construir_contenido()
        page.update()

    contenedor.content = construir_contenido()

    return ft.Column(expand=True, spacing=20, controls=[navbar, contenedor])

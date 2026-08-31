import flet as ft

from database.database import SessionLocal
from database.models import proveedores, rol


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

    def badge(texto, color):
        return ft.Container(
            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
            border_radius=999,
            bgcolor=color,
            content=ft.Text(texto, color="white", size=12, weight="bold"),
        )

    def obtener_proveedores():
        db_local = SessionLocal()
        try:
            query = db_local.query(proveedores).order_by(proveedores.nombre.asc())
            if not es_admin:
                query = query.filter(proveedores.estado == ESTADO_ACTIVO)
            return query.all()
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

    def abrir_formulario(prov=None):
        nombre = ft.TextField(label="Nombre del proveedor", value=prov.nombre if prov else "")
        que_provee = ft.TextField(label="Qué provee", value=prov.que_provee if prov else "")
        telefono = ft.TextField(label="Número de teléfono", value=prov.telefono if prov else "")
        correo = ft.TextField(label="Correo", value=prov.correo if prov else "")
        cuanto_cobra = ft.TextField(label="Cuánto cobra", value=str(prov.cuanto_cobra if prov else 0))
        mensaje = ft.Text("", color="#FF7B7B", size=12)

        def guardar(mensaje_local):
            if not nombre.value.strip() or not que_provee.value.strip() or not correo.value.strip():
                mensaje_local.value = "Completa nombre, qué provee y correo."
                return False

            try:
                cobro = float(cuanto_cobra.value)
            except ValueError:
                mensaje_local.value = "Cuánto cobra debe ser numérico."
                return False

            db_local = SessionLocal()
            try:
                if prov is None:
                    db_local.add(
                        proveedores(
                            nombre=nombre.value.strip(),
                            que_provee=que_provee.value.strip(),
                            telefono=telefono.value.strip() or None,
                            correo=correo.value.strip(),
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
                    registro.que_provee = que_provee.value.strip()
                    registro.telefono = telefono.value.strip() or None
                    registro.correo = correo.value.strip()
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
                content=ft.Column(tight=True, scroll="auto", controls=[nombre, que_provee, telefono, correo, cuanto_cobra, mensaje]),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Guardar", on_click=lambda e: (page.pop_dialog() if guardar(mensaje) else page.update())),
            ],
        )
        page.show_dialog(dialog)

    def construir_filas(items):
        filas = []
        for prov in items:
            estado = prov.estado or ESTADO_ACTIVO
            acciones = []
            if es_admin:
                acciones = [
                    ft.TextButton("Editar", on_click=lambda e, p=prov: abrir_formulario(p)),
                    ft.TextButton("Restaurar" if estado == ESTADO_INACTIVO else "Eliminar", on_click=lambda e, p=prov: alternar_estado(p)),
                ]
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(prov.nombre, color="white")),
                        ft.DataCell(ft.Text(prov.que_provee, color="white")),
                        ft.DataCell(ft.Text(prov.telefono or "-", color="white")),
                        ft.DataCell(ft.Text(prov.correo, color="white")),
                        ft.DataCell(ft.Text(f"${prov.cuanto_cobra:,.0f}".replace(",", "."), color="#F2C744", weight="bold")),
                        ft.DataCell(badge(estado, "#7AE582" if estado == ESTADO_ACTIVO else "#FF7B7B")),
                        ft.DataCell(ft.Row(spacing=8, controls=acciones)) if es_admin else ft.DataCell(ft.Text("-", color="white")),
                    ]
                )
            )
        return filas

    def construir_contenido():
        items = obtener_proveedores()

        if not items:
            return ft.Column(
                expand=True,
                spacing=16,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        controls=[
                            ft.Text("PROVEEDORES", size=24, weight="bold", color="white"),
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Button(content=ft.Text("Agregar proveedor", color="white"), bgcolor="#5A5F72", on_click=lambda e: abrir_formulario()) if es_admin else ft.Container(),
                                ] if es_admin else [],
                            ),
                        ],
                    ),
                    ft.Container(expand=True, alignment=ft.Alignment(0, 0), content=ft.Text("No hay proveedores registrados.", color="white")),
                ],
            )

        tabla = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nombre", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Qué provee", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Teléfono", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Correo", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Cuánto cobra", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Estado", color="white", weight="bold")),
                ft.DataColumn(ft.Text("Acciones", color="white", weight="bold")),
            ],
            rows=construir_filas(items),
            column_spacing=24,
            heading_row_color="#1C1F2B",
        )

        acciones_admin = ft.Row(
            spacing=10,
            controls=[ft.Button(content=ft.Text("Agregar proveedor", color="white"), bgcolor="#5A5F72", on_click=lambda e: abrir_formulario())] if es_admin else [],
        )

        return ft.Column(
            expand=True,
            spacing=16,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("PROVEEDORES", size=24, weight="bold", color="white"),
                        acciones_admin,
                    ],
                ),
                ft.Container(
                    expand=True,
                    bgcolor="#3A3F52",
                    border_radius=18,
                    padding=16,
                    content=ft.Column(scroll="auto", expand=True, controls=[tabla]),
                ),
            ],
        )

    def recargar():
        contenedor.content = construir_contenido()
        page.update()

    contenedor.content = construir_contenido()

    return ft.Column(expand=True, spacing=20, controls=[navbar, contenedor])

import flet as ft

from database.database import SessionLocal
from database.models import inventario, proveedores
from services.compras_service import registrar_compra
from services.retiros_caja_service import (
    DIAS_ALERTA_RETIRO,
    listar_compras_disponibles,
    listar_conciliacion_retiros,
    vincular_retiro_compra,
)


def compras_view(page: ft.Page, navbar, usuario_actual=None):
    db = SessionLocal()
    try:
        rol_usuario = None
        if usuario_actual:
            from database.models import rol

            rol_usuario = db.query(rol).filter(rol.id_rol == usuario_actual.id_rol).first()
        es_admin = bool(rol_usuario and rol_usuario.nombre == "ADMIN")
        proveedores_activos = (
            db.query(proveedores)
            .filter(proveedores.estado == "ACTIVO")
            .order_by(proveedores.nombre.asc())
            .all()
        )
        inventario_activo = (
            db.query(inventario)
            .filter(inventario.estado == "ACTIVO")
            .order_by(inventario.nombre.asc())
            .all()
        )
    finally:
        db.close()

    mensaje = ft.Text("", size=13)
    conciliacion = ft.Column(spacing=10)
    proveedor = ft.Dropdown(
        label="Proveedor",
        options=[
            ft.dropdown.Option(str(item.id_proveedor), item.nombre)
            for item in proveedores_activos
        ],
    )
    lineas = []
    lineas_container = ft.Column(spacing=8)

    def mostrar_mensaje(texto, color):
        mensaje.value = texto
        mensaje.color = color
        page.update()

    def quitar_linea(linea):
        lineas.remove(linea)
        reconstruir_lineas()

    def reconstruir_lineas():
        lineas_container.controls = []
        for linea in lineas:
            lineas_container.controls.append(
                ft.Row(
                    vertical_alignment="center",
                    controls=[
                        linea["item"],
                        linea["cantidad"],
                        linea["precio"],
                        ft.TextButton(
                            "Quitar",
                            on_click=lambda e, registro=linea: quitar_linea(registro),
                        ),
                    ],
                )
            )
        page.update()

    def opciones_inventario(proveedor_id=None):
        return [
            ft.dropdown.Option(
                str(item.id_inventario),
                (
                    f"{item.nombre} — "
                    f"{proveedores_por_id[item.id_proveedor]}"
                    if item.id_proveedor in proveedores_por_id
                    else f"{item.nombre} — sin proveedor específico"
                ),
            )
            for item in inventario_activo
            if item.id_proveedor is None or item.id_proveedor == proveedor_id
        ]

    proveedores_por_id = {
        item.id_proveedor: item.nombre
        for item in proveedores_activos
    }

    def actualizar_opciones_lineas(_e=None):
        proveedor_id = int(proveedor.value) if proveedor.value else None
        opciones_validas = {
            str(item.id_inventario)
            for item in inventario_activo
            if item.id_proveedor is None or item.id_proveedor == proveedor_id
        }
        for linea in lineas:
            linea["item"].options = opciones_inventario(proveedor_id)
            if linea["item"].value not in opciones_validas:
                linea["item"].value = None
        page.update()

    proveedor.on_select = actualizar_opciones_lineas

    def agregar_linea(_e):
        if not inventario_activo:
            mostrar_mensaje(
                "Registra primero un ítem desde la vista Inventario.",
                "#FF7B7B",
            )
            return
        linea = {
            "item": ft.Dropdown(
                label="Ítem de inventario",
                width=260,
                options=opciones_inventario(
                    int(proveedor.value) if proveedor.value else None
                ),
            ),
            "cantidad": ft.TextField(label="Cantidad", width=120),
            "precio": ft.TextField(label="Precio unitario", width=150),
        }
        lineas.append(linea)
        reconstruir_lineas()

    def guardar(_e):
        if not proveedor.value:
            mostrar_mensaje("Selecciona un proveedor.", "#FF7B7B")
            return
        if not lineas:
            mostrar_mensaje("Agrega al menos un ítem a la compra.", "#FF7B7B")
            return

        datos = []
        try:
            for linea in lineas:
                if not linea["item"].value:
                    raise ValueError("Selecciona un ítem en cada línea.")
                cantidad = int(linea["cantidad"].value)
                precio = float(linea["precio"].value)
                if cantidad <= 0 or precio < 0:
                    raise ValueError("La cantidad debe ser mayor que cero y el precio no puede ser negativo.")
                datos.append(
                    {
                        "id_inventario": int(linea["item"].value),
                        "cantidad": cantidad,
                        "precio": precio,
                    }
                )
        except (TypeError, ValueError) as error:
            mostrar_mensaje(str(error), "#FF7B7B")
            return

        db = SessionLocal()
        try:
            compra = registrar_compra(db, int(proveedor.value), datos)
        except ValueError as error:
            db.close()
            mostrar_mensaje(str(error), "#FF7B7B")
            return
        except Exception:
            db.close()
            mostrar_mensaje("No fue posible registrar la compra.", "#FF7B7B")
            return
        db.close()

        nombre_proveedor = next(
            item.nombre for item in proveedores_activos
            if item.id_proveedor == int(proveedor.value)
        )
        items_por_id = {item.id_inventario: item for item in inventario_activo}
        resumen = ", ".join(
            f"{linea['cantidad']} {items_por_id[dato['id_inventario']].nombre}"
            + (
                f" — {proveedores_por_id[items_por_id[dato['id_inventario']].id_proveedor]}"
                if items_por_id[dato["id_inventario"]].id_proveedor in proveedores_por_id
                else ""
            )
            for linea, dato in zip(lineas, datos)
        )
        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Compra registrada", color="#7AE582"),
                content=ft.Text(
                    f"Compra registrada: {resumen} de {nombre_proveedor} agregados al inventario."
                ),
                actions=[ft.TextButton("Aceptar", on_click=lambda e: page.pop_dialog())],
            )
        )
        proveedor.value = None
        lineas.clear()
        reconstruir_lineas()
        refrescar_conciliacion()

    def abrir_vinculo(retiro_id):
        db = SessionLocal()
        try:
            compras_disponibles = listar_compras_disponibles(db)
        finally:
            db.close()
        if not compras_disponibles:
            mostrar_mensaje(
                "No hay compras con saldo disponible para vincular.",
                "#FFB86C",
            )
            return

        compra_field = ft.Dropdown(
            label="Compra / entrada de inventario",
            options=[
                ft.dropdown.Option(
                    str(item["compra"].id_compra),
                    (
                        f"Compra #{item['compra'].id_compra} · "
                        f"{item['compra'].fecha:%d/%m/%Y} · "
                        f"Disponible ${item['saldo_disponible']:,.0f}".replace(",", ".")
                    ),
                )
                for item in compras_disponibles
            ],
        )
        monto_field = ft.TextField(
            label="Monto de esta conciliación (COP)",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        error = ft.Text("", color="#FF7B7B", size=12)

        def guardar_vinculo(_evento):
            try:
                if not compra_field.value:
                    raise ValueError("Selecciona una compra.")
                db_local = SessionLocal()
                try:
                    vincular_retiro_compra(
                        db_local,
                        retiro_id,
                        int(compra_field.value),
                        monto_field.value,
                    )
                finally:
                    db_local.close()
            except ValueError as exc:
                error.value = str(exc)
                page.update()
                return
            page.pop_dialog()
            refrescar_conciliacion()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Vincular compra al retiro"),
                content=ft.Column(
                    tight=True,
                    controls=[compra_field, monto_field, error],
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _evento: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Vincular",
                        on_click=guardar_vinculo,
                    ),
                ],
            )
        )

    def refrescar_conciliacion(actualizar=True):
        db_local = SessionLocal()
        try:
            filas = listar_conciliacion_retiros(db_local)
        finally:
            db_local.close()
        if not filas:
            conciliacion.controls = [
                ft.Container(
                    padding=16,
                    bgcolor="#2C2F3E",
                    border_radius=10,
                    content=ft.Text(
                        "No hay retiros pendientes o conciliados.",
                        color="#C9CEDB",
                    ),
                )
            ]
        else:
            conciliacion.controls = []
            for fila in filas:
                retiro = fila["retiro"]
                color_estado = (
                    "#7AE582"
                    if fila["estado"] == "Conciliado"
                    else "#FFB86C"
                    if fila["estado"] == "Parcial"
                    else "#FF7B7B"
                )
                compras_texto = ", ".join(
                    (
                        f"Compra #{enlace['compra'].id_compra}: "
                        f"${enlace['monto_justificado']:,.0f}".replace(",", ".")
                    )
                    for enlace in fila["compras"]
                ) or "Sin compras vinculadas"
                conciliacion.controls.append(
                    ft.Container(
                        padding=14,
                        border_radius=12,
                        bgcolor="#2C2F3E",
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    wrap=True,
                                    alignment="spaceBetween",
                                    controls=[
                                        ft.Text(
                                            f"Retiro #{retiro.id_retiro} · "
                                            f"{retiro.fecha_hora:%d/%m/%Y %H:%M}",
                                            color="white",
                                            weight="bold",
                                        ),
                                        ft.Text(
                                            (
                                                f"ALERTA · {fila['dias_transcurridos']} días"
                                                if fila["alerta"]
                                                else fila["estado"]
                                            ),
                                            color="#FF7B7B" if fila["alerta"] else color_estado,
                                            weight="bold",
                                        ),
                                        ft.TextButton(
                                            "Vincular compra",
                                            disabled=fila["saldo_pendiente"] <= 0,
                                            on_click=lambda _e, rid=retiro.id_retiro:
                                                abrir_vinculo(rid),
                                        ),
                                    ],
                                ),
                                ft.Text(
                                    f"Motivo: {retiro.motivo}",
                                    color="#C9CEDB",
                                ),
                                ft.Text(
                                    f"Compras vinculadas: {compras_texto}",
                                    color="#C9CEDB",
                                ),
                                ft.Text(
                                    (
                                        f"Retirado ${fila['monto_retirado']:,.0f} · "
                                        f"Justificado ${fila['monto_justificado']:,.0f} · "
                                        f"Pendiente ${fila['saldo_pendiente']:,.0f}"
                                    ).replace(",", "."),
                                    color="#C9CEDB",
                                ),
                            ],
                        ),
                    )
                )
        if actualizar:
            page.update()

    def abrir_registro(_e):
        mensaje.value = ""
        lineas.clear()
        agregar_linea(None)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registrar compra"),
            content=ft.Container(
                width=720,
                content=ft.Column(
                    tight=True,
                    scroll="auto",
                    controls=[
                        proveedor,
                        ft.Row(
                            controls=[
                                ft.Text("Ítem", width=260),
                                ft.Text("Cantidad", width=120),
                                ft.Text("Precio unitario", width=150),
                            ]
                        ),
                        lineas_container,
                        mensaje,
                        ft.TextButton("Agregar otra línea", on_click=agregar_linea),
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton("Guardar compra", on_click=guardar),
            ],
        )
        page.show_dialog(dialog)

    if not es_admin:
        return ft.Column(
            expand=True,
            controls=[
                navbar,
                ft.Container(
                    padding=30,
                    content=ft.Text("Solo un usuario ADMIN puede registrar compras.", color="#FF7B7B"),
                ),
            ],
        )

    refrescar_conciliacion(actualizar=False)
    return ft.Column(
        expand=True,
        spacing=20,
        scroll="auto",
        controls=[
            navbar,
            ft.Container(
                bgcolor="#3A3F52",
                border_radius=20,
                padding=24,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Text("COMPRAS", size=24, weight="bold", color="white"),
                        ft.Text(
                            "Registra compras y aumenta el inventario de insumos.",
                            color="#C9CEDB",
                        ),
                        ft.Button(
                            content=ft.Text("Registrar compra", color="white", weight="bold"),
                            bgcolor="#5A5F72",
                            on_click=abrir_registro,
                        ),
                        ft.Divider(color="#5A5F72"),
                        ft.Text(
                            "CONCILIACIÓN DE RETIROS",
                            size=18,
                            weight="bold",
                            color="white",
                        ),
                        ft.Text(
                            f"Los retiros sin justificar generan alerta después de "
                            f"{DIAS_ALERTA_RETIRO} días.",
                            color="#C9CEDB",
                        ),
                        conciliacion,
                    ],
                ),
            ),
        ],
    )

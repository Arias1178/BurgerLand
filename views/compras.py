import flet as ft

from database.database import SessionLocal
from database.models import inventario, proveedores
from services.compras_service import registrar_compra


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
                options=[
                    ft.dropdown.Option(str(item.id_inventario), item.nombre)
                    for item in inventario_activo
                ],
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
        resumen = ", ".join(
            f"{linea['cantidad']} {next(item.nombre for item in inventario_activo if item.id_inventario == dato['id_inventario'])}"
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

    return ft.Column(
        expand=True,
        spacing=20,
        scroll="auto",
        controls=[
            navbar,
            ft.Container(
                expand=True,
                bgcolor="#3A3F52",
                border_radius=20,
                padding=24,
                content=ft.Column(
                    expand=True,
                    scroll="auto",
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
                    ],
                ),
            ),
        ],
    )

import flet as ft

from database.database import SessionLocal
from services.usuarios_service import (
    cambiar_rol_usuario,
    cambiar_estado_usuario,
    crear_usuario as crear_usuario_service,
    editar_usuario,
    eliminar_usuario,
    listar_usuarios_para_administracion,
)


def usuarios_view(page: ft.Page, navbar, usuario_actual, on_cerrar_sesion=None):
    actor_id = getattr(usuario_actual, "id_usuario", None)
    mensaje = ft.Text("", size=13)
    busqueda = ft.TextField(
        label="Buscar por nombre o correo",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=10,
        width=360,
    )
    lista_usuarios = ft.ListView(spacing=10, expand=True)
    contador_resultados = ft.Text(color="#AEB6C9", size=12)
    total_usuarios = ft.Text("0", size=22, weight="bold", color="white")
    total_admins = ft.Text("0", size=22, weight="bold", color="white")
    total_vendedores = ft.Text("0", size=22, weight="bold", color="white")
    usuarios_cargados = []

    def cargar_usuarios():
        db = SessionLocal()
        try:
            return listar_usuarios_para_administracion(db, actor_id)
        finally:
            db.close()

    def tarjeta_resumen(titulo, valor, icono, color):
        return ft.Container(
            expand=True,
            padding=16,
            bgcolor="#2E3344",
            border_radius=14,
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Container(
                        width=42,
                        height=42,
                        border_radius=12,
                        bgcolor=color,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icono, color="white", size=21),
                    ),
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text(titulo, color="#C9CEDB", size=12),
                            valor,
                        ],
                    ),
                ],
            ),
        )

    def mostrar_error(error):
        mensaje.value = str(error)
        mensaje.color = "#FF7B7B"

    def guardar_usuario(registro_id, nombre, correo, contrasena, selector_rol=None):
        db = SessionLocal()
        try:
            if registro_id is None:
                crear_usuario_service(
                    db,
                    actor_id,
                    nombre.value,
                    correo.value,
                    contrasena.value,
                    selector_rol.value,
                )
            else:
                editar_usuario(
                    db,
                    actor_id,
                    registro_id,
                    nombre.value,
                    correo.value,
                    contrasena.value or None,
                )
        except ValueError as error:
            db.rollback()
            mostrar_error(error)
        except Exception as error:
            db.rollback()
            mensaje.value = f"No se pudo guardar el usuario: {error}"
            mensaje.color = "#FF7B7B"
        else:
            page.pop_dialog()
            mensaje.value = (
                "Usuario creado correctamente."
                if registro_id is None
                else "Usuario actualizado correctamente."
            )
            mensaje.color = "#80C78A"
            renderizar_usuarios()
        finally:
            db.close()
        page.update()

    def abrir_dialogo_usuario(registro=None):
        nombre = ft.TextField(
            label="Nombre",
            value=registro["nombre"] if registro else "",
            autofocus=True,
        )
        correo = ft.TextField(
            label="Correo electrónico",
            value=registro["correo"] if registro else "",
        )
        contrasena = ft.TextField(
            label=(
                "Nueva contraseña (opcional)"
                if registro
                else "Contraseña"
            ),
            password=True,
            can_reveal_password=True,
        )
        selector_rol = None
        campos = [nombre, correo, contrasena]
        if registro is None:
            selector_rol = ft.Dropdown(
                label="Rol",
                value="VENDEDOR",
                options=[
                    ft.dropdown.Option("ADMIN", "Administrador"),
                    ft.dropdown.Option("VENDEDOR", "Trabajador / Vendedor"),
                ],
            )
            campos.append(selector_rol)

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo usuario" if registro is None else "Editar usuario"),
            content=ft.Column(width=340, tight=True, spacing=12, controls=campos),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _e: page.pop_dialog()),
                ft.Button(
                    "Guardar",
                    icon=ft.Icons.SAVE_OUTLINED,
                    on_click=lambda _e: guardar_usuario(
                        registro["id_usuario"] if registro else None,
                        nombre,
                        correo,
                        contrasena,
                        selector_rol,
                    ),
                ),
            ],
        )
        page.show_dialog(dialogo)

    def confirmar_cambio_estado(registro, activar):
        accion = "activar" if activar else "inhabilitar"

        def confirmar(_evento):
            db = SessionLocal()
            try:
                cambiar_estado_usuario(
                    db,
                    actor_id,
                    registro["id_usuario"],
                    activar,
                )
            except ValueError as error:
                db.rollback()
                mostrar_error(error)
            except Exception as error:
                db.rollback()
                mensaje.value = f"No se pudo cambiar el estado: {error}"
                mensaje.color = "#FF7B7B"
            else:
                mensaje.value = (
                    "Usuario activado correctamente."
                    if activar
                    else "Usuario inhabilitado correctamente."
                )
                mensaje.color = "#80C78A"
                renderizar_usuarios()
            finally:
                db.close()
            page.pop_dialog()
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar cambio de estado"),
                content=ft.Text(
                    f"¿Deseas {accion} a «{registro['nombre']}»?"
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.Button(
                        "Confirmar",
                        on_click=confirmar,
                    ),
                ],
            )
        )

    def confirmar_eliminacion(registro):
        def eliminar(_evento):
            db = SessionLocal()
            try:
                eliminar_usuario(db, actor_id, registro["id_usuario"])
            except ValueError as error:
                db.rollback()
                mostrar_error(error)
            except Exception as error:
                db.rollback()
                mensaje.value = f"No se pudo eliminar el usuario: {error}"
                mensaje.color = "#FF7B7B"
            else:
                mensaje.value = "Usuario eliminado correctamente."
                mensaje.color = "#80C78A"
                renderizar_usuarios()
            finally:
                db.close()
            page.pop_dialog()
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar usuario"),
                content=ft.Text(
                    f"¿Deseas eliminar a «{registro['nombre']}»? "
                    "Si tiene actividad registrada, solo podrás inhabilitarlo."
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.Button(
                        "Eliminar",
                        icon=ft.Icons.DELETE_OUTLINE,
                        bgcolor="#8A3A3A",
                        color="white",
                        on_click=eliminar,
                    ),
                ],
            )
        )

    def renderizar_usuarios():
        nonlocal usuarios_cargados
        try:
            usuarios_cargados = cargar_usuarios()
        except ValueError as error:
            mensaje.value = str(error)
            mensaje.color = "#FF7B7B"
            lista_usuarios.controls = []
            contador_resultados.value = ""
            return

        admins = sum(registro["rol"] == "ADMIN" for registro in usuarios_cargados)
        vendedores = sum(
            registro["rol"] == "VENDEDOR" for registro in usuarios_cargados
        )
        total_usuarios.value = str(len(usuarios_cargados))
        total_admins.value = str(admins)
        total_vendedores.value = str(vendedores)
        renderizar_lista_filtrada()

    def renderizar_lista_filtrada():
        consulta = (busqueda.value or "").strip().casefold()
        usuarios_visibles = [
            registro
            for registro in usuarios_cargados
            if consulta in registro["nombre"].casefold()
            or consulta in registro["correo"].casefold()
        ]
        contador_resultados.value = (
            f"{len(usuarios_visibles)} de {len(usuarios_cargados)} usuarios"
        )
        filas = []

        for registro in usuarios_visibles:
            usuario_id = registro["id_usuario"]
            rol_actual = registro["rol"]
            es_usuario_actual = usuario_id == actor_id
            nombre = registro["nombre"]
            iniciales = "".join(
                parte[0] for parte in nombre.split()[:2] if parte
            ).upper()
            color_rol = "#7ABAFB" if rol_actual == "ADMIN" else "#80C78A"
            estado_actual = registro.get("estado", "ACTIVO")
            esta_activo = estado_actual == "ACTIVO"
            etiqueta_rol = {
                "ADMIN": "Administrador",
                "VENDEDOR": "Vendedor",
                "CAJERO": "Cajero",
            }.get(rol_actual, rol_actual.title())
            selector = ft.Dropdown(
                label="Asignar rol",
                value=rol_actual,
                width=190,
                options=[
                    ft.dropdown.Option("ADMIN", "Administrador"),
                    ft.dropdown.Option("VENDEDOR", "Trabajador / Vendedor"),
                    *(
                        [ft.dropdown.Option("CAJERO", "Cajero (rol actual)")]
                        if rol_actual == "CAJERO"
                        else []
                    ),
                ],
                disabled=es_usuario_actual,
            )
            boton_guardar = ft.Button(
                "Guardar cambios",
                icon=ft.Icons.SAVE_OUTLINED,
                bgcolor="#4A6741",
                color="white",
                disabled=es_usuario_actual or selector.value == rol_actual,
            )

            def marcar_cambio_rol(
                _evento,
                campo=selector,
                boton=boton_guardar,
                rol_original=rol_actual,
                es_actual=es_usuario_actual,
            ):
                boton.disabled = es_actual or campo.value == rol_original
                page.update()

            selector.on_change = marcar_cambio_rol

            def guardar_rol(
                _evento,
                id_destino=usuario_id,
                campo=selector,
            ):
                db = SessionLocal()
                try:
                    cambiar_rol_usuario(
                        db,
                        actor_id,
                        id_destino,
                        campo.value,
                    )
                except ValueError as error:
                    db.rollback()
                    mensaje.value = str(error)
                    mensaje.color = "#FF7B7B"
                except Exception as error:
                    db.rollback()
                    mensaje.value = f"No se pudo actualizar el rol: {error}"
                    mensaje.color = "#FF7B7B"
                else:
                    mensaje.value = "Rol actualizado correctamente."
                    mensaje.color = "#80C78A"
                finally:
                    db.close()
                renderizar_usuarios()
                page.update()

            boton_guardar.on_click = guardar_rol
            filas.append(
                ft.Container(
                    bgcolor="#252A39",
                    border=ft.Border.all(1, "#41485B"),
                    border_radius=12,
                    padding=14,
                    content=ft.Row(
                        wrap=True,
                        spacing=14,
                        alignment="spaceBetween",
                        controls=[
                            ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Container(
                                        width=44,
                                        height=44,
                                        border_radius=22,
                                        alignment=ft.Alignment.CENTER,
                                        bgcolor=color_rol,
                                        content=ft.Text(
                                            iniciales or "?",
                                            color="#18202D",
                                            weight="bold",
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=3,
                                        controls=[
                                            ft.Text(
                                                nombre,
                                                color="white",
                                                weight="bold",
                                            ),
                                            ft.Text(
                                                registro["correo"],
                                                color="#AEB6C9",
                                                size=12,
                                            ),
                                            *(
                                                [
                                                    ft.Text(
                                                        "Tu cuenta: no puedes "
                                                        "cambiar tu propio rol.",
                                                        color="#FFB86C",
                                                        size=11,
                                                    )
                                                ]
                                                if es_usuario_actual
                                                else []
                                            ),
                                        ],
                                    ),
                                    ft.Container(
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=6
                                        ),
                                        border_radius=20,
                                        bgcolor="#343B4E",
                                        content=ft.Text(
                                            etiqueta_rol,
                                            color=color_rol,
                                            size=11,
                                            weight="bold",
                                        ),
                                    ),
                                    ft.Container(
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=6
                                        ),
                                        border_radius=20,
                                        bgcolor="#33463A" if esta_activo else "#5A3B3B",
                                        content=ft.Text(
                                            "Activo" if esta_activo else "Inhabilitado",
                                            color="#80C78A" if esta_activo else "#FFB86C",
                                            size=11,
                                            weight="bold",
                                        ),
                                    ),
                                ],
                            ),
                            selector,
                            boton_guardar,
                            ft.Button(
                                "Editar",
                                icon=ft.Icons.EDIT_OUTLINED,
                                on_click=lambda _e, usuario=registro: (
                                    abrir_dialogo_usuario(usuario)
                                ),
                            ),
                            ft.Button(
                                "Inhabilitar" if esta_activo else "Activar",
                                icon=(
                                    ft.Icons.BLOCK
                                    if esta_activo
                                    else ft.Icons.CHECK_CIRCLE_OUTLINE
                                ),
                                disabled=es_usuario_actual,
                                on_click=lambda _e, usuario=registro, estado=esta_activo: (
                                    confirmar_cambio_estado(usuario, not estado)
                                ),
                            ),
                            ft.Button(
                                "Eliminar",
                                icon=ft.Icons.DELETE_OUTLINE,
                                bgcolor="#8A3A3A",
                                color="white",
                                disabled=es_usuario_actual,
                                on_click=lambda _e, usuario=registro: (
                                    confirmar_eliminacion(usuario)
                                ),
                            ),
                        ],
                    ),
                )
            )

        if filas:
            lista_usuarios.controls = filas
        else:
            lista_usuarios.controls = [
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=30,
                    content=ft.Column(
                        horizontal_alignment="center",
                        spacing=8,
                        controls=[
                            ft.Icon(
                                ft.Icons.PERSON_SEARCH_OUTLINED,
                                size=38,
                                color="#7C8498",
                            ),
                            ft.Text(
                                "No encontramos usuarios",
                                color="white",
                                size=16,
                                weight="bold",
                            ),
                            ft.Text(
                                "Prueba con otro nombre o correo.",
                                color="#AEB6C9",
                                size=12,
                            ),
                        ],
                    ),
                )
            ]

    def actualizar_busqueda(_evento):
        renderizar_lista_filtrada()
        page.update()

    busqueda.on_change = actualizar_busqueda
    renderizar_usuarios()

    return ft.Column(
        expand=True,
        spacing=18,
        controls=[
            navbar,
            ft.Container(
                expand=True,
                bgcolor="#3A3F52",
                border_radius=20,
                padding=24,
                content=ft.Column(
                    expand=True,
                    spacing=18,
                    controls=[
                        ft.Row(
                            spacing=14,
                            controls=[
                                ft.Container(
                                    width=52,
                                    height=52,
                                    border_radius=14,
                                    alignment=ft.Alignment.CENTER,
                                    bgcolor="#4A6741",
                                    content=ft.Icon(
                                        ft.Icons.GROUPS_OUTLINED,
                                        color="white",
                                        size=28,
                                    ),
                                ),
                                ft.Column(
                                    expand=True,
                                    spacing=4,
                                    controls=[
                                        ft.Text(
                                            "Usuarios y roles",
                                            size=24,
                                            weight="bold",
                                            color="white",
                                        ),
                                        ft.Text(
                                            "Administra los permisos del equipo "
                                            "de BurgerLand.",
                                            color="#C9CEDB",
                                            size=13,
                                        ),
                                    ],
                                ),
                                *(
                                    [
                                        ft.Button(
                                            "Cerrar sesión",
                                            icon=ft.Icons.LOGOUT,
                                            bgcolor="#8A3A3A",
                                            color="white",
                                            on_click=lambda _e: on_cerrar_sesion(),
                                        )
                                    ]
                                    if on_cerrar_sesion
                                    else []
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                tarjeta_resumen(
                                    "Usuarios registrados",
                                    total_usuarios,
                                    ft.Icons.PEOPLE_OUTLINE,
                                    "#52617F",
                                ),
                                tarjeta_resumen(
                                    "Administradores",
                                    total_admins,
                                    ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                                    "#416488",
                                ),
                                tarjeta_resumen(
                                    "Vendedores",
                                    total_vendedores,
                                    ft.Icons.POINT_OF_SALE_OUTLINED,
                                    "#4A6741",
                                ),
                            ],
                        ),
                        ft.Container(
                            expand=True,
                            bgcolor="#2E3344",
                            border_radius=14,
                            padding=18,
                            content=ft.Column(
                                expand=True,
                                spacing=12,
                                controls=[
                                    ft.Row(
                                        wrap=True,
                                        alignment="spaceBetween",
                                        controls=[
                                            ft.Column(
                                                spacing=3,
                                                controls=[
                                                    ft.Text(
                                                        "Equipo",
                                                        color="white",
                                                        size=17,
                                                        weight="bold",
                                                    ),
                                                    contador_resultados,
                                                ],
                                            ),
                                            ft.Button(
                                                "Crear usuario",
                                                icon=ft.Icons.PERSON_ADD_ALT_1,
                                                bgcolor="#4A6741",
                                                color="white",
                                                on_click=lambda _e: abrir_dialogo_usuario(),
                                            ),
                                            busqueda,
                                        ],
                                    ),
                                    mensaje,
                                    ft.Divider(height=1, color="#41485B"),
                                    lista_usuarios,
                                ],
                            ),
                        ),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(
                                    ft.Icons.INFO_OUTLINE,
                                    color="#FFB86C",
                                    size=16,
                                ),
                                ft.Text(
                                    "No puedes cambiar tu propio rol, inhabilitar "
                                    "o eliminar tu cuenta ni quitar el último "
                                    "administrador activo.",
                                    color="#C9CEDB",
                                    size=12,
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )

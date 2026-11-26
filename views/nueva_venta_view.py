import datetime
import logging
from collections.abc import Callable

import flet as ft

from database.database import SessionLocal
from database.models import (
    productos,
    categorias,
    estados_productos,
    metodos_pago,
    mesas,
)
from services.mesa_service import (
    ESTADO_MESA_LIBRE,
    ESTADO_MESA_OCUPADA,
    ESTADO_MESA_POR_PAGAR,
    obtener_mesas,
)
from services.venta_service import validar_stock_disponible
from services.cuenta_service import (
    cobrar_cuenta_abierta,
    cobrar_subcuenta,
    dividir_cuenta_en_partes_iguales,
    dividir_cuenta_por_items,
    dividir_cuenta_por_valores,
    guardar_cuenta_abierta,
    listar_cuentas_abiertas,
    listar_subcuentas,
    obtener_cuenta_abierta,
    obtener_items_cuenta,
)
from services.inventario_service import (
    buscar_inventario_para_producto,
    extraer_variantes_producto,
)

logger = logging.getLogger(__name__)


def tarjeta_mesa(
    mesa: mesas,
    on_click: Callable[..., None],
    ancho: dict[str, int] | None = None,
    cuenta_abierta: dict | None = None,
) -> ft.Container:
    colores = {
        ESTADO_MESA_LIBRE: ("#4A6741", "Libre"),
        ESTADO_MESA_OCUPADA: ("#B87924", "Ocupada"),
        ESTADO_MESA_POR_PAGAR: ("#8A3A3A", "Por pagar"),
    }
    color, etiqueta = colores.get(mesa.estado, ("#5A5F72", mesa.estado))
    disponible = mesa.estado == ESTADO_MESA_LIBRE
    puede_abrir = disponible or cuenta_abierta is not None
    detalle = (
        f"${cuenta_abierta['cuenta'].total:,.0f}".replace(",", ".")
        if cuenta_abierta
        else etiqueta
    )
    return ft.Container(
        col=ancho or {"xs": 6, "sm": 4, "md": 3, "lg": 2},
        height=112,
        padding=12,
        bgcolor=color,
        border_radius=14,
        alignment=ft.Alignment(0, 0),
        disabled=not puede_abrir,
        on_click=on_click if puede_abrir else None,
        content=ft.Column(
            alignment="center",
            horizontal_alignment="center",
            spacing=6,
            controls=[
                ft.Text(f"Mesa {mesa.numero}", color="white", size=18, weight="bold"),
                ft.Text(etiqueta, color="white", size=13),
                *(
                    [ft.Text(detalle, color="white", size=13, weight="bold")]
                    if cuenta_abierta
                    else []
                ),
            ],
        ),
    )


def tarjeta_para_llevar(
    on_click: Callable[..., None],
    ancho: dict[str, int] | None = None,
) -> ft.Container:
    return ft.Container(
        col=ancho or {"xs": 6, "sm": 4, "md": 3, "lg": 2},
        height=112,
        padding=12,
        bgcolor="#5A5F72",
        border_radius=14,
        alignment=ft.Alignment(0, 0),
        on_click=on_click,
        content=ft.Column(
            alignment="center",
            horizontal_alignment="center",
            spacing=6,
            controls=[
                ft.Text("Para llevar", color="white", size=18, weight="bold"),
                ft.Text("Mostrador", color="white", size=13),
            ],
        ),
    )


def tarjeta_domicilio(
    on_click: Callable[..., None],
    ancho: dict[str, int] | None = None,
) -> ft.Container:
    return ft.Container(
        col=ancho or {"xs": 6, "sm": 4, "md": 3, "lg": 2},
        height=112,
        padding=12,
        bgcolor="#7A4E9B",
        border_radius=14,
        alignment=ft.Alignment(0, 0),
        on_click=on_click,
        content=ft.Column(
            alignment="center",
            horizontal_alignment="center",
            spacing=6,
            controls=[
                ft.Text("Domicilio", color="white", size=18, weight="bold"),
                ft.Text("Entrega a dirección", color="white", size=13),
            ],
        ),
    )


def construir_selector_mesa(
    navbar,
    lista_mesas: list[mesas],
    on_seleccionar_mesa: Callable[[int | None, int | None, str], None],
    cuentas_por_mesa: dict[int, dict] | None = None,
    on_volver: Callable[[], None] | None = None,
) -> ft.Column:
    tarjetas = [
        tarjeta_mesa(
            mesa,
            lambda _e, id_mesa=mesa.id_mesa, cuenta=(
                (cuentas_por_mesa or {}).get(mesa.id_mesa)
            ): on_seleccionar_mesa(
                id_mesa,
                cuenta["cuenta"].id_cuenta if cuenta else None,
                "MESA",
            ),
            cuenta_abierta=(cuentas_por_mesa or {}).get(mesa.id_mesa),
        )
        for mesa in lista_mesas
    ]
    tarjetas.insert(
        0,
        tarjeta_para_llevar(
            lambda _e: on_seleccionar_mesa(None, None, "MOSTRADOR")
        ),
    )
    tarjetas.insert(
        1,
        tarjeta_domicilio(
            lambda _e: on_seleccionar_mesa(None, None, "DOMICILIO")
        ),
    )
    return ft.Column(
        expand=True,
        spacing=18,
        scroll="auto",
        controls=[
            navbar,
            ft.Container(
                expand=True,
                bgcolor="#3A3F52",
                border_radius=20,
                padding=24,
                content=ft.Column(
                    scroll="auto",
                    spacing=16,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    icon_color="white",
                                    tooltip="Volver a ventas",
                                    on_click=(
                                        (lambda _e: on_volver())
                                        if on_volver
                                        else None
                                    ),
                                ),
                                ft.Text(
                                    "SELECCIONAR MESA",
                                    size=22,
                                    weight="bold",
                                    color="white",
                                ),
                            ],
                        ),
                        ft.Text(
                            "Elige una mesa, Para llevar / Mostrador o Domicilio.",
                            color="#C9CEDB",
                        ),
                        ft.ResponsiveRow(controls=tarjetas),
                    ],
                ),
            ),
        ],
    )


def nueva_venta_view(
    page: ft.Page,
    navbar,
    usuario_actual,
    on_venta_completada,
    caja_actual=None,
    mesa_id=None,
    mesa_elegida=False,
    on_seleccionar_mesa=None,
    cuenta_id=None,
    on_cuenta_guardada=None,
    on_recargar_cuenta=None,
    tipo_pedido="MOSTRADOR",
    on_volver_a_mesas=None,
):
    db = SessionLocal()
    lista_categorias = db.query(categorias).all()
    categoria_combos = next(
        (cat for cat in lista_categorias if cat.nombre == "Combos"),
        None,
    )
    lista_metodos = db.query(metodos_pago).all()
    estado_activo = db.query(estados_productos).filter(estados_productos.nombre == "ACTIVO").first()
    lista_mesas = obtener_mesas(db)
    cuentas_por_mesa = {
        registro["cuenta"].id_mesa: registro
        for registro in listar_cuentas_abiertas(db)
        if registro["cuenta"].id_mesa is not None
    }
    cuenta_cargada = None
    items_cargados = []
    subcuentas_cargadas = []

    if caja_actual is None and cuenta_id is None:
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

    if not mesa_elegida:
        db.close()
        return construir_selector_mesa(
            navbar,
            lista_mesas,
            on_seleccionar_mesa
            or (lambda _mesa_id, _cuenta_id, _tipo_pedido: None),
            cuentas_por_mesa,
            on_volver=on_venta_completada,
        )

    if cuenta_id is not None:
        try:
            cuenta_cargada = obtener_cuenta_abierta(db, cuenta_id)
            items_cargados = obtener_items_cuenta(db, cuenta_id)
            subcuentas_cargadas = listar_subcuentas(db, cuenta_id)
        except ValueError as error:
            db.close()
            return ft.Column(
                expand=True,
                controls=[
                    navbar,
                    ft.Container(
                        padding=24,
                        bgcolor="#3A3F52",
                        border_radius=18,
                        content=ft.Column(
                            controls=[
                                ft.Text(str(error), color="#FF7B7B"),
                                ft.TextButton(
                                    "Volver a cuentas abiertas",
                                    on_click=lambda _e: (
                                        on_cuenta_guardada()
                                        if on_cuenta_guardada
                                        else on_venta_completada()
                                    ),
                                ),
                            ]
                        ),
                    ),
                ],
            )

    mesa_id_actual = cuenta_cargada.id_mesa if cuenta_cargada else mesa_id
    mesa_actual = db.get(mesas, mesa_id_actual) if mesa_id_actual is not None else None
    if mesa_id is not None and (
        cuenta_cargada is None
        and (mesa_actual is None or mesa_actual.estado != ESTADO_MESA_LIBRE)
    ):
        db.close()
        return construir_selector_mesa(
            navbar,
            lista_mesas,
            on_seleccionar_mesa
            or (lambda _mesa_id, _cuenta_id, _tipo_pedido: None),
            cuentas_por_mesa,
            on_volver=on_venta_completada,
        )

    mesa_seleccionada = {
        "id": mesa_actual.id_mesa if mesa_actual else None,
        "numero": mesa_actual.numero if mesa_actual else None,
    }
    tipo_pedido_actual = (
        "MESA"
        if mesa_seleccionada["id"] is not None
        else tipo_pedido
        if not cuenta_cargada
        else "MOSTRADOR"
    )
    mesa_persistida_id = mesa_seleccionada["id"]
    cuenta_abierta = {
        "id": cuenta_cargada.id_cuenta if cuenta_cargada else None,
        "version": cuenta_cargada.version if cuenta_cargada else None,
    }
    cuenta_dividida = bool(subcuentas_cargadas)

    carrito = [
        {
            "id_producto": item.id_producto,
            "id_inventario": item.id_inventario,
            "nombre": item.nombre,
            "precio": item.precio_unitario,
            "cantidad": item.cantidad,
            "personalizacion": item.personalizacion,
            "agregado_en": item.agregado_en,
        }
        for item in items_cargados
    ]
    metodo_seleccionado = {
        "id": lista_metodos[0].id_metodos_pago if lista_metodos else None,
        "nombre": lista_metodos[0].nombre if lista_metodos else "",
    }
    pestaña_actual = {"indice": 0}
    busqueda = {"texto": ""}

    carrito_column = ft.Column(spacing=8, scroll="auto", expand=True)
    subcuentas_column = ft.Column(spacing=10, scroll="auto")
    total_text = ft.Text("Total: $0", size=20, weight="bold", color="white")
    metodo_text = ft.Text(f"Método: {metodo_seleccionado['nombre']}", color="white")
    cliente_domicilio_field = ft.TextField(label="Cliente", expand=True)
    telefono_domicilio_field = ft.TextField(
        label="Teléfono",
        hint_text="3001234567",
        keyboard_type=ft.KeyboardType.PHONE,
        max_length=10,
        expand=True,
    )
    direccion_domicilio_field = ft.TextField(
        label="Dirección de entrega",
        expand=True,
    )
    barrio_domicilio_field = ft.TextField(
        label="Barrio o referencia",
        expand=True,
    )
    costo_domicilio_field = ft.TextField(
        label="Costo del domicilio (COP)",
        value="0",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=210,
    )
    domiciliario_field = ft.TextField(
        label="Domiciliario (opcional)",
        expand=True,
    )
    domicilio_fields = ft.Column(
        visible=tipo_pedido_actual == "DOMICILIO",
        spacing=8,
        controls=[
            ft.Text("DATOS DEL DOMICILIO", color="white", weight="bold"),
            ft.ResponsiveRow(
                controls=[
                    ft.Container(col={"xs": 12, "md": 6}, content=cliente_domicilio_field),
                    ft.Container(col={"xs": 12, "md": 6}, content=telefono_domicilio_field),
                    ft.Container(col={"xs": 12}, content=direccion_domicilio_field),
                    ft.Container(col={"xs": 12, "md": 6}, content=barrio_domicilio_field),
                    ft.Container(col={"xs": 12, "md": 6}, content=domiciliario_field),
                    ft.Container(col={"xs": 12}, content=costo_domicilio_field),
                ],
            ),
        ],
    )
    mensaje_venta_text = ft.Text("", color="#FF7B7B", size=12)
    contenedor_menu = ft.Container(expand=True)
    mesa_text = ft.Text("", color="#C9CEDB")
    encabezado_venta = ft.Text("", size=22, weight="bold", color="white")

    def nombre_mesa_seleccionada():
        if tipo_pedido_actual == "DOMICILIO":
            return "Domicilio"
        if tipo_pedido_actual == "MOSTRADOR":
            return "Para llevar / Mostrador"
        return (
            f"Mesa {mesa_seleccionada['numero']}"
            if mesa_seleccionada["numero"] is not None
            else "Para llevar / Mostrador"
        )

    def actualizar_mesa_seleccionada():
        mesa_text.value = f"Cuenta: {nombre_mesa_seleccionada()}"
        prefijo = "CUENTA ABIERTA" if cuenta_abierta["id"] else "NUEVA VENTA"
        encabezado_venta.value = f"{prefijo} · {nombre_mesa_seleccionada()}"
        page.update()

    def mostrar_selector_para_cambio():
        mesas_actualizadas = obtener_mesas(db)
        opciones = [
            tarjeta_mesa(
                mesa,
                lambda _e, registro=mesa: seleccionar_nueva_mesa(registro),
            )
            for mesa in mesas_actualizadas
        ]
        if cuenta_abierta["id"] is None:
            opciones.insert(
                0,
                tarjeta_para_llevar(
                    lambda _e: seleccionar_nueva_mesa(None),
                    ancho={"xs": 6, "sm": 4, "md": 3, "lg": 2},
                ),
            )
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Cambiar mesa"),
                content=ft.Container(
                    width=720,
                    height=460,
                    content=ft.Column(
                        scroll="auto",
                        controls=[ft.ResponsiveRow(controls=opciones)],
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    )
                ],
            )
        )

    def seleccionar_nueva_mesa(mesa):
        nonlocal mesa_persistida_id
        page.pop_dialog()
        mesa_id_nueva = mesa.id_mesa if mesa else None
        if cuenta_abierta["id"] is not None:
            try:
                cuenta = guardar_cuenta_abierta(
                    db=db,
                    carrito=carrito,
                    mesa_id=mesa_id_nueva,
                    usuario_id=getattr(usuario_actual, "id_usuario", None),
                    cuenta_id=cuenta_abierta["id"],
                    version=cuenta_abierta["version"],
                )
            except ValueError as error:
                mensaje_venta_text.value = str(error)
                mensaje_venta_text.color = "#FF7B7B"
                page.update()
                return
            except Exception as error:
                db.rollback()
                mensaje_venta_text.value = (
                    f"No se pudo cambiar la cuenta de mesa: {error}"
                )
                mensaje_venta_text.color = "#FF7B7B"
                page.update()
                return
            cuenta_abierta["version"] = cuenta.version
            mesa_persistida_id = mesa_id_nueva
            mensaje_venta_text.value = (
                "Cuenta transferida a "
                f"{f'Mesa {mesa.numero}' if mesa else 'Para llevar / Mostrador'}."
            )
            mensaje_venta_text.color = "#80C78A"
        mesa_seleccionada["id"] = mesa.id_mesa if mesa else None
        mesa_seleccionada["numero"] = mesa.numero if mesa else None
        actualizar_mesa_seleccionada()

    def confirmar_cambio_mesa(_e):
        nombre_actual = nombre_mesa_seleccionada()

        def aceptar(_evento):
            page.pop_dialog()
            mostrar_selector_para_cambio()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar cambio de mesa"),
                content=ft.Text(
                    f"Vas a cambiar {nombre_actual}. El carrito se conservará."
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _evento: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Elegir otra mesa",
                        bgcolor="#4A6741",
                        color="white",
                        on_click=aceptar,
                    ),
                ],
            )
        )

    btn_cambiar_mesa = ft.TextButton(
        "Cambiar mesa",
        on_click=confirmar_cambio_mesa,
    )
    actualizar_mesa_seleccionada()

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

    def actualizar_carrito():
        carrito_column.controls.clear()
        total = 0
        for item in carrito:
            subtotal = item["precio"] * item["cantidad"]
            total += subtotal

            def quitar(
                e,
                id_producto=item["id_producto"],
                id_inventario=item.get("id_inventario"),
                personalizacion=item.get("personalizacion"),
                precio=item["precio"],
            ):
                carrito[:] = [
                    i for i in carrito
                    if not (
                        i["id_producto"] == id_producto
                        and i.get("id_inventario") == id_inventario
                        and i.get("personalizacion") == personalizacion
                        and i["precio"] == precio
                    )
                ]
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
                                    item.get("personalizacion") or "",
                                    color="#C7C9D9",
                                    size=11,
                                ),
                                ft.Text(
                                    f"{item['cantidad']} x ${item['precio']:,.0f}".replace(",", "."),
                                    color="#C7C9D9",
                                    size=12,
                                ),
                            ],
                        ),
                        ft.Text(f"${subtotal:,.0f}".replace(",", "."), color="#F2C744", weight="bold"),
                        (
                            ft.Container(
                                width=35,
                                height=35,
                                bgcolor="#8A3A3A",
                                border_radius=18,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Text(
                                    "X",
                                    color="white",
                                    weight="bold",
                                    text_align="center",
                                ),
                                on_click=quitar,
                            )
                            if not cuenta_dividida
                            else ft.Container(width=1)
                        ),
                    ]
                )
            )
        if tipo_pedido_actual == "DOMICILIO":
            try:
                total += _parsear_costo_domicilio()
                mensaje_venta_text.value = ""
            except ValueError as error:
                mensaje_venta_text.value = str(error)
        total_text.value = f"Total: ${total:,.0f}".replace(",", ".")
        btn_dividir.visible = (
            not cuenta_dividida
            and bool(carrito)
            and tipo_pedido_actual != "DOMICILIO"
        )
        page.update()

    def volver_a_seleccion():
        volver = on_volver_a_mesas or on_venta_completada
        tiene_cambios_sin_guardar = bool(
            carrito
            or cliente_domicilio_field.value
            or telefono_domicilio_field.value
            or direccion_domicilio_field.value
            or barrio_domicilio_field.value
            or domiciliario_field.value
            or (costo_domicilio_field.value or "0") != "0"
        )

        def salir(_evento=None):
            page.pop_dialog()
            db.close()
            volver()

        if not tiene_cambios_sin_guardar:
            db.close()
            volver()
            return

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("¿Salir de la venta?"),
                content=ft.Text(
                    "Los productos o datos que no hayas guardado se perderán."
                ),
                actions=[
                    ft.TextButton(
                        "Seguir aquí",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.Button(
                        content=ft.Text("Salir", color="white"),
                        bgcolor="#8A3A3A",
                        on_click=salir,
                    ),
                ],
            )
        )

    def _parsear_costo_domicilio():
        valor = (costo_domicilio_field.value or "").strip()
        if not valor:
            return 0
        normalizado = valor.replace("$", "").replace(".", "").replace(",", "")
        if not normalizado.isdigit():
            raise ValueError("El costo del domicilio debe ser un valor entero en COP.")
        return int(normalizado)

    costo_domicilio_field.on_change = lambda _evento: actualizar_carrito()

    def abrir_selector_cantidad(producto):
        cantidad_field = ft.TextField(value="1", width=80, text_align="center")
        categoria_producto = db.query(categorias).filter(
            categorias.id_categoria == producto.id_categoria
        ).first()
        nombre_categoria = categoria_producto.nombre if categoria_producto else ""
        variantes = extraer_variantes_producto(producto.nombre)
        variante_inventario = {}
        variante_dropdown = None

        if variantes:
            opciones = []
            for variante in variantes:
                item_inventario = buscar_inventario_para_producto(
                    db,
                    variante,
                    None,
                )
                if item_inventario:
                    variante_inventario[variante] = item_inventario.id_inventario
                    etiqueta = (
                        f"{variante} — disponible: "
                        f"{item_inventario.cantidad} {item_inventario.unidad_medida}"
                    )
                    valor = str(item_inventario.id_inventario)
                else:
                    etiqueta = f"{variante} — sin inventario asociado"
                    valor = f"__sin_inventario__:{variante}"
                opciones.append(ft.dropdown.Option(valor, etiqueta))

            variante_dropdown = ft.Dropdown(
                label="Presentación",
                value=opciones[0].key,
                options=opciones,
            )

        es_burger = nombre_categoria == "Burgers"
        es_sandwich = nombre_categoria == "Sándwiches"
        es_hot_dog = nombre_categoria == "Hot Dogs"
        es_mazorcada = nombre_categoria == "Mazorcadas"
        es_plancha = nombre_categoria == "A la Plancha"
        es_infantil = nombre_categoria == "Menú Infantil"
        permite_combo = es_burger or es_sandwich or es_hot_dog or es_mazorcada
        carne_dropdown = (
            ft.Dropdown(
                label="Tipo de carne",
                value="Carne de la casa (140 g, 100 % res)",
                options=[
                    ft.dropdown.Option("Carne de la casa (140 g, 100 % res)"),
                    ft.dropdown.Option("Koller"),
                    ft.dropdown.Option("Pollo apanado"),
                ],
            )
            if es_burger
            else None
        )
        arepa_checkbox = (
            ft.Checkbox(label="Cambiar a arepa de maíz artesanal (+$1.000)", value=False)
            if es_burger
            else None
        )
        tocineta_checkbox = (
            ft.Checkbox(label="Agregar tocineta (+$3.000)", value=False)
            if es_hot_dog
            else None
        )
        tipo_infantil_dropdown = (
            ft.Dropdown(
                label="Opción infantil",
                value="6 Nuggets",
                options=[
                    ft.dropdown.Option("6 Nuggets"),
                    ft.dropdown.Option("Hamburguesa con carne Koller"),
                    ft.dropdown.Option("Hamburguesa con pollo apanado"),
                ],
            )
            if es_infantil
            else None
        )
        acompanamientos = [
            "Papas francesas",
            "Papas criollas",
            "Casquitos de papa",
            "Ensalada Primavera",
            "Ensalada Zanahoria",
            "Arepa con queso",
        ]
        acompanamientos_checks = (
            [ft.Checkbox(label=nombre, value=False) for nombre in acompanamientos]
            if es_plancha
            else []
        )
        combo_dropdown = (
            ft.Dropdown(
                label="Agregar combo",
                value="ninguno",
                options=[
                    ft.dropdown.Option("ninguno", "Sin combo"),
                    ft.dropdown.Option("7500", "Combo — 150 g de papas + gaseosa 250 ml (+$7.500)"),
                    ft.dropdown.Option("10500", "Combo agrandado — 250 g de papas + gaseosa 350 ml (+$10.500)"),
                ],
            )
            if permite_combo
            else None
        )

        def confirmar(e):
            try:
                cantidad = int(cantidad_field.value)
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor que 0.")
            except ValueError:
                mensaje_venta_text.value = "La cantidad debe ser un número entero mayor que 0."
                page.update()
                return

            inventario_id = None
            nombre_carrito = producto.nombre
            variante_seleccionada = None
            if variante_dropdown:
                valor_variante = variante_dropdown.value
                if valor_variante.startswith("__sin_inventario__:"):
                    mensaje_venta_text.value = (
                        "No hay un artículo de inventario único asociado a "
                        f"{valor_variante.split(':', 1)[1]}."
                    )
                    page.update()
                    return
                inventario_id = int(valor_variante)
                variante = next(
                    nombre
                    for nombre, id_item in variante_inventario.items()
                    if id_item == inventario_id
                )
                nombre_carrito = f"{producto.nombre} — {variante}"
                variante_seleccionada = f"variante: {variante}"

            precio_carrito = float(producto.precio)
            personalizaciones = (
                [variante_seleccionada] if variante_seleccionada else []
            )
            if carne_dropdown:
                personalizaciones.append(f"carne: {carne_dropdown.value}")
            if arepa_checkbox and arepa_checkbox.value:
                precio_carrito += 1000
                personalizaciones.append("arepa artesanal (+$1.000)")
            if tocineta_checkbox and tocineta_checkbox.value:
                precio_carrito += 3000
                personalizaciones.append("con tocineta (+$3.000)")
            if tipo_infantil_dropdown:
                personalizaciones.append(tipo_infantil_dropdown.value)
            if es_plancha:
                elegidos = [
                    checkbox.label
                    for checkbox in acompanamientos_checks
                    if checkbox.value
                ]
                if len(elegidos) != 2:
                    mensaje_venta_text.value = "Selecciona exactamente dos acompañamientos."
                    page.update()
                    return
                personalizaciones.append("acompañamientos: " + " y ".join(elegidos))
            if combo_dropdown and combo_dropdown.value != "ninguno":
                precio_carrito += int(combo_dropdown.value)
                personalizaciones.append(
                    "combo agrandado (+$10.500)"
                    if combo_dropdown.value == "10500"
                    else "combo (+$7.500)"
                )
            personalizacion = "; ".join(personalizaciones) or None

            carrito_candidato = [dict(item) for item in carrito]
            for item in carrito:
                if (
                    item["id_producto"] == producto.id_producto
                    and item.get("id_inventario") == inventario_id
                    and item.get("personalizacion") == personalizacion
                    and item["precio"] == precio_carrito
                ):
                    next(
                        carrito_item for carrito_item in carrito_candidato
                        if carrito_item["id_producto"] == producto.id_producto
                        and carrito_item.get("id_inventario") == inventario_id
                        and carrito_item.get("personalizacion") == personalizacion
                        and carrito_item["precio"] == precio_carrito
                    )["cantidad"] += cantidad
                    break
            else:
                item_carrito = {
                    "id_producto": producto.id_producto,
                    "nombre": nombre_carrito,
                    "precio": precio_carrito,
                    "cantidad": cantidad,
                    "personalizacion": personalizacion,
                    "agregado_en": datetime.datetime.now(),
                }
                if inventario_id is not None:
                    item_carrito["id_inventario"] = inventario_id
                carrito_candidato.append(item_carrito)

            try:
                validar_stock_disponible(db, carrito_candidato)
            except ValueError as error:
                mensaje_venta_text.value = str(error)
                page.update()
                return

            carrito[:] = carrito_candidato
            page.pop_dialog()
            actualizar_carrito()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(producto.nombre),
            content=ft.Column(
                tight=True,
                controls=[
                    *([variante_dropdown] if variante_dropdown else []),
                    *([carne_dropdown] if carne_dropdown else []),
                    *([arepa_checkbox] if arepa_checkbox else []),
                    *([tocineta_checkbox] if tocineta_checkbox else []),
                    *([tipo_infantil_dropdown] if tipo_infantil_dropdown else []),
                    *(
                        [ft.Text("Elige exactamente dos acompañamientos:")]
                        + acompanamientos_checks
                        if es_plancha
                        else []
                    ),
                    *([combo_dropdown] if combo_dropdown else []),
                    ft.Row(controls=[ft.Text("Cantidad:"), cantidad_field]),
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Agregar", on_click=confirmar),
            ],
        )
        page.show_dialog(dialog)

    def construir_tarjeta_producto(producto):
        descripcion = (producto.descripcion or "").strip()
        contenido = [
            ft.Text(producto.nombre, size=14, weight="bold", color="white"),
            ft.Text(
                f"${producto.precio:,.0f}".replace(",", "."),
                size=14,
                color="#F2C744",
                weight="bold",
            ),
        ]
        if descripcion:
            contenido.append(
                ft.Text(
                    descripcion,
                    size=11,
                    color="#C7C9D9",
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        return ft.Button(
            content=ft.Column(
                tight=True,
                spacing=4,
                controls=contenido,
            ),
            bgcolor="#3A3F52",
            width=220,
            height=125 if descripcion else 90,
            on_click=lambda e, p=producto: abrir_selector_cantidad(p),
        )

    def productos_visibles():
        texto = busqueda["texto"].strip().lower()
        if estado_activo:
            candidatos = [
                p for p in db.query(productos)
                .filter(productos.id_estado == estado_activo.id_estado_producto)
                .all()
                if categoria_combos is None or p.id_categoria != categoria_combos.id_categoria
            ]
        else:
            candidatos = [
                p for p in db.query(productos).all()
                if categoria_combos is None or p.id_categoria != categoria_combos.id_categoria
            ]
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
            expand=True,
            padding=15,
            content=ft.Column(
                expand=True,
                scroll="auto",
                controls=[
                    ft.Row(
                        wrap=True,
                        spacing=10,
                        run_spacing=10,
                        controls=[construir_tarjeta_producto(p) for p in lista_productos_local],
                    )
                ],
            ),
        )

    def construir_tabs():
        categorias_menu = [
            categoria for categoria in lista_categorias
            if categoria.nombre != "Combos"
        ]
        if not categorias_menu:
            return ft.Text("No hay productos registrados.", color="white")

        indice_seleccionado = min(
            pestaña_actual["indice"],
            len(categorias_menu) - 1,
        )
        pestaña_actual["indice"] = indice_seleccionado
        candidatos = productos_visibles()
        selector_categorias = ft.Row(
            height=48,
            scroll=ft.ScrollMode.AUTO,
            spacing=0,
            controls=[
                ft.Container(
                    bgcolor="#454B60" if indice == indice_seleccionado else None,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    content=ft.Text(
                        categoria.nombre,
                        color="white",
                        weight="bold" if indice == indice_seleccionado else "normal",
                    ),
                    on_click=lambda _e, indice=indice: seleccionar_categoria(indice),
                )
                for indice, categoria in enumerate(categorias_menu)
            ],
        )
        productos_categoria = [
            producto for producto in candidatos
            if producto.id_categoria
            == categorias_menu[indice_seleccionado].id_categoria
        ]
        return ft.Column(
            expand=True,
            controls=[
                selector_categorias,
                ft.Container(
                    expand=True,
                    content=construir_grid_productos(productos_categoria),
                ),
            ],
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

    def seleccionar_categoria(indice):
        pestaña_actual["indice"] = indice
        refrescar_menu()

    def seleccionar_metodo(m):
        metodo_seleccionado["id"] = m.id_metodos_pago
        metodo_seleccionado["nombre"] = m.nombre
        metodo_text.value = f"Método: {m.nombre}"
        page.update()

    def ejecutar_venta():
        if not carrito:
            mensaje_venta_text.value = "Agrega al menos un producto para registrar la venta."
            page.update()
            return
        if caja_actual is None:
            mensaje_venta_text.value = (
                "Debes abrir caja antes de cobrar esta cuenta."
            )
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
            datos_domicilio = None
            if tipo_pedido_actual == "DOMICILIO":
                datos_domicilio = {
                    "cliente": cliente_domicilio_field.value,
                    "telefono": telefono_domicilio_field.value,
                    "direccion": direccion_domicilio_field.value,
                    "barrio_referencia": barrio_domicilio_field.value,
                    "valor_domicilio": _parsear_costo_domicilio(),
                    "domiciliario": domiciliario_field.value,
                }
            if cuenta_abierta["id"] is not None:
                if datos_domicilio:
                    raise ValueError(
                        "No se puede convertir una cuenta abierta en domicilio."
                    )
                if mesa_seleccionada["id"] != mesa_persistida_id:
                    raise ValueError(
                        "Guarda primero el cambio de mesa antes de cobrar la cuenta."
                    )
                cobrar_cuenta_abierta(
                    db=db,
                    cuenta_id=cuenta_abierta["id"],
                    version=cuenta_abierta["version"],
                    metodo_id=metodo_seleccionado["id"],
                    usuario_actual=usuario_actual,
                    caja_actual=caja_actual,
                    carrito=carrito,
                )
            else:
                from services.venta_service import registrar_venta

                registrar_venta(
                    db_session=db,
                    carrito=carrito,
                    metodo_id=metodo_seleccionado["id"],
                    usuario_actual=usuario_actual,
                    caja_actual=caja_actual,
                    mesa_id=mesa_seleccionada["id"],
                    domicilio=datos_domicilio,
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
        mensaje_venta_text.value = ""
        db.close()
        on_venta_completada()

    def guardar_cuenta(e):
        if not carrito:
            mensaje_venta_text.value = "Agrega al menos un producto antes de guardar la cuenta."
            page.update()
            return
        try:
            cuenta = guardar_cuenta_abierta(
                db=db,
                carrito=carrito,
                mesa_id=mesa_seleccionada["id"],
                usuario_id=getattr(usuario_actual, "id_usuario", None),
                cuenta_id=cuenta_abierta["id"],
                version=cuenta_abierta["version"],
            )
        except ValueError as error:
            mensaje_venta_text.value = str(error)
            page.update()
            return
        except Exception:
            mensaje_venta_text.value = "No fue posible guardar la cuenta abierta."
            page.update()
            return

        cuenta_abierta["id"] = cuenta.id_cuenta
        cuenta_abierta["version"] = cuenta.version
        mensaje_venta_text.value = ""
        db.close()
        if on_cuenta_guardada:
            on_cuenta_guardada()
        else:
            on_venta_completada()

    def persistir_cuenta_para_dividir():
        nonlocal mesa_persistida_id
        if cuenta_dividida:
            raise ValueError("Esta cuenta ya está dividida.")
        if not carrito:
            raise ValueError("Agrega productos antes de dividir la cuenta.")
        cuenta = guardar_cuenta_abierta(
            db=db,
            carrito=carrito,
            mesa_id=mesa_seleccionada["id"],
            usuario_id=getattr(usuario_actual, "id_usuario", None),
            cuenta_id=cuenta_abierta["id"],
            version=cuenta_abierta["version"],
        )
        cuenta_abierta["id"] = cuenta.id_cuenta
        cuenta_abierta["version"] = cuenta.version
        mesa_persistida_id = mesa_seleccionada["id"]
        return cuenta

    def finalizar_division():
        page.pop_dialog()
        mensaje_venta_text.value = ""
        if on_recargar_cuenta:
            db.close()
            on_recargar_cuenta(cuenta_abierta["id"])
        elif on_cuenta_guardada:
            db.close()
            on_cuenta_guardada()
        else:
            db.close()
            on_venta_completada()

    def formato_pesos(valor):
        return f"${float(valor):,.0f}".replace(",", ".")

    def mostrar_division_igual():
        partes_field = ft.TextField(
            label="¿Entre cuántas personas?",
            value="2",
            width=220,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        total_division = sum(
            item["precio"] * item["cantidad"] for item in carrito
        )
        total_pesos = int(round(total_division))
        vista_previa = ft.Text("", color="#80C78A", weight="bold")
        detalle_redondeo = ft.Text("", color="#C9CEDB", size=12)

        def actualizar_vista_previa(_evento=None):
            try:
                personas = int(partes_field.value or "")
                if personas < 2:
                    raise ValueError
            except (TypeError, ValueError):
                vista_previa.value = "Ingresa 2 o más personas para ver el reparto."
                vista_previa.color = "#FFB86C"
                detalle_redondeo.value = ""
                page.update()
                return

            base, residuo = divmod(total_pesos, personas)
            valores = [base] * (personas - 1) + [base + residuo]
            vista_previa.value = " · ".join(
                f"Persona {indice + 1}: {formato_pesos(valor)}"
                for indice, valor in enumerate(valores)
            )
            vista_previa.color = "#80C78A"
            detalle_redondeo.value = (
                "Si sobran pesos por el redondeo, se agregan a la última persona."
                if residuo
                else "Todas las personas pagan el mismo valor."
            )
            page.update()

        partes_field.on_change = actualizar_vista_previa

        def aceptar(_evento):
            try:
                numero_partes = int(partes_field.value)
                if numero_partes < 2:
                    raise ValueError("El número de personas debe ser al menos 2.")
                cuenta = persistir_cuenta_para_dividir()
                dividir_cuenta_en_partes_iguales(
                    db,
                    cuenta.id_cuenta,
                    cuenta.version,
                    numero_partes,
                )
            except ValueError as error:
                mensaje_venta_text.value = str(error)
                page.update()
                return
            except Exception:
                db.rollback()
                logger.exception("Error al dividir una cuenta en partes iguales")
                mensaje_venta_text.value = "No fue posible dividir la cuenta."
                page.update()
                return
            finalizar_division()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Dividir en partes iguales"),
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text(
                            f"Total de la cuenta: {formato_pesos(total_division)}",
                            color="#F2C744",
                            size=18,
                            weight="bold",
                        ),
                        ft.Text(
                            "El total se reparte automáticamente. Puedes revisar "
                            "cuánto pagará cada persona antes de confirmar.",
                            color="#C9CEDB",
                        ),
                        partes_field,
                        ft.Container(
                            padding=12,
                            bgcolor="#2C2F3E",
                            border_radius=10,
                            content=ft.Column(
                                spacing=6,
                                controls=[vista_previa, detalle_redondeo],
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Dividir cuenta",
                        bgcolor="#4A6741",
                        color="white",
                        on_click=aceptar,
                    ),
                ],
            )
        )
        actualizar_vista_previa()

    def mostrar_division_por_items():
        partes_field = ft.TextField(
            label="¿Cuántas personas pagarán?",
            value="2",
            width=220,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        matriz = ft.Column(spacing=8, scroll="auto")
        vista_previa_items = ft.Column(spacing=4)
        campos_por_item = []

        def actualizar_vista_previa_items(_evento=None):
            try:
                totales_persona = [0.0] * len(
                    campos_por_item[0] if campos_por_item else []
                )
                errores = []
                for item, campos in zip(carrito, campos_por_item):
                    cantidades = [int(campo.value or "0") for campo in campos]
                    asignadas = sum(cantidades)
                    if asignadas != int(item["cantidad"]):
                        errores.append(
                            f"{item['nombre']}: asigna {item['cantidad']} "
                            f"unidad(es); llevas {asignadas}."
                        )
                    for indice, cantidad in enumerate(cantidades):
                        totales_persona[indice] += (
                            float(item["precio"]) * cantidad
                        )
                if errores:
                    vista_previa_items.controls = [
                        ft.Text(error, color="#FFB86C", size=12)
                        for error in errores
                    ]
                elif not totales_persona:
                    vista_previa_items.controls = [
                        ft.Text(
                            "Configura las personas para ver el resumen.",
                            color="#C9CEDB",
                        )
                    ]
                else:
                    vista_previa_items.controls = [
                        ft.Text(
                            f"Persona {indice + 1}: {formato_pesos(total)}",
                            color="#80C78A",
                            weight="bold",
                        )
                        for indice, total in enumerate(totales_persona)
                    ]
            except (TypeError, ValueError):
                vista_previa_items.controls = [
                    ft.Text(
                        "Usa cantidades enteras iguales o mayores que cero.",
                        color="#FF7B7B",
                        size=12,
                    )
                ]
            page.update()

        def reconstruir_matriz(_evento=None):
            try:
                cantidad_partes = int(partes_field.value)
                if cantidad_partes < 2 or cantidad_partes > 26 * 26:
                    raise ValueError
            except (TypeError, ValueError):
                matriz.controls = [
                    ft.Text(
                        "Indica entre 2 y 676 personas y pulsa «Preparar reparto».",
                        color="#FFB86C",
                    )
                ]
                campos_por_item.clear()
                vista_previa_items.controls = []
                page.update()
                return

            matriz.controls.clear()
            campos_por_item.clear()
            etiquetas = []
            for indice in range(cantidad_partes):
                numero = indice + 1
                etiqueta = ""
                while numero:
                    numero, resto = divmod(numero - 1, 26)
                    etiqueta = chr(65 + resto) + etiqueta
                etiquetas.append(etiqueta)

            for item in carrito:
                campos = [
                    ft.TextField(
                        value=str(item["cantidad"] if indice == 0 else 0),
                        width=90,
                        height=52,
                        text_align="center",
                        keyboard_type=ft.KeyboardType.NUMBER,
                        on_change=actualizar_vista_previa_items,
                    )
                    for indice, etiqueta in enumerate(etiquetas)
                ]
                campos_por_item.append(campos)
                matriz.controls.append(
                    ft.Container(
                        padding=8,
                        bgcolor="#2C2F3E",
                        border_radius=10,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Row(
                                    alignment="spaceBetween",
                                    controls=[
                                        ft.Text(
                                            item["nombre"],
                                            color="white",
                                            weight="bold",
                                            expand=True,
                                        ),
                                        ft.Text(
                                            f"{item['cantidad']} un. · "
                                            f"{formato_pesos(item['precio'])} c/u",
                                            color="#C9CEDB",
                                            size=12,
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    wrap=True,
                                    spacing=10,
                                    controls=[
                                        ft.Column(
                                            spacing=2,
                                            horizontal_alignment="center",
                                            controls=[
                                                ft.Text(
                                                    f"Persona {etiqueta}",
                                                    color="#C9CEDB",
                                                    size=11,
                                                ),
                                                campo,
                                            ],
                                        )
                                        for etiqueta, campo in zip(
                                            etiquetas,
                                            campos,
                                        )
                                    ],
                                ),
                            ],
                        ),
                    )
                )
            actualizar_vista_previa_items()
            page.update()

        def aceptar(_evento):
            try:
                cantidades = [
                    [int(campo.value or "0") for campo in campos]
                    for campos in campos_por_item
                ]
                cuenta = persistir_cuenta_para_dividir()
                dividir_cuenta_por_items(
                    db,
                    cuenta.id_cuenta,
                    cuenta.version,
                    cantidades,
                )
            except ValueError as error:
                mensaje_venta_text.value = str(error)
                page.update()
                return
            except Exception:
                db.rollback()
                mensaje_venta_text.value = "No fue posible dividir la cuenta."
                page.update()
                return
            finalizar_division()

        reconstruir_matriz()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Dividir por productos"),
                content=ft.Container(
                    width=720,
                    height=480,
                    content=ft.Column(
                        scroll="auto",
                        controls=[
                            ft.Text(
                                            "Escribe cuántas unidades de cada producto paga "
                                            "cada persona. La suma de la fila debe coincidir "
                                            "con las unidades disponibles.",
                                            color="#C9CEDB",
                                        ),
                                        ft.Row(
                                            controls=[
                                                partes_field,
                                                ft.Button(
                                                    "Preparar reparto",
                                                    on_click=reconstruir_matriz,
                                                ),
                                            ],
                                        ),
                                        matriz,
                                        ft.Divider(color="#5A5F72"),
                                        ft.Text(
                                            "RESUMEN POR PERSONA",
                                            color="white",
                                            weight="bold",
                                        ),
                                        vista_previa_items,
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Dividir cuenta",
                        bgcolor="#4A6741",
                        color="white",
                        on_click=aceptar,
                    ),
                ],
            )
        )

    def mostrar_division_por_valores():
        total_actual = sum(item["precio"] * item["cantidad"] for item in carrito)
        total_pesos = int(round(total_actual))
        partes_field = ft.TextField(
            label="¿Cuántas personas?",
            value="2",
            width=220,
            text_align="center",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        matriz_valores = ft.ResponsiveRow(spacing=10, run_spacing=8)
        campos_valores = []
        resumen_valores = ft.Text("", size=13, weight="bold")

        def reconstruir_valores(_evento=None):
            try:
                cantidad_partes = int(partes_field.value)
                if cantidad_partes < 2 or cantidad_partes > 26 * 26:
                    raise ValueError
            except (TypeError, ValueError):
                matriz_valores.controls = [
                    ft.Text(
                        "Indica entre 2 y 676 personas.",
                        color="#FFB86C",
                    )
                ]
                campos_valores.clear()
                resumen_valores.value = ""
                page.update()
                return

            matriz_valores.controls.clear()
            campos_valores.clear()
            for indice in range(cantidad_partes):
                base, residuo = divmod(total_pesos, cantidad_partes)
                valor = base + (1 if indice < residuo else 0)
                campo = ft.TextField(
                    label=f"Persona {indice + 1} paga",
                    value=str(valor),
                    keyboard_type=ft.KeyboardType.NUMBER,
                )
                contenedor = ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4},
                    content=campo,
                    padding=4,
                )
                campo.on_change = actualizar_resumen_valores
                campos_valores.append(campo)
                matriz_valores.controls.append(contenedor)

            actualizar_resumen_valores()
            page.update()

        def actualizar_resumen_valores(_evento=None):
            try:
                valores = [
                    int((campo.value or "").replace(".", "").replace("$", ""))
                    for campo in campos_valores
                ]
                if any(valor < 0 for valor in valores):
                    raise ValueError
                diferencia = total_pesos - sum(valores)
            except ValueError:
                resumen_valores.value = (
                    "Ingresa valores enteros no negativos para cada persona."
                )
                resumen_valores.color = "#FF7B7B"
                page.update()
                return

            if diferencia == 0:
                resumen_valores.value = (
                    f"Reparto completo: {formato_pesos(sum(valores))} "
                    "asignados."
                )
                resumen_valores.color = "#80C78A"
            elif diferencia > 0:
                resumen_valores.value = (
                    f"Faltan {formato_pesos(diferencia)} por asignar "
                    f"de {formato_pesos(total_pesos)}."
                )
                resumen_valores.color = "#FFB86C"
            else:
                resumen_valores.value = (
                    f"Te pasaste por {formato_pesos(abs(diferencia))}; "
                    f"el total es {formato_pesos(total_pesos)}."
                )
                resumen_valores.color = "#FF7B7B"
            page.update()

        def aceptar(_evento):
            try:
                valores = [
                    int((campo.value or "").replace(".", "").replace("$", ""))
                    for campo in campos_valores
                ]
                if sum(valores) != total_pesos:
                    raise ValueError(
                        "La suma debe coincidir con el total de la cuenta."
                    )
                cuenta = persistir_cuenta_para_dividir()
                dividir_cuenta_por_valores(
                    db,
                    cuenta.id_cuenta,
                    cuenta.version,
                    valores,
                )
            except ValueError as error:
                mensaje_venta_text.value = str(error)
                page.update()
                return
            except Exception:
                db.rollback()
                mensaje_venta_text.value = "No fue posible dividir la cuenta."
                page.update()
                return
            finalizar_division()

        reconstruir_valores()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Cada persona paga un valor diferente"),
                content=ft.Container(
                    width=640,
                    content=ft.Column(
                        spacing=12,
                        scroll="auto",
                        controls=[
                            ft.Text(
                                f"Total de la cuenta: {formato_pesos(total_actual)}",
                                color="#F2C744",
                                size=18,
                                weight="bold",
                            ),
                            ft.Text(
                                "Define cuánto paga cada persona. El resumen te "
                                "indica lo que falta o sobra; solo podrás confirmar "
                                "cuando el reparto complete el total.",
                                color="#C9CEDB",
                            ),
                            ft.Row(
                                controls=[
                                    partes_field,
                                    ft.Button(
                                        "Preparar personas",
                                        on_click=reconstruir_valores,
                                    ),
                                ],
                                wrap=True,
                            ),
                            matriz_valores,
                            resumen_valores,
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Dividir cuenta",
                        bgcolor="#4A6741",
                        color="white",
                        on_click=aceptar,
                    ),
                ],
            )
        )

    def mostrar_opciones_division(_evento):
        if not carrito:
            mensaje_venta_text.value = "Agrega productos antes de dividir la cuenta."
            page.update()
            return
        total_actual = sum(
            item["precio"] * item["cantidad"] for item in carrito
        )

        def opcion_division(titulo, descripcion, accion, color):
            return ft.Container(
                padding=14,
                bgcolor="#2C2F3E",
                border=ft.Border.all(1, "#5A5F72"),
                border_radius=12,
                on_click=lambda _evento: (
                    page.pop_dialog(),
                    accion(),
                ),
                content=ft.Row(
                    spacing=12,
                    controls=[
                        ft.Container(
                            width=38,
                            height=38,
                            border_radius=19,
                            bgcolor=color,
                            alignment=ft.Alignment(0, 0),
                            content=ft.Text(
                                titulo[0],
                                color="white",
                                weight="bold",
                                size=18,
                            ),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=3,
                            controls=[
                                ft.Text(
                                    titulo,
                                    color="white",
                                    weight="bold",
                                ),
                                ft.Text(
                                    descripcion,
                                    color="#C9CEDB",
                                    size=12,
                                ),
                            ],
                        ),
                        ft.Text("›", color="#C9CEDB", size=22),
                    ],
                ),
            )

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Dividir cuenta"),
                content=ft.Container(
                    width=560,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Container(
                                padding=12,
                                bgcolor="#3A3F52",
                                border_radius=10,
                                content=ft.Row(
                                    alignment="spaceBetween",
                                    controls=[
                                        ft.Text(
                                            f"{sum(item['cantidad'] for item in carrito)} "
                                            "producto(s)",
                                            color="#C9CEDB",
                                        ),
                                        ft.Text(
                                            f"Total: {formato_pesos(total_actual)}",
                                            color="#F2C744",
                                            weight="bold",
                                            size=16,
                                        ),
                                    ],
                                ),
                            ),
                            ft.Text(
                                "¿Cómo prefieren pagar?",
                                color="white",
                                weight="bold",
                            ),
                            opcion_division(
                                "Por productos",
                                "Cada persona elige los productos o unidades que paga.",
                                mostrar_division_por_items,
                                "#7ABAFB",
                            ),
                            opcion_division(
                                "Partes iguales",
                                "Divide el total entre las personas automáticamente.",
                                mostrar_division_igual,
                                "#80C78A",
                            ),
                            opcion_division(
                                "Cada persona paga un valor",
                                "Escribe cuánto paga cada persona; la suma debe dar el total.",
                                mostrar_division_por_valores,
                                "#C792EA",
                            ),
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                ],
            )
        )

    def mostrar_confirmacion_cobro_subcuenta(
        subcuenta,
        metodo_dropdown,
    ):
        def aceptar(_evento):
            try:
                metodo_id = int(metodo_dropdown.value)
                _, cuenta_cerrada = cobrar_subcuenta(
                    db=db,
                    cuenta_id=cuenta_abierta["id"],
                    version_cuenta=cuenta_abierta["version"],
                    subcuenta_id=subcuenta.id_subcuenta,
                    version_subcuenta=subcuenta.version,
                    metodo_id=metodo_id,
                    usuario_actual=usuario_actual,
                    caja_actual=caja_actual,
                )
            except ValueError as error:
                page.pop_dialog()
                mensaje_venta_text.value = str(error)
                page.update()
                return
            except Exception:
                db.rollback()
                page.pop_dialog()
                mensaje_venta_text.value = "No fue posible cobrar esta subcuenta."
                page.update()
                return

            page.pop_dialog()
            if cuenta_cerrada:
                db.close()
                on_venta_completada()
            elif on_recargar_cuenta:
                db.close()
                on_recargar_cuenta(cuenta_abierta["id"])
            elif on_cuenta_guardada:
                db.close()
                on_cuenta_guardada()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Cobrar subcuenta {subcuenta.etiqueta}"),
                content=ft.Text(
                    f"¿Confirmas el cobro de "
                    f"${subcuenta.total:,.0f}".replace(",", ".")
                    + "? La mesa seguirá ocupada si quedan otras subcuentas."
                ),
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda _e: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Confirmar cobro",
                        bgcolor="#4A6741",
                        color="white",
                        on_click=aceptar,
                    ),
                ],
            )
        )

    def renderizar_subcuentas():
        subcuentas_column.controls.clear()
        if not cuenta_dividida:
            return
        subcuentas_column.controls.append(
            ft.Text(
                "Subcuentas · cada pago se registra por separado",
                color="#C9CEDB",
                weight="bold",
            )
        )
        for registro in subcuentas_cargadas:
            subcuenta = registro["subcuenta"]
            pagada = subcuenta.estado == "PAGADA"
            selector_metodo = ft.Dropdown(
                label="Método de pago",
                width=150,
                value=str(
                    subcuenta.id_metodo_pago
                    or (lista_metodos[0].id_metodos_pago if lista_metodos else "")
                ),
                options=[
                    ft.dropdown.Option(
                        str(metodo.id_metodos_pago),
                        metodo.nombre,
                    )
                    for metodo in lista_metodos
                ],
                disabled=pagada or not lista_metodos,
            )
            detalle = []
            for item_registro in registro["items"]:
                asignacion = item_registro["asignacion"]
                item = item_registro["item"]
                detalle.append(f"{asignacion.cantidad} × {item.nombre}")

            subcuentas_column.controls.append(
                ft.Container(
                    padding=12,
                    bgcolor="#2C2F3E",
                    border_radius=12,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment="spaceBetween",
                                controls=[
                                    ft.Text(
                                        f"Subcuenta {subcuenta.etiqueta}",
                                        color="white",
                                        weight="bold",
                                    ),
                                    ft.Text(
                                        "Pagada" if pagada else "Pendiente",
                                        color="#80C78A" if pagada else "#FFB86C",
                                        weight="bold",
                                    ),
                                ],
                            ),
                            *(
                                [ft.Text(", ".join(detalle), color="#C9CEDB", size=12)]
                                if detalle
                                else []
                            ),
                            ft.Text(
                                f"${subcuenta.total:,.0f}".replace(",", "."),
                                color="#F2C744",
                                size=18,
                                weight="bold",
                            ),
                            ft.Row(
                                controls=[
                                    selector_metodo,
                                    ft.Button(
                                        "Cobrar",
                                        bgcolor="#4A6741",
                                        color="white",
                                        disabled=pagada or not lista_metodos,
                                        on_click=lambda _e, registro=subcuenta,
                                        selector=selector_metodo:
                                            mostrar_confirmacion_cobro_subcuenta(
                                                registro,
                                                selector,
                                            ),
                                    ),
                                ],
                                wrap=True,
                            ),
                        ],
                    ),
                )
            )

    def confirmar_venta(e):
        if not carrito:
            mensaje_venta_text.value = "Agrega al menos un producto para confirmar la venta."
            page.update()
            return

        total = sum(item["precio"] * item["cantidad"] for item in carrito)
        if tipo_pedido_actual == "DOMICILIO":
            try:
                total += _parsear_costo_domicilio()
            except ValueError as error:
                mensaje_venta_text.value = str(error)
                page.update()
                return

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
        content=ft.Text("Cobrar" if cuenta_abierta["id"] else "Confirmar Venta", color="white", weight="bold"),
        bgcolor="#4A6741",
        width=250,
        height=50,
        on_click=confirmar_venta,
    )
    btn_guardar_cuenta = ft.Button(
        content=ft.Text("Guardar cuenta abierta", color="white", weight="bold"),
        bgcolor="#5A5F72",
        width=250,
        height=50,
        on_click=guardar_cuenta,
    )
    btn_dividir = ft.Button(
        content=ft.Text("Dividir cuenta", color="white", weight="bold"),
        bgcolor="#5A5F72",
        width=250,
        height=50,
        on_click=mostrar_opciones_division,
        visible=False,
    )
    domicilio_fields.visible = (
        tipo_pedido_actual == "DOMICILIO" and not cuenta_dividida
    )
    btn_guardar_cuenta.visible = (
        not cuenta_dividida and tipo_pedido_actual != "DOMICILIO"
    )
    btn_confirmar.visible = not cuenta_dividida
    btn_cambiar_mesa.visible = (
        not cuenta_dividida and tipo_pedido_actual != "DOMICILIO"
    )
    panel_carrito = ft.Container(
        width=320,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            scroll="auto",
            controls=[
                ft.Text("CARRITO", size=18, weight="bold", color="white"),
                ft.Row(
                    alignment="spaceBetween",
                    controls=[mesa_text, btn_cambiar_mesa],
                ),
                ft.Divider(color="#5A5F72"),
                carrito_column,
                subcuentas_column,
                ft.Divider(color="#5A5F72"),
                total_text,
                metodo_text,
                botones_metodo,
                ft.Divider(color="#5A5F72"),
                domicilio_fields,
                mensaje_venta_text,
                ft.Container(height=15),
                btn_dividir,
                btn_guardar_cuenta,
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
    if cuenta_dividida:
        encabezado_venta.value = f"CUENTA DIVIDIDA · {nombre_mesa_seleccionada()}"
        campo_busqueda.visible = False
        contenedor_menu.content = ft.Container(
            padding=20,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text(
                        "Cuenta dividida",
                        color="white",
                        size=20,
                        weight="bold",
                    ),
                    ft.Text(
                        "Los productos quedan bloqueados para conservar los "
                        "totales y asignaciones. Cobra cada subcuenta desde el carrito.",
                        color="#C9CEDB",
                    ),
                ],
            ),
        )

    panel_menu = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Row(
                    spacing=8,
                    vertical_alignment="center",
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color="white",
                            tooltip="Volver a seleccionar mesa",
                            on_click=lambda _e: volver_a_seleccion(),
                        ),
                        encabezado_venta,
                    ],
                ),
                campo_busqueda,
                ft.Container(expand=True, content=contenedor_menu),
            ],
        ),
    )

    renderizar_subcuentas()
    actualizar_carrito()

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

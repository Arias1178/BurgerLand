import asyncio
import datetime
import os

import flet as ft

from database.database import SessionLocal
from database.models import (
    Usuario,
    detalle_ventas,
    mesas,
    metodos_pago,
    productos,
    ventas,
)
from services.domicilios_service import (
    cambiar_estado_domicilio,
    listar_domicilios_activos,
)
from services.historial_service import buscar_ventas_historial
from services.whatsapp_service import (
    ESTADO_ENVIADO,
    ESTADO_ERROR,
    ESTADO_PENDIENTE,
    actualizar_estado_envio_venta,
    enviar_comprobante,
    generar_comprobante_pdf,
    generar_mensaje_comprobante,
)


def obtener_productos_texto(db, id_venta):
    detalles = db.query(detalle_ventas).filter(detalle_ventas.id_venta == id_venta).all()
    partes = []
    for d in detalles:
        prod = db.query(productos).filter(productos.id_producto == d.id_producto).first()
        nombre = d.nombre_producto or (prod.nombre if prod else "Producto eliminado")
        if d.personalizacion:
            nombre = f"{nombre} ({d.personalizacion})"
        partes.append(f"{nombre} x{d.cantidad}")
    return ", ".join(partes) if partes else "-"


def _badge(texto, color):
    return ft.Container(
        padding=ft.Padding(left=10, right=10, top=4, bottom=4),
        border_radius=999,
        bgcolor=color,
        content=ft.Text(texto, color="white", size=12, weight="bold"),
    )


def _crear_tarjeta_venta(page, db, venta):
    metodo = db.query(metodos_pago).filter(metodos_pago.id_metodos_pago == venta.id_metodos_pagos).first()
    usuario = db.query(Usuario).filter(Usuario.id_usuario == venta.id_usuario).first()
    productos_texto = obtener_productos_texto(db, venta.id_venta)
    tipo_pedido = getattr(venta, "tipo_pedido", None) or (
        "MESA" if venta.id_mesa is not None else "MOSTRADOR"
    )
    mesa = db.get(mesas, venta.id_mesa) if venta.id_mesa is not None else None
    etiqueta_pedido = (
        f"Mesa {mesa.numero}"
        if tipo_pedido == "MESA" and mesa
        else "Domicilio"
        if tipo_pedido == "DOMICILIO"
        else "Mostrador"
    )
    whatsapp_estado = ft.Text(
        (
            f"WhatsApp: {venta.whatsapp_estado_envio}"
            if venta.whatsapp_cliente
            else "WhatsApp: Sin número"
        ),
        color="#FFB86C" if venta.whatsapp_estado_envio != ESTADO_ENVIADO else "#80C78A",
        size=12,
    )
    btn_whatsapp = ft.Button(
        "Enviar comprobante",
        bgcolor="#2E7D5B",
        color="white",
        visible=bool(
            venta.whatsapp_cliente
            and venta.whatsapp_estado_envio != ESTADO_ENVIADO
        ),
    )

    async def reintentar_envio(_evento):
        if not venta.whatsapp_cliente:
            return
        detalles = (
            db.query(detalle_ventas)
            .filter(detalle_ventas.id_venta == venta.id_venta)
            .order_by(detalle_ventas.id_detalle)
            .all()
        )
        items = []
        for detalle in detalles:
            producto = (
                db.get(productos, detalle.id_producto)
                if detalle.id_producto is not None
                else None
            )
            items.append(
                {
                    "nombre": detalle.nombre_producto
                    or (producto.nombre if producto else "Producto"),
                    "cantidad": detalle.cantidad,
                    "precio": detalle.precio_unitario,
                    "personalizacion": detalle.personalizacion,
                }
            )
        mesa = db.get(mesas, venta.id_mesa) if venta.id_mesa is not None else None
        destino = f"Mesa {mesa.numero}" if mesa else "Para llevar / Mostrador"
        mensaje = generar_mensaje_comprobante(
            negocio=os.environ.get("BUSINESS_NAME", "BurgerLand").strip()
            or "BurgerLand",
            consecutivo=str(venta.id_venta),
            fecha_hora=venta.fecha_hora,
            mesa=destino,
            items=items,
            subtotal=float(venta.total),
            total=float(venta.total),
            metodo_pago=metodo.nombre if metodo else "No disponible",
        )
        pdf_bytes = None
        if os.environ.get("WHATSAPP_PROVIDER", "wa_me").strip().lower() == "cloud_api":
            pdf_bytes = generar_comprobante_pdf(
                negocio=os.environ.get("BUSINESS_NAME", "BurgerLand").strip()
                or "BurgerLand",
                consecutivo=str(venta.id_venta),
                fecha_hora=venta.fecha_hora,
                mesa=destino,
                items=items,
                subtotal=float(venta.total),
                total=float(venta.total),
                metodo_pago=metodo.nombre if metodo else "No disponible",
            )
        try:
            resultado = await asyncio.to_thread(
                enviar_comprobante,
                venta.whatsapp_cliente,
                mensaje,
                pdf_bytes,
                f"comprobante-{venta.id_venta}.pdf",
            )
            if resultado.url:
                page.launch_url(resultado.url)
            actualizar_estado_envio_venta(
                db,
                venta.id_venta,
                resultado.estado,
            )
            whatsapp_estado.value = f"WhatsApp: {resultado.estado}"
            whatsapp_estado.color = (
                "#FFB86C"
                if resultado.estado == ESTADO_PENDIENTE
                else "#80C78A"
            )
            btn_whatsapp.text = (
                "Enviar comprobante"
                if resultado.estado == ESTADO_PENDIENTE
                else "Comprobante enviado"
            )
            btn_whatsapp.visible = resultado.estado != ESTADO_ENVIADO
        except Exception as error:
            actualizar_estado_envio_venta(
                db,
                venta.id_venta,
                ESTADO_ERROR,
                str(error),
            )
            whatsapp_estado.value = "WhatsApp: ERROR"
            whatsapp_estado.color = "#FF7B7B"
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("No se pudo enviar el comprobante"),
                    content=ft.Text(
                        f"{error}\nLa venta se conserva y puedes volver a intentar."
                    ),
                    actions=[
                        ft.TextButton(
                            "Cerrar",
                            on_click=lambda _e: page.pop_dialog(),
                        )
                    ],
                )
            )
        page.update()

    btn_whatsapp.on_click = reintentar_envio

    return ft.Container(
        border_radius=16,
        padding=16,
        bgcolor="#2E3344",
        border=ft.Border(
            left=ft.BorderSide(1, "#5A5F72"),
            right=ft.BorderSide(1, "#5A5F72"),
            top=ft.BorderSide(1, "#5A5F72"),
            bottom=ft.BorderSide(1, "#5A5F72"),
        ),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(
                                    venta.fecha_hora.strftime("%d/%m/%Y"),
                                    color="white",
                                    size=13,
                                    weight="bold",
                                ),
                                ft.Text(
                                    venta.fecha_hora.strftime("%H:%M"),
                                    color="#C9CEDB",
                                    size=12,
                                ),
                            ],
                        ),
                        _badge(f"${venta.total:,.0f}".replace(",", "."), "#F2C744"),
                    ],
                ),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        _badge(usuario.nombre if usuario else "Sin usuario", "#5A5F72"),
                        _badge(metodo.nombre if metodo else "Sin pago", "#7ABAFB"),
                        _badge(
                            etiqueta_pedido,
                            "#7A6AFB" if tipo_pedido == "DOMICILIO" else "#5A5F72",
                        ),
                    ],
                ),
                *(
                    [
                        ft.Text(
                            (
                                f"{venta.cliente or 'Sin cliente'} · "
                                f"{venta.telefono_cliente or 'Sin teléfono'} · "
                                f"{venta.direccion_domicilio or 'Sin dirección'} · "
                                f"Estado: "
                                f"{(venta.estado_domicilio or 'RECIBIDO').replace('_', ' ').title()}"
                            ),
                            color="#C9CEDB",
                            size=12,
                        ),
                        ft.Text(
                            f"Domicilio: ${venta.valor_domicilio:,.0f}".replace(",", "."),
                            color="#FFB86C",
                            size=12,
                        ),
                    ]
                    if tipo_pedido == "DOMICILIO"
                    else []
                ),
                ft.Text(
                    productos_texto,
                    color="#E3E7F1",
                    size=13,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                *(
                    [
                        ft.Text(
                            f"Error de WhatsApp: {venta.whatsapp_error}",
                            color="#FF7B7B",
                            size=12,
                        )
                    ]
                    if venta.whatsapp_estado_envio == ESTADO_ERROR
                    and venta.whatsapp_error
                    else []
                ),
                ft.Row(
                    controls=[whatsapp_estado, btn_whatsapp],
                    wrap=True,
                ),
            ],
        ),
    )


def _crear_lista_ventas(page, ventas_lista, db):
    if not ventas_lista:
        return ft.Container(
            padding=20,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("No hay registros para mostrar.", color="white"),
        )

    return ft.Column(
        spacing=12,
        scroll="auto",
        controls=[_crear_tarjeta_venta(page, db, venta) for venta in ventas_lista],
    )


def historial_view(page: ft.Page, navbar, usuario_actual=None):
    db = SessionLocal()
    try:
        metodos = db.query(metodos_pago).order_by(metodos_pago.nombre).all()
        usuarios = db.query(Usuario).order_by(Usuario.nombre).all()
    finally:
        db.close()

    estilo_campo_filtro = {
        "expand": True,
        "height": 50,
        "border_radius": 10,
        "filled": True,
        "fill_color": "#252A39",
        "border_color": "#454B60",
        "focused_border_color": "#F2C744",
        "label_style": ft.TextStyle(size=12, color="#AEB6C9"),
        "text_style": ft.TextStyle(size=13, color="#F4F5F8"),
        "content_padding": ft.Padding(left=12, right=12, top=10, bottom=8),
    }
    dia = ft.TextField(
        label="Día",
        keyboard_type=ft.KeyboardType.NUMBER,
        **estilo_campo_filtro,
    )
    mes = ft.TextField(
        label="Mes",
        keyboard_type=ft.KeyboardType.NUMBER,
        **estilo_campo_filtro,
    )
    anio = ft.TextField(
        label="Año",
        keyboard_type=ft.KeyboardType.NUMBER,
        **estilo_campo_filtro,
    )
    hora_desde = ft.TextField(
        label="Hora desde",
        hint_text="HH:MM",
        **estilo_campo_filtro,
    )
    hora_hasta = ft.TextField(
        label="Hora hasta",
        hint_text="HH:MM",
        **estilo_campo_filtro,
    )
    tipo = ft.Dropdown(
        label="Tipo de pedido",
        **estilo_campo_filtro,
        value="TODOS",
        options=[
            ft.dropdown.Option("TODOS", "Todos"),
            ft.dropdown.Option("MESA", "Mesa"),
            ft.dropdown.Option("DOMICILIO", "Domicilio"),
            ft.dropdown.Option("MOSTRADOR", "Mostrador"),
        ],
    )
    metodo = ft.Dropdown(
        label="Método de pago",
        **estilo_campo_filtro,
        value="TODOS",
        options=[
            ft.dropdown.Option("TODOS", "Todos"),
            *[
                ft.dropdown.Option(str(item.id_metodos_pago), item.nombre)
                for item in metodos
            ],
        ],
    )
    usuario = ft.Dropdown(
        label="Usuario / cajero",
        **estilo_campo_filtro,
        value="TODOS",
        options=[
            ft.dropdown.Option("TODOS", "Todos"),
            *[
                ft.dropdown.Option(str(item.id_usuario), item.nombre)
                for item in usuarios
            ],
        ],
    )
    mensaje = ft.Text("", size=13)
    resumen = ft.Text("", color="#F2C744", size=15, weight="bold")
    pagina_texto = ft.Text("", color="#C9CEDB")
    lista_ventas = ft.Column(spacing=12, scroll="auto", expand=True)
    domicilios_activos = ft.Column(spacing=10)
    estado_paginacion = {"pagina": 1, "paginas": 1}
    anterior = ft.TextButton("Anterior")
    siguiente = ft.TextButton("Siguiente")

    def cambiar_estado(venta_id, estado, motivo=None):
        try:
            db_estado = SessionLocal()
            try:
                cambiar_estado_domicilio(
                    db_estado,
                    venta_id,
                    estado,
                    getattr(usuario_actual, "id_usuario", None),
                    motivo,
                )
            finally:
                db_estado.close()
        except ValueError as error:
            mensaje.value = str(error)
            mensaje.color = "#FF7B7B"
            page.update()
            return
        refrescar_domicilios()
        refrescar(estado_paginacion["pagina"])

    def confirmar_cancelacion(venta_id):
        motivo_field = ft.TextField(
            label="Motivo de cancelación",
            multiline=True,
            min_lines=2,
            max_lines=3,
        )
        error = ft.Text("", color="#FF7B7B", size=12)

        def cancelar(_evento):
            try:
                db_estado = SessionLocal()
                try:
                    cambiar_estado_domicilio(
                        db_estado,
                        venta_id,
                        "CANCELADO",
                        getattr(usuario_actual, "id_usuario", None),
                        motivo_field.value,
                    )
                finally:
                    db_estado.close()
            except ValueError as exc:
                error.value = str(exc)
                page.update()
                return
            page.pop_dialog()
            refrescar_domicilios()
            refrescar(estado_paginacion["pagina"])

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Cancelar domicilio"),
                content=ft.Column(
                    tight=True,
                    controls=[
                        ft.Text(
                            "Se registrará la devolución contable. Para pagos "
                            "no efectivos, realiza también la devolución por el "
                            "canal correspondiente.",
                            color="#FFB86C",
                        ),
                        motivo_field,
                        error,
                    ],
                ),
                actions=[
                    ft.TextButton(
                        "Volver",
                        on_click=lambda _evento: page.pop_dialog(),
                    ),
                    ft.ElevatedButton(
                        "Cancelar pedido",
                        bgcolor="#8A3A3A",
                        color="white",
                        on_click=cancelar,
                    ),
                ],
            )
        )

    def refrescar_domicilios():
        db_local = SessionLocal()
        try:
            registros = listar_domicilios_activos(db_local)
            filas = []
            for domicilio in registros:
                estado_actual = domicilio.estado_domicilio or "RECIBIDO"
                siguientes = {
                    "RECIBIDO": ["EN_PREPARACION", "CANCELADO"],
                    "EN_PREPARACION": ["EN_CAMINO", "CANCELADO"],
                    "EN_CAMINO": ["ENTREGADO", "CANCELADO"],
                }.get(estado_actual, [])
                selector_estado = ft.Dropdown(
                    label="Cambiar estado",
                    width=205,
                    options=[
                        ft.dropdown.Option(
                            estado,
                            estado.replace("_", " ").title(),
                        )
                        for estado in siguientes
                    ],
                )

                def guardar_estado(
                    _evento,
                    venta_id=domicilio.id_venta,
                    selector=selector_estado,
                ):
                    if not selector.value:
                        return
                    if selector.value == "CANCELADO":
                        confirmar_cancelacion(venta_id)
                    else:
                        cambiar_estado(venta_id, selector.value)

                filas.append(
                    ft.Container(
                        bgcolor="#2E3344",
                        border_radius=12,
                        padding=14,
                        content=ft.Row(
                            wrap=True,
                            alignment="spaceBetween",
                            controls=[
                                ft.Column(
                                    spacing=3,
                                    controls=[
                                        ft.Text(
                                            f"Venta #{domicilio.id_venta} · "
                                            f"{domicilio.cliente} · "
                                            f"{domicilio.telefono_cliente}",
                                            color="white",
                                            weight="bold",
                                        ),
                                        ft.Text(
                                            f"{domicilio.direccion_domicilio} · "
                                            f"{domicilio.barrio_referencia or 'Sin referencia'}",
                                            color="#C9CEDB",
                                        ),
                                        ft.Text(
                                            f"{estado_actual.replace('_', ' ').title()} · "
                                            f"{domicilio.domiciliario or 'Sin domiciliario'}",
                                            color="#FFB86C",
                                        ),
                                    ],
                                ),
                                selector_estado,
                                ft.ElevatedButton(
                                    "Actualizar",
                                    on_click=guardar_estado,
                                ),
                            ],
                        ),
                    )
                )
            domicilios_activos.controls = filas or [
                ft.Text("No hay domicilios activos.", color="#C9CEDB")
            ]
        finally:
            db_local.close()

    def refrescar(numero_pagina=1):
        try:
            filtros = {
                "dia": dia.value or None,
                "mes": mes.value or None,
                "anio": anio.value or None,
                "hora_desde": hora_desde.value or None,
                "hora_hasta": hora_hasta.value or None,
                "tipo_pedido": (
                    tipo.value if tipo.value and tipo.value != "TODOS" else None
                ),
                "metodo_pago_id": (
                    int(metodo.value)
                    if metodo.value and metodo.value != "TODOS"
                    else None
                ),
                "usuario_id": (
                    int(usuario.value)
                    if usuario.value and usuario.value != "TODOS"
                    else None
                ),
            }
            db_local = SessionLocal()
            try:
                resultado = buscar_ventas_historial(
                    db_local,
                    **filtros,
                    pagina=numero_pagina,
                )
                lista_ventas.controls = [
                    _crear_tarjeta_venta(page, db_local, venta)
                    for venta in resultado["ventas"]
                ] or [
                    ft.Container(
                        padding=20,
                        content=ft.Text(
                            "No hay registros para los filtros seleccionados.",
                            color="#C9CEDB",
                        ),
                    )
                ]
            finally:
                db_local.close()
            estado_paginacion["pagina"] = resultado["pagina"]
            estado_paginacion["paginas"] = resultado["paginas"]
            resumen.value = (
                f"{resultado['cantidad']} ventas · "
                f"Total filtrado: ${resultado['total']:,.0f}".replace(",", ".")
            )
            mensaje.value = ""
            mensaje.color = "#C9CEDB"
        except ValueError as error:
            lista_ventas.controls = []
            resumen.value = ""
            mensaje.value = str(error)
            mensaje.color = "#FF7B7B"

        pagina_texto.value = (
            f"Página {estado_paginacion['pagina']} de {estado_paginacion['paginas']}"
        )
        anterior.disabled = estado_paginacion["pagina"] <= 1
        siguiente.disabled = (
            estado_paginacion["pagina"] >= estado_paginacion["paginas"]
        )
        page.update()

    anterior.on_click = lambda _e: refrescar(estado_paginacion["pagina"] - 1)
    siguiente.on_click = lambda _e: refrescar(estado_paginacion["pagina"] + 1)
    aplicar_filtros = ft.ElevatedButton(
        "Aplicar filtros",
        bgcolor="#F2C744",
        color="#111111",
        on_click=lambda _e: refrescar(1),
    )
    limpiar_filtros = ft.TextButton(
        "Limpiar",
        icon=ft.Icons.FILTER_ALT_OFF_OUTLINED,
        style=ft.ButtonStyle(color="#C9CEDB"),
        on_click=lambda _e: (
            setattr(dia, "value", ""),
            setattr(mes, "value", ""),
            setattr(anio, "value", ""),
            setattr(hora_desde, "value", ""),
            setattr(hora_hasta, "value", ""),
            setattr(tipo, "value", "TODOS"),
            setattr(metodo, "value", "TODOS"),
            setattr(usuario, "value", "TODOS"),
            refrescar(1),
        ),
    )
    filtros_fecha = ft.ResponsiveRow(
        spacing=10,
        run_spacing=8,
        controls=[
            ft.Container(col={"xs": 4, "md": 1.5}, content=dia),
            ft.Container(col={"xs": 4, "md": 1.5}, content=mes),
            ft.Container(col={"xs": 4, "md": 2}, content=anio),
            ft.Container(col={"xs": 6, "md": 3.5}, content=hora_desde),
            ft.Container(col={"xs": 6, "md": 3.5}, content=hora_hasta),
        ],
    )
    filtros_categoria = ft.ResponsiveRow(
        spacing=10,
        run_spacing=8,
        controls=[
            ft.Container(col={"xs": 12, "sm": 4}, content=tipo),
            ft.Container(col={"xs": 12, "sm": 4}, content=metodo),
            ft.Container(col={"xs": 12, "sm": 4}, content=usuario),
        ],
    )
    panel_filtros = ft.Container(
        padding=18,
        bgcolor="#2E3344",
        border=ft.Border.all(1, "#454B60"),
        border_radius=14,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    spacing=9,
                    controls=[
                        ft.Icon(
                            ft.Icons.FILTER_ALT_OUTLINED,
                            color="#F2C744",
                            size=19,
                        ),
                        ft.Text(
                            "Filtrar ventas",
                            color="white",
                            size=15,
                            weight="bold",
                        ),
                        ft.Text(
                            "Combina fecha, hora y detalles del pedido",
                            color="#AEB6C9",
                            size=12,
                        ),
                    ],
                ),
                filtros_fecha,
                filtros_categoria,
                ft.Row(
                    wrap=True,
                    spacing=8,
                    alignment="spaceBetween",
                    controls=[
                        ft.Row(
                            wrap=True,
                            spacing=8,
                            controls=[aplicar_filtros, limpiar_filtros],
                        ),
                        ft.Row(
                            wrap=True,
                            spacing=12,
                            controls=[resumen, mensaje],
                        ),
                    ],
                ),
            ],
        ),
    )

    tarjeta = ft.Container(
        expand=True,
        bgcolor="#3A3F52",
        border_radius=20,
        padding=30,
        content=ft.Column(
            expand=True,
            spacing=20,
            scroll="auto",
            controls=[
                ft.Row(
                    alignment="spaceBetween",
                    controls=[
                        ft.Text("HISTORIAL DE VENTAS", size=22, weight="bold", color="white"),
                        _badge("Filtros combinables", "#5A5F72"),
                    ],
                ),
                ft.Text(
                    "DOMICILIOS ACTIVOS",
                    size=18,
                    weight="bold",
                    color="white",
                ),
                domicilios_activos,
                ft.Divider(color="#5A5F72"),
                panel_filtros,
                ft.Container(height=460, content=lista_ventas),
                ft.Row(
                    alignment="center",
                    controls=[anterior, pagina_texto, siguiente],
                ),
            ],
        ),
    )

    refrescar_domicilios()
    refrescar()
    return ft.Column(expand=True, spacing=20, scroll="auto", controls=[navbar, tarjeta])

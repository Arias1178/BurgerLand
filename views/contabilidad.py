"""
Vista de Operatividad Contable.

Muestra el desglose de ventas brutas/netas, la separación de
Impoconsumo/IVA, el registro de propinas y el costo de ventas de la
caja del día, pero SOLO permite procesar/guardar la consolidación si la
caja ya fue arqueada y cerrada (estado CERRADA/COMPLETADA).

Si la caja sigue ABIERTA, se muestra un mensaje informativo y el
formulario queda deshabilitado.
"""

import datetime as dt

import flet as ft

from database.database import SessionLocal
from database.models import Debt, Payroll, Service, Transaction, rol
from services.financial_engine import FinancialEngine

from services.contabilidad_service import (
    ContabilidadError,
    TASA_IMPOCONSUMO_DEFECTO,
    TASA_IVA_DEFECTO,
    can_process_accounting,
    procesar_consolidacion_contable,
)


def _formatear_pesos(valor):
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _tarjeta_resumen(titulo, valor, color="#F2C744"):
    return ft.Container(
        width=210,
        height=110,
        bgcolor="#2E3344",
        border_radius=18,
        padding=18,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text(titulo, size=14, color="#C9CEDB", weight="bold"),
                ft.Text(valor, size=20, color=color, weight="bold"),
            ],
        ),
    )


def _panel_financiero(page: ft.Page, usuario_actual=None):
    """Panel de P&L, flujo de caja y registro rápido dentro de Contabilidad."""
    hoy = dt.date.today()
    db_usuario = SessionLocal()
    try:
        rol_usuario = db_usuario.query(rol).filter(
            rol.id_rol == getattr(usuario_actual, "id_rol", None)
        ).first()
    finally:
        db_usuario.close()
    es_administrador = rol_usuario is not None and rol_usuario.nombre == "ADMIN"
    inicio_field = ft.TextField(
        label="Desde (AAAA-MM-DD)", value=hoy.replace(day=1).isoformat(), width=190
    )
    fin_field = ft.TextField(label="Hasta (AAAA-MM-DD)", value=hoy.isoformat(), width=190)
    tipo_field = ft.Dropdown(
        label="Tipo de transacción",
        width=310,
        value="ingreso",
        options=[
            ft.dropdown.Option("ingreso", "Ingreso"),
            ft.dropdown.Option("gasto_fijo", "Gasto fijo"),
            ft.dropdown.Option("gasto_variable", "Gasto variable"),
            ft.dropdown.Option("gasto_financiero", "Gasto financiero"),
        ],
    )
    monto_field = ft.TextField(label="Monto", width=150, keyboard_type=ft.KeyboardType.NUMBER)
    categoria_field = ft.TextField(label="Categoría", width=190)
    pagado_field = ft.Checkbox(label="Pagado", value=True)
    mensaje = ft.Text("", size=13)
    resultados = ft.Column(spacing=8)

    def cargar_datos():
        try:
            inicio = dt.date.fromisoformat(inicio_field.value)
            fin = dt.date.fromisoformat(fin_field.value)
            if inicio > fin:
                raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
        except (TypeError, ValueError) as error:
            mensaje.value = f"Fechas inválidas: {error}"
            mensaje.color = "#FF7B7B"
            page.update()
            return

        db = SessionLocal()
        try:
            engine = FinancialEngine(
                transactions=db.query(Transaction).all(),
                payroll=db.query(Payroll).all(),
                debts=db.query(Debt).all(),
                services=db.query(Service).all(),
            )
            pnl = engine.calculate_pnl(inicio, fin)
            cash = engine.calculate_cash_flow(inicio, fin)
            try:
                break_even = engine.calculate_break_even()
                break_even_text = _formatear_pesos(break_even)
            except ValueError:
                break_even_text = "Sin datos suficientes"
        finally:
            db.close()

        resultados.controls = [
            ft.Text("Resultados financieros", size=18, weight="bold", color="white"),
            ft.Row(
                wrap=True,
                spacing=14,
                run_spacing=14,
                controls=[
                    _tarjeta_resumen("Ingresos", _formatear_pesos(pnl.ingresos_totales), "#7AE582"),
                    _tarjeta_resumen("Utilidad bruta", _formatear_pesos(pnl.utilidad_bruta), "#7AE582"),
                    _tarjeta_resumen("Utilidad operativa", _formatear_pesos(pnl.utilidad_operativa), "#7ABAFB"),
                    _tarjeta_resumen("Utilidad neta", _formatear_pesos(pnl.utilidad_neta), "#F2C744"),
                    _tarjeta_resumen("Flujo neto", _formatear_pesos(cash.flujo_neto), "#7AE582"),
                    _tarjeta_resumen("Abonos a capital", _formatear_pesos(cash.abonos_capital), "#FFB86C"),
                    _tarjeta_resumen("Punto de equilibrio", break_even_text, "#F2C744"),
                ],
            ),
            ft.Text(
                f"Salidas de caja: {_formatear_pesos(cash.salidas)} | "
                f"Cuentas pendientes: {_formatear_pesos(cash.cuentas_pendientes)}",
                color="#C9CEDB",
            ),
            ft.Text(
                "La utilidad neta descuenta intereses, pero no abonos a capital. "
                "El flujo de caja sí incluye todos los pagos y el capital.",
                color="#9AA0B4",
                size=12,
            ),
        ]
        mensaje.value = "Resultados actualizados."
        mensaje.color = "#7AE582"
        page.update()

    def registrar_transaccion(_e):
        try:
            monto = float(monto_field.value or 0)
            if monto < 0:
                raise ValueError("El monto no puede ser negativo.")
            tipo = (tipo_field.value or "").strip()
            tipos_validos = {"ingreso", "gasto_fijo", "gasto_variable", "gasto_financiero"}
            if tipo not in tipos_validos:
                raise ValueError("El tipo no coincide con uno de los tipos permitidos.")
            fecha = dt.datetime.combine(dt.date.fromisoformat(fin_field.value), dt.time.min)
            if not categoria_field.value:
                raise ValueError("La categoría es obligatoria.")
        except (TypeError, ValueError) as error:
            mensaje.value = f"No se pudo registrar: {error}"
            mensaje.color = "#FF7B7B"
            page.update()
            return

        db = SessionLocal()
        try:
            db.add(
                Transaction(
                    tipo=tipo,
                    monto=monto,
                    fecha=fecha,
                    categoria=categoria_field.value.strip(),
                    pagado=bool(pagado_field.value),
                )
            )
            db.commit()
        finally:
            db.close()
        monto_field.value = ""
        categoria_field.value = ""
        mensaje.value = "Transacción registrada correctamente."
        mensaje.color = "#7AE582"
        cargar_datos()

    lista_nomina = ft.Column(spacing=10)
    lista_deudas = ft.Column(spacing=10)
    lista_servicios = ft.Column(spacing=10)
    resumen_calculo = ft.Column(spacing=4)

    def _texto_numero(valor):
        try:
            return f"${float(valor):,.2f}"
        except (TypeError, ValueError):
            return str(valor)

    def _badge_incluido(incluido, on_click):
        return ft.Container(
            bgcolor="#7AE582" if incluido else "#3A3F52",
            border_radius=8,
            padding=ft.padding.Padding(left=10, top=4, right=10, bottom=4),
            on_click=on_click,
            ink=True,
            tooltip="Clic para incluir/excluir del cálculo",
            content=ft.Text(
                "Incluido" if incluido else "Excluido",
                size=11,
                weight="bold",
                color="#101420" if incluido else "#A7AEC2",
            ),
        )

    def _fila_registro(titulo, subtitulo, incluido, on_toggle, on_editar, on_eliminar):
        return ft.Container(
            bgcolor="#232838",
            border_radius=14,
            padding=14,
            border=ft.Border.all(1, "#323852"),
            content=ft.Row(
                alignment="spaceBetween",
                vertical_alignment="center",
                wrap=True,
                spacing=10,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(titulo, size=15, weight="bold", color="white"),
                            ft.Text(subtitulo, size=12, color="#A7AEC2"),
                        ],
                    ),
                    ft.Row(
                        spacing=6,
                        vertical_alignment="center",
                        controls=[
                            _badge_incluido(incluido, on_toggle),
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                icon_color="#F2C744",
                                tooltip="Editar",
                                on_click=on_editar,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="#FF7B7B",
                                tooltip="Eliminar",
                                on_click=on_eliminar,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _fila_vacia(texto):
        return ft.Container(
            bgcolor="#1B202B",
            border_radius=14,
            padding=16,
            content=ft.Text(texto, color="#7A8194", size=13, italic=True),
        )

    def refrescar_catalogos():
        db = SessionLocal()
        try:
            empleados = db.query(Payroll).order_by(Payroll.nombre).all()
            deudas = db.query(Debt).order_by(Debt.nombre).all()
            servicios = db.query(Service).order_by(Service.nombre).all()
        finally:
            db.close()

        lista_nomina.controls = [
            _fila_registro(
                item.nombre,
                f"Base {_texto_numero(item.salario_base)} · Comisiones {_texto_numero(item.comisiones)} · {item.tipo_contrato}",
                bool(item.incluido_en_calculo),
                lambda e, i=item: toggle_incluido(Payroll, i.id, bool(i.incluido_en_calculo)),
                lambda e, i=item: abrir_dialogo_nomina(i.id),
                lambda e, i=item: eliminar_click(Payroll, i.id, i.nombre),
            )
            for item in empleados
        ] or [_fila_vacia("Aún no hay empleados registrados.")]

        lista_deudas.controls = [
            _fila_registro(
                item.nombre,
                f"Total {_texto_numero(item.monto_total)} · Cuota {_texto_numero(item.cuota_mensual)} · {'Pagada' if item.pagado else 'Pendiente'}",
                bool(item.incluido_en_calculo),
                lambda e, i=item: toggle_incluido(Debt, i.id, bool(i.incluido_en_calculo)),
                lambda e, i=item: abrir_dialogo_deuda(i.id),
                lambda e, i=item: eliminar_click(Debt, i.id, i.nombre),
            )
            for item in deudas
        ] or [_fila_vacia("Aún no hay deudas registradas.")]

        lista_servicios.controls = [
            _fila_registro(
                item.nombre,
                f"{_texto_numero(item.monto)} · {(item.tipo or '').capitalize()} · {'Pagado' if item.pagado else 'Pendiente'}",
                bool(item.incluido_en_calculo),
                lambda e, i=item: toggle_incluido(Service, i.id, bool(i.incluido_en_calculo)),
                lambda e, i=item: abrir_dialogo_servicio(i.id),
                lambda e, i=item: eliminar_click(Service, i.id, i.nombre),
            )
            for item in servicios
        ] or [_fila_vacia("Aún no hay servicios registrados.")]

        resumen_calculo.controls = [
            ft.Text("Se tendrá en cuenta en el cálculo:", color="#C9CEDB", weight="bold"),
            ft.Text(
                "Empleados: " + (", ".join(item.nombre for item in empleados if item.incluido_en_calculo) or "ninguno"),
                color="#7AE582",
            ),
            ft.Text(
                "Deudas: " + (", ".join(item.nombre for item in deudas if item.incluido_en_calculo) or "ninguna"),
                color="#FFB86C",
            ),
            ft.Text(
                "Servicios: " + (", ".join(item.nombre for item in servicios if item.incluido_en_calculo) or "ninguno"),
                color="#7ABAFB",
            ),
        ]

    def toggle_incluido(modelo, registro_id, valor_actual):
        if not es_administrador:
            mensaje.value = "Solo un administrador puede modificar catálogos."
            mensaje.color = "#FF7B7B"
            page.update()
            return
        db = SessionLocal()
        try:
            registro = db.get(modelo, registro_id)
            if registro:
                registro.incluido_en_calculo = not valor_actual
                db.commit()
        finally:
            db.close()
        refrescar_catalogos()
        cargar_datos()

    def eliminar_registro(modelo, registro_id, nombre, cerrar_dialogo_previo=False):
        def borrar(_e):
            db = SessionLocal()
            try:
                registro = db.get(modelo, registro_id)
                if registro:
                    db.delete(registro)
                    db.commit()
            finally:
                db.close()
            mensaje.value = f"{nombre} eliminado correctamente."
            mensaje.color = "#7AE582"
            page.pop_dialog()
            refrescar_catalogos()
            cargar_datos()

        if cerrar_dialogo_previo:
            page.pop_dialog()

        confirmacion = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text(f"¿Deseas eliminar «{nombre}» del sistema? Esta acción no se puede deshacer."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Eliminar", on_click=borrar),
            ],
        )
        page.show_dialog(confirmacion)

    def eliminar_click(modelo, registro_id, nombre):
        if not es_administrador:
            mensaje.value = "Solo un administrador puede eliminar catálogos."
            mensaje.color = "#FF7B7B"
            page.update()
            return
        eliminar_registro(modelo, registro_id, nombre)

    def _dialogo_acciones(guardar, eliminar=None):
        acciones = [ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog())]
        if eliminar is not None:
            acciones.append(
                ft.TextButton("Eliminar", style=ft.ButtonStyle(color="#FF7B7B"), on_click=eliminar)
            )
        acciones.append(
            ft.ElevatedButton(content="Guardar", bgcolor="#F2C744", color="#101420", on_click=guardar)
        )
        return acciones

    def abrir_dialogo_nomina(registro_id=None):
        if not es_administrador:
            mensaje.value = "Solo un administrador puede modificar catálogos."
            mensaje.color = "#FF7B7B"
            page.update()
            return
        registro = None
        if registro_id is not None:
            db = SessionLocal()
            try:
                registro = db.get(Payroll, registro_id)
            finally:
                db.close()
            if registro is None:
                mensaje.value = "El registro ya no existe."
                mensaje.color = "#FF7B7B"
                page.update()
                return

        campo_nombre = ft.TextField(label="Nombre del empleado", width=280, value=registro.nombre if registro else "")
        campo_base = ft.TextField(label="Salario base", width=280, value=str(registro.salario_base) if registro else "")
        campo_comisiones = ft.TextField(label="Comisiones", width=280, value=str(registro.comisiones) if registro else "0")
        campo_cargas = ft.TextField(label="Cargas sociales %", width=280, value=str(registro.cargas_sociales_porcentaje) if registro else "0")
        campo_contrato = ft.Dropdown(
            label="Tipo de contrato",
            width=280,
            value=registro.tipo_contrato if registro else "Indefinido",
            options=[
                ft.dropdown.Option("Indefinido"),
                ft.dropdown.Option("Fijo"),
                ft.dropdown.Option("Prestación de servicios"),
                ft.dropdown.Option("Aprendiz"),
            ],
        )
        campo_incluido = ft.Checkbox(
            label="Incluir en cálculo",
            value=bool(registro.incluido_en_calculo) if registro else True,
        )
        error_texto = ft.Text("", color="#FF7B7B", size=12)

        def guardar(_e):
            try:
                base = float(campo_base.value or 0)
                comisiones = float(campo_comisiones.value or 0)
                cargas = float(campo_cargas.value or 0)
                if base < 0 or comisiones < 0 or cargas < 0:
                    raise ValueError("Los valores no pueden ser negativos.")
                nombre = campo_nombre.value.strip() or "Empleado"
                db = SessionLocal()
                try:
                    if registro_id is None:
                        db.add(
                            Payroll(
                                nombre=nombre,
                                salario_base=base,
                                comisiones=comisiones,
                                cargas_sociales_porcentaje=cargas,
                                tipo_contrato=campo_contrato.value or "No especificado",
                                incluido_en_calculo=bool(campo_incluido.value),
                            )
                        )
                    else:
                        item = db.get(Payroll, registro_id)
                        item.nombre = nombre
                        item.salario_base = base
                        item.comisiones = comisiones
                        item.cargas_sociales_porcentaje = cargas
                        item.tipo_contrato = campo_contrato.value or "No especificado"
                        item.incluido_en_calculo = bool(campo_incluido.value)
                    db.commit()
                finally:
                    db.close()
                mensaje.value = "Empleado registrado correctamente." if registro_id is None else "Empleado actualizado correctamente."
                mensaje.color = "#7AE582"
                page.pop_dialog()
                refrescar_catalogos()
                cargar_datos()
            except (TypeError, ValueError) as error:
                error_texto.value = str(error)
                page.update()

        eliminar = None
        if registro is not None:
            eliminar = lambda e: eliminar_registro(Payroll, registro.id, registro.nombre, cerrar_dialogo_previo=True)

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo empleado" if registro is None else "Editar empleado"),
            content=ft.Column(
                width=320,
                spacing=12,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[campo_nombre, campo_base, campo_comisiones, campo_cargas, campo_contrato, campo_incluido, error_texto],
            ),
            actions=_dialogo_acciones(guardar, eliminar),
        )
        page.show_dialog(dialogo)

    def abrir_dialogo_deuda(registro_id=None):
        if not es_administrador:
            mensaje.value = "Solo un administrador puede modificar catálogos."
            mensaje.color = "#FF7B7B"
            page.update()
            return
        registro = None
        if registro_id is not None:
            db = SessionLocal()
            try:
                registro = db.get(Debt, registro_id)
            finally:
                db.close()
            if registro is None:
                mensaje.value = "El registro ya no existe."
                mensaje.color = "#FF7B7B"
                page.update()
                return

        campo_nombre = ft.TextField(label="Nombre de la deuda", width=280, value=registro.nombre if registro else "")
        campo_total = ft.TextField(label="Deuda total", width=280, value=str(registro.monto_total) if registro else "")
        campo_tasa = ft.TextField(label="Tasa interés %", width=280, value=str(registro.tasa_interes) if registro else "0")
        campo_cuota = ft.TextField(label="Cuota mensual", width=280, value=str(registro.cuota_mensual) if registro else "")
        campo_capital = ft.TextField(label="Abono capital", width=280, value=str(registro.abono_capital) if registro else "0")
        campo_interes = ft.TextField(label="Pago interés", width=280, value=str(registro.pago_interes) if registro else "0")
        campo_pagada = ft.Checkbox(label="Pagada", value=bool(registro.pagado) if registro else True)
        campo_incluido = ft.Checkbox(
            label="Incluir en cálculo",
            value=bool(registro.incluido_en_calculo) if registro else True,
        )
        error_texto = ft.Text("", color="#FF7B7B", size=12)

        def guardar(_e):
            try:
                total = float(campo_total.value or 0)
                tasa = float(campo_tasa.value or 0)
                cuota = float(campo_cuota.value or 0)
                capital = float(campo_capital.value or 0)
                interes = float(campo_interes.value or 0)
                if any(valor < 0 for valor in (total, tasa, cuota, capital, interes)):
                    raise ValueError("Los valores no pueden ser negativos.")
                nombre = campo_nombre.value.strip() or "Deuda"
                db = SessionLocal()
                try:
                    if registro_id is None:
                        db.add(
                            Debt(
                                nombre=nombre,
                                monto_total=total,
                                tasa_interes=tasa,
                                cuota_mensual=cuota,
                                abono_capital=capital,
                                pago_interes=interes,
                                pagado=bool(campo_pagada.value),
                                incluido_en_calculo=bool(campo_incluido.value),
                            )
                        )
                    else:
                        item = db.get(Debt, registro_id)
                        item.nombre = nombre
                        item.monto_total = total
                        item.tasa_interes = tasa
                        item.cuota_mensual = cuota
                        item.abono_capital = capital
                        item.pago_interes = interes
                        item.pagado = bool(campo_pagada.value)
                        item.incluido_en_calculo = bool(campo_incluido.value)
                    db.commit()
                finally:
                    db.close()
                mensaje.value = "Deuda registrada correctamente." if registro_id is None else "Deuda actualizada correctamente."
                mensaje.color = "#7AE582"
                page.pop_dialog()
                refrescar_catalogos()
                cargar_datos()
            except (TypeError, ValueError) as error:
                error_texto.value = str(error)
                page.update()

        eliminar = None
        if registro is not None:
            eliminar = lambda e: eliminar_registro(Debt, registro.id, registro.nombre, cerrar_dialogo_previo=True)

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva deuda" if registro is None else "Editar deuda"),
            content=ft.Column(
                width=320,
                spacing=12,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    campo_nombre,
                    campo_total,
                    campo_tasa,
                    campo_cuota,
                    campo_capital,
                    campo_interes,
                    campo_pagada,
                    campo_incluido,
                    error_texto,
                ],
            ),
            actions=_dialogo_acciones(guardar, eliminar),
        )
        page.show_dialog(dialogo)

    def abrir_dialogo_servicio(registro_id=None):
        if not es_administrador:
            mensaje.value = "Solo un administrador puede modificar catálogos."
            mensaje.color = "#FF7B7B"
            page.update()
            return
        registro = None
        if registro_id is not None:
            db = SessionLocal()
            try:
                registro = db.get(Service, registro_id)
            finally:
                db.close()
            if registro is None:
                mensaje.value = "El registro ya no existe."
                mensaje.color = "#FF7B7B"
                page.update()
                return

        campo_nombre = ft.TextField(label="Servicio", width=280, value=registro.nombre if registro else "")
        campo_monto = ft.TextField(label="Monto", width=280, value=str(registro.monto) if registro else "")
        campo_tipo = ft.Dropdown(
            label="Tipo de servicio",
            width=280,
            value=registro.tipo if registro else "fijo",
            options=[
                ft.dropdown.Option("fijo", "Fijo"),
                ft.dropdown.Option("variable", "Variable"),
            ],
        )
        campo_pagado = ft.Checkbox(label="Pagado", value=bool(registro.pagado) if registro else True)
        campo_incluido = ft.Checkbox(
            label="Incluir en cálculo",
            value=bool(registro.incluido_en_calculo) if registro else True,
        )
        error_texto = ft.Text("", color="#FF7B7B", size=12)

        def guardar(_e):
            try:
                monto = float(campo_monto.value or 0)
                if monto < 0:
                    raise ValueError("El monto no puede ser negativo.")
                tipo = (campo_tipo.value or "").lower()
                if tipo not in {"fijo", "variable"}:
                    raise ValueError("El servicio debe ser fijo o variable.")
                nombre = campo_nombre.value.strip() or "Servicio"
                db = SessionLocal()
                try:
                    if registro_id is None:
                        db.add(
                            Service(
                                nombre=nombre,
                                monto=monto,
                                tipo=tipo,
                                pagado=bool(campo_pagado.value),
                                incluido_en_calculo=bool(campo_incluido.value),
                            )
                        )
                    else:
                        item = db.get(Service, registro_id)
                        item.nombre = nombre
                        item.monto = monto
                        item.tipo = tipo
                        item.pagado = bool(campo_pagado.value)
                        item.incluido_en_calculo = bool(campo_incluido.value)
                    db.commit()
                finally:
                    db.close()
                mensaje.value = "Servicio registrado correctamente." if registro_id is None else "Servicio actualizado correctamente."
                mensaje.color = "#7AE582"
                page.pop_dialog()
                refrescar_catalogos()
                cargar_datos()
            except (TypeError, ValueError) as error:
                error_texto.value = str(error)
                page.update()

        eliminar = None
        if registro is not None:
            eliminar = lambda e: eliminar_registro(Service, registro.id, registro.nombre, cerrar_dialogo_previo=True)

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo servicio" if registro is None else "Editar servicio"),
            content=ft.Column(
                width=320,
                spacing=12,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[campo_nombre, campo_monto, campo_tipo, campo_pagado, campo_incluido, error_texto],
            ),
            actions=_dialogo_acciones(guardar, eliminar),
        )
        page.show_dialog(dialogo)

    def _boton_accion(texto, on_click, icono=None, color="#F2C744"):
        return ft.ElevatedButton(
            content=texto,
            icon=icono,
            on_click=on_click,
            bgcolor=color,
            color="#101420",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        )

    def _seccion_lista(titulo, descripcion, lista_column, on_nuevo):
        return ft.Container(
            bgcolor="#1F2430",
            border_radius=18,
            padding=18,
            border=ft.Border.all(1, "#313A4F"),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        vertical_alignment="center",
                        wrap=True,
                        spacing=10,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(titulo, size=18, weight="bold", color="white"),
                                    ft.Text(descripcion, size=12, color="#A7AEC2"),
                                ],
                            ),
                            _boton_accion("Nuevo", on_click=on_nuevo, icono=ft.Icons.ADD_CIRCLE_OUTLINE, color="#7AE582"),
                        ],
                    ),
                    lista_column,
                ],
            ),
        )

    formulario = ft.Container(
        bgcolor="#2E3344",
        border_radius=22,
        padding=22,
        content=ft.Column(
            spacing=18,
            controls=[
                ft.Container(
                    bgcolor="#1F2430",
                    border_radius=18,
                    padding=18,
                    border=ft.Border.all(1, "#38415A"),
                    content=ft.Row(
                        alignment="spaceBetween",
                        vertical_alignment="center",
                        controls=[
                            ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text("Análisis financiero", size=22, weight="bold", color="white"),
                                    ft.Text("Gestión de ingresos, egresos, nómina, deudas y servicios.", size=13, color="#A7AEC2"),
                                ],
                            ),
                            ft.Container(
                                bgcolor="#2D3748",
                                border_radius=12,
                                padding=8,
                                content=ft.Text("Panel administrativo", color="#F2C744", weight="bold"),
                            ),
                        ],
                    ),
                ),
                ft.Row(
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
                    controls=[
                        inicio_field,
                        fin_field,
                        _boton_accion("Calcular", on_click=cargar_datos, icono=ft.Icons.CALCULATE_OUTLINED),
                    ],
                ),
                ft.Container(
                    bgcolor="#1F2430",
                    border_radius=18,
                    padding=18,
                    border=ft.Border.all(1, "#313A4F"),
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Text("Registrar transacción", size=18, weight="bold", color="white"),
                            ft.Row(
                                wrap=True,
                                spacing=10,
                                run_spacing=10,
                                controls=[
                                    tipo_field,
                                    monto_field,
                                    categoria_field,
                                    pagado_field,
                                    _boton_accion("Registrar", on_click=registrar_transaccion, icono=ft.Icons.ADD_CIRCLE_OUTLINE),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Divider(color="#4A5064"),
                ft.Text("Catálogos y costos operativos", size=20, weight="bold", color="white"),
                ft.Column(
                    spacing=16,
                    controls=[
                        _seccion_lista(
                            "Nómina",
                            "Registra y administra empleados, salarios, cargas y contrato.",
                            lista_nomina,
                            lambda e: abrir_dialogo_nomina(),
                        ),
                        _seccion_lista(
                            "Deudas",
                            "Controla financiamiento, cuota, intereses y abonos a capital.",
                            lista_deudas,
                            lambda e: abrir_dialogo_deuda(),
                        ),
                        _seccion_lista(
                            "Servicios",
                            "Administra gastos operativos o servicios contratados del negocio.",
                            lista_servicios,
                            lambda e: abrir_dialogo_servicio(),
                        ),
                    ],
                ),
                ft.Container(
                    bgcolor="#1F2430",
                    border_radius=18,
                    padding=18,
                    border=ft.Border.all(1, "#313A4F"),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Text("Estado del cálculo", size=18, weight="bold", color="white"),
                            resumen_calculo,
                        ],
                    ),
                ),
                mensaje,
                resultados,
            ],
        ),
    )
    refrescar_catalogos()
    cargar_datos()
    return formulario


def contabilidad_view(page: ft.Page, navbar, usuario_actual=None, caja_actual=None):
    """
    Construye la vista de Operatividad Contable.

    - `caja_actual`: instancia de la caja abierta del usuario (si existe),
      obtenida de la misma manera que en el resto del sistema
      (ver `main.cargar_caja_actual`). Puede ser None si no hay caja
      abierta ni cerrada reciente para el usuario.
    """
    caja_id = caja_actual.id_caja if caja_actual else None
    estado = can_process_accounting(caja_id)

    mensaje_resultado = ft.Text("", size=14)

    # --- Caso bloqueado: caja abierta o inexistente -------------------
    if not estado.habilitado:
        panel_bloqueo = ft.Container(
            expand=True,
            bgcolor="#2E3344",
            border_radius=18,
            padding=30,
            content=ft.Column(
                spacing=16,
                horizontal_alignment="center",
                alignment="center",
                controls=[
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=48, color="#F2C744"),
                    ft.Text(
                        "Operatividad Contable no disponible",
                        size=22,
                        weight="bold",
                        color="white",
                    ),
                    ft.Text(
                        estado.mensaje,
                        size=15,
                        color="#C9CEDB",
                        text_align="center",
                    ),
                    ft.Text(
                        f"Estado actual de caja: {estado.estado_caja or 'SIN CAJA'}",
                        size=13,
                        color="#9AA0B4",
                    ),
                ],
            ),
        )

        return ft.Column(
            expand=True,
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                navbar,
                ft.Text("CONTABILIDAD Y OPERATIVIDAD", size=26, weight="bold", color="white"),
                _panel_financiero(page, usuario_actual),
                panel_bloqueo,
            ],
        )

    # --- Caso habilitado: caja cerrada, se puede procesar --------------
    propinas_field = ft.TextField(
        label="Propinas registradas",
        value="0",
        width=260,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    impoconsumo_field = ft.TextField(
        label="Tasa Impoconsumo (ej. 0.08 = 8%)",
        value=str(TASA_IMPOCONSUMO_DEFECTO),
        width=260,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    iva_field = ft.TextField(
        label="Tasa IVA (ej. 0.19 = 19%)",
        value=str(TASA_IVA_DEFECTO),
        width=260,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    observaciones_field = ft.TextField(
        label="Observaciones",
        value="",
        width=540,
        multiline=True,
        min_lines=2,
        max_lines=4,
    )

    tarjetas_resultado = ft.Row(wrap=True, spacing=18, run_spacing=18, controls=[])

    aviso_ya_procesada = ft.Text(
        "Esta caja ya tiene una consolidación contable guardada. Al procesar de nuevo se actualizará.",
        color="#F2C744",
        size=13,
        visible=estado.ya_procesada,
    )

    def procesar(_e):
        try:
            resultado = procesar_consolidacion_contable(
                caja_id,
                usuario_id=usuario_actual.id_usuario if usuario_actual else None,
                propinas=propinas_field.value,
                tasa_impoconsumo=impoconsumo_field.value,
                tasa_iva=iva_field.value,
                observaciones=observaciones_field.value,
            )
        except ContabilidadError as error:
            mensaje_resultado.value = str(error)
            mensaje_resultado.color = "#FF7B7B"
            page.update()
            return
        except Exception as error:  # noqa: BLE001 - mensaje amigable al usuario
            mensaje_resultado.value = f"Error inesperado al procesar la consolidación: {error}"
            mensaje_resultado.color = "#FF7B7B"
            page.update()
            return

        consolidacion = resultado["consolidacion"]
        tarjetas_resultado.controls = [
            _tarjeta_resumen("Venta bruta", _formatear_pesos(consolidacion["venta_bruta"]), "#F2C744"),
            _tarjeta_resumen("Venta neta", _formatear_pesos(consolidacion["venta_neta"]), "#7AE582"),
            _tarjeta_resumen("Impoconsumo", _formatear_pesos(consolidacion["impoconsumo"]), "#FFB86C"),
            _tarjeta_resumen("IVA", _formatear_pesos(consolidacion["iva"]), "#FFB86C"),
            _tarjeta_resumen("Propinas", _formatear_pesos(consolidacion["propinas"]), "#7ABAFB"),
            _tarjeta_resumen("Costo de ventas", _formatear_pesos(consolidacion["costo_ventas"]), "#FF7B7B"),
            _tarjeta_resumen("Utilidad bruta", _formatear_pesos(consolidacion["utilidad_bruta"]), "#7AE582"),
        ]
        mensaje_resultado.value = resultado["mensaje"]
        mensaje_resultado.color = "#7AE582"
        aviso_ya_procesada.visible = True
        page.update()

    boton_procesar = ft.ElevatedButton(
        "Procesar consolidación contable",
        bgcolor="#F2C744",
        color="#111111",
        on_click=procesar,
    )

    formulario = ft.Container(
        bgcolor="#2E3344",
        border_radius=18,
        padding=24,
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Text("Datos para la consolidación", size=18, weight="bold", color="white"),
                ft.Row(spacing=16, controls=[propinas_field, impoconsumo_field, iva_field]),
                observaciones_field,
                aviso_ya_procesada,
                boton_procesar,
                mensaje_resultado,
            ],
        ),
    )

    return ft.Column(
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            navbar,
            ft.Text("OPERATIVIDAD CONTABLE", size=26, weight="bold", color="white"),
            ft.Text(f"Caja #{caja_id} — Estado: {estado.estado_caja}", size=14, color="#C9CEDB"),
            _panel_financiero(page, usuario_actual),
            formulario,
            tarjetas_resultado,
        ],
    )

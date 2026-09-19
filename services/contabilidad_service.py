# services/contabilidad_service.py
"""
Servicio de Operatividad Contable.

Contiene la lógica necesaria para determinar si una caja ya puede ser
procesada contablemente (desglose de ventas brutas/netas, separación de
Impoconsumo/IVA, registro de propinas y costo de ventas), y para calcular
y persistir dicha consolidación.

Regla de negocio central: la Operatividad Contable de una caja SOLO se
habilita cuando el Cierre de Caja del día ya pasó a un estado
"CERRADA" (o "COMPLETADA", si el sistema llegara a usar ese nombre).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import (
    caja,
    categorias_gasto,
    cierre_contable,
    consolidaciones_contables,
    costo_producto,
    detalle_ventas,
    empleados,
    estados_caja,
    gastos,
    informes,
    nomina_mensual,
    parametros_legales,
    productos,
    ventas,
)

# Estados de caja que habilitan el procesamiento contable.
ESTADOS_CAJA_HABILITAN_CONTABILIDAD = {"CERRADA", "COMPLETADA"}

# Tasas por defecto usadas para el desglose de ventas brutas -> netas.
# Se pueden ajustar según la normativa vigente (Colombia: Impoconsumo 8%).
TASA_IMPOCONSUMO_DEFECTO = 0.08
TASA_IVA_DEFECTO = 0.0


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _get_parametros_legales(db: Session, anio: Optional[int] = None) -> parametros_legales:
    if anio is None:
        anio = datetime.date.today().year
    parametros = db.query(parametros_legales).filter(parametros_legales.anio == anio).first()
    if parametros is None:
        parametros = parametros_legales(
            anio=anio,
            smlv=1750905,
            auxilio_transporte=249095,
            uvt=52374,
            pct_salud_empleador=0.085,
            pct_pension_empleador=0.12,
            pct_arl=0.00522,
            pct_caja_compensacion=0.04,
            pct_cesantias=1 / 12,
            pct_intereses_cesantias=0.12,
            pct_prima=1 / 12,
            pct_vacaciones=1 / 24,
            tarifa_impoconsumo=0.08,
            tarifa_rst=0.019,
        )
        db.add(parametros)
        db.commit()
        db.refresh(parametros)
    return parametros


class ContabilidadError(Exception):
    """Error de negocio propio del módulo de Operatividad Contable."""


@dataclass
class EstadoOperatividadContable:
    """Resultado de validar si una caja puede procesarse contablemente."""

    habilitado: bool
    mensaje: str
    caja_id: Optional[int] = None
    estado_caja: Optional[str] = None
    ya_procesada: bool = False


def _obtener_nombre_estado_caja(db: Session, caja_obj: caja) -> Optional[str]:
    if caja_obj is None or caja_obj.id_estado_caja is None:
        return None
    estado = db.query(estados_caja).filter(
        estados_caja.id_estado_caja == caja_obj.id_estado_caja
    ).first()
    return estado.nombre if estado else None


def can_process_accounting(caja_id: Optional[int]) -> EstadoOperatividadContable:
    """
    Valida si la caja indicada ya puede procesarse en Operatividad Contable.

    Reglas:
      - Si no hay caja (caja_id es None), no se puede procesar.
      - Si la caja no existe en la base de datos, no se puede procesar.
      - Solo si el estado de la caja está en CERRADA/COMPLETADA se habilita.
      - Si la caja ya tiene una consolidación contable guardada, se informa
        para evitar procesarla dos veces (aunque puede seguir siendo
        editable si el flujo de negocio lo permite).

    No lanza excepciones: siempre retorna un objeto informativo para que
    la interfaz decida cómo mostrar el mensaje al usuario.
    """
    if not caja_id:
        return EstadoOperatividadContable(
            habilitado=False,
            mensaje="Debes abrir y cerrar la caja del día antes de acceder a Operatividad Contable.",
        )

    db = SessionLocal()
    try:
        caja_obj = db.query(caja).filter(caja.id_caja == caja_id).first()
        if not caja_obj:
            return EstadoOperatividadContable(
                habilitado=False,
                mensaje="La caja indicada no existe.",
                caja_id=caja_id,
            )

        nombre_estado = _obtener_nombre_estado_caja(db, caja_obj)
        if nombre_estado not in ESTADOS_CAJA_HABILITAN_CONTABILIDAD:
            return EstadoOperatividadContable(
                habilitado=False,
                mensaje=(
                    "La Operatividad Contable solo se habilita después de "
                    "cerrar la caja del día. Realiza el arqueo y cierre de "
                    "caja para continuar."
                ),
                caja_id=caja_id,
                estado_caja=nombre_estado,
            )

        consolidacion_existente = db.query(consolidaciones_contables).filter(
            consolidaciones_contables.id_caja == caja_id
        ).first()

        return EstadoOperatividadContable(
            habilitado=True,
            mensaje="Caja cerrada. Puedes procesar la consolidación contable.",
            caja_id=caja_id,
            estado_caja=nombre_estado,
            ya_procesada=consolidacion_existente is not None,
        )
    finally:
        db.close()


def requiere_caja_cerrada(func_vista):
    """
    Decorador para funciones/callbacks de vista que reciben `caja_id` como
    primer argumento posicional o como kwarg `caja_id`.

    Si la caja no está cerrada, lanza ContabilidadError con un mensaje
    apto para mostrar al usuario, en vez de ejecutar la lógica contable.
    """

    def envoltura(*args, **kwargs):
        caja_id = kwargs.get("caja_id")
        if caja_id is None and args:
            caja_id = args[0]

        estado = can_process_accounting(caja_id)
        if not estado.habilitado:
            raise ContabilidadError(estado.mensaje)

        return func_vista(*args, **kwargs)

    return envoltura


def _totales_caja(db: Session, caja_id: int):
    venta_bruta = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
        ventas.id_caja == caja_id
    ).scalar() or 0

    costo_ventas = db.query(func.coalesce(func.sum(ventas.costo_proveedor), 0)).filter(
        ventas.id_caja == caja_id
    ).scalar() or 0

    return float(venta_bruta), float(costo_ventas)


def calcular_costo_ventas(id_caja: int) -> float:
    """Calcula el costo real de ventas para una caja usando el costo unitario por producto."""
    db = SessionLocal()
    try:
        ventas_caja = db.query(ventas).filter(ventas.id_caja == id_caja).all()
        costo_total = 0.0
        for venta in ventas_caja:
            detalles = db.query(detalle_ventas).filter(detalle_ventas.id_venta == venta.id_venta).all()
            for detalle in detalles:
                if detalle.id_producto is None:
                    continue
                costo_producto_actual = (
                    db.query(costo_producto)
                    .filter(costo_producto.id_producto == detalle.id_producto)
                    .filter(costo_producto.fecha_actualizacion <= venta.fecha_hora.date())
                    .order_by(costo_producto.fecha_actualizacion.desc())
                    .first()
                )
                costo_unitario = float(costo_producto_actual.costo_unitario) if costo_producto_actual else 0.0
                costo_total += float(detalle.cantidad or 0) * costo_unitario
        return float(costo_total)
    finally:
        db.close()


def generar_cierre_contable(id_caja: int) -> cierre_contable:
    """Genera el cierre contable del día para la caja indicada y lo registra en BD."""
    db = SessionLocal()
    try:
        caja_obj = db.query(caja).filter(caja.id_caja == id_caja).first()
        if caja_obj is None:
            raise ContabilidadError(f"La caja {id_caja} no existe.")

        ingresos_totales = float(db.query(func.coalesce(func.sum(ventas.total), 0)).filter(ventas.id_caja == id_caja).scalar() or 0)
        costo_ventas = calcular_costo_ventas(id_caja)
        utilidad_bruta = ingresos_totales - costo_ventas
        fecha_cierre = (caja_obj.fecha_cierre or datetime.datetime.now()).date()
        gastos_del_dia = float(
            db.query(func.coalesce(func.sum(gastos.valor), 0))
            .filter(gastos.fecha == fecha_cierre)
            .scalar() or 0
        )
        utilidad_operacional = utilidad_bruta - gastos_del_dia
        margen_bruto_pct = (utilidad_bruta / ingresos_totales * 100) if ingresos_totales else 0.0

        cierre = db.query(cierre_contable).filter(cierre_contable.id_caja == id_caja).first()
        if cierre is None:
            cierre = cierre_contable(
                id_caja=id_caja,
                fecha=fecha_cierre,
                ingresos_totales=ingresos_totales,
                costo_ventas=costo_ventas,
                utilidad_bruta=utilidad_bruta,
                gastos_del_dia=gastos_del_dia,
                utilidad_operacional=utilidad_operacional,
                margen_bruto_pct=margen_bruto_pct,
            )
            db.add(cierre)
        else:
            cierre.fecha = fecha_cierre
            cierre.ingresos_totales = ingresos_totales
            cierre.costo_ventas = costo_ventas
            cierre.utilidad_bruta = utilidad_bruta
            cierre.gastos_del_dia = gastos_del_dia
            cierre.utilidad_operacional = utilidad_operacional
            cierre.margen_bruto_pct = margen_bruto_pct

        informe = db.query(informes).filter(informes.id_caja == id_caja).first()
        if informe is not None:
            cierre.id_informe = informe.id_informe

        db.commit()
        db.refresh(cierre)
        return cierre
    except ContabilidadError:
        db.rollback()
        raise
    except Exception as exc:  # pragma: no cover - handled by caller
        db.rollback()
        raise ContabilidadError(f"No fue posible generar el cierre contable: {exc}") from exc
    finally:
        db.close()


def calcular_nomina_mensual(id_empleado: int, periodo: str, parametros: parametros_legales) -> nomina_mensual:
    """Calcula el costo total del empleador para un mes, aplicando prestaciones sociales y seguridad social.

    La fórmula aplica auxilio de transporte cuando el salario base no supera 2*SMLV, suma salud,
    pensión, ARL, caja de compensación, cesantías, intereses a cesantías, prima y vacaciones.
    """
    if not id_empleado:
        raise ValueError("Debe indicar el empleado.")

    db = SessionLocal()
    try:
        empleado = db.query(empleados).filter(empleados.id_empleado == id_empleado).first()
        if empleado is None:
            raise ValueError(f"No existe el empleado con id {id_empleado}.")

        if parametros is None:
            parametros = _get_parametros_legales(db, None)
        if isinstance(parametros, dict):
            parametros = parametros_legales(
                anio=int(parametros.get("anio") or datetime.date.today().year),
                smlv=_float(parametros.get("smlv"), 1750905),
                auxilio_transporte=_float(parametros.get("auxilio_transporte"), 249095),
                uvt=_float(parametros.get("uvt"), 52374),
                pct_salud_empleador=_float(parametros.get("pct_salud_empleador"), 0.085),
                pct_pension_empleador=_float(parametros.get("pct_pension_empleador"), 0.12),
                pct_arl=_float(parametros.get("pct_arl"), 0.00522),
                pct_caja_compensacion=_float(parametros.get("pct_caja_compensacion"), 0.04),
                pct_cesantias=_float(parametros.get("pct_cesantias"), 1 / 12),
                pct_intereses_cesantias=_float(parametros.get("pct_intereses_cesantias"), 0.12),
                pct_prima=_float(parametros.get("pct_prima"), 1 / 12),
                pct_vacaciones=_float(parametros.get("pct_vacaciones"), 1 / 24),
                tarifa_impoconsumo=_float(parametros.get("tarifa_impoconsumo"), 0.08),
                tarifa_rst=_float(parametros.get("tarifa_rst"), 0.019),
            )

        salario_base = float(empleado.salario_base or 0)
        auxilio = float(parametros.auxilio_transporte) if salario_base <= (2 * float(parametros.smlv)) else 0.0
        salud_empleador = salario_base * float(parametros.pct_salud_empleador)
        pension_empleador = salario_base * float(parametros.pct_pension_empleador)
        arl = salario_base * float(parametros.pct_arl)
        caja_compensacion = salario_base * float(parametros.pct_caja_compensacion)
        base_cesantias = salario_base + auxilio
        provision_cesantias = base_cesantias * float(parametros.pct_cesantias)
        provision_intereses_cesantias = provision_cesantias * float(parametros.pct_intereses_cesantias)
        provision_prima = base_cesantias * float(parametros.pct_prima)
        provision_vacaciones = salario_base * float(parametros.pct_vacaciones)
        costo_total_empleador = (
            salario_base
            + auxilio
            + salud_empleador
            + pension_empleador
            + arl
            + caja_compensacion
            + provision_cesantias
            + provision_intereses_cesantias
            + provision_prima
            + provision_vacaciones
        )

        registro = db.query(nomina_mensual).filter(
            nomina_mensual.id_empleado == id_empleado,
            nomina_mensual.periodo == periodo,
        ).first()
        if registro is None:
            registro = nomina_mensual(id_empleado=id_empleado, periodo=periodo)
            db.add(registro)

        registro.salario_base = salario_base
        registro.auxilio_transporte = auxilio
        registro.salud_empleador = salud_empleador
        registro.pension_empleador = pension_empleador
        registro.arl = arl
        registro.caja_compensacion = caja_compensacion
        registro.provision_cesantias = provision_cesantias
        registro.provision_intereses_cesantias = provision_intereses_cesantias
        registro.provision_prima = provision_prima
        registro.provision_vacaciones = provision_vacaciones
        registro.costo_total_empleador = costo_total_empleador
        db.commit()
        db.refresh(registro)
        return registro
    finally:
        db.close()


def obtener_estado_resultados(fecha_inicio, fecha_fin) -> dict:
    """Calcula un estado de resultados resumido para un rango de fechas."""
    db = SessionLocal()
    try:
        fecha_inicio = datetime.date.fromisoformat(str(fecha_inicio))
        fecha_fin = datetime.date.fromisoformat(str(fecha_fin))
        cierres = db.query(cierre_contable).filter(cierre_contable.fecha >= fecha_inicio, cierre_contable.fecha <= fecha_fin).all()
        ingresos_totales = sum(float(item.ingresos_totales or 0) for item in cierres)
        costo_ventas = sum(float(item.costo_ventas or 0) for item in cierres)
        utilidad_bruta = ingresos_totales - costo_ventas
        gastos_fijos = sum(
            float(item.valor or 0)
            for item in db.query(gastos).filter(gastos.fecha >= fecha_inicio, gastos.fecha <= fecha_fin).all()
            if item.id_categoria_gasto is not None
        )

        nomina_total = 0.0
        for registro in db.query(nomina_mensual).all():
            try:
                periodo = datetime.datetime.strptime(registro.periodo, "%Y-%m").date()
            except ValueError:
                continue
            if fecha_inicio.year <= periodo.year <= fecha_fin.year and fecha_inicio.month <= periodo.month <= fecha_fin.month:
                nomina_total += float(registro.costo_total_empleador or 0)

        utilidad_operacional = utilidad_bruta - gastos_fijos - nomina_total
        margen_bruto_pct = (utilidad_bruta / ingresos_totales * 100) if ingresos_totales else 0.0
        parametros = _get_parametros_legales(db, fecha_inicio.year)
        impuesto_consumo = ingresos_totales * float(parametros.tarifa_impoconsumo or 0)
        rst = ingresos_totales * float(parametros.tarifa_rst or 0)

        return {
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "ingresos_totales": round(ingresos_totales, 2),
            "costo_ventas": round(costo_ventas, 2),
            "utilidad_bruta": round(utilidad_bruta, 2),
            "gastos_fijos": round(gastos_fijos, 2),
            "nomina_total": round(nomina_total, 2),
            "utilidad_operacional": round(utilidad_operacional, 2),
            "impuesto_consumo": round(impuesto_consumo, 2),
            "rst": round(rst, 2),
            "margen_bruto_pct": round(margen_bruto_pct, 2),
        }
    finally:
        db.close()


def calcular_punto_equilibrio(costos_fijos_mensuales, margen_bruto_pct) -> float:
    """Calcula el volumen mínimo de ventas para cubrir costos fijos mensuales."""
    costos_fijos = _float(costos_fijos_mensuales, 0.0)
    margen = _float(margen_bruto_pct, 0.0) / 100.0
    if margen <= 0:
        raise ValueError("El margen bruto debe ser mayor que cero.")
    return costos_fijos / margen


def exportar_estado_resultados_pdf(fecha_inicio, fecha_fin, path) -> str:
    """Exporta el estado de resultados a PDF usando reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    datos = obtener_estado_resultados(fecha_inicio, fecha_fin)
    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Estado de resultados", styles["Title"]),
        Spacer(1, 20),
        Paragraph(f"Periodo: {datos['fecha_inicio']} a {datos['fecha_fin']}", styles["BodyText"]),
        Spacer(1, 10),
    ]
    for clave, etiqueta in [
        ("ingresos_totales", "Ingresos totales"),
        ("costo_ventas", "Costo de ventas"),
        ("utilidad_bruta", "Utilidad bruta"),
        ("gastos_fijos", "Gastos fijos"),
        ("nomina_total", "Nómina"),
        ("utilidad_operacional", "Utilidad operacional"),
        ("impuesto_consumo", "Impuesto al consumo"),
        ("rst", "RST"),
        ("margen_bruto_pct", "Margen bruto %"),
    ]:
        story.append(Paragraph(f"{etiqueta}: ${float(datos[clave]):,.0f}".replace(",", "."), styles["BodyText"]))
    doc.build(story)
    return path


@requiere_caja_cerrada
def procesar_consolidacion_contable(
    caja_id: int,
    usuario_id: Optional[int] = None,
    propinas: float = 0.0,
    tasa_impoconsumo: float = TASA_IMPOCONSUMO_DEFECTO,
    tasa_iva: float = TASA_IVA_DEFECTO,
    observaciones: Optional[str] = None,
):
    """
    Calcula y persiste (crea o actualiza) la consolidación contable diaria
    de la caja indicada.

    Solo se ejecuta si `can_process_accounting(caja_id)` indica que la
    caja ya está cerrada; de lo contrario levanta ContabilidadError
    (gestionado por el decorador `requiere_caja_cerrada`).

    Retorna un diccionario con el resultado para la interfaz.
    """
    try:
        propinas = float(propinas or 0)
        tasa_impoconsumo = float(tasa_impoconsumo or 0)
        tasa_iva = float(tasa_iva or 0)
    except (TypeError, ValueError) as exc:
        raise ContabilidadError("Las propinas y las tasas deben ser valores numéricos.") from exc

    if propinas < 0 or tasa_impoconsumo < 0 or tasa_iva < 0:
        raise ContabilidadError("Las propinas y las tasas no pueden ser negativas.")

    db = SessionLocal()
    try:
        venta_bruta, costo_ventas = _totales_caja(db, caja_id)

        # Desglose venta bruta -> venta neta + impuestos.
        divisor = 1 + tasa_impoconsumo + tasa_iva
        venta_neta = venta_bruta / divisor if divisor else venta_bruta
        impoconsumo = venta_neta * tasa_impoconsumo
        iva = venta_neta * tasa_iva
        utilidad_bruta = venta_neta - costo_ventas

        registro = db.query(consolidaciones_contables).filter(
            consolidaciones_contables.id_caja == caja_id
        ).first()

        if registro is None:
            registro = consolidaciones_contables(id_caja=caja_id)
            db.add(registro)

        registro.id_usuario = usuario_id
        registro.fecha_procesamiento = datetime.datetime.now()
        registro.venta_bruta = venta_bruta
        registro.impoconsumo = impoconsumo
        registro.iva = iva
        registro.venta_neta = venta_neta
        registro.propinas = propinas
        registro.costo_ventas = costo_ventas
        registro.utilidad_bruta = utilidad_bruta
        registro.observaciones = observaciones

        db.commit()
        db.refresh(registro)

        return {
            "ok": True,
            "mensaje": "Consolidación contable procesada correctamente.",
            "consolidacion": {
                "id_consolidacion": registro.id_consolidacion,
                "id_caja": registro.id_caja,
                "venta_bruta": registro.venta_bruta,
                "impoconsumo": registro.impoconsumo,
                "iva": registro.iva,
                "venta_neta": registro.venta_neta,
                "propinas": registro.propinas,
                "costo_ventas": registro.costo_ventas,
                "utilidad_bruta": registro.utilidad_bruta,
                "observaciones": registro.observaciones,
                "fecha_procesamiento": registro.fecha_procesamiento,
            },
        }
    except ContabilidadError:
        raise
    except Exception as exc:  # noqa: BLE001 - se traduce a mensaje amigable
        db.rollback()
        raise ContabilidadError(f"No fue posible guardar la consolidación contable: {exc}") from exc
    finally:
        db.close()


def obtener_ultima_caja_cerrada(usuario_id: Optional[int] = None) -> Optional[caja]:
    """
    Retorna la caja cerrada más reciente (opcionalmente filtrada por
    usuario), útil para precargar la vista de Operatividad Contable.
    """
    db = SessionLocal()
    try:
        estado_cerrada = db.query(estados_caja).filter(
            estados_caja.nombre.in_(list(ESTADOS_CAJA_HABILITAN_CONTABILIDAD))
        ).all()
        ids_estado = [e.id_estado_caja for e in estado_cerrada]
        if not ids_estado:
            return None

        query = db.query(caja).filter(caja.id_estado_caja.in_(ids_estado))
        if usuario_id is not None:
            query = query.filter(caja.id_usuario == usuario_id)
        return query.order_by(caja.fecha_cierre.desc()).first()
    finally:
        db.close()

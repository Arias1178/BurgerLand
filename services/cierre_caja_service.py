# services/cierre_caja_service.py
"""
Servicio de Cierre de Caja.

Implementa `procesar_cierre_caja`, la función principal encargada de:
  1. Validar que la caja esté en estado "abierta".
  2. Calcular las ventas totales del turno, desglosadas por medio de
     pago (Efectivo, Tarjeta, Transferencia, Apps de Delivery).
  3. Comparar el conteo físico recibido contra el saldo teórico
     esperado por el sistema.
  4. Calcular la diferencia (sobrante o faltante).
  5. Descontar la "Base de Caja" configurada para el siguiente turno.
  6. Generar el registro de `AsientoContableDiario` desglosando ventas
     totales, impuestos (IVA / Impuesto al consumo) y egresos/gastos de
     caja chica del turno.
  7. Cambiar el estado de la caja a "cerrada" y guardar fecha/hora de
     cierre.

Todas las operaciones de base de datos se ejecutan dentro de un bloque
try/except con rollback ante cualquier error, para no dejar la caja en
un estado inconsistente.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import (
    AsientoContableDiario,
    Orden,
    Pago,
    caja,
    estados_caja,
    movimiento_caja,
)

# Medios de pago soportados en el desglose de ventas del turno.
MEDIOS_PAGO_SOPORTADOS = ("EFECTIVO", "TARJETA", "TRANSFERENCIA", "APP_DELIVERY")

# Tipos de movimiento de caja considerados egresos/gastos de caja chica.
TIPOS_MOVIMIENTO_EGRESO = ("EGRESO", "GASTO", "CAJA_CHICA")


class CierreCajaError(Exception):
    """Error de negocio genérico del proceso de cierre de caja."""


class CajaYaCerradaError(CierreCajaError):
    """La caja indicada ya se encuentra cerrada (o no está abierta)."""


class CajaNoEncontradaError(CierreCajaError):
    """No existe una caja con el id indicado."""


class DescuadreCajaError(CierreCajaError):
    """
    El conteo físico presenta una diferencia frente al saldo teórico
    que supera la tolerancia permitida.

    No necesariamente detiene el cierre (el negocio puede permitir
    cerrar con descuadre dejando constancia), pero se expone para que
    quien llame decida cómo manejarlo (ver parámetro `tolerancia`).
    """

    def __init__(self, mensaje: str, diferencia: float):
        super().__init__(mensaje)
        self.diferencia = diferencia


@dataclass
class ResumenCierreCaja:
    """Resumen del cierre de caja, listo para mostrarse en la vista."""

    id_caja: int
    fecha_cierre: datetime.datetime
    ventas_totales: float
    ventas_por_medio_pago: Dict[str, float]
    iva_total: float
    impuesto_consumo_total: float
    egresos_caja_chica: float
    saldo_teorico: float
    saldo_fisico_contado: float
    diferencia: float
    base_caja_siguiente_turno: float
    efectivo_a_consignar: float
    id_asiento: Optional[int] = None
    observaciones: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resumen a diccionario plano para la UI/serialización."""
        return {
            "id_caja": self.id_caja,
            "fecha_cierre": self.fecha_cierre,
            "ventas_totales": self.ventas_totales,
            "ventas_por_medio_pago": self.ventas_por_medio_pago,
            "iva_total": self.iva_total,
            "impuesto_consumo_total": self.impuesto_consumo_total,
            "egresos_caja_chica": self.egresos_caja_chica,
            "saldo_teorico": self.saldo_teorico,
            "saldo_fisico_contado": self.saldo_fisico_contado,
            "diferencia": self.diferencia,
            "base_caja_siguiente_turno": self.base_caja_siguiente_turno,
            "efectivo_a_consignar": self.efectivo_a_consignar,
            "id_asiento": self.id_asiento,
            "observaciones": self.observaciones,
        }


def _obtener_nombre_estado_caja(db: Session, caja_obj: caja) -> Optional[str]:
    if caja_obj is None or caja_obj.id_estado_caja is None:
        return None
    estado = db.query(estados_caja).filter(
        estados_caja.id_estado_caja == caja_obj.id_estado_caja
    ).first()
    return estado.nombre if estado else None


def _validar_conteo_fisico(conteo_fisico: Dict[str, Any]) -> float:
    """
    Valida y normaliza el diccionario de conteo físico recibido.

    Se admite:
      - {"total": 350000}
      - {"EFECTIVO": 300000, "TARJETA": 50000, ...}  -> se suma todo

    Retorna el total físico contado como float.
    Lanza CierreCajaError si el formato es inválido.
    """
    if not isinstance(conteo_fisico, dict) or not conteo_fisico:
        raise CierreCajaError("El conteo físico debe ser un diccionario no vacío.")

    try:
        if "total" in conteo_fisico:
            return float(conteo_fisico["total"])
        return float(sum(float(v) for v in conteo_fisico.values()))
    except (TypeError, ValueError) as exc:
        raise CierreCajaError(
            "El conteo físico debe contener únicamente valores numéricos."
        ) from exc


def _calcular_ventas_por_medio_pago(db: Session, id_caja: int) -> Dict[str, float]:
    """
    Calcula las ventas totales del turno agrupadas por medio de pago,
    considerando únicamente órdenes en estado PAGADA.
    """
    resultado = {medio: 0.0 for medio in MEDIOS_PAGO_SOPORTADOS}

    filas = (
        db.query(Pago.medio_pago, func.coalesce(func.sum(Pago.monto), 0))
        .join(Orden, Pago.id_orden == Orden.id_orden)
        .filter(Orden.id_caja == id_caja, Orden.estado == "PAGADA")
        .group_by(Pago.medio_pago)
        .all()
    )

    for medio_pago, total in filas:
        clave = (medio_pago or "").upper()
        resultado[clave] = resultado.get(clave, 0.0) + float(total or 0)

    return resultado


def _calcular_impuestos_turno(db: Session, id_caja: int) -> Dict[str, float]:
    """
    Suma el IVA y el Impuesto al Consumo de las órdenes pagadas del
    turno, tal como quedaron registrados en cada orden.
    """
    fila = (
        db.query(
            func.coalesce(func.sum(Orden.iva), 0),
            func.coalesce(func.sum(Orden.impuesto_consumo), 0),
        )
        .filter(Orden.id_caja == id_caja, Orden.estado == "PAGADA")
        .first()
    )
    iva_total, impuesto_consumo_total = fila if fila else (0, 0)
    return {
        "iva_total": float(iva_total or 0),
        "impuesto_consumo_total": float(impuesto_consumo_total or 0),
    }


def _calcular_egresos_caja_chica(db: Session, id_caja: int) -> float:
    """
    Suma los movimientos de caja del turno clasificados como egresos o
    gastos de caja chica (tabla `movimiento_caja`).
    """
    total = (
        db.query(func.coalesce(func.sum(movimiento_caja.valor), 0))
        .filter(
            movimiento_caja.id_caja == id_caja,
            movimiento_caja.tipo.in_(TIPOS_MOVIMIENTO_EGRESO),
        )
        .scalar()
    )
    return float(total or 0)


def procesar_cierre_caja(
    id_caja: int,
    conteo_fisico: Dict[str, Any],
    base_caja_siguiente_turno: float = 0.0,
    tolerancia_descuadre: float = 0.0,
    permitir_cierre_con_descuadre: bool = True,
) -> Dict[str, Any]:
    """
    Procesa el cierre de caja de un turno.

    Args:
        id_caja: Identificador de la caja activa a cerrar.
        conteo_fisico: Diccionario con el conteo físico del dinero al
            cierre. Acepta `{"total": <valor>}` o un desglose por
            canal (ej. `{"EFECTIVO": 300000, "TARJETA": 50000}`), en
            cuyo caso se suman todos los valores.
        base_caja_siguiente_turno: Monto que se debe dejar como base
            para el siguiente turno (se descuenta del efectivo a
            consignar).
        tolerancia_descuadre: Diferencia absoluta (en pesos) que se
            considera aceptable sin generar advertencia/errror.
        permitir_cierre_con_descuadre: Si es False y la diferencia
            absoluta supera `tolerancia_descuadre`, se lanza
            `DescuadreCajaError` y NO se cierra la caja. Si es True
            (por defecto), el cierre continúa dejando la diferencia
            registrada en el asiento contable y en el resumen.

    Returns:
        Un diccionario con el resumen completo del cierre, listo para
        que la vista lo muestre (ver `ResumenCierreCaja.to_dict`).

    Raises:
        CajaNoEncontradaError: si `id_caja` no existe.
        CajaYaCerradaError: si la caja no está en estado "ABIERTA".
        CierreCajaError: si el conteo físico es inválido o ocurre un
            error inesperado al persistir los cambios.
        DescuadreCajaError: si hay descuadre fuera de tolerancia y
            `permitir_cierre_con_descuadre` es False.
    """
    saldo_fisico_contado = _validar_conteo_fisico(conteo_fisico)

    db = SessionLocal()
    try:
        # --- 1. Validar que la caja esté abierta ------------------------
        caja_obj = db.query(caja).filter(caja.id_caja == id_caja).first()
        if not caja_obj:
            raise CajaNoEncontradaError(f"No existe la caja con id {id_caja}.")

        nombre_estado = _obtener_nombre_estado_caja(db, caja_obj)
        if nombre_estado != "ABIERTA":
            raise CajaYaCerradaError(
                f"La caja #{id_caja} no está abierta (estado actual: {nombre_estado or 'DESCONOCIDO'})."
            )

        estado_cerrada = db.query(estados_caja).filter(estados_caja.nombre == "CERRADA").first()
        if not estado_cerrada:
            raise CierreCajaError("No existe el estado 'CERRADA' configurado para caja.")

        # --- 2. Ventas totales del turno por medio de pago --------------
        ventas_por_medio_pago = _calcular_ventas_por_medio_pago(db, id_caja)
        ventas_totales = sum(ventas_por_medio_pago.values())

        # --- Impuestos y egresos ------------------------------------------
        impuestos = _calcular_impuestos_turno(db, id_caja)
        egresos_caja_chica = _calcular_egresos_caja_chica(db, id_caja)

        # --- 3. Saldo teórico vs conteo físico ---------------------------
        # Saldo teórico = saldo inicial + ventas en efectivo - egresos de caja chica.
        # (Solo el efectivo impacta el arqueo físico de caja; tarjeta,
        # transferencia y apps de delivery no mueven el cajón físico.)
        efectivo_turno = ventas_por_medio_pago.get("EFECTIVO", 0.0)
        saldo_teorico = float(caja_obj.saldo_inicial or 0) + efectivo_turno - egresos_caja_chica

        # --- 4. Diferencia (sobrante/faltante) ---------------------------
        diferencia = round(saldo_fisico_contado - saldo_teorico, 2)

        observaciones: List[str] = []
        if abs(diferencia) > tolerancia_descuadre:
            texto_diferencia = "sobrante" if diferencia > 0 else "faltante"
            mensaje_descuadre = (
                f"Se detectó un {texto_diferencia} de {abs(diferencia):,.2f} "
                f"en la caja #{id_caja}."
            )
            if not permitir_cierre_con_descuadre:
                raise DescuadreCajaError(mensaje_descuadre, diferencia)
            observaciones.append(mensaje_descuadre)

        # --- 5. Descontar base de caja para el siguiente turno -----------
        try:
            base_caja_siguiente_turno = float(base_caja_siguiente_turno or 0)
        except (TypeError, ValueError) as exc:
            raise CierreCajaError("La base de caja del siguiente turno debe ser numérica.") from exc

        if base_caja_siguiente_turno < 0:
            raise CierreCajaError("La base de caja del siguiente turno no puede ser negativa.")

        efectivo_a_consignar = round(saldo_fisico_contado - base_caja_siguiente_turno, 2)
        if efectivo_a_consignar < 0:
            observaciones.append(
                "El efectivo contado es menor que la base configurada para el "
                "siguiente turno; revisa el conteo físico."
            )

        # --- 6. Generar AsientoContableDiario ----------------------------
        detalle = {
            "ventas_por_medio_pago": ventas_por_medio_pago,
            "efectivo_turno": efectivo_turno,
        }
        asiento = db.query(AsientoContableDiario).filter(
            AsientoContableDiario.id_caja == id_caja
        ).first()
        if asiento is None:
            asiento = AsientoContableDiario(id_caja=id_caja)
            db.add(asiento)

        asiento.fecha = datetime.datetime.now()
        asiento.ventas_totales = ventas_totales
        asiento.iva_total = impuestos["iva_total"]
        asiento.impuesto_consumo_total = impuestos["impuesto_consumo_total"]
        asiento.egresos_caja_chica = egresos_caja_chica
        asiento.saldo_teorico = saldo_teorico
        asiento.saldo_fisico_contado = saldo_fisico_contado
        asiento.diferencia = diferencia
        asiento.base_caja_siguiente_turno = base_caja_siguiente_turno
        asiento.efectivo_a_consignar = efectivo_a_consignar
        asiento.detalle_json = json.dumps(detalle, ensure_ascii=False)

        # --- 7. Cambiar estado de la caja a cerrada ----------------------
        fecha_cierre = datetime.datetime.now()
        caja_obj.fecha_cierre = fecha_cierre
        caja_obj.saldo_final = saldo_fisico_contado
        caja_obj.id_estado_caja = estado_cerrada.id_estado_caja

        db.commit()
        db.refresh(asiento)
        db.refresh(caja_obj)

        resumen = ResumenCierreCaja(
            id_caja=id_caja,
            fecha_cierre=fecha_cierre,
            ventas_totales=ventas_totales,
            ventas_por_medio_pago=ventas_por_medio_pago,
            iva_total=impuestos["iva_total"],
            impuesto_consumo_total=impuestos["impuesto_consumo_total"],
            egresos_caja_chica=egresos_caja_chica,
            saldo_teorico=saldo_teorico,
            saldo_fisico_contado=saldo_fisico_contado,
            diferencia=diferencia,
            base_caja_siguiente_turno=base_caja_siguiente_turno,
            efectivo_a_consignar=efectivo_a_consignar,
            id_asiento=asiento.id_asiento,
            observaciones=observaciones,
        )
        return resumen.to_dict()

    except CierreCajaError:
        db.rollback()
        raise
    except Exception as exc:  # noqa: BLE001 - se traduce a excepción de negocio
        db.rollback()
        raise CierreCajaError(f"Error inesperado al procesar el cierre de caja: {exc}") from exc
    finally:
        db.close()

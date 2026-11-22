import datetime
import os
from decimal import Decimal, InvalidOperation

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    Transaction,
    caja,
    compras,
    estados_caja,
    movimiento_caja,
    retiros_caja,
    vinculos_retiro_compra,
)


DIAS_ALERTA_RETIRO = int(os.environ.get("RETIRO_ALERTA_DIAS", "3"))
CENTAVOS = Decimal("0.01")


def _monto(valor) -> Decimal:
    try:
        resultado = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("El monto debe ser numérico.") from error
    if not resultado.is_finite():
        raise ValueError("El monto debe ser un valor finito.")
    return resultado.quantize(CENTAVOS)


def _estado_caja(db: Session, caja_id: int) -> str | None:
    caja_registro = db.get(caja, caja_id)
    if caja_registro is None:
        return None
    estado = db.get(estados_caja, caja_registro.id_estado_caja)
    return estado.nombre if estado else None


def registrar_retiro(
    db: Session,
    caja_id: int,
    usuario_id: int | None,
    monto,
    motivo: str,
) -> retiros_caja:
    valor = _monto(monto)
    motivo = (motivo or "").strip()
    if valor <= 0:
        raise ValueError("El monto del retiro debe ser mayor que cero.")
    if not motivo:
        raise ValueError("Indica el motivo del retiro.")
    if _estado_caja(db, caja_id) != "ABIERTA":
        raise ValueError("El retiro requiere una caja abierta.")

    ahora = datetime.datetime.now()
    retiro = retiros_caja(
        id_caja=caja_id,
        id_usuario=usuario_id,
        fecha_hora=ahora,
        monto=float(valor),
        motivo=motivo,
    )
    try:
        db.add(retiro)
        db.flush()
        db.add(
            movimiento_caja(
                fecha=ahora,
                tipo="EGRESO",
                valor=float(valor),
                descripcion=f"Retiro pendiente #{retiro.id_retiro}: {motivo}",
                id_caja=caja_id,
            )
        )
        db.add(
            Transaction(
                tipo="retiro_inventario",
                monto=float(valor),
                fecha=ahora,
                categoria="Retiro pendiente de justificar",
                centro_de_costo_id=retiro.id_retiro,
                pagado=True,
            )
        )
        db.commit()
        db.refresh(retiro)
        return retiro
    except Exception:
        db.rollback()
        raise


def vincular_retiro_compra(
    db: Session,
    retiro_id: int,
    compra_id: int,
    monto_justificado,
) -> vinculos_retiro_compra:
    valor = _monto(monto_justificado)
    if valor <= 0:
        raise ValueError("El valor a justificar debe ser mayor que cero.")

    retiro = db.get(retiros_caja, retiro_id)
    compra = db.get(compras, compra_id)
    if retiro is None:
        raise ValueError("El retiro seleccionado no existe.")
    if compra is None:
        raise ValueError("La compra seleccionada no existe.")

    try:
        justificado_retiro = Decimal(
            str(
                db.query(
                    func.coalesce(func.sum(vinculos_retiro_compra.monto_justificado), 0)
                )
                .filter(vinculos_retiro_compra.id_retiro == retiro_id)
                .scalar()
                or 0
            )
        )
        justificado_compra = Decimal(
            str(
                db.query(
                    func.coalesce(func.sum(vinculos_retiro_compra.monto_justificado), 0)
                )
                .filter(vinculos_retiro_compra.id_compra == compra_id)
                .scalar()
                or 0
            )
        )
        if justificado_retiro + valor > _monto(retiro.monto):
            raise ValueError("El valor supera el saldo pendiente del retiro.")
        if justificado_compra + valor > _monto(compra.total):
            raise ValueError("El valor supera el saldo disponible de la compra.")

        vinculo = vinculos_retiro_compra(
            id_retiro=retiro_id,
            id_compra=compra_id,
            monto_justificado=float(valor),
        )
        db.add(vinculo)
        db.commit()
        db.refresh(vinculo)
        return vinculo
    except Exception:
        db.rollback()
        raise


def listar_conciliacion_retiros(
    db: Session,
    ahora: datetime.datetime | None = None,
    dias_alerta: int = DIAS_ALERTA_RETIRO,
) -> list[dict]:
    if dias_alerta < 0:
        raise ValueError("Los días para alertar no pueden ser negativos.")
    ahora = ahora or datetime.datetime.now()
    retiros = (
        db.query(retiros_caja)
        .order_by(retiros_caja.fecha_hora.desc(), retiros_caja.id_retiro.desc())
        .all()
    )
    resultado = []
    for retiro in retiros:
        enlaces = (
            db.query(vinculos_retiro_compra, compras)
            .join(compras, compras.id_compra == vinculos_retiro_compra.id_compra)
            .filter(vinculos_retiro_compra.id_retiro == retiro.id_retiro)
            .order_by(compras.fecha, compras.id_compra)
            .all()
        )
        monto_justificado = sum(
            (Decimal(str(vinculo.monto_justificado)) for vinculo, _ in enlaces),
            Decimal(0),
        ).quantize(CENTAVOS)
        pendiente = (_monto(retiro.monto) - monto_justificado).quantize(CENTAVOS)
        if pendiente <= 0:
            estado = "Conciliado"
        elif monto_justificado:
            estado = "Parcial"
        else:
            estado = "Pendiente"
        dias_transcurridos = (ahora - retiro.fecha_hora).days
        resultado.append(
            {
                "retiro": retiro,
                "compras": [
                    {
                        "compra": compra,
                        "monto_justificado": float(vinculo.monto_justificado),
                    }
                    for vinculo, compra in enlaces
                ],
                "monto_retirado": float(_monto(retiro.monto)),
                "monto_justificado": float(monto_justificado),
                "saldo_pendiente": float(pendiente),
                "estado": estado,
                "alerta": pendiente > 0 and dias_transcurridos >= dias_alerta,
                "dias_transcurridos": dias_transcurridos,
            }
        )
    return resultado


def listar_compras_disponibles(db: Session) -> list[dict]:
    resultado = []
    for compra in db.query(compras).order_by(compras.fecha.desc()).all():
        justificado = Decimal(
            str(
                db.query(
                    func.coalesce(func.sum(vinculos_retiro_compra.monto_justificado), 0)
                )
                .filter(vinculos_retiro_compra.id_compra == compra.id_compra)
                .scalar()
                or 0
            )
        ).quantize(CENTAVOS)
        pendiente = (_monto(compra.total) - justificado).quantize(CENTAVOS)
        if pendiente > 0:
            resultado.append(
                {"compra": compra, "saldo_disponible": float(pendiente)}
            )
    return resultado

import datetime

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from database.models import ventas


TAMANO_PAGINA_HISTORIAL = 30
MAXIMO_PAGINA_HISTORIAL = 100


def _validar_hora(valor: str | None, etiqueta: str) -> datetime.time | None:
    if not valor:
        return None
    try:
        return datetime.time.fromisoformat(valor)
    except (TypeError, ValueError) as error:
        raise ValueError(f"La hora {etiqueta} debe tener formato HH:MM.") from error


def buscar_ventas_historial(
    db: Session,
    *,
    dia: str | None = None,
    mes: str | None = None,
    anio: str | None = None,
    hora_desde: str | None = None,
    hora_hasta: str | None = None,
    tipo_pedido: str | None = None,
    metodo_pago_id: int | None = None,
    usuario_id: int | None = None,
    pagina: int = 1,
    tamano_pagina: int = TAMANO_PAGINA_HISTORIAL,
) -> dict:
    if pagina < 1:
        raise ValueError("La página debe ser mayor que cero.")
    if not 1 <= tamano_pagina <= MAXIMO_PAGINA_HISTORIAL:
        raise ValueError("El tamaño de página debe estar entre 1 y 100.")

    consulta = db.query(ventas)
    for valor, formato, etiqueta, minimo, maximo, ancho in (
        (dia, "%d", "día", 1, 31, 2),
        (mes, "%m", "mes", 1, 12, 2),
        (anio, "%Y", "año", 1, 9999, 4),
    ):
        if valor in (None, ""):
            continue
        try:
            entero = int(valor)
        except (TypeError, ValueError) as error:
            raise ValueError(f"El filtro de {etiqueta} debe ser numérico.") from error
        if not minimo <= entero <= maximo:
            raise ValueError(f"El filtro de {etiqueta} está fuera de rango.")
        consulta = consulta.filter(
            func.strftime(formato, ventas.fecha_hora) == f"{entero:0{ancho}d}"
        )

    hora_inicio = _validar_hora(hora_desde, "inicial")
    hora_fin = _validar_hora(hora_hasta, "final")
    if hora_inicio and hora_fin:
        inicio_texto = hora_inicio.strftime("%H:%M:%S")
        fin_texto = hora_fin.strftime("%H:%M:%S")
        criterio_hora = (
            or_(
                func.time(ventas.fecha_hora) >= inicio_texto,
                func.time(ventas.fecha_hora) <= fin_texto,
            )
            if hora_inicio > hora_fin
            else (
                (func.time(ventas.fecha_hora) >= inicio_texto)
                & (func.time(ventas.fecha_hora) <= fin_texto)
            )
        )
        consulta = consulta.filter(criterio_hora)
    elif hora_inicio:
        consulta = consulta.filter(
            func.time(ventas.fecha_hora) >= hora_inicio.strftime("%H:%M:%S")
        )
    elif hora_fin:
        consulta = consulta.filter(
            func.time(ventas.fecha_hora) <= hora_fin.strftime("%H:%M:%S")
        )

    if tipo_pedido:
        if tipo_pedido == "MESA":
            consulta = consulta.filter(ventas.tipo_pedido == "MESA")
        elif tipo_pedido == "MOSTRADOR":
            consulta = consulta.filter(ventas.tipo_pedido == "MOSTRADOR")
        elif tipo_pedido == "DOMICILIO":
            consulta = consulta.filter(ventas.tipo_pedido == "DOMICILIO")
        else:
            raise ValueError("El tipo de pedido seleccionado no es válido.")
    if metodo_pago_id is not None:
        consulta = consulta.filter(ventas.id_metodos_pagos == metodo_pago_id)
    if usuario_id is not None:
        consulta = consulta.filter(ventas.id_usuario == usuario_id)

    total = consulta.count()
    total_monto = float(
        consulta.with_entities(
            func.coalesce(
                func.sum(
                    case(
                        (ventas.estado_domicilio == "CANCELADO", 0),
                        else_=ventas.total,
                    )
                ),
                0,
            )
        ).scalar()
        or 0
    )
    registros = (
        consulta.order_by(ventas.fecha_hora.desc(), ventas.id_venta.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )
    return {
        "ventas": registros,
        "cantidad": total,
        "total": total_monto,
        "pagina": pagina,
        "paginas": max(1, (total + tamano_pagina - 1) // tamano_pagina),
    }

import os
import calendar
from collections import defaultdict
from pathlib import Path
import datetime as dt

import flet as ft
import flet.canvas as fcanvas
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from database.database import SessionLocal
from database.models import (
    Debt,
    Payroll,
    Service,
    Transaction,
    detalle_ventas,
    informes,
    metodos_pago,
    productos,
    ventas,
)
from services.financial_engine import FinancialEngine


def _formatear_pesos(valor):
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def _tarjeta_resumen(titulo, valor, color="#F2C744"):
    return ft.Container(
        width=210,
        height=120,
        bgcolor="#2E3344",
        border_radius=18,
        padding=18,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text(titulo, size=14, color="#C9CEDB", weight="bold"),
                ft.Text(valor, size=22, color=color, weight="bold"),
            ],
        ),
    )


_PALETA_GRAFICOS = ["#F2C744", "#7AE582", "#7ABAFB", "#FF7B7B", "#C792EA", "#5AD8A6", "#F2946B"]


def _total_general(informe):
    return float(informe.ventas_totales) - float(informe.total_proveedores)


def _grafico_barras(items, color="#F2C744", max_alto=150, formateador=None, ancho_barra=44):
    """Gráfica de barras simple construida con controles nativos de Flet."""
    items = [(nombre, float(valor or 0)) for nombre, valor in items]
    if not items:
        return ft.Text("No hay datos suficientes para graficar.", color="#C9CEDB", size=13)

    formateador = formateador or (lambda v: f"{v:,.0f}".replace(",", "."))
    valor_maximo = max((abs(v) for _, v in items), default=0) or 1

    barras = []
    for nombre, valor in items:
        alto_barra = max(6, (abs(valor) / valor_maximo) * max_alto)
        barras.append(
            ft.Column(
                spacing=6,
                horizontal_alignment="center",
                controls=[
                    ft.Text(formateador(valor), size=11, color="#E5E7EB", weight="bold"),
                    ft.Container(
                        width=ancho_barra,
                        height=alto_barra,
                        bgcolor=color,
                        border_radius=8,
                        alignment=ft.alignment.Alignment(0, 1),
                    ),
                    ft.Container(
                        width=ancho_barra + 26,
                        content=ft.Text(
                            nombre,
                            size=11,
                            color="#C9CEDB",
                            text_align="center",
                            max_lines=2,
                            overflow="ellipsis",
                        ),
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                ],
            )
        )

    return ft.Row(
        spacing=18,
        alignment="start",
        vertical_alignment="end",
        scroll="auto",
        controls=barras,
    )


def _grafico_pastel(items, tamano=170, formateador_valor=None):
    """Gráfica tipo pastel (donut) usando flet.canvas, con leyenda de porcentajes."""
    items = [(nombre, float(valor or 0)) for nombre, valor in items if valor and float(valor) > 0]
    if not items:
        return ft.Text("No hay datos suficientes para graficar.", color="#C9CEDB", size=13)

    formateador_valor = formateador_valor or _formatear_pesos
    total = sum(valor for _, valor in items) or 1

    figuras = []
    angulo_actual = 0.0
    for indice, (_, valor) in enumerate(items):
        color = _PALETA_GRAFICOS[indice % len(_PALETA_GRAFICOS)]
        angulo_barrido = 360 * (valor / total)
        figuras.append(
            fcanvas.Arc(
                x=5,
                y=5,
                width=tamano - 10,
                height=tamano - 10,
                start_angle=angulo_actual,
                sweep_angle=angulo_barrido,
                use_center=True,
                paint=ft.Paint(style=ft.PaintingStyle.FILL, color=color),
            )
        )
        angulo_actual += angulo_barrido

    lienzo = fcanvas.Canvas(shapes=figuras, width=tamano, height=tamano)

    leyenda = ft.Column(
        spacing=10,
        controls=[
            ft.Row(
                spacing=10,
                vertical_alignment="center",
                controls=[
                    ft.Container(width=14, height=14, bgcolor=_PALETA_GRAFICOS[i % len(_PALETA_GRAFICOS)], border_radius=4),
                    ft.Text(
                        f"{nombre}: {formateador_valor(valor)} ({valor / total * 100:.1f}%)",
                        size=12,
                        color="#E5E7EB",
                    ),
                ],
            )
            for i, (nombre, valor) in enumerate(items)
        ],
    )

    return ft.Row(spacing=24, vertical_alignment="center", controls=[lienzo, leyenda])


def _obtener_analisis_negocio(fecha_inicio=None, fecha_fin=None):
    db = SessionLocal()
    try:
        filtro_fecha = []
        if fecha_inicio is not None and fecha_fin is not None:
            inicio_dt = dt.datetime.combine(fecha_inicio, dt.time.min)
            fin_dt = dt.datetime.combine(fecha_fin, dt.time.max)
            filtro_fecha = [ventas.fecha_hora >= inicio_dt, ventas.fecha_hora <= fin_dt]

        total_ventas = db.query(func.coalesce(func.sum(ventas.total), 0)).filter(*filtro_fecha).scalar() or 0
        total_unidades = db.query(func.coalesce(func.sum(detalle_ventas.cantidad), 0)).join(
            ventas, detalle_ventas.id_venta == ventas.id_venta
        ).filter(*filtro_fecha).scalar() or 0
        ticket_promedio = 0
        total_ventas_registradas = db.query(ventas).filter(*filtro_fecha).count()
        if total_ventas_registradas:
            ticket_promedio = float(total_ventas) / float(total_ventas_registradas)

        metodo_totales = {}
        for metodo in db.query(metodos_pago).all():
            metodo_totales[metodo.nombre] = float(
                db.query(func.coalesce(func.sum(ventas.total), 0)).filter(
                    ventas.id_metodos_pagos == metodo.id_metodos_pago, *filtro_fecha
                ).scalar() or 0
            )

        productos_ventas = defaultdict(lambda: {"cantidad": 0, "ventas": 0.0})
        detalles_query = db.query(detalle_ventas).join(ventas, detalle_ventas.id_venta == ventas.id_venta).filter(*filtro_fecha)
        for detalle in detalles_query.all():
            producto = db.query(productos).filter(productos.id_producto == detalle.id_producto).first()
            if not producto:
                continue
            productos_ventas[producto.nombre]["cantidad"] += int(detalle.cantidad or 0)
            productos_ventas[producto.nombre]["ventas"] += float(detalle.subtotal or 0)

        productos_ordenados = sorted(
            [
                {
                    "nombre": nombre,
                    "cantidad": data["cantidad"],
                    "ventas": data["ventas"],
                }
                for nombre, data in productos_ventas.items()
            ],
            key=lambda item: item["cantidad"],
            reverse=True,
        )
        top_productos = productos_ordenados[:5]
        menos_vendidos = sorted(productos_ordenados, key=lambda item: item["cantidad"])[:5]

        return {
            "total_ventas": float(total_ventas),
            "total_unidades": int(total_unidades),
            "ticket_promedio": float(ticket_promedio),
            "metodo_totales": metodo_totales,
            "top_productos": top_productos,
            "menos_vendidos": menos_vendidos,
            "productos_detalle": {
                nombre: {"cantidad": data["cantidad"], "ventas": data["ventas"]}
                for nombre, data in productos_ventas.items()
            },
        }
    finally:
        db.close()


def _obtener_resumen_contabilidad_periodo(fecha_inicio, fecha_fin):
    db = SessionLocal()
    try:
        engine = FinancialEngine(
            transactions=db.query(Transaction).all(),
            payroll=db.query(Payroll).all(),
            debts=db.query(Debt).all(),
            services=db.query(Service).all(),
        )
        pnl = engine.calculate_pnl(fecha_inicio, fecha_fin)
        cash = engine.calculate_cash_flow(fecha_inicio, fecha_fin)
        return {
            "ingresos": float(pnl.ingresos_totales),
            "costos_variables": float(pnl.costos_variables_directos),
            "gastos_fijos": float(pnl.gastos_fijos_operativos),
            "gastos_financieros": float(pnl.gastos_financieros),
            "utilidad_neta": float(pnl.utilidad_neta),
            "flujo_neto": float(cash.flujo_neto),
            "entradas_caja": float(cash.entradas),
            "salidas_caja": float(cash.salidas),
            "periodo": f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}",
        }
    finally:
        db.close()


def _obtener_resumen_contabilidad():
    hoy = dt.date.today()
    inicio_mes = hoy.replace(day=1)
    return _obtener_resumen_contabilidad_periodo(inicio_mes, hoy)


def _ultimo_dia_mes(fecha):
    ultimo = calendar.monthrange(fecha.year, fecha.month)[1]
    return fecha.replace(day=ultimo)


def _es_fin_de_mes(fecha):
    return fecha.day == _ultimo_dia_mes(fecha).day


def informe_quincenal_habilitado(hoy=None):
    """El informe comparativo solo se habilita el día 15 y el último día del mes."""
    hoy = hoy or dt.date.today()
    return hoy.day == 15 or _es_fin_de_mes(hoy)


def _proxima_fecha_habilitacion(hoy=None):
    hoy = hoy or dt.date.today()
    ultimo_dia = _ultimo_dia_mes(hoy)
    if hoy.day < 15:
        return hoy.replace(day=15)
    if hoy.day < ultimo_dia.day:
        return ultimo_dia
    # Hoy ya es día 15 o el último día del mes (habilitado): calculamos la próxima ventana.
    if hoy.day == 15:
        return ultimo_dia
    if hoy.month == 12:
        return dt.date(hoy.year + 1, 1, 15)
    return dt.date(hoy.year, hoy.month + 1, 15)


def _rango_quincenas(hoy=None):
    """Devuelve (periodo_actual, periodo_anterior) para el informe comparativo quincenal."""
    hoy = hoy or dt.date.today()
    if hoy.day == 15:
        inicio_actual = hoy.replace(day=1)
        fin_actual = hoy
        fin_anterior = inicio_actual - dt.timedelta(days=1)
        inicio_anterior = fin_anterior.replace(day=16)
    else:
        inicio_actual = hoy.replace(day=16)
        fin_actual = hoy
        fin_anterior = hoy.replace(day=15)
        inicio_anterior = hoy.replace(day=1)

    periodo_actual = {
        "inicio": inicio_actual,
        "fin": fin_actual,
        "etiqueta": f"{inicio_actual.strftime('%d/%m/%Y')} - {fin_actual.strftime('%d/%m/%Y')}",
    }
    periodo_anterior = {
        "inicio": inicio_anterior,
        "fin": fin_anterior,
        "etiqueta": f"{inicio_anterior.strftime('%d/%m/%Y')} - {fin_anterior.strftime('%d/%m/%Y')}",
    }
    return periodo_actual, periodo_anterior


def _variacion_porcentual(actual, anterior):
    actual = float(actual or 0)
    anterior = float(anterior or 0)
    if anterior == 0:
        return None if actual == 0 else 100.0
    return ((actual - anterior) / abs(anterior)) * 100


def _indicador_variacion(variacion):
    if variacion is None:
        return "Sin datos previos", "#9AA0B4"
    if variacion > 0.05:
        return f"▲ {variacion:.1f}%", "#7AE582"
    if variacion < -0.05:
        return f"▼ {abs(variacion):.1f}%", "#FF7B7B"
    return "= 0.0%", "#C9CEDB"


def _obtener_comparativo_negocio(periodo_actual, periodo_anterior):
    actual = _obtener_analisis_negocio(periodo_actual["inicio"], periodo_actual["fin"])
    anterior = _obtener_analisis_negocio(periodo_anterior["inicio"], periodo_anterior["fin"])

    metricas = {
        "ventas": {
            "nombre": "Ventas totales",
            "actual": actual["total_ventas"],
            "anterior": anterior["total_ventas"],
            "variacion": _variacion_porcentual(actual["total_ventas"], anterior["total_ventas"]),
            "formato": "pesos",
        },
        "unidades": {
            "nombre": "Unidades vendidas",
            "actual": actual["total_unidades"],
            "anterior": anterior["total_unidades"],
            "variacion": _variacion_porcentual(actual["total_unidades"], anterior["total_unidades"]),
            "formato": "entero",
        },
        "ticket_promedio": {
            "nombre": "Ticket promedio",
            "actual": actual["ticket_promedio"],
            "anterior": anterior["ticket_promedio"],
            "variacion": _variacion_porcentual(actual["ticket_promedio"], anterior["ticket_promedio"]),
            "formato": "pesos",
        },
    }

    nombres_productos = set(actual["productos_detalle"]) | set(anterior["productos_detalle"])
    productos_comparados = []
    for nombre in nombres_productos:
        cantidad_actual = actual["productos_detalle"].get(nombre, {}).get("cantidad", 0)
        cantidad_anterior = anterior["productos_detalle"].get(nombre, {}).get("cantidad", 0)
        productos_comparados.append(
            {
                "nombre": nombre,
                "actual": cantidad_actual,
                "anterior": cantidad_anterior,
                "variacion": _variacion_porcentual(cantidad_actual, cantidad_anterior),
            }
        )
    productos_comparados.sort(key=lambda item: item["actual"], reverse=True)

    return {
        "periodo_actual": periodo_actual,
        "periodo_anterior": periodo_anterior,
        "actual": actual,
        "anterior": anterior,
        "metricas": metricas,
        "productos_comparados": productos_comparados[:8],
    }


def _obtener_comparativo_contabilidad(periodo_actual, periodo_anterior):
    actual = _obtener_resumen_contabilidad_periodo(periodo_actual["inicio"], periodo_actual["fin"])
    anterior = _obtener_resumen_contabilidad_periodo(periodo_anterior["inicio"], periodo_anterior["fin"])

    campos = [
        ("ingresos", "Ingresos"),
        ("costos_variables", "Costos variables"),
        ("gastos_fijos", "Gastos fijos"),
        ("gastos_financieros", "Gastos financieros"),
        ("utilidad_neta", "Utilidad neta"),
        ("flujo_neto", "Flujo neto de caja"),
    ]
    metricas = {
        clave: {
            "nombre": etiqueta,
            "actual": actual[clave],
            "anterior": anterior[clave],
            "variacion": _variacion_porcentual(actual[clave], anterior[clave]),
            "formato": "pesos",
        }
        for clave, etiqueta in campos
    }

    return {
        "periodo_actual": periodo_actual,
        "periodo_anterior": periodo_anterior,
        "actual": actual,
        "anterior": anterior,
        "metricas": metricas,
    }


def _grafico_comparativo_horizontal(metricas, color_actual="#F2C744", color_anterior="#5A5F72", ancho_max=220):
    """Compara periodo actual vs anterior con barras horizontales y variación porcentual."""
    metricas = list(metricas)
    if not metricas:
        return ft.Text("No hay datos suficientes para comparar.", color="#C9CEDB", size=13)

    filas = []
    for metrica in metricas:
        formato = metrica.get("formato", "pesos")
        formateador = _formatear_pesos if formato == "pesos" else (lambda v: f"{v:,.0f}".replace(",", "."))
        valor_maximo = max(abs(metrica["actual"]), abs(metrica["anterior"]), 1)
        ancho_actual = max(6, (abs(metrica["actual"]) / valor_maximo) * ancho_max)
        ancho_anterior = max(6, (abs(metrica["anterior"]) / valor_maximo) * ancho_max)
        texto_variacion, color_variacion = _indicador_variacion(metrica.get("variacion"))

        filas.append(
            ft.Container(
                bgcolor="#262B3B",
                border_radius=14,
                padding=14,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment="spaceBetween",
                            controls=[
                                ft.Text(metrica["nombre"], size=14, weight="bold", color="white"),
                                ft.Text(texto_variacion, size=13, weight="bold", color=color_variacion),
                            ],
                        ),
                        ft.Row(
                            spacing=10,
                            vertical_alignment="center",
                            controls=[
                                ft.Container(width=64, content=ft.Text("Anterior", size=11, color="#9AA0B4")),
                                ft.Container(width=ancho_anterior, height=14, bgcolor=color_anterior, border_radius=6),
                                ft.Text(formateador(metrica["anterior"]), size=11, color="#C9CEDB"),
                            ],
                        ),
                        ft.Row(
                            spacing=10,
                            vertical_alignment="center",
                            controls=[
                                ft.Container(width=64, content=ft.Text("Actual", size=11, color="#9AA0B4")),
                                ft.Container(width=ancho_actual, height=14, bgcolor=color_actual, border_radius=6),
                                ft.Text(formateador(metrica["actual"]), size=11, color="#E5E7EB", weight="bold"),
                            ],
                        ),
                    ],
                ),
            )
        )

    return ft.Column(spacing=12, controls=filas)


def _grafico_comparativo_pdf(metricas, ancho=470, alto=230, color_anterior=None, color_actual=None):
    """Gráfica de barras agrupadas (ReportLab) comparando periodo anterior vs actual."""
    metricas = list(metricas)
    if not metricas:
        return None

    color_anterior = color_anterior or colors.HexColor("#8A90A6")
    color_actual = color_actual or colors.HexColor("#2E3344")

    drawing = Drawing(ancho, alto)
    grafico = VerticalBarChart()
    grafico.x = 50
    grafico.y = 45
    grafico.width = ancho - 90
    grafico.height = alto - 90
    grafico.data = [
        [m["anterior"] for m in metricas],
        [m["actual"] for m in metricas],
    ]
    grafico.categoryAxis.categoryNames = [
        (m["nombre"] if len(m["nombre"]) <= 16 else m["nombre"][:14] + "…") for m in metricas
    ]
    grafico.categoryAxis.labels.fontSize = 8
    grafico.categoryAxis.labels.boxAnchor = "n"
    grafico.valueAxis.labels.fontSize = 8
    grafico.bars[0].fillColor = color_anterior
    grafico.bars[1].fillColor = color_actual
    grafico.barWidth = 10
    grafico.groupSpacing = 16
    drawing.add(grafico)

    leyenda = Legend()
    leyenda.x = ancho - 150
    leyenda.y = alto - 10
    leyenda.dx = 8
    leyenda.dy = 8
    leyenda.fontName = "Helvetica"
    leyenda.fontSize = 9
    leyenda.alignment = "right"
    leyenda.colorNamePairs = [(color_anterior, "Periodo anterior"), (color_actual, "Periodo actual")]
    drawing.add(leyenda)

    return drawing


def _encabezado_pdf(canvas, doc, titulo, fecha_texto):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(colors.HexColor("#2E3344"))
    canvas.rect(0, height - 72, width, 72, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(40, height - 34, titulo)
    canvas.setFont("Helvetica", 10)
    canvas.drawString(40, height - 50, fecha_texto)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(width - 40, height - 50, f"Página {doc.page}")
    canvas.restoreState()


_PALETA_PDF = [colors.HexColor(c) for c in _PALETA_GRAFICOS]


def _grafico_barras_pdf(pares, ancho=470, alto=200, color_barra=None, forzar_min_cero=True):
    """Construye una gráfica de barras verticales (ReportLab) para incluir en el PDF."""
    pares = [(str(nombre), float(valor or 0)) for nombre, valor in pares]
    if not pares:
        return None

    color_barra = color_barra or colors.HexColor("#2E3344")
    drawing = Drawing(ancho, alto)
    grafico = VerticalBarChart()
    grafico.x = 50
    grafico.y = 35
    grafico.width = ancho - 90
    grafico.height = alto - 65
    grafico.data = [[valor for _, valor in pares]]
    grafico.categoryAxis.categoryNames = [
        (nombre if len(nombre) <= 14 else nombre[:12] + "…") for nombre, _ in pares
    ]
    grafico.categoryAxis.labels.fontSize = 8
    grafico.categoryAxis.labels.boxAnchor = "n"
    grafico.valueAxis.labels.fontSize = 8
    grafico.bars[0].fillColor = color_barra
    grafico.barWidth = 12
    grafico.groupSpacing = 14
    if forzar_min_cero:
        grafico.valueAxis.valueMin = 0
    drawing.add(grafico)
    return drawing


def _grafico_pastel_pdf(pares, ancho=470, alto=210):
    """Construye una gráfica de pastel con leyenda de porcentajes (ReportLab)."""
    pares = [(str(nombre), float(valor or 0)) for nombre, valor in pares if valor and float(valor) > 0]
    if not pares:
        return None

    total = sum(valor for _, valor in pares) or 1
    drawing = Drawing(ancho, alto)

    pastel = Pie()
    pastel.x = 40
    pastel.y = 20
    pastel.width = 170
    pastel.height = 170
    pastel.data = [valor for _, valor in pares]
    pastel.slices.strokeWidth = 0.75
    pastel.slices.strokeColor = colors.white
    for indice in range(len(pares)):
        pastel.slices[indice].fillColor = _PALETA_PDF[indice % len(_PALETA_PDF)]
    drawing.add(pastel)

    leyenda = Legend()
    leyenda.x = 250
    leyenda.y = 170
    leyenda.dx = 8
    leyenda.dy = 8
    leyenda.fontName = "Helvetica"
    leyenda.fontSize = 9
    leyenda.alignment = "right"
    leyenda.columnMaximum = len(pares)
    leyenda.colorNamePairs = [
        (_PALETA_PDF[i % len(_PALETA_PDF)], f"{nombre}: {valor / total * 100:.1f}%")
        for i, (nombre, valor) in enumerate(pares)
    ]
    drawing.add(leyenda)
    return drawing


def _generar_pdf_informe(informe):
    carpeta = Path(__file__).resolve().parent.parent / "reportes"
    carpeta.mkdir(exist_ok=True)
    nombre_archivo = f"cierre_caja_{informe.fecha.strftime('%d_%m_%Y')}_{informe.id_informe}.pdf"
    ruta = carpeta / nombre_archivo

    estilos = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle(
        "TituloReporte",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=colors.HexColor("#2E3344"),
        spaceAfter=8,
    )
    subtitulo_estilo = ParagraphStyle(
        "SubtituloReporte",
        parent=estilos["BodyText"],
        alignment=TA_CENTER,
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.HexColor("#5A5F72"),
        spaceAfter=12,
    )
    seccion_estilo = ParagraphStyle(
        "SeccionReporte",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor("#2E3344"),
        leftIndent=0,
        spaceBefore=8,
        spaceAfter=8,
        borderPadding=6,
    )

    documento = SimpleDocTemplate(
        str(ruta),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=90,
        bottomMargin=40,
    )

    contenido = []
    contenido.append(Paragraph("REPORTE DE CAJA", titulo_estilo))
    contenido.append(Paragraph(f"Fecha del reporte: {informe.fecha.strftime('%d/%m/%Y')}", subtitulo_estilo))

    resumen_caja = Table(
        [
            ["Saldo inicial", _formatear_pesos(informe.saldo_inicial)],
            ["Ventas totales", _formatear_pesos(informe.ventas_totales)],
            ["Saldo final", _formatear_pesos(informe.saldo_final)],
            ["Productos vendidos", str(informe.productos_vendidos)],
        ],
        colWidths=[220, 220],
    )
    resumen_caja.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F7F8FC")]),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2E3344")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    resumen_ventas = Table(
        [
            ["Efectivo", _formatear_pesos(informe.total_efectivo)],
            ["Tarjeta", _formatear_pesos(informe.total_tarjeta)],
            ["Nequi", _formatear_pesos(informe.total_nequi)],
        ],
        colWidths=[220, 220],
    )
    resumen_ventas.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F7F8FC")]),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2E3344")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    resumen_proveedores = Table(
        [["Costo proveedores", _formatear_pesos(informe.total_proveedores)]],
        colWidths=[220, 220],
    )
    resumen_proveedores.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2E3344")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    total_general = Table(
        [["TOTAL GENERAL", _formatear_pesos(_total_general(informe))]],
        colWidths=[220, 220],
    )
    total_general.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#2E3344")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 13),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#F2C744")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    contenido.append(Paragraph("RESUMEN DE CAJA", seccion_estilo))
    contenido.append(resumen_caja)
    contenido.append(Spacer(1, 10))
    contenido.append(Paragraph("RESUMEN DE VENTAS", seccion_estilo))
    contenido.append(resumen_ventas)
    contenido.append(Spacer(1, 10))
    contenido.append(Paragraph("RESUMEN DE PROVEEDORES", seccion_estilo))
    contenido.append(resumen_proveedores)
    contenido.append(Spacer(1, 16))
    contenido.append(total_general)

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D3D8E3"))
        canvas.line(doc.leftMargin, 34, letter[0] - doc.rightMargin, 34)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5A5F72"))
        canvas.drawString(doc.leftMargin, 22, "BurgerLand - Reporte de caja")
        canvas.drawRightString(letter[0] - doc.rightMargin, 22, f"Página {doc.page}")
        canvas.restoreState()

    def dibujar_pagina(canvas, doc):
        _encabezado_pdf(canvas, doc, "REPORTE DE CAJA", f"Fecha: {informe.fecha.strftime('%d/%m/%Y')}")
        pie(canvas, doc)

    documento.build(contenido, onFirstPage=dibujar_pagina, onLaterPages=dibujar_pagina)
    return str(ruta)


def _generar_pdf_reporte_negocio(datos):
    carpeta = Path(__file__).resolve().parent.parent / "reportes"
    carpeta.mkdir(exist_ok=True)
    archivo = carpeta / f"reporte_negocio_{dt.date.today().strftime('%d_%m_%Y')}.pdf"

    estilos = getSampleStyleSheet()
    contenido = []
    contenido.append(Paragraph("REPORTE GENERAL DEL NEGOCIO", ParagraphStyle(
        "TituloNegocio",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#2E3344"),
        spaceAfter=10,
    )))
    contenido.append(Paragraph(f"Periodo: {dt.date.today().strftime('%d/%m/%Y')}", ParagraphStyle(
        "SubtituloNegocio",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#5A5F72"),
        spaceAfter=14,
    )))

    resumen = Table(
        [
            ["Ventas totales", _formatear_pesos(datos["total_ventas"])],
            ["Productos vendidos", str(datos["total_unidades"])],
            ["Ticket promedio", _formatear_pesos(datos["ticket_promedio"])],
        ],
        colWidths=[220, 220],
    )
    resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(Paragraph("Resumen general", ParagraphStyle(
        "SeccionNegocio",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor("#2E3344"),
        borderPadding=6,
        spaceBefore=8,
        spaceAfter=8,
    )))
    contenido.append(resumen)

    if datos["metodo_totales"]:
        contenido.append(Spacer(1, 10))
        contenido.append(Paragraph("Ventas por medio de pago", ParagraphStyle(
            "SeccionNegocio2",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            backColor=colors.HexColor("#2E3344"),
            borderPadding=6,
            spaceBefore=8,
            spaceAfter=8,
        )))
        filas_metodos = [[nombre, _formatear_pesos(valor)] for nombre, valor in datos["metodo_totales"].items() if valor > 0]
        tabla_metodos = Table(filas_metodos, colWidths=[220, 220])
        tabla_metodos.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        contenido.append(tabla_metodos)
        grafico_metodos = _grafico_pastel_pdf(list(datos["metodo_totales"].items()))
        if grafico_metodos is not None:
            contenido.append(Spacer(1, 12))
            contenido.append(grafico_metodos)

    if datos["top_productos"]:
        contenido.append(Spacer(1, 10))
        contenido.append(Paragraph("Productos más vendidos", ParagraphStyle(
            "SeccionNegocio3",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            backColor=colors.HexColor("#2E3344"),
            borderPadding=6,
            spaceBefore=8,
            spaceAfter=8,
        )))
        filas_top = [[item["nombre"], str(item["cantidad"]), _formatear_pesos(item["ventas"])] for item in datos["top_productos"]]
        tabla_top = Table(filas_top, colWidths=[200, 100, 140])
        tabla_top.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        contenido.append(tabla_top)
        grafico_top = _grafico_barras_pdf(
            [(item["nombre"], item["cantidad"]) for item in datos["top_productos"]],
            color_barra=colors.HexColor("#7AE582"),
        )
        if grafico_top is not None:
            contenido.append(Spacer(1, 12))
            contenido.append(grafico_top)

    if datos["menos_vendidos"]:
        contenido.append(Spacer(1, 10))
        contenido.append(Paragraph("Productos menos vendidos", ParagraphStyle(
            "SeccionNegocio4",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            backColor=colors.HexColor("#2E3344"),
            borderPadding=6,
            spaceBefore=8,
            spaceAfter=8,
        )))
        filas_low = [[item["nombre"], str(item["cantidad"])] for item in datos["menos_vendidos"]]
        tabla_low = Table(filas_low, colWidths=[260, 120])
        tabla_low.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        contenido.append(tabla_low)
        grafico_low = _grafico_barras_pdf(
            [(item["nombre"], item["cantidad"]) for item in datos["menos_vendidos"]],
            color_barra=colors.HexColor("#FF7B7B"),
        )
        if grafico_low is not None:
            contenido.append(Spacer(1, 12))
            contenido.append(grafico_low)

    documento = SimpleDocTemplate(str(archivo), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=40)
    documento.build(contenido, onFirstPage=lambda canvas, doc: _encabezado_pdf(canvas, doc, "REPORTE GENERAL DEL NEGOCIO", f"Fecha: {dt.date.today().strftime('%d/%m/%Y')}"), onLaterPages=lambda canvas, doc: _encabezado_pdf(canvas, doc, "REPORTE GENERAL DEL NEGOCIO", f"Fecha: {dt.date.today().strftime('%d/%m/%Y')}"))
    return str(archivo)


def _generar_pdf_reporte_contabilidad(datos):
    carpeta = Path(__file__).resolve().parent.parent / "reportes"
    carpeta.mkdir(exist_ok=True)
    archivo = carpeta / f"reporte_contabilidad_{dt.date.today().strftime('%d_%m_%Y')}.pdf"

    estilos = getSampleStyleSheet()
    contenido = []
    contenido.append(Paragraph("REPORTE DE CONTABILIDAD", ParagraphStyle(
        "TituloContabilidad",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#2E3344"),
        spaceAfter=10,
    )))
    contenido.append(Paragraph(f"Periodo: {datos['periodo']}", ParagraphStyle(
        "SubtituloContabilidad",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#5A5F72"),
        spaceAfter=14,
    )))

    ingresos = Table([
        ["Ingresos totales", _formatear_pesos(datos["ingresos"])],
        ["Entradas de caja", _formatear_pesos(datos["entradas_caja"])],
    ], colWidths=[220, 220])
    ingresos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(Paragraph("Ingresos", ParagraphStyle(
        "SeccionContabilidad1",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor("#2E3344"),
        borderPadding=6,
        spaceBefore=8,
        spaceAfter=8,
    )))
    contenido.append(ingresos)

    egresos = Table([
        ["Costos variables", _formatear_pesos(datos["costos_variables"])],
        ["Gastos fijos", _formatear_pesos(datos["gastos_fijos"])],
        ["Gastos financieros", _formatear_pesos(datos["gastos_financieros"])],
        ["Salidas de caja", _formatear_pesos(datos["salidas_caja"])],
    ], colWidths=[220, 220])
    egresos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    contenido.append(Spacer(1, 10))
    contenido.append(Paragraph("Egresos", ParagraphStyle(
        "SeccionContabilidad2",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor("#2E3344"),
        borderPadding=6,
        spaceBefore=8,
        spaceAfter=8,
    )))
    contenido.append(egresos)

    grafico_egresos = _grafico_pastel_pdf(
        [
            ("Costos variables", datos["costos_variables"]),
            ("Gastos fijos", datos["gastos_fijos"]),
            ("Gastos financieros", datos["gastos_financieros"]),
        ]
    )
    if grafico_egresos is not None:
        contenido.append(Spacer(1, 10))
        contenido.append(Paragraph("Composición de egresos", ParagraphStyle(
            "SeccionContabilidad3",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            backColor=colors.HexColor("#2E3344"),
            borderPadding=6,
            spaceBefore=8,
            spaceAfter=8,
        )))
        contenido.append(grafico_egresos)

    total_egresos = float(datos["costos_variables"]) + float(datos["gastos_fijos"]) + float(datos["gastos_financieros"])
    grafico_comparativo = _grafico_barras_pdf(
        [
            ("Ingresos", datos["ingresos"]),
            ("Egresos", total_egresos),
            ("Utilidad neta", datos["utilidad_neta"]),
        ],
        color_barra=colors.HexColor("#F2C744"),
        forzar_min_cero=False,
    )
    if grafico_comparativo is not None:
        contenido.append(Spacer(1, 10))
        contenido.append(Paragraph("Ingresos vs. egresos vs. utilidad", ParagraphStyle(
            "SeccionContabilidad4",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            backColor=colors.HexColor("#2E3344"),
            borderPadding=6,
            spaceBefore=8,
            spaceAfter=8,
        )))
        contenido.append(grafico_comparativo)

    total = Table([
        ["Utilidad neta", _formatear_pesos(datos["utilidad_neta"])],
        ["Flujo neto", _formatear_pesos(datos["flujo_neto"])],
    ], colWidths=[220, 220])
    total.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#2E3344")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F2C744")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    contenido.append(Spacer(1, 14))
    contenido.append(total)

    documento = SimpleDocTemplate(str(archivo), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=40)
    documento.build(contenido, onFirstPage=lambda canvas, doc: _encabezado_pdf(canvas, doc, "REPORTE DE CONTABILIDAD", f"Periodo: {datos['periodo']}"), onLaterPages=lambda canvas, doc: _encabezado_pdf(canvas, doc, "REPORTE DE CONTABILIDAD", f"Periodo: {datos['periodo']}"))
    return str(archivo)


def _seccion_pdf(texto, nombre_estilo, estilos):
    return Paragraph(texto, ParagraphStyle(
        nombre_estilo,
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.white,
        backColor=colors.HexColor("#2E3344"),
        borderPadding=6,
        spaceBefore=8,
        spaceAfter=8,
    ))


def _tabla_comparativa_pdf(metricas):
    filas = [["Indicador", "Periodo anterior", "Periodo actual", "Variación"]]
    for metrica in metricas.values():
        formateador = _formatear_pesos if metrica.get("formato") == "pesos" else (lambda v: f"{v:,.0f}".replace(",", "."))
        variacion = metrica.get("variacion")
        texto_variacion = "Sin datos previos" if variacion is None else f"{variacion:+.1f}%"
        filas.append([metrica["nombre"], formateador(metrica["anterior"]), formateador(metrica["actual"]), texto_variacion])

    tabla = Table(filas, colWidths=[150, 120, 120, 90])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3344")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7F8FC")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return tabla


def _generar_pdf_comparativo_negocio(datos):
    carpeta = Path(__file__).resolve().parent.parent / "reportes"
    carpeta.mkdir(exist_ok=True)
    archivo = carpeta / f"comparativo_negocio_{dt.date.today().strftime('%d_%m_%Y')}.pdf"

    estilos = getSampleStyleSheet()
    contenido = []
    contenido.append(Paragraph("INFORME COMPARATIVO QUINCENAL - NEGOCIO", ParagraphStyle(
        "TituloComparativoNegocio",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#2E3344"),
        spaceAfter=8,
    )))
    contenido.append(Paragraph(
        f"Periodo actual: {datos['periodo_actual']['etiqueta']}  |  Periodo anterior: {datos['periodo_anterior']['etiqueta']}",
        ParagraphStyle(
            "SubtituloComparativoNegocio",
            parent=estilos["BodyText"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#5A5F72"),
            spaceAfter=14,
        ),
    ))

    contenido.append(_seccion_pdf("Indicadores generales", "SeccionCompNeg1", estilos))
    contenido.append(_tabla_comparativa_pdf(datos["metricas"]))

    grafico = _grafico_comparativo_pdf(list(datos["metricas"].values()))
    if grafico is not None:
        contenido.append(Spacer(1, 12))
        contenido.append(grafico)

    if datos["productos_comparados"]:
        contenido.append(Spacer(1, 12))
        contenido.append(_seccion_pdf("Comparativo de productos (unidades vendidas)", "SeccionCompNeg2", estilos))
        filas_productos = [["Producto", "Periodo anterior", "Periodo actual", "Variación"]]
        for item in datos["productos_comparados"]:
            variacion = item.get("variacion")
            texto_variacion = "Sin datos previos" if variacion is None else f"{variacion:+.1f}%"
            filas_productos.append([item["nombre"], str(item["anterior"]), str(item["actual"]), texto_variacion])
        tabla_productos = Table(filas_productos, colWidths=[190, 100, 100, 90])
        tabla_productos.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3344")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7F8FC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D3D8E3")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        contenido.append(tabla_productos)

    documento = SimpleDocTemplate(str(archivo), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=40)
    titulo_encabezado = "INFORME COMPARATIVO QUINCENAL - NEGOCIO"
    fecha_encabezado = f"Actual: {datos['periodo_actual']['etiqueta']}"
    documento.build(
        contenido,
        onFirstPage=lambda canvas, doc: _encabezado_pdf(canvas, doc, titulo_encabezado, fecha_encabezado),
        onLaterPages=lambda canvas, doc: _encabezado_pdf(canvas, doc, titulo_encabezado, fecha_encabezado),
    )
    return str(archivo)


def _generar_pdf_comparativo_contabilidad(datos):
    carpeta = Path(__file__).resolve().parent.parent / "reportes"
    carpeta.mkdir(exist_ok=True)
    archivo = carpeta / f"comparativo_contabilidad_{dt.date.today().strftime('%d_%m_%Y')}.pdf"

    estilos = getSampleStyleSheet()
    contenido = []
    contenido.append(Paragraph("INFORME COMPARATIVO QUINCENAL - CONTABILIDAD", ParagraphStyle(
        "TituloComparativoContab",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#2E3344"),
        spaceAfter=8,
    )))
    contenido.append(Paragraph(
        f"Periodo actual: {datos['periodo_actual']['etiqueta']}  |  Periodo anterior: {datos['periodo_anterior']['etiqueta']}",
        ParagraphStyle(
            "SubtituloComparativoContab",
            parent=estilos["BodyText"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#5A5F72"),
            spaceAfter=14,
        ),
    ))

    contenido.append(_seccion_pdf("Ingresos, egresos y utilidad", "SeccionCompContab1", estilos))
    contenido.append(_tabla_comparativa_pdf(datos["metricas"]))

    grafico = _grafico_comparativo_pdf(
        list(datos["metricas"].values()),
        color_anterior=colors.HexColor("#8A90A6"),
        color_actual=colors.HexColor("#7AE582"),
    )
    if grafico is not None:
        contenido.append(Spacer(1, 12))
        contenido.append(grafico)

    documento = SimpleDocTemplate(str(archivo), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=40)
    titulo_encabezado = "INFORME COMPARATIVO QUINCENAL - CONTABILIDAD"
    fecha_encabezado = f"Actual: {datos['periodo_actual']['etiqueta']}"
    documento.build(
        contenido,
        onFirstPage=lambda canvas, doc: _encabezado_pdf(canvas, doc, titulo_encabezado, fecha_encabezado),
        onLaterPages=lambda canvas, doc: _encabezado_pdf(canvas, doc, titulo_encabezado, fecha_encabezado),
    )
    return str(archivo)


def informes_view(page: ft.Page, navbar, ultimo_informe=None):
    negocio = _obtener_analisis_negocio()
    contabilidad = _obtener_resumen_contabilidad()

    hoy = dt.date.today()
    quincenal_disponible = informe_quincenal_habilitado(hoy)
    comparativo_negocio = None
    comparativo_contabilidad = None
    if quincenal_disponible:
        periodo_actual, periodo_anterior = _rango_quincenas(hoy)
        comparativo_negocio = _obtener_comparativo_negocio(periodo_actual, periodo_anterior)
        comparativo_contabilidad = _obtener_comparativo_contabilidad(periodo_actual, periodo_anterior)

    def descargar_reporte_negocio(e):
        ruta_pdf = _generar_pdf_reporte_negocio(negocio)
        if os.name == "nt":
            os.startfile(ruta_pdf)
        else:
            os.system(f'xdg-open "{ruta_pdf}"')

    def descargar_reporte_contabilidad(e):
        ruta_pdf = _generar_pdf_reporte_contabilidad(contabilidad)
        if os.name == "nt":
            os.startfile(ruta_pdf)
        else:
            os.system(f'xdg-open "{ruta_pdf}"')

    def descargar_comparativo_negocio(e):
        ruta_pdf = _generar_pdf_comparativo_negocio(comparativo_negocio)
        if os.name == "nt":
            os.startfile(ruta_pdf)
        else:
            os.system(f'xdg-open "{ruta_pdf}"')

    def descargar_comparativo_contabilidad(e):
        ruta_pdf = _generar_pdf_comparativo_contabilidad(comparativo_contabilidad)
        if os.name == "nt":
            os.startfile(ruta_pdf)
        else:
            os.system(f'xdg-open "{ruta_pdf}"')

    resumen_negocio = ft.Row(
        wrap=True,
        spacing=18,
        run_spacing=18,
        controls=[
            _tarjeta_resumen("Ventas", _formatear_pesos(negocio["total_ventas"]), "#F2C744"),
            _tarjeta_resumen("Unidades", str(negocio["total_unidades"]), "#7AE582"),
            _tarjeta_resumen("Ticket promedio", _formatear_pesos(negocio["ticket_promedio"]), "#7ABAFB"),
        ],
    )

    resumen_contabilidad = ft.Row(
        wrap=True,
        spacing=18,
        run_spacing=18,
        controls=[
            _tarjeta_resumen("Ingresos", _formatear_pesos(contabilidad["ingresos"]), "#7AE582"),
            _tarjeta_resumen("Egresos", _formatear_pesos(contabilidad["gastos_fijos"] + contabilidad["costos_variables"] + contabilidad["gastos_financieros"]), "#FF7B7B"),
            _tarjeta_resumen("Utilidad neta", _formatear_pesos(contabilidad["utilidad_neta"]), "#F2C744"),
        ],
    )

    negocio_card = ft.Container(
        bgcolor="#2E3344",
        border_radius=20,
        padding=24,
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Text("REPORTE GENERAL DEL NEGOCIO", size=24, weight="bold", color="white"),
                ft.Text("Resumen operativo del negocio: ventas, productos, ticket promedio y comportamiento del negocio.", size=14, color="#C9CEDB"),
                resumen_negocio,
                ft.Divider(color="#3A3F52", height=1),
                ft.Text("Ventas por medio de pago", size=16, weight="bold", color="white"),
                _grafico_pastel(list(negocio["metodo_totales"].items())),
                ft.Divider(color="#3A3F52", height=1),
                ft.Text("Productos más vendidos (unidades)", size=16, weight="bold", color="white"),
                _grafico_barras(
                    [(item["nombre"], item["cantidad"]) for item in negocio["top_productos"]],
                    color="#7AE582",
                    formateador=lambda v: f"{v:.0f}",
                ),
                ft.Text("Productos menos vendidos (unidades)", size=16, weight="bold", color="white"),
                _grafico_barras(
                    [(item["nombre"], item["cantidad"]) for item in negocio["menos_vendidos"]],
                    color="#FF7B7B",
                    formateador=lambda v: f"{v:.0f}",
                ),
                ft.Row(alignment="end", controls=[ft.ElevatedButton("Descargar PDF", on_click=descargar_reporte_negocio, bgcolor="#F2C744", color="#111111")]),
            ],
        ),
    )

    contabilidad_card = ft.Container(
        bgcolor="#2E3344",
        border_radius=20,
        padding=24,
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Text("REPORTE DE CONTABILIDAD", size=24, weight="bold", color="white"),
                ft.Text("Resumen claro de ingresos y egresos para entender la contabilidad básica del negocio.", size=14, color="#C9CEDB"),
                resumen_contabilidad,
                ft.Divider(color="#3A3F52", height=1),
                ft.Text("Composición de egresos", size=16, weight="bold", color="white"),
                _grafico_pastel(
                    [
                        ("Costos variables", contabilidad["costos_variables"]),
                        ("Gastos fijos", contabilidad["gastos_fijos"]),
                        ("Gastos financieros", contabilidad["gastos_financieros"]),
                    ]
                ),
                ft.Divider(color="#3A3F52", height=1),
                ft.Text("Ingresos vs. egresos vs. utilidad neta", size=16, weight="bold", color="white"),
                _grafico_barras(
                    [
                        ("Ingresos", contabilidad["ingresos"]),
                        ("Egresos", contabilidad["gastos_fijos"] + contabilidad["costos_variables"] + contabilidad["gastos_financieros"]),
                        ("Utilidad neta", contabilidad["utilidad_neta"]),
                    ],
                    color="#F2C744",
                    formateador=_formatear_pesos,
                ),
                ft.Column(
                    controls=[
                        ft.Text(f"Ingresos: {_formatear_pesos(contabilidad['ingresos'])}", color="#E5E7EB"),
                        ft.Text(f"Costos variables: {_formatear_pesos(contabilidad['costos_variables'])}", color="#E5E7EB"),
                        ft.Text(f"Gastos fijos: {_formatear_pesos(contabilidad['gastos_fijos'])}", color="#E5E7EB"),
                        ft.Text(f"Gastos financieros: {_formatear_pesos(contabilidad['gastos_financieros'])}", color="#E5E7EB"),
                        ft.Text(f"Utilidad neta: {_formatear_pesos(contabilidad['utilidad_neta'])}", color="#F2C744", weight="bold"),
                    ]
                ),
                ft.Row(alignment="end", controls=[ft.ElevatedButton("Descargar PDF", on_click=descargar_reporte_contabilidad, bgcolor="#7AE582", color="#111111")]),
            ],
        ),
    )

    if ultimo_informe:
        total_general = _total_general(ultimo_informe)
        cierre_card = ft.Container(
            bgcolor="#3A3F52",
            border_radius=20,
            padding=24,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Cierre de caja actual", size=22, weight="bold", color="white"),
                    ft.Text(f"Fecha: {ultimo_informe.fecha.strftime('%d/%m/%Y')}", color="#C9CEDB"),
                    ft.Text(f"Ventas: {_formatear_pesos(ultimo_informe.ventas_totales)}", color="#E5E7EB"),
                    ft.Text(f"Saldo final: {_formatear_pesos(ultimo_informe.saldo_final)}", color="#E5E7EB"),
                    ft.Text(f"Total general: {_formatear_pesos(total_general)}", color="#7AE582", weight="bold"),
                ],
            ),
        )
    else:
        cierre_card = ft.Container(
            bgcolor="#3A3F52",
            border_radius=20,
            padding=24,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Cierre de caja", size=22, weight="bold", color="white"),
                    ft.Text("Aún no hay cierre generado.", color="#C9CEDB"),
                    ft.Text("Cierra una caja para generar el resumen del día.", color="#E5E7EB"),
                ],
            ),
        )

    if quincenal_disponible:
        comparativo_card = ft.Container(
            bgcolor="#2E3344",
            border_radius=20,
            padding=24,
            border=ft.Border.all(1.5, "#F2C744"),
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        controls=[
                            ft.Text("INFORME COMPARATIVO QUINCENAL", size=24, weight="bold", color="white"),
                            ft.Container(
                                bgcolor="#F2C744",
                                border_radius=8,
                                padding=ft.padding.Padding(left=10, top=4, right=10, bottom=4),
                                content=ft.Text("DISPONIBLE HOY", size=12, weight="bold", color="#111111"),
                            ),
                        ],
                    ),
                    ft.Text(
                        f"Comparativo entre {comparativo_negocio['periodo_anterior']['etiqueta']} (periodo anterior) "
                        f"y {comparativo_negocio['periodo_actual']['etiqueta']} (periodo actual). "
                        "Disponible únicamente el día 15 y el último día de cada mes.",
                        size=13,
                        color="#C9CEDB",
                    ),
                    ft.Divider(color="#3A3F52", height=1),
                    ft.Text("Negocio: ventas, unidades y ticket promedio", size=16, weight="bold", color="white"),
                    _grafico_comparativo_horizontal(comparativo_negocio["metricas"].values()),
                    ft.Row(alignment="end", controls=[
                        ft.ElevatedButton("Descargar PDF de negocio", on_click=descargar_comparativo_negocio, bgcolor="#F2C744", color="#111111"),
                    ]),
                    ft.Divider(color="#3A3F52", height=1),
                    ft.Text("Contabilidad: ingresos, egresos y utilidad", size=16, weight="bold", color="white"),
                    _grafico_comparativo_horizontal(
                        comparativo_contabilidad["metricas"].values(),
                        color_actual="#7AE582",
                    ),
                    ft.Row(alignment="end", controls=[
                        ft.ElevatedButton("Descargar PDF de contabilidad", on_click=descargar_comparativo_contabilidad, bgcolor="#7AE582", color="#111111"),
                    ]),
                ],
            ),
        )
    else:
        proxima_fecha = _proxima_fecha_habilitacion(hoy)
        comparativo_card = ft.Container(
            bgcolor="#3A3F52",
            border_radius=20,
            padding=24,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Informe comparativo quincenal", size=22, weight="bold", color="white"),
                    ft.Text(
                        "Este informe compara el negocio y la contabilidad de los últimos 15 días con la quincena anterior. "
                        "Solo se habilita el día 15 y el último día de cada mes.",
                        size=13,
                        color="#C9CEDB",
                    ),
                    ft.Text(f"Próxima disponibilidad: {proxima_fecha.strftime('%d/%m/%Y')}", size=13, color="#F2C744", weight="bold"),
                ],
            ),
        )

    return ft.Column(
        expand=True,
        spacing=20,
        scroll="auto",
        controls=[
            navbar,
            ft.Text("REPORTES Y ESTADÍSTICAS", size=28, weight="bold", color="white"),
            negocio_card,
            contabilidad_card,
            comparativo_card,
            cierre_card,
        ],
    )

import os
from pathlib import Path

import flet as ft
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _formatear_pesos(valor):
    return f"${valor:,.0f}".replace(",", ".")


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


def _total_general(informe):
    return float(informe.ventas_totales) - float(informe.total_proveedores)


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
    valor_estilo = ParagraphStyle(
        "ValorReporte",
        parent=estilos["BodyText"],
        alignment=TA_RIGHT,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#F2C744"),
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


def informes_view(page: ft.Page, navbar, ultimo_informe=None):
    def descargar_pdf(e):
        if ultimo_informe is None:
            return
        ruta_pdf = _generar_pdf_informe(ultimo_informe)
        if os.name == "nt":
            os.startfile(ruta_pdf)
        else:
            os.system(f'xdg-open "{ruta_pdf}"')

    if ultimo_informe:
        total_general = _total_general(ultimo_informe)
        resumen = ft.Row(
            wrap=True,
            spacing=18,
            run_spacing=18,
            controls=[
                _tarjeta_resumen("Ventas", _formatear_pesos(ultimo_informe.ventas_totales), "#F2C744"),
                _tarjeta_resumen("Efectivo", _formatear_pesos(ultimo_informe.total_efectivo), "#7AE582"),
                _tarjeta_resumen("Tarjeta", _formatear_pesos(ultimo_informe.total_tarjeta), "#7ABAFB"),
                _tarjeta_resumen("Nequi", _formatear_pesos(ultimo_informe.total_nequi), "#FFB86C"),
                _tarjeta_resumen("Proveedores", _formatear_pesos(ultimo_informe.total_proveedores), "#FF7B7B"),
                _tarjeta_resumen("Total general", _formatear_pesos(total_general), "#7AE582"),
            ],
        )

        detalle = ft.Column(
            spacing=12,
            controls=[
                ft.Text("RESUMEN DEL CIERRE", size=24, weight="bold", color="white"),
                ft.Text(f"Fecha: {ultimo_informe.fecha.strftime('%d/%m/%Y')}", size=16, color="white"),
                ft.Divider(color="#5A5F72"),
                ft.Text(f"Saldo inicial: {_formatear_pesos(ultimo_informe.saldo_inicial)}", color="white", size=16),
                ft.Text(f"Saldo final: {_formatear_pesos(ultimo_informe.saldo_final)}", color="white", size=16),
                ft.Text(f"Productos vendidos: {ultimo_informe.productos_vendidos}", color="white", size=16),
                ft.Text(f"Total general: {_formatear_pesos(total_general)}", color="#7AE582", size=16, weight="bold"),
            ],
        )

        seccion_proveedores = ft.Container(
            bgcolor="#2E3344",
            border_radius=18,
            padding=20,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("SECCIÓN PROVEEDORES", size=18, weight="bold", color="white"),
                    ft.Text(
                        f"Costo total de proveedores: {_formatear_pesos(ultimo_informe.total_proveedores)}",
                        size=16,
                        color="#F2C744",
                        weight="bold",
                    ),
                    ft.Text(
                        "Este valor se calcula con las ventas donde se seleccionó proveedor.",
                        size=13,
                        color="#C9CEDB",
                    ),
                ],
            ),
        )

        btn_descargar_pdf = ft.ElevatedButton(
            "Descargar PDF",
            on_click=descargar_pdf,
            bgcolor="#2E3344",
            color="white",
        )

        tarjeta = ft.Container(
            expand=True,
            bgcolor="#3A3F52",
            border_radius=20,
            padding=30,
            content=ft.Column(
                expand=True,
                spacing=22,
                controls=[
                    ft.Row(
                        alignment="spaceBetween",
                        controls=[
                            ft.Text("REPORTE DE CAJA", size=26, weight="bold", color="white"),
                            ft.Container(
                                bgcolor="#2E3344",
                                border_radius=12,
                                padding=10,
                                content=ft.Text("Cierre generado", color="#7AE582", weight="bold"),
                            ),
                        ],
                    ),
                    resumen,
                    seccion_proveedores,
                    ft.Container(
                        bgcolor="#2E3344",
                        border_radius=18,
                        padding=20,
                        content=detalle,
                    ),
                    ft.Row(alignment="end", controls=[btn_descargar_pdf]),
                ],
            ),
        )
    else:
        tarjeta = ft.Container(
            expand=True,
            bgcolor="#3A3F52",
            border_radius=20,
            padding=40,
            content=ft.Column(
                controls=[
                    ft.Text("REPORTE DE CAJA", size=26, weight="bold", color="white"),
                    ft.Text("Aún no hay reportes generados.", size=18, color="white"),
                    ft.Text("Cierra una caja para generar el reporte.", size=16, color="#C9CEDB"),
                ]
            ),
        )

    return ft.Column(expand=True, spacing=20, scroll="auto", controls=[navbar, tarjeta])

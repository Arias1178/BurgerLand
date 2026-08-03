import os
from pathlib import Path

import flet as ft
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet


def _tarjeta_resumen(titulo, valor, color="#F2C744"):
    return ft.Container(
        width=200,
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


def _generar_pdf_informe(informe):
    carpeta = Path(__file__).resolve().parent.parent / "reportes"
    carpeta.mkdir(exist_ok=True)
    nombre_archivo = f"cierre_caja_{informe.fecha.strftime('%d_%m_%Y')}_{informe.id_informe}.pdf"
    ruta = carpeta / nombre_archivo

    estilos = getSampleStyleSheet()
    documento = SimpleDocTemplate(str(ruta), pagesize=letter)
    contenido = []

    contenido.append(Paragraph("REPORTE DE CAJA", estilos["Title"]))
    contenido.append(Spacer(1, 18))
    contenido.append(Paragraph(f"Fecha: {informe.fecha.strftime('%d/%m/%Y')}", estilos["BodyText"]))
    contenido.append(Paragraph(f"Saldo inicial: ${informe.saldo_inicial:,.0f}".replace(",", "."), estilos["BodyText"]))
    contenido.append(Paragraph(f"Saldo final: ${informe.saldo_final:,.0f}".replace(",", "."), estilos["BodyText"]))
    contenido.append(Paragraph(f"Ventas totales: ${informe.ventas_totales:,.0f}".replace(",", "."), estilos["BodyText"]))
    contenido.append(Paragraph(f"Productos vendidos: {informe.productos_vendidos}", estilos["BodyText"]))
    contenido.append(Paragraph(f"Clientes atendidos: {informe.clientes_atendidos}", estilos["BodyText"]))
    contenido.append(Spacer(1, 18))

    tabla = Table([
        ["Efectivo", f"${informe.total_efectivo:,.0f}".replace(",", ".")],
        ["Tarjeta", f"${informe.total_tarjeta:,.0f}".replace(",", ".")],
        ["Nequi", f"${informe.total_nequi:,.0f}".replace(",", ".")],
    ], colWidths=[180, 200])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#3A3F52")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#5A5F72")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    contenido.append(tabla)

    documento.build(contenido)
    return str(ruta)


def informes_view(page: ft.Page, navbar, ultimo_informe=None):
    def descargar_pdf(e):
        if ultimo_informe is None:
            return
        ruta_pdf = _generar_pdf_informe(ultimo_informe)
        if os.name == "nt":
            os.startfile(ruta_pdf)
        else:
            os.system(f"xdg-open '{ruta_pdf}'")

    if ultimo_informe:
        resumen = ft.Row(
            wrap=True,
            spacing=18,
            run_spacing=18,
            controls=[
                _tarjeta_resumen("Ventas", f"${ultimo_informe.ventas_totales:,.0f}".replace(",", "."), "#F2C744"),
                _tarjeta_resumen("Efectivo", f"${ultimo_informe.total_efectivo:,.0f}".replace(",", "."), "#7AE582"),
                _tarjeta_resumen("Tarjeta", f"${ultimo_informe.total_tarjeta:,.0f}".replace(",", "."), "#7ABAFB"),
                _tarjeta_resumen("Nequi", f"${ultimo_informe.total_nequi:,.0f}".replace(",", "."), "#FFB86C"),
            ],
        )

        detalle = ft.Column(
            spacing=12,
            controls=[
                ft.Text("RESUMEN DEL CIERRE", size=24, weight="bold", color="white"),
                ft.Text(f"Fecha: {ultimo_informe.fecha.strftime('%d/%m/%Y')}", size=16, color="white"),
                ft.Divider(color="#5A5F72"),
                ft.Text(f"Saldo inicial: ${ultimo_informe.saldo_inicial:,.0f}".replace(",", "."), color="white", size=16),
                ft.Text(f"Saldo final: ${ultimo_informe.saldo_final:,.0f}".replace(",", "."), color="white", size=16),
                ft.Text(f"Productos vendidos: {ultimo_informe.productos_vendidos}", color="white", size=16),
                ft.Text(f"Clientes atendidos: {ultimo_informe.clientes_atendidos}", color="white", size=16),
            ],
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

    return ft.Column(expand=True, spacing=20, controls=[navbar, tarjeta])

import datetime
import math
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import flet.canvas as fcanvas
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import String
from reportlab.pdfbase.pdfmetrics import stringWidth
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import estado_ventas, metodos_pago, ventas
from views.informes import (
    _obtener_analisis_negocio,
    _grafico_barras_pdf,
    _grafico_comparativo_pdf,
    _grafico_pastel_pdf,
    _generar_pdf_reporte_negocio,
    _encabezado_pdf,
    _grafico_pastel,
    MARGEN_SUPERIOR_REPORTE_PDF,
    _variacion_porcentual,
)


class InformesTests(unittest.TestCase):
    def test_pdf_report_header_does_not_overlap_period_and_page_number(self):
        class CanvasStub:
            def __init__(self):
                self.font = ("Helvetica", 10)
                self.drawn = []

            def saveState(self):
                pass

            def restoreState(self):
                pass

            def setFillColor(self, _color):
                pass

            def rect(self, *_args, **_kwargs):
                pass

            def setFont(self, font, size):
                self.font = (font, size)

            def stringWidth(self, text, font, size):
                return stringWidth(text, font, size)

            def drawString(self, x, y, text):
                self.drawn.append((x, y, text, self.font))

            def drawRightString(self, x, y, text):
                self.drawn.append((x - self.stringWidth(text, *self.font), y, text, self.font))

        canvas = CanvasStub()
        titulo = "INFORME COMPARATIVO QUINCENAL - CONTABILIDAD"
        periodo = "Actual: 01/11/2026 - 15/11/2026"
        _encabezado_pdf(canvas, SimpleNamespace(page=1), titulo, periodo)

        titulo_drawn, periodo_drawn, pagina_drawn = canvas.drawn
        self.assertLessEqual(
            stringWidth(titulo_drawn[2], *titulo_drawn[3]),
            612 - 80,
        )
        self.assertLessEqual(
            periodo_drawn[0] + stringWidth(periodo_drawn[2], *periodo_drawn[3]),
            pagina_drawn[0] - 10,
        )

    def test_business_pdf_starts_below_header_without_repeating_title(self):
        documento = MagicMock()
        datos = {
            "periodo": "Histórico: 03/11/2026 - 10/11/2026",
            "total_ventas": 0,
            "cantidad_ventas": 0,
            "total_unidades": 0,
            "ticket_promedio": 0,
            "cantidad_domicilios": 0,
            "ingresos_domicilios": 0,
            "domicilios_entregados": 0,
            "ventas_por_tipo": {},
            "metodo_totales": {},
            "metodo_cantidades": {},
            "top_productos": [],
            "menos_vendidos": [],
            "productos_detalle": {},
        }

        with (
            patch("views.informes.Path.mkdir"),
            patch("views.informes.SimpleDocTemplate", return_value=documento) as doc_factory,
        ):
            _generar_pdf_reporte_negocio(datos)

        self.assertEqual(
            doc_factory.call_args.kwargs["topMargin"],
            MARGEN_SUPERIOR_REPORTE_PDF,
        )
        contenido = documento.build.call_args.args[0]
        titulos = [
            item.getPlainText()
            for item in contenido
            if hasattr(item, "getPlainText")
        ]
        self.assertNotIn("REPORTE GENERAL DEL NEGOCIO", titulos)
        self.assertIn("Resumen general", titulos)

    def test_variation_with_zero_base_is_not_reported_as_percentage(self):
        self.assertIsNone(_variacion_porcentual(10, 0))
        self.assertIsNone(_variacion_porcentual(0, 0))

    def test_comparative_chart_only_plots_comparable_percentage_changes(self):
        drawing = _grafico_comparativo_pdf([
            {"nombre": "Ventas (COP)", "variacion": 25.0},
            {"nombre": "Unidades", "variacion": -10.0},
            {"nombre": "Sin base", "variacion": None},
        ])

        chart = next(item for item in drawing.contents if isinstance(item, VerticalBarChart))
        self.assertEqual(list(chart.data[0]), [25.0, -10.0])
        self.assertEqual(list(chart.categoryAxis.categoryNames), ["Ventas (COP)", "Unidades"])
        self.assertTrue(any(
            isinstance(item, String) and "Variación porcentual" in item.text
            for item in drawing.contents
        ))

    def test_value_chart_displays_metric_and_unit(self):
        drawing = _grafico_barras_pdf(
            [("Hamburguesa", 12)],
            titulo="Unidades vendidas por producto",
            unidad="unidades vendidas",
        )

        chart = next(item for item in drawing.contents if isinstance(item, HorizontalBarChart))
        self.assertEqual(list(chart.categoryAxis.categoryNames), ["Hamburguesa"])
        self.assertEqual(list(chart.data[0]), [12.0])
        captions = [item.text for item in drawing.contents if isinstance(item, String)]
        self.assertTrue(any("Unidades vendidas por producto" in caption for caption in captions))
        self.assertTrue(any("unidades vendidas" in caption for caption in captions))

    def test_pie_chart_legend_includes_amounts_and_shares(self):
        drawing = _grafico_pastel_pdf([("Efectivo", 75), ("Tarjeta", 25)])

        legend = next(item for item in drawing.contents if isinstance(item, Legend))
        self.assertIn("Efectivo: $75 (75.0%)", legend.colorNamePairs[0][1])
        self.assertIn("Tarjeta: $25 (25.0%)", legend.colorNamePairs[1][1])

    def test_interactive_pie_chart_uses_radian_sweeps_for_each_share(self):
        grafico = _grafico_pastel([("Efectivo", 417_500), ("Tarjeta", 60_000)])
        lienzo = grafico.controls[0]
        sectores = lienzo.shapes

        self.assertEqual(len(sectores), 2)
        self.assertAlmostEqual(
            sectores[0].sweep_angle,
            2 * math.pi * 417_500 / 477_500,
        )
        self.assertAlmostEqual(
            sectores[1].sweep_angle,
            2 * math.pi * 60_000 / 477_500,
        )
        self.assertAlmostEqual(
            sum(sector.sweep_angle for sector in sectores),
            2 * math.pi,
        )
        self.assertNotEqual(
            sectores[0].paint.color,
            sectores[1].paint.color,
        )

    def test_business_report_counts_deliveries_and_ignores_cancelled_sales(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        try:
            completada = estado_ventas(nombre="COMPLETADA")
            anulada = estado_ventas(nombre="ANULADA")
            efectivo = metodos_pago(nombre="EFECTIVO")
            db.add_all([completada, anulada, efectivo])
            db.flush()
            db.add_all(
                [
                    ventas(
                        fecha_hora=datetime.datetime(2026, 1, 10, 12),
                        total=15_000,
                        id_estado_ventas=completada.id_estado_venta,
                        id_metodos_pagos=efectivo.id_metodos_pago,
                        tipo_pedido="DOMICILIO",
                        valor_domicilio=3_000,
                        estado_domicilio="ENTREGADO",
                    ),
                    ventas(
                        fecha_hora=datetime.datetime(2026, 1, 10, 13),
                        total=12_000,
                        id_estado_ventas=completada.id_estado_venta,
                        id_metodos_pagos=efectivo.id_metodos_pago,
                        tipo_pedido="MESA",
                    ),
                    ventas(
                        fecha_hora=datetime.datetime(2026, 1, 10, 14),
                        total=20_000,
                        id_estado_ventas=anulada.id_estado_venta,
                        id_metodos_pagos=efectivo.id_metodos_pago,
                        tipo_pedido="DOMICILIO",
                        valor_domicilio=2_000,
                        estado_domicilio="CANCELADO",
                    ),
                ]
            )
            db.commit()
            with patch("views.informes.SessionLocal", return_value=db):
                resultado = _obtener_analisis_negocio(
                    datetime.date(2026, 1, 1),
                    datetime.date(2026, 1, 31),
                )

            self.assertEqual(resultado["total_ventas"], 27_000)
            self.assertEqual(resultado["cantidad_ventas"], 2)
            self.assertEqual(resultado["cantidad_domicilios"], 1)
            self.assertEqual(resultado["domicilios_entregados"], 1)
            self.assertEqual(resultado["ingresos_domicilios"], 3_000)
            self.assertEqual(resultado["ventas_por_tipo"], {"DOMICILIO": 1, "MESA": 1})
        finally:
            db.close()
            Base.metadata.drop_all(engine)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()

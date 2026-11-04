import datetime as dt
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import pymupdf

from views import informes as reports


BODY_TOP_CLEARANCE_PT = 4


def _datasets():
    return {
        "empty": {
            "total_ventas": 0,
            "total_unidades": 0,
            "ticket_promedio": 0,
            "metodo_totales": {"EFECTIVO": 0, "TARJETA": 0, "NEQUI": 0},
            "top_productos": [],
            "menos_vendidos": [],
            "ingresos": 0,
            "entradas_caja": 0,
            "costos_variables": 0,
            "gastos_fijos": 0,
            "gastos_financieros": 0,
            "salidas_caja": 0,
            "utilidad_neta": 0,
            "flujo_neto": 0,
        },
        "small_real": {
            "total_ventas": 173000,
            "total_unidades": 24,
            "ticket_promedio": 34600,
            "metodo_totales": {"EFECTIVO": 155000, "TARJETA": 18000},
            "top_productos": [
                {"nombre": "Callejera", "cantidad": 12, "ventas": 216000},
                {"nombre": "Pollo", "cantidad": 8, "ventas": 120000},
            ],
            "menos_vendidos": [
                {"nombre": "Capuchino Vainilla", "cantidad": 1, "ventas": 4500},
            ],
            "ingresos": 155000,
            "entradas_caja": 155000,
            "costos_variables": 0,
            "gastos_fijos": 0,
            "gastos_financieros": 0,
            "salidas_caja": 0,
            "utilidad_neta": 155000,
            "flujo_neto": 155000,
        },
        "demo": {
            "total_ventas": 1250000,
            "total_unidades": 200,
            "ticket_promedio": 62500,
            "metodo_totales": {"EFECTIVO": 650000, "TARJETA": 400000, "NEQUI": 200000},
            "top_productos": [
                {"nombre": f"Producto {index}", "cantidad": 30 - index, "ventas": 180000 - index * 5000}
                for index in range(1, 8)
            ],
            "menos_vendidos": [
                {"nombre": f"Producto {index}", "cantidad": index, "ventas": index * 12000}
                for index in range(1, 8)
            ],
            "ingresos": 1250000,
            "entradas_caja": 1250000,
            "costos_variables": 390000,
            "gastos_fijos": 220000,
            "gastos_financieros": 40000,
            "salidas_caja": 650000,
            "utilidad_neta": 600000,
            "flujo_neto": 580000,
        },
    }


def _comparative_metrics(data, accounting=False):
    keys = (
        [
            ("ingresos", "Ingresos", "pesos"),
            ("costos_variables", "Costos variables", "pesos"),
            ("gastos_fijos", "Gastos fijos", "pesos"),
            ("gastos_financieros", "Gastos financieros", "pesos"),
            ("utilidad_neta", "Utilidad neta", "pesos"),
            ("flujo_neto", "Flujo neto", "pesos"),
        ]
        if accounting
        else [
            ("total_ventas", "Ventas totales", "pesos"),
            ("total_unidades", "Unidades vendidas", "entero"),
            ("ticket_promedio", "Ticket promedio", "pesos"),
        ]
    )
    result = {}
    for key, name, format_name in keys:
        current = data[key]
        previous = current * 0.8
        result[key] = {
            "nombre": name,
            "actual": current,
            "anterior": previous,
            "variacion": 25.0 if previous else (0.0 if current == 0 else 100.0),
            "formato": format_name,
        }
    return result


def _report_inputs(data):
    current_period = {"etiqueta": "01/11/2026 - 03/11/2026"}
    previous_period = {"etiqueta": "16/10/2026 - 31/10/2026"}
    common = {
        "periodo_actual": current_period,
        "periodo_anterior": previous_period,
    }
    business_compare = {
        **common,
        "metricas": _comparative_metrics(data),
        "productos_comparados": [
            {
                "nombre": product["nombre"],
                "actual": product["cantidad"],
                "anterior": max(0, product["cantidad"] - 1),
                "variacion": 100.0 if product["cantidad"] else 0.0,
            }
            for product in data["top_productos"]
        ],
    }
    accounting_compare = {
        **common,
        "metricas": _comparative_metrics(data, accounting=True),
    }
    business = {
        key: data[key]
        for key in (
            "total_ventas", "total_unidades", "ticket_promedio", "metodo_totales",
            "top_productos", "menos_vendidos",
        )
    }
    accounting = {
        key: data[key]
        for key in (
            "ingresos", "entradas_caja", "costos_variables", "gastos_fijos",
            "gastos_financieros", "salidas_caja", "utilidad_neta", "flujo_neto",
        )
    }
    accounting["periodo"] = "01/11/2026 - 03/11/2026"
    cash_close = SimpleNamespace(
        id_informe=1,
        fecha=dt.date(2026, 11, 3),
        ventas_totales=data["total_ventas"],
        productos_vendidos=data["total_unidades"],
        total_efectivo=data["metodo_totales"].get("EFECTIVO", 0),
        total_tarjeta=data["metodo_totales"].get("TARJETA", 0),
        total_nequi=data["metodo_totales"].get("NEQUI", 0),
        total_proveedores=0,
        saldo_inicial=50000,
        saldo_final=50000 + data["total_ventas"],
    )
    return business, accounting, business_compare, accounting_compare, cash_close


class ReportPdfLayoutTests(unittest.TestCase):
    def test_every_current_report_stays_outside_header_and_footer(self):
        titles_and_generators = (
            ("REPORTE GENERAL DEL NEGOCIO", "business"),
            ("REPORTE DE CONTABILIDAD", "accounting"),
            ("INFORME COMPARATIVO QUINCENAL - NEGOCIO", "business_compare"),
            ("INFORME COMPARATIVO QUINCENAL - CONTABILIDAD", "accounting_compare"),
            ("REPORTE DE CAJA", "cash_close"),
        )

        with TemporaryDirectory() as temporary_directory:
            for dataset_name, data in _datasets().items():
                with self.subTest(dataset=dataset_name):
                    output_dir = Path(temporary_directory) / dataset_name
                    output_dir.mkdir()
                    business, accounting, business_compare, accounting_compare, cash_close = _report_inputs(data)
                    paths = {
                        "business": reports._generar_pdf_reporte_negocio(business, output_dir=output_dir),
                        "accounting": reports._generar_pdf_reporte_contabilidad(accounting, output_dir=output_dir),
                        "business_compare": reports._generar_pdf_comparativo_negocio(
                            business_compare, vista_previa=True, output_dir=output_dir
                        ),
                        "accounting_compare": reports._generar_pdf_comparativo_contabilidad(
                            accounting_compare, vista_previa=True, output_dir=output_dir
                        ),
                        "cash_close": reports._generar_pdf_informe(cash_close, output_dir=output_dir),
                    }
                    if dataset_name == "empty":
                        with pymupdf.open(paths["business"]) as document:
                            self.assertIn(
                                "ventas registradas por medio de pago",
                                document[0].get_text().lower(),
                            )
                    for title, report_key in titles_and_generators:
                        self._assert_layout(Path(paths[report_key]), title)

    def _assert_layout(self, path, title):
        document = pymupdf.open(path)
        try:
            for page_number, page in enumerate(document, start=1):
                with self.subTest(report=path.name, page=page_number):
                    header_rectangles = [
                        drawing["rect"]
                        for drawing in page.get_drawings()
                        if drawing.get("fill")
                        and drawing["rect"].x0 <= 1
                        and drawing["rect"].y0 <= 1
                        and drawing["rect"].width >= page.rect.width - 1
                    ]
                    self.assertEqual(len(header_rectangles), 1)
                    header_bottom = header_rectangles[0].y1
                    self.assertLessEqual(header_bottom, 14 * 72 / 25.4)

                    for word in page.get_text("words"):
                        if word[3] <= header_bottom + 0.5:
                            continue
                        self.assertGreaterEqual(
                            word[1],
                            header_bottom + BODY_TOP_CLEARANCE_PT,
                            f"Text intersects the header on page {page_number}: {word[4]}",
                        )

                    footer_top = page.rect.height - (10 + 12) * 72 / 25.4
                    for drawing in page.get_drawings():
                        rect = drawing["rect"]
                        if rect.width >= page.rect.width - 1 and rect.y0 <= 1 and rect.y1 <= header_bottom + 0.5:
                            continue
                        if rect.height < 1 and rect.y0 >= footer_top - 1:
                            continue
                        self.assertGreaterEqual(rect.y0, header_bottom + BODY_TOP_CLEARANCE_PT)
                        self.assertLessEqual(rect.y1, footer_top + 1)

                    normalized_text = " ".join(page.get_text().split())
                    self.assertLessEqual(normalized_text.count(title), 1)
                    self.assertLessEqual(
                        max((word[3] for word in page.get_text("words") if word[1] < footer_top), default=0),
                        footer_top + 1,
                    )
        finally:
            document.close()


if __name__ == "__main__":
    unittest.main()
import datetime as dt
import unittest

from database.models import Debt, Service, Transaction
from services.financial_engine import FinancialEngine


class FinancialEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.period = (dt.date(2026, 1, 1), dt.date(2026, 1, 31))

    def test_net_profit_excludes_debt_principal(self) -> None:
        engine = FinancialEngine(
            transactions=[
                Transaction(tipo="ingreso", monto=1000, fecha=dt.datetime(2026, 1, 10), categoria="ventas"),
                Transaction(tipo="gasto_variable", monto=400, fecha=dt.datetime(2026, 1, 10), categoria="insumos"),
                Transaction(tipo="gasto_fijo", monto=200, fecha=dt.datetime(2026, 1, 10), categoria="arriendo"),
            ],
            debts=[Debt(abono_capital=150, pago_interes=50, fecha=dt.datetime(2026, 1, 10))],
        )
        result = engine.calculate_pnl(*self.period)
        self.assertEqual(result.utilidad_neta, 350)

    def test_cash_flow_separates_paid_amounts_receivables_and_payables(self) -> None:
        engine = FinancialEngine(
            transactions=[
                Transaction(
                    tipo="ingreso",
                    monto=1000,
                    pagado=True,
                    categoria="ventas",
                    fecha=dt.datetime(2026, 1, 10),
                ),
                Transaction(
                    tipo="ingreso",
                    monto=250,
                    pagado=False,
                    categoria="venta a crédito",
                    fecha=dt.datetime(2026, 1, 11),
                ),
                Transaction(
                    tipo="gasto_variable",
                    monto=200,
                    pagado=True,
                    categoria="insumos",
                    fecha=dt.datetime(2026, 1, 10),
                ),
                Transaction(
                    tipo="gasto_fijo",
                    monto=300,
                    pagado=False,
                    categoria="factura pendiente",
                    fecha=dt.datetime(2026, 1, 12),
                ),
            ],
            services=[
                Service(
                    nombre="Internet pagado",
                    monto=120,
                    pagado=True,
                    fecha=dt.datetime(2026, 1, 10),
                ),
                Service(
                    nombre="Servicio pendiente",
                    monto=80,
                    pagado=False,
                    fecha=dt.datetime(2026, 1, 13),
                ),
            ],
            debts=[
                Debt(
                    nombre="Cuota pagada",
                    cuota_mensual=200,
                    abono_capital=150,
                    pago_interes=50,
                    pagado=True,
                    fecha=dt.datetime(2026, 1, 10),
                ),
                Debt(
                    nombre="Cuota pendiente",
                    cuota_mensual=400,
                    abono_capital=300,
                    pago_interes=100,
                    pagado=False,
                    fecha=dt.datetime(2026, 1, 14),
                ),
            ],
        )
        result = engine.calculate_cash_flow(*self.period)
        self.assertEqual(result.entradas, 1000)
        self.assertEqual(result.salidas, 520)
        self.assertEqual(result.abonos_capital, 150)
        self.assertEqual(result.flujo_neto, 480)
        self.assertEqual(result.cuentas_pendientes, 780)
        self.assertEqual(result.ingresos_pendientes, 250)
        self.assertEqual(len(result.detalle_pendientes), 4)
        self.assertEqual(
            {item.concepto for item in result.detalle_pendientes},
            {
                "venta a crédito",
                "factura pendiente",
                "Servicio pendiente",
                "Cuota pendiente",
            },
        )

    def test_pending_items_and_break_even_respect_selected_period(self) -> None:
        engine = FinancialEngine(
            transactions=[
                Transaction(
                    tipo="ingreso",
                    monto=1000,
                    pagado=True,
                    categoria="Ventas",
                    fecha=dt.datetime(2026, 1, 10),
                ),
                Transaction(
                    tipo="gasto_fijo",
                    monto=200,
                    pagado=False,
                    categoria="Arriendo",
                    fecha=dt.datetime(2026, 2, 10),
                ),
            ]
        )
        january = dt.date(2026, 1, 1), dt.date(2026, 1, 31)
        result = engine.calculate_cash_flow(*january)
        self.assertEqual(result.cuentas_pendientes, 0)
        self.assertEqual(result.detalle_pendientes, ())
        self.assertEqual(engine.calculate_break_even(*january), 0)


if __name__ == "__main__":
    unittest.main()

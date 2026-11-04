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

    def test_cash_flow_only_includes_paid_expenses_and_debt_payments(self) -> None:
        engine = FinancialEngine(
            transactions=[
                Transaction(tipo="ingreso", monto=1000, pagado=True, categoria="ventas"),
                Transaction(tipo="gasto_variable", monto=200, pagado=True, categoria="insumos"),
                Transaction(tipo="gasto_fijo", monto=300, pagado=False, categoria="factura pendiente"),
            ],
            debts=[
                Debt(cuota_mensual=250, abono_capital=150, pago_interes=50, pagado=True),
                Debt(cuota_mensual=200, pagado=False),
            ],
            services=[
                Service(monto=75, tipo="fijo", pagado=True),
                Service(monto=125, tipo="variable", pagado=False),
            ],
        )
        result = engine.calculate_cash_flow(*self.period)
        self.assertEqual(result.flujo_neto, 475)
        self.assertEqual(result.salidas, 525)
        self.assertEqual(result.abonos_capital, 150)
        self.assertEqual(result.cuentas_pendientes, 625)

    def test_paid_and_pending_debt_installments_are_reflected_in_cash_flow(self) -> None:
        engine = FinancialEngine(
            debts=[
                Debt(
                    cuota_mensual=300,
                    abono_capital=250,
                    pago_interes=50,
                    pagado=True,
                ),
                Debt(
                    cuota_mensual=400,
                    abono_capital=350,
                    pago_interes=50,
                    pagado=False,
                ),
            ],
        )

        result = engine.calculate_cash_flow(*self.period)

        self.assertEqual(result.salidas, 300)
        self.assertEqual(result.flujo_neto, -300)
        self.assertEqual(result.abonos_capital, 250)
        self.assertEqual(result.cuentas_pendientes, 400)

    def test_break_even_uses_the_requested_period(self) -> None:
        engine = FinancialEngine(
            transactions=[
                Transaction(tipo="ingreso", monto=1000, fecha=dt.datetime(2026, 1, 10), categoria="ventas"),
                Transaction(tipo="gasto_variable", monto=200, fecha=dt.datetime(2026, 1, 10), categoria="insumos"),
                Transaction(tipo="gasto_fijo", monto=100, fecha=dt.datetime(2026, 1, 10), categoria="arriendo"),
                Transaction(tipo="ingreso", monto=2000, fecha=dt.datetime(2026, 2, 10), categoria="ventas"),
                Transaction(tipo="gasto_variable", monto=1000, fecha=dt.datetime(2026, 2, 10), categoria="insumos"),
                Transaction(tipo="gasto_fijo", monto=1000, fecha=dt.datetime(2026, 2, 10), categoria="arriendo"),
            ],
        )

        punto_equilibrio = engine.calculate_break_even(
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 31),
        )

        self.assertEqual(punto_equilibrio, 125)


if __name__ == "__main__":
    unittest.main()

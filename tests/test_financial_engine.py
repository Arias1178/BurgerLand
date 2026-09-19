import datetime as dt
import unittest

from database.models import Debt, Transaction
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

    def test_cash_flow_includes_paid_principal_and_pending_invoice(self) -> None:
        engine = FinancialEngine(
            transactions=[
                Transaction(tipo="ingreso", monto=1000, pagado=True, categoria="ventas"),
                Transaction(tipo="gasto_variable", monto=200, pagado=True, categoria="insumos"),
                Transaction(tipo="gasto_fijo", monto=300, pagado=False, categoria="factura pendiente"),
            ],
            debts=[Debt(abono_capital=150, pago_interes=50, pagado=True)],
        )
        result = engine.calculate_cash_flow(*self.period)
        self.assertEqual(result.flujo_neto, 350)
        self.assertEqual(result.cuentas_pendientes, 300)


if __name__ == "__main__":
    unittest.main()

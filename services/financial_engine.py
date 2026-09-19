"""Motor financiero independiente de la interfaz y de la persistencia."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Sequence

from database.models import Debt, Payroll, Service, Transaction


MONEY = Decimal("0.01")


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _in_period(item: object, start_date: dt.date, end_date: dt.date) -> bool:
    value = getattr(item, "fecha", None)
    if value is None:
        return True
    if isinstance(value, dt.datetime):
        value = value.date()
    return start_date <= value <= end_date


def _is_paid(item: object) -> bool:
    return bool(getattr(item, "pagado", False))


@dataclass(frozen=True)
class PnlResult:
    ingresos_totales: Decimal
    costos_variables_directos: Decimal
    utilidad_bruta: Decimal
    gastos_fijos_operativos: Decimal
    utilidad_operativa: Decimal
    gastos_financieros: Decimal
    utilidad_neta: Decimal

    def __getitem__(self, key: str) -> Decimal:
        aliases = {
            "ingresos": "ingresos_totales",
            "costos_variables": "costos_variables_directos",
            "gastos_fijos": "gastos_fijos_operativos",
            "gastos_financieros": "gastos_financieros",
            "net_profit": "utilidad_neta",
        }
        return getattr(self, aliases.get(key, key))


@dataclass(frozen=True)
class CashFlowResult:
    entradas: Decimal
    salidas: Decimal
    abonos_capital: Decimal
    flujo_neto: Decimal
    cuentas_pendientes: Decimal

    def __getitem__(self, key: str) -> Decimal:
        aliases = {"cash_flow": "flujo_neto", "net_cash_flow": "flujo_neto"}
        return getattr(self, aliases.get(key, key))


class FinancialEngine:
    """Calcula resultados financieros con reglas explícitas de devengo y caja."""

    def __init__(
        self,
        transactions: Iterable[Transaction] = (),
        payroll: Iterable[Payroll] = (),
        debts: Iterable[Debt] = (),
        services: Iterable[Service] = (),
    ) -> None:
        self.transactions: Sequence[Transaction] = tuple(transactions)
        self.payroll: Sequence[Payroll] = tuple(payroll)
        self.debts: Sequence[Debt] = tuple(debts)
        self.services: Sequence[Service] = tuple(services)

    def calculate_pnl(self, start_date: dt.date, end_date: dt.date) -> PnlResult:
        period_transactions = [
            item for item in self.transactions if _in_period(item, start_date, end_date)
        ]
        ingresos = sum(
            (_decimal(item.monto) for item in period_transactions if item.tipo == "ingreso"),
            Decimal(0),
        )
        transaction_variables = sum(
            (_decimal(item.monto) for item in period_transactions if item.tipo == "gasto_variable"),
            Decimal(0),
        )
        service_variable = sum(
            (_decimal(item.monto) for item in self.services
             if item.tipo == "variable" and getattr(item, "incluido_en_calculo", True) is not False
             and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        variables = transaction_variables + service_variable
        fixed_transactions = sum(
            (_decimal(item.monto) for item in period_transactions if item.tipo == "gasto_fijo"),
            Decimal(0),
        )
        service_fixed = sum(
            (_decimal(item.monto) for item in self.services
             if item.tipo == "fijo" and getattr(item, "incluido_en_calculo", True) is not False
             and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        payroll_cost = sum(
            (_decimal(item.costo_total_empleado()) for item in self.payroll
             if getattr(item, "incluido_en_calculo", True) is not False
             and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        financial_transactions = sum(
            (_decimal(item.monto) for item in period_transactions if item.tipo == "gasto_financiero"),
            Decimal(0),
        )
        debt_interest = sum(
            (_decimal(item.pago_interes) for item in self.debts
             if getattr(item, "incluido_en_calculo", True) is not False
             and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        gross_profit = ingresos - variables
        operating_profit = gross_profit - fixed_transactions - service_fixed - payroll_cost
        net_profit = operating_profit - financial_transactions - debt_interest
        return PnlResult(
            ingresos.quantize(MONEY), variables.quantize(MONEY), gross_profit.quantize(MONEY),
            (fixed_transactions + service_fixed + payroll_cost).quantize(MONEY),
            operating_profit.quantize(MONEY),
            (financial_transactions + debt_interest).quantize(MONEY),
            net_profit.quantize(MONEY),
        )

    def calculate_cash_flow(self, start_date: dt.date, end_date: dt.date) -> CashFlowResult:
        period_transactions = [
            item for item in self.transactions if _in_period(item, start_date, end_date)
        ]
        paid = [item for item in period_transactions if _is_paid(item)]
        entries = sum(
            (_decimal(item.monto) for item in paid if item.tipo == "ingreso"), Decimal(0)
        )
        # Las ventas no cobradas no son liquidez; una factura de gasto
        # pendiente sí representa una obligación que el flujo debe mostrar.
        transaction_outflows = sum(
            (_decimal(item.monto) for item in period_transactions if item.tipo != "ingreso"),
            Decimal(0),
        )
        service_outflows = sum(
            (_decimal(item.monto) for item in self.services
             if getattr(item, "incluido_en_calculo", True) is not False
             and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        principal = sum(
            (_decimal(item.abono_capital) for item in self.debts
             if getattr(item, "incluido_en_calculo", True) is not False
             and _is_paid(item) and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        # El capital no es gasto en P&L, pero sí una salida real de efectivo.
        outflows = transaction_outflows + service_outflows + principal
        pending = sum(
            (_decimal(item.monto) for item in period_transactions if not _is_paid(item)),
            Decimal(0),
        )
        pending += sum(
            (_decimal(item.monto) for item in self.services
             if getattr(item, "incluido_en_calculo", True) is not False
             and not _is_paid(item) and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        return CashFlowResult(
            entries.quantize(MONEY),
            outflows.quantize(MONEY),
            principal.quantize(MONEY),
            (entries - outflows).quantize(MONEY),
            pending.quantize(MONEY),
        )

    def calculate_break_even(self) -> Decimal:
        """Retorna ventas necesarias: costos fijos / margen de contribución."""
        pnl = self.calculate_pnl(dt.date.min, dt.date.max)
        variable_costs = pnl.costos_variables_directos
        revenue = pnl.ingresos_totales
        if revenue <= 0:
            raise ValueError("Se requiere al menos un ingreso para calcular el punto de equilibrio.")
        contribution_margin = (revenue - variable_costs) / revenue
        if contribution_margin <= 0:
            raise ValueError("El margen de contribución promedio debe ser positivo.")
        return (pnl.gastos_fijos_operativos / contribution_margin).quantize(MONEY)


FinancialService = FinancialEngine

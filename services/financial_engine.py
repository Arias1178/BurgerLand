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
        value = getattr(item, "fecha_hora", None)
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
    ingresos_pendientes: Decimal = Decimal(0)
    detalle_pendientes: tuple["PendingItem", ...] = ()

    def __getitem__(self, key: str) -> Decimal:
        aliases = {"cash_flow": "flujo_neto", "net_cash_flow": "flujo_neto"}
        return getattr(self, aliases.get(key, key))


@dataclass(frozen=True)
class PendingItem:
    concepto: str
    tipo: str
    monto: Decimal
    fecha: dt.date | None


class FinancialEngine:
    """Calcula resultados financieros con reglas explícitas de devengo y caja."""

    def __init__(
        self,
        transactions: Iterable[Transaction] = (),
        payroll: Iterable[Payroll] = (),
        debts: Iterable[Debt] = (),
        services: Iterable[Service] = (),
        sales: Iterable[object] = (),
    ) -> None:
        self.transactions: Sequence[Transaction] = tuple(transactions)
        self.payroll: Sequence[Payroll] = tuple(payroll)
        self.debts: Sequence[Debt] = tuple(debts)
        self.services: Sequence[Service] = tuple(services)
        self.sales: Sequence[object] = tuple(sales)

    def calculate_pnl(self, start_date: dt.date, end_date: dt.date) -> PnlResult:
        period_transactions = [
            item for item in self.transactions if _in_period(item, start_date, end_date)
        ]
        period_sales = [
            item for item in self.sales if _in_period(item, start_date, end_date)
        ]
        ingresos = sum(
            (_decimal(item.monto) for item in period_transactions if item.tipo == "ingreso"),
            Decimal(0),
        )
        ingresos += sum(
            (_decimal(item.total) for item in period_sales),
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
        period_sales = [
            item for item in self.sales if _in_period(item, start_date, end_date)
        ]
        paid = [item for item in period_transactions if _is_paid(item)]
        entries = sum(
            (_decimal(item.monto) for item in paid if item.tipo == "ingreso"), Decimal(0)
        )
        entries += sum(
            (_decimal(item.total) for item in period_sales),
            Decimal(0),
        )
        # Las ventas no cobradas no son liquidez; una factura de gasto
        # pendiente sí representa una obligación que el flujo debe mostrar.
        transaction_outflows = sum(
            (
                _decimal(item.monto)
                for item in paid
                if item.tipo != "ingreso"
            ),
            Decimal(0),
        )
        service_outflows = sum(
            (_decimal(item.monto) for item in self.services
             if _is_paid(item)
             and getattr(item, "incluido_en_calculo", True) is not False
             and _in_period(item, start_date, end_date)),
            Decimal(0),
        )
        paid_debt_payments = [
            item for item in self.debts
            if getattr(item, "incluido_en_calculo", True) is not False
            and _in_period(item, start_date, end_date)
            and _is_paid(item)
        ]
        principal = sum(
            (_decimal(item.abono_capital) for item in paid_debt_payments),
            Decimal(0),
        )
        paid_debt_interest = sum(
            (_decimal(item.pago_interes) for item in paid_debt_payments),
            Decimal(0),
        )
        # Solo los pagos realizados afectan el efectivo; las obligaciones
        # pendientes se muestran aparte para no reducir el flujo prematuramente.
        outflows = (
            transaction_outflows
            + service_outflows
            + principal
            + paid_debt_interest
        )
        detalle_pendientes = []
        for item in period_transactions:
            if _is_paid(item):
                continue
            fecha = getattr(item, "fecha", None)
            detalle_pendientes.append(
                PendingItem(
                    concepto=getattr(item, "categoria", None) or item.tipo,
                    tipo=(
                        "Por cobrar"
                        if item.tipo == "ingreso"
                        else "Por pagar"
                    ),
                    monto=_decimal(item.monto),
                    fecha=fecha.date() if isinstance(fecha, dt.datetime) else fecha,
                )
            )
        for item in self.services:
            if (
                _is_paid(item)
                or getattr(item, "incluido_en_calculo", True) is False
                or not _in_period(item, start_date, end_date)
            ):
                continue
            fecha = getattr(item, "fecha", None)
            detalle_pendientes.append(
                PendingItem(
                    concepto=item.nombre,
                    tipo="Servicio pendiente",
                    monto=_decimal(item.monto),
                    fecha=fecha.date() if isinstance(fecha, dt.datetime) else fecha,
                )
            )
        for item in self.debts:
            if (
                _is_paid(item)
                or getattr(item, "incluido_en_calculo", True) is False
                or not _in_period(item, start_date, end_date)
            ):
                continue
            fecha = getattr(item, "fecha", None)
            cuota = _decimal(getattr(item, "cuota_mensual", 0))
            if cuota <= 0:
                cuota = _decimal(item.abono_capital) + _decimal(item.pago_interes)
            detalle_pendientes.append(
                PendingItem(
                    concepto=item.nombre,
                    tipo="Cuota de deuda pendiente",
                    monto=cuota,
                    fecha=fecha.date() if isinstance(fecha, dt.datetime) else fecha,
                )
            )

        pendientes_por_pagar = sum(
            (
                item.monto
                for item in detalle_pendientes
                if item.tipo != "Por cobrar"
            ),
            Decimal(0),
        )
        ingresos_pendientes = sum(
            (
                item.monto
                for item in detalle_pendientes
                if item.tipo == "Por cobrar"
            ),
            Decimal(0),
        )
        return CashFlowResult(
            entries.quantize(MONEY),
            outflows.quantize(MONEY),
            principal.quantize(MONEY),
            (entries - outflows).quantize(MONEY),
            pendientes_por_pagar.quantize(MONEY),
            ingresos_pendientes.quantize(MONEY),
            tuple(detalle_pendientes),
        )

    def calculate_break_even(
        self,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> Decimal:
        """Retorna ventas necesarias: costos fijos / margen de contribución."""
        pnl = self.calculate_pnl(
            start_date or dt.date.min,
            end_date or dt.date.max,
        )
        variable_costs = pnl.costos_variables_directos
        revenue = pnl.ingresos_totales
        if revenue <= 0:
            raise ValueError("Se requiere al menos un ingreso para calcular el punto de equilibrio.")
        contribution_margin = (revenue - variable_costs) / revenue
        if contribution_margin <= 0:
            raise ValueError("El margen de contribución promedio debe ser positivo.")
        return (pnl.gastos_fijos_operativos / contribution_margin).quantize(MONEY)


FinancialService = FinancialEngine

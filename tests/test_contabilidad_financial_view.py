import datetime as dt
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import Debt, Service, Transaction, rol
from views.contabilidad import _obtener_rango_periodo, _panel_financiero


class ContabilidadFinancialViewTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _buscar_controles(self, control, tipo):
        if isinstance(control, tipo):
            yield control
        for hijo in getattr(control, "controls", []):
            yield from self._buscar_controles(hijo, tipo)
        contenido = getattr(control, "content", None)
        if contenido is not None:
            yield from self._buscar_controles(contenido, tipo)

    def test_period_presets_and_custom_period_controls(self):
        hoy = dt.date(2026, 3, 18)
        self.assertEqual(_obtener_rango_periodo("hoy", hoy), (hoy, hoy))
        self.assertEqual(
            _obtener_rango_periodo("mes_anterior", hoy),
            (dt.date(2026, 2, 1), dt.date(2026, 2, 28)),
        )

        page = MagicMock(spec=ft.Page)
        with patch("views.contabilidad.SessionLocal", self.session_factory):
            panel = _panel_financiero(page)

        controles = list(self._buscar_controles(panel, ft.Control))
        periodo = next(
            control
            for control in controles
            if isinstance(control, ft.Dropdown)
            and control.label == "Periodo del cálculo"
        )
        self.assertEqual(periodo.value, "hoy")
        fechas = [
            control
            for control in controles
            if isinstance(control, ft.OutlinedButton)
            and control.icon == ft.Icons.CALENDAR_TODAY_OUTLINED
        ]
        self.assertEqual(len(fechas), 3)
        periodo.value = "personalizado"
        periodo.on_change(None)
        self.assertTrue(fechas[0].visible)
        self.assertTrue(fechas[1].visible)
        self.assertFalse(
            any(
                isinstance(control, ft.TextField)
                and control.label in {"Fecha inicio", "Fecha fin"}
                for control in controles
            )
        )

    def test_unpaid_transaction_is_saved_and_shown_in_pending_totals(self):
        page = MagicMock(spec=ft.Page)
        with patch("views.contabilidad.SessionLocal", self.session_factory):
            panel = _panel_financiero(page)

        controles = list(self._buscar_controles(panel, ft.Control))
        tipo = next(
            control
            for control in controles
            if isinstance(control, ft.Dropdown)
            and control.label.startswith("Tipo de")
        )
        monto = next(
            control
            for control in controles
            if isinstance(control, ft.TextField) and control.label == "Monto"
        )
        categoria = next(
            control
            for control in controles
            if isinstance(control, ft.TextField)
            and control.label.startswith("Categor")
        )
        tipo.value = "gasto_fijo"
        monto.value = "12000"
        categoria.value = "Arriendo pendiente"
        next(
            control
            for control in controles
            if isinstance(control, ft.Checkbox) and control.label == "Pagado"
        ).value = False
        boton_registrar = next(
            control
            for control in controles
            if isinstance(control, ft.ElevatedButton)
            and control.content == "Registrar"
        )
        periodo = next(
            control
            for control in controles
            if isinstance(control, ft.Dropdown)
            and control.label == "Periodo del cálculo"
        )

        with patch.object(periodo, "update"):
            with patch("views.contabilidad.SessionLocal", self.session_factory):
                boton_registrar.on_click(None)

        with self.session_factory() as db:
            transaction = db.query(Transaction).one()
            self.assertEqual(transaction.monto, 12000)
            self.assertFalse(transaction.pagado)
            self.assertEqual(transaction.categoria, "Arriendo pendiente")

        textos = [
            control.value
            for control in self._buscar_controles(panel, ft.Text)
            if control.value
        ]
        self.assertTrue(any("Por pagar · Arriendo pendiente" in texto for texto in textos))
        self.assertTrue(
            any(texto == "$12.000" for texto in textos),
            "El total pendiente debe reflejar la transacción impaga.",
        )

    def test_admin_can_mark_pending_items_paid_or_collected(self):
        with self.session_factory() as db:
            admin_role = rol(nombre="ADMIN")
            db.add(admin_role)
            db.flush()
            role_id = admin_role.id_rol
            db.add_all(
                [
                    Transaction(
                        tipo="ingreso",
                        monto=5000,
                        categoria="Deuda",
                        pagado=False,
                    ),
                    Transaction(
                        tipo="gasto_fijo",
                        monto=120000,
                        categoria="Empanadas",
                        pagado=False,
                    ),
                    Service(
                        nombre="Internet",
                        monto=80000,
                        tipo="fijo",
                        pagado=False,
                    ),
                    Debt(
                        nombre="Préstamo",
                        monto_total=500000,
                        cuota_mensual=50000,
                        abono_capital=40000,
                        pago_interes=10000,
                        pagado=False,
                    ),
                ]
            )
            db.commit()

        page = MagicMock(spec=ft.Page)
        admin = SimpleNamespace(id_rol=role_id)
        with patch("views.contabilidad.SessionLocal", self.session_factory):
            panel = _panel_financiero(page, usuario_actual=admin)

            botones = [
                control
                for control in self._buscar_controles(panel, ft.TextButton)
                if getattr(control.content, "value", control.content)
                in {"Marcar pagado", "Marcar cobrado"}
            ]
            self.assertEqual(len(botones), 4)
            self.assertEqual(
                sum(
                    getattr(control.content, "value", control.content)
                    == "Marcar cobrado"
                    for control in botones
                ),
                1,
            )

            for boton in botones:
                boton.on_click(None)

        with self.session_factory() as db:
            self.assertTrue(
                all(
                    item.pagado
                    for item in db.query(Transaction).all()
                    + db.query(Service).all()
                    + db.query(Debt).all()
                )
            )

        textos = [
            control.value
            for control in self._buscar_controles(panel, ft.Text)
            if control.value
        ]
        self.assertFalse(any("Por cobrar · Deuda" in texto for texto in textos))
        self.assertFalse(any("Por pagar · Empanadas" in texto for texto in textos))
        self.assertFalse(any("Servicio pendiente · Internet" in texto for texto in textos))
        self.assertFalse(any("Cuota de deuda pendiente · Préstamo" in texto for texto in textos))


if __name__ == "__main__":
    unittest.main()

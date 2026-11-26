import datetime
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import compras, detalles_compras, inventario, rol
from views.compras import compras_view


class ComprasViewTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        with self.session_factory() as db:
            admin_role = rol(nombre="ADMIN")
            db.add(admin_role)
            db.commit()
            self.admin_role_id = admin_role.id_rol

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def crear_vista(self, filas):
        page = MagicMock(spec=ft.Page)
        with (
            patch("views.compras.SessionLocal", self.session_factory),
            patch("views.compras.listar_conciliacion_retiros", return_value=filas),
        ):
            view = compras_view(
                page,
                ft.Container(),
                usuario_actual=SimpleNamespace(id_rol=self.admin_role_id),
            )
        return page, view

    def recopilar_textos(self, control):
        textos = []
        if isinstance(control, ft.Text):
            textos.append(control.value)
        if isinstance(control, ft.TextButton) and isinstance(control.content, str):
            textos.append(control.content)
        contenido = getattr(control, "content", None)
        if contenido is not None:
            textos.extend(self.recopilar_textos(contenido))
        for hijo in getattr(control, "controls", []) or []:
            textos.extend(self.recopilar_textos(hijo))
        return textos

    def test_empty_reconciliation_shows_explicit_state_without_nested_scrolling(self):
        page, view = self.crear_vista([])
        tarjeta = view.controls[1]

        self.assertIn(
            "No hay retiros pendientes o conciliados.",
            self.recopilar_textos(view),
        )
        self.assertIn("Aún no hay compras registradas.", self.recopilar_textos(view))
        self.assertIsNone(tarjeta.expand)
        self.assertIsNone(tarjeta.content.scroll)
        self.assertFalse(page.update.called)

    def test_purchase_history_shows_detached_supplier_and_line_details(self):
        fecha = datetime.datetime(2026, 11, 25, 14, 30)
        with self.session_factory() as db:
            item = inventario(
                nombre="Caja de vasos",
                categoria="Empaques",
                unidad_medida="caja",
                cantidad=2,
                stock_minimo=0,
                costo_unitario=12000,
            )
            db.add(item)
            db.flush()
            compra = compras(fecha=fecha, total=24000, id_proveedor=None)
            db.add(compra)
            db.flush()
            db.add(
                detalles_compras(
                    cantidad=2,
                    precio=12000,
                    subtotal=24000,
                    id_compra=compra.id_compra,
                    id_inventario=item.id_inventario,
                )
            )
            db.commit()

        _, view = self.crear_vista([])
        textos = self.recopilar_textos(view)

        self.assertIn("HISTORIAL DE COMPRAS", textos)
        self.assertIn("Compra #1 · 25/11/2026 14:30", textos)
        self.assertIn("Proveedor eliminado / sin asignar", textos)
        self.assertIn("2 × Caja de vasos — $12.000 c/u · Subtotal $24.000", textos)
        self.assertIn("Total $24.000", textos)

    def test_reconciliation_renders_withdrawal_details_and_action(self):
        retiro = SimpleNamespace(
            id_retiro=12,
            fecha_hora=datetime.datetime(2025, 5, 1, 10, 30),
            motivo="Compra de mercancía",
        )
        fila = {
            "retiro": retiro,
            "compras": [],
            "monto_retirado": 1_000_000,
            "monto_justificado": 250_000,
            "saldo_pendiente": 750_000,
            "estado": "Parcial",
            "alerta": False,
            "dias_transcurridos": 2,
        }

        _, view = self.crear_vista([fila])
        textos = self.recopilar_textos(view)

        self.assertIn("Retiro #12 · 01/05/2025 10:30", textos)
        self.assertIn("Motivo: Compra de mercancía", textos)
        self.assertIn("Compras vinculadas: Sin compras vinculadas", textos)
        self.assertIn("Retirado $1.000.000 · Justificado $250.000 · Pendiente $750.000", textos)
        self.assertIn("Vincular compra", textos)


if __name__ == "__main__":
    unittest.main()

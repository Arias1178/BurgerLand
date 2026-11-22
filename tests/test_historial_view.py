import datetime
import unittest
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import ventas
from views.historial import historial_view


class HistorialViewTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        with self.session_factory() as db:
            db.add(
                ventas(
                    fecha_hora=datetime.datetime(2026, 11, 11, 12, 30),
                    total=13_500,
                    tipo_pedido="DOMICILIO",
                    cliente="Ana Pérez",
                    telefono_cliente="3001234567",
                    direccion_domicilio="Calle 10",
                    estado_domicilio="RECIBIDO",
                )
            )
            db.commit()

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _recorrer_controles(self, control):
        yield control
        for hijo in getattr(control, "controls", []):
            yield from self._recorrer_controles(hijo)
        contenido = getattr(control, "content", None)
        if contenido is not None:
            yield from self._recorrer_controles(contenido)

    def test_active_delivery_row_has_no_expanded_column_in_wrapping_row(self):
        page = MagicMock(spec=ft.Page)
        with patch("views.historial.SessionLocal", self.session_factory):
            view = historial_view(page, ft.Container())

        controls = list(self._recorrer_controles(view))
        textos = [
            control.value
            for control in controls
            if isinstance(control, ft.Text) and control.value
        ]
        self.assertTrue(any("Venta #1" in texto for texto in textos))

        filas_envueltas = [
            control
            for control in controls
            if isinstance(control, ft.Row) and control.wrap
        ]
        self.assertTrue(filas_envueltas)
        self.assertFalse(
            any(
                isinstance(hijo, ft.Column) and hijo.expand
                for fila in filas_envueltas
                for hijo in fila.controls
            )
        )


if __name__ == "__main__":
    unittest.main()

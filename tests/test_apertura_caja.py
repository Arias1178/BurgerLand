import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from database.database import Base
from database.models import cuentas_abiertas
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class AperturaCajaTests(unittest.TestCase):
    def test_cop_parser_accepts_local_thousands_separators(self):
        self.assertEqual(main.parsear_valor_cop("$2.000.000"), 2_000_000)

    def test_unusual_opening_requires_confirmation_then_is_persisted(self):
        usuario = SimpleNamespace(id_usuario=1)
        estado_abierta = SimpleNamespace(id_estado_caja=2)
        db = Mock()
        db.refresh.side_effect = lambda record: None

        with (
            patch.object(main, "SessionLocal", return_value=db),
            patch.object(main, "obtener_caja_abierta", side_effect=[None, None]),
            patch.object(main, "obtener_estado_caja", return_value=estado_abierta),
            patch.object(
                main,
                "advertencia_apertura",
                return_value="El valor supera el promedio histórico.",
            ),
        ):
            requiere_confirmacion = main.abrir_caja(usuario, "10.000.000")
            self.assertFalse(requiere_confirmacion["ok"])
            self.assertTrue(requiere_confirmacion["requiere_confirmacion"])
            self.assertIn("$10.000.000", requiere_confirmacion["mensaje"])

            resultado = main.abrir_caja(
                usuario,
                "10.000.000",
                confirmar_inusual=True,
            )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["caja"].saldo_inicial, 10_000_000)
        db.add.assert_called_once()
        self.assertEqual(db.commit.call_count, 1)
        self.assertEqual(db.close.call_count, 2)

    def test_zero_and_negative_values_are_advisory_until_confirmed(self):
        with patch.object(main, "SessionLocal"):
            self.assertIn("mayor que cero", main.advertencia_apertura(Mock(), 0))
            self.assertIn("mayor que cero", main.advertencia_apertura(Mock(), -1))

    def test_final_cash_balance_includes_withdrawals(self):
        self.assertEqual(
            main.calcular_saldo_final_caja(2_000_000, 300_000, 1_000_000),
            1_300_000,
        )

    def test_cash_cannot_close_while_open_accounts_remain(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        try:
            db.add(cuentas_abiertas(estado="ABIERTA"))
            db.commit()
            with (
                patch.object(main, "SessionLocal", return_value=db),
                patch.object(
                    main,
                    "obtener_caja_abierta",
                    return_value=SimpleNamespace(id_caja=1),
                ),
            ):
                resultado = main.cerrar_caja(SimpleNamespace(id_usuario=1))
            self.assertFalse(resultado["ok"])
            self.assertIn("1 cuenta(s) abierta(s)", resultado["mensaje"])
        finally:
            db.close()
            Base.metadata.drop_all(engine)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()

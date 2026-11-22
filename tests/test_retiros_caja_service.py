import datetime
import unittest

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    Transaction,
    caja,
    compras,
    estados_caja,
    movimiento_caja,
    retiros_caja,
    vinculos_retiro_compra,
)
from services.financial_engine import FinancialEngine
from services.retiros_caja_service import (
    listar_conciliacion_retiros,
    listar_compras_disponibles,
    registrar_retiro,
    vincular_retiro_compra,
)


class RetirosCajaServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.estado = estados_caja(nombre="ABIERTA")
        self.db.add(self.estado)
        self.db.flush()
        self.caja = caja(
            fecha_apertura=datetime.datetime.now(),
            saldo_inicial=2_000_000,
            id_estado_caja=self.estado.id_estado_caja,
            id_usuario=1,
        )
        self.db.add(self.caja)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def crear_compra(self, total):
        compra = compras(
            fecha=datetime.datetime.now(),
            total=total,
        )
        self.db.add(compra)
        self.db.commit()
        return compra

    def test_partial_and_multiple_purchase_links_reconcile_once(self):
        retiro = registrar_retiro(
            self.db,
            self.caja.id_caja,
            7,
            1_000_000,
            "Compra de mercancía",
        )
        compra_uno = self.crear_compra(600_000)
        compra_dos = self.crear_compra(500_000)

        vincular_retiro_compra(
            self.db,
            retiro.id_retiro,
            compra_uno.id_compra,
            600_000,
        )
        vincular_retiro_compra(
            self.db,
            retiro.id_retiro,
            compra_dos.id_compra,
            300_000,
        )

        conciliacion = listar_conciliacion_retiros(
            self.db,
            ahora=datetime.datetime.now() + datetime.timedelta(days=4),
            dias_alerta=3,
        )[0]
        self.assertEqual(conciliacion["monto_retirado"], 1_000_000)
        self.assertEqual(conciliacion["monto_justificado"], 900_000)
        self.assertEqual(conciliacion["saldo_pendiente"], 100_000)
        self.assertEqual(conciliacion["estado"], "Parcial")
        self.assertTrue(conciliacion["alerta"])
        self.assertEqual(len(conciliacion["compras"]), 2)
        self.assertEqual(
            len(listar_compras_disponibles(self.db)),
            1,
        )

        movimientos = self.db.query(
            func.coalesce(func.sum(movimiento_caja.valor), 0)
        ).scalar()
        flujo = FinancialEngine(
            transactions=self.db.query(Transaction).all()
        ).calculate_cash_flow(
            datetime.date.today(),
            datetime.date.today(),
        )
        self.assertEqual(movimientos, 1_000_000)
        self.assertEqual(flujo.salidas, 1_000_000)
        self.assertEqual(
            self.db.query(vinculos_retiro_compra)
            .filter_by(id_retiro=retiro.id_retiro)
            .count(),
            2,
        )

    def test_rejects_negative_zero_and_unjustified_overallocation(self):
        with self.assertRaisesRegex(ValueError, "mayor que cero"):
            registrar_retiro(
                self.db,
                self.caja.id_caja,
                7,
                -1,
                "Motivo",
            )
        with self.assertRaisesRegex(ValueError, "mayor que cero"):
            registrar_retiro(
                self.db,
                self.caja.id_caja,
                7,
                0,
                "Motivo",
            )
        retiro = registrar_retiro(
            self.db,
            self.caja.id_caja,
            7,
            1_000_000,
            "Compra",
        )
        compra = self.crear_compra(700_000)
        vincular_retiro_compra(
            self.db,
            retiro.id_retiro,
            compra.id_compra,
            600_000,
        )

        with self.assertRaisesRegex(ValueError, "saldo pendiente del retiro"):
            vincular_retiro_compra(
                self.db,
                retiro.id_retiro,
                compra.id_compra,
                500_000,
            )
        with self.assertRaisesRegex(ValueError, "saldo disponible de la compra"):
            vincular_retiro_compra(
                self.db,
                retiro.id_retiro,
                compra.id_compra,
                200_000,
            )

    def test_fully_linked_retirement_is_conciliated(self):
        retiro = registrar_retiro(
            self.db,
            self.caja.id_caja,
            7,
            1_000_000,
            "Compra",
        )
        compra = self.crear_compra(1_000_000)
        vincular_retiro_compra(
            self.db,
            retiro.id_retiro,
            compra.id_compra,
            1_000_000,
        )

        fila = listar_conciliacion_retiros(self.db)[0]
        self.assertEqual(fila["estado"], "Conciliado")
        self.assertEqual(fila["saldo_pendiente"], 0)
        self.assertFalse(fila["alerta"])
        self.assertEqual(listar_compras_disponibles(self.db), [])


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import mesas
from services.mesa_service import (
    ESTADO_MESA_LIBRE,
    ESTADO_MESA_OCUPADA,
    NUMERO_MESAS,
    obtener_mesas,
    sembrar_mesas,
    validar_mesa_disponible,
)


class MesaServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_seed_crea_17_mesas_una_sola_vez(self):
        self.assertEqual(sembrar_mesas(self.db), NUMERO_MESAS)
        self.db.commit()

        self.assertEqual(sembrar_mesas(self.db), 0)
        self.db.commit()
        mesas_disponibles = obtener_mesas(self.db)
        self.assertEqual(len(mesas_disponibles), NUMERO_MESAS)
        self.assertEqual(
            [mesa.numero for mesa in mesas_disponibles],
            list(range(1, NUMERO_MESAS + 1)),
        )
        self.assertTrue(
            all(mesa.estado == ESTADO_MESA_LIBRE for mesa in mesas_disponibles)
        )

    def test_seed_no_reinicia_estado_de_mesas_existentes(self):
        self.db.add(mesas(numero=1, estado=ESTADO_MESA_OCUPADA))
        self.db.commit()

        self.assertEqual(sembrar_mesas(self.db), NUMERO_MESAS - 1)
        self.db.commit()

        self.assertEqual(self.db.query(mesas).filter_by(numero=1).one().estado, ESTADO_MESA_OCUPADA)

    def test_valida_mesa_libre_y_rechaza_ocupada_o_inexistente(self):
        libre = mesas(numero=1, estado=ESTADO_MESA_LIBRE)
        ocupada = mesas(numero=2, estado=ESTADO_MESA_OCUPADA)
        self.db.add_all([libre, ocupada])
        self.db.commit()

        self.assertIs(validar_mesa_disponible(self.db, libre.id_mesa), libre)
        with self.assertRaisesRegex(ValueError, "no está disponible"):
            validar_mesa_disponible(self.db, ocupada.id_mesa)
        with self.assertRaisesRegex(ValueError, "no existe"):
            validar_mesa_disponible(self.db, 999)
        self.assertIsNone(validar_mesa_disponible(self.db, None))


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import catalogo_proveedores, categorias_proveedores, proveedores
from services.proveedores_service import (
    CATALOGO_INICIAL,
    actualizar_precio_catalogo,
    sembrar_catalogo_proveedores,
)


class ProveedoresServiceTests(unittest.TestCase):
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

    def test_siembra_los_proveedores_y_su_catalogo_completo(self):
        cantidad = sembrar_catalogo_proveedores(self.db)
        esperados = sum(len(articulos) for _, _, articulos in CATALOGO_INICIAL)

        self.assertEqual(self.db.query(proveedores).count(), len(CATALOGO_INICIAL))
        self.assertEqual(self.db.query(catalogo_proveedores).count(), esperados)
        self.assertEqual(cantidad, esperados)
        self.assertIsNone(self.db.query(proveedores).first().correo)
        self.assertGreater(
            self.db.query(categorias_proveedores).count(),
            1,
        )

    def test_siembra_es_idempotente_y_no_sobrescribe_datos_de_contacto(self):
        nombre, categoria, _ = CATALOGO_INICIAL[0]
        existente = proveedores(
            nombre=nombre,
            que_provee=categoria,
            telefono="123456",
            correo="contacto@example.com",
            cuanto_cobra=15000,
            estado="INACTIVO",
        )
        self.db.add(existente)
        self.db.commit()

        primera_siembra = sembrar_catalogo_proveedores(self.db)
        segunda_siembra = sembrar_catalogo_proveedores(self.db)

        self.assertGreater(primera_siembra, 0)
        self.assertEqual(segunda_siembra, 0)
        self.assertEqual(self.db.query(proveedores).count(), len(CATALOGO_INICIAL))
        self.assertEqual(self.db.query(catalogo_proveedores).count(), primera_siembra)
        self.assertEqual(existente.telefono, "123456")
        self.assertEqual(existente.correo, "contacto@example.com")
        self.assertEqual(existente.cuanto_cobra, 15000)
        self.assertEqual(existente.estado, "INACTIVO")

    def test_bebidas_quedan_individuales_por_proveedor_y_presentacion(self):
        sembrar_catalogo_proveedores(self.db)
        agua_cristal = (
            self.db.query(catalogo_proveedores)
            .join(proveedores)
            .filter(
                proveedores.nombre == "Postobón",
                catalogo_proveedores.nombre == "Agua Cristal - PET",
            )
            .one()
        )
        agua_brisa = (
            self.db.query(catalogo_proveedores)
            .join(proveedores)
            .filter(
                proveedores.nombre == "Coca-Cola FEMSA",
                catalogo_proveedores.nombre == "Agua Brisa - PET",
            )
            .one()
        )

        actualizar_precio_catalogo(self.db, agua_cristal.id_producto_proveedor, 1800)
        actualizar_precio_catalogo(self.db, agua_brisa.id_producto_proveedor, 2200)
        sembrar_catalogo_proveedores(self.db)
        self.db.refresh(agua_cristal)
        self.db.refresh(agua_brisa)

        self.assertNotEqual(agua_cristal.id_proveedor, agua_brisa.id_proveedor)
        self.assertEqual(agua_cristal.precio_unitario, 1800)
        self.assertEqual(agua_brisa.precio_unitario, 2200)
        self.assertEqual(
            self.db.query(catalogo_proveedores)
            .join(proveedores)
            .filter(
                proveedores.nombre == "Postobón",
                catalogo_proveedores.nombre == "Agua Cristal - Vidrio",
            )
            .count(),
            1,
        )
        self.assertEqual(
            self.db.query(catalogo_proveedores)
            .join(proveedores)
            .filter(
                proveedores.nombre == "Coca-Cola FEMSA",
                catalogo_proveedores.nombre == "Agua Brisa - PET",
            )
            .count(),
            1,
        )
        self.assertEqual(
            self.db.query(catalogo_proveedores)
            .join(proveedores)
            .filter(
                proveedores.nombre == "Postobón",
                catalogo_proveedores.nombre == "Aguas",
            )
            .count(),
            0,
        )

    def test_precio_de_catalogo_rechaza_valores_invalidos(self):
        sembrar_catalogo_proveedores(self.db)
        articulo = self.db.query(catalogo_proveedores).first()

        with self.assertRaises(ValueError):
            actualizar_precio_catalogo(
                self.db, articulo.id_producto_proveedor, "no es precio"
            )
        with self.assertRaises(ValueError):
            actualizar_precio_catalogo(
                self.db, articulo.id_producto_proveedor, -1
            )
        self.assertIsNone(articulo.precio_unitario)

    def test_seed_reemplaza_registros_de_bebidas_agrupadas_anteriores(self):
        sembrar_catalogo_proveedores(self.db)
        postobon = self.db.query(proveedores).filter_by(nombre="Postobón").one()
        registro_agrupado = catalogo_proveedores(
            id_proveedor=postobon.id_proveedor,
            grupo="Aguas",
            nombre="Aguas",
            detalles="Agua Cristal y otras bebidas.",
        )
        self.db.add(registro_agrupado)
        self.db.commit()

        nuevos = sembrar_catalogo_proveedores(self.db)

        self.assertEqual(nuevos, 0)
        self.assertIsNone(
            self.db.query(catalogo_proveedores)
            .filter_by(
                id_proveedor=postobon.id_proveedor,
                nombre="Aguas",
            )
            .first()
        )
        self.assertEqual(
            self.db.query(catalogo_proveedores)
            .filter_by(
                id_proveedor=postobon.id_proveedor,
                nombre="Agua Cristal - PET",
            )
            .count(),
            1,
        )


if __name__ == "__main__":
    unittest.main()

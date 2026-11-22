import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import inventario, proveedores
from services.compras_service import registrar_compra


class ComprasServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.proveedor = proveedores(
            nombre="Proveedor de prueba",
            que_provee="Insumos",
            correo="proveedor-prueba@example.com",
            estado="ACTIVO",
        )
        self.item = inventario(
            nombre="Pan",
            categoria="Insumos",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=1,
            costo_unitario=1000,
            estado="ELIMINADO",
        )
        self.db.add_all([self.proveedor, self.item])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_rechaza_compra_de_insumo_inhabilitado_o_eliminado(self):
        with self.assertRaisesRegex(ValueError, "está inhabilitado o eliminado"):
            registrar_compra(
                self.db,
                self.proveedor.id_proveedor,
                [{
                    "id_inventario": self.item.id_inventario,
                    "cantidad": 2,
                    "precio": 1000,
                }],
            )

        self.assertEqual(self.item.cantidad, 5)

    def test_rechaza_compra_de_articulo_asignado_a_otro_proveedor(self):
        segundo_proveedor = proveedores(
            nombre="Otro proveedor",
            que_provee="Insumos",
            correo="otro-proveedor@example.com",
            estado="ACTIVO",
        )
        self.db.add(segundo_proveedor)
        self.db.flush()
        self.item.estado = "ACTIVO"
        self.item.id_proveedor = segundo_proveedor.id_proveedor
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "pertenece a otro proveedor"):
            registrar_compra(
                self.db,
                self.proveedor.id_proveedor,
                [{
                    "id_inventario": self.item.id_inventario,
                    "cantidad": 2,
                    "precio": 1000,
                }],
            )

        self.assertEqual(self.item.cantidad, 5)

    def test_compra_actualiza_el_sku_asociado_al_proveedor(self):
        self.item.estado = "ACTIVO"
        self.item.id_proveedor = self.proveedor.id_proveedor
        self.db.commit()

        registrar_compra(
            self.db,
            self.proveedor.id_proveedor,
            [{
                "id_inventario": self.item.id_inventario,
                "cantidad": 2,
                "precio": 1000,
            }],
        )

        self.assertEqual(self.item.cantidad, 7)
        self.assertEqual(self.item.costo_unitario, 1000)

    def test_compra_actualiza_costo_promedio_del_sku(self):
        self.item.estado = "ACTIVO"
        self.item.id_proveedor = self.proveedor.id_proveedor
        self.db.commit()

        registrar_compra(
            self.db,
            self.proveedor.id_proveedor,
            [{
                "id_inventario": self.item.id_inventario,
                "cantidad": 5,
                "precio": 3000,
            }],
        )

        self.assertEqual(self.item.cantidad, 10)
        self.assertEqual(self.item.costo_unitario, 2000)


if __name__ == "__main__":
    unittest.main()

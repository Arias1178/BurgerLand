import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    categorias,
    categorias_inventario,
    detalles_compras,
    inventario,
    productos,
)
from services.inventario_service import (
    cambiar_estado_categoria_inventario,
    cambiar_estado_insumo_inventario,
    eliminar_categoria_inventario,
    eliminar_insumo_inventario,
    obtener_o_crear_categoria_inventario,
    sincronizar_categorias_inventario,
)


class InventarioEliminacionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.categoria_menu = categorias(nombre="Bebidas", estado="ACTIVO")
        self.db.add(self.categoria_menu)
        self.item = inventario(
            nombre="Gaseosa",
            categoria="Bebidas",
            unidad_medida="unidad",
            cantidad=10,
            stock_minimo=1,
            costo_unitario=1000,
            estado="ACTIVO",
        )
        self.db.add(self.item)
        self.db.flush()
        self.categoria = obtener_o_crear_categoria_inventario(self.db, "Bebidas")
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_elimina_insumo_sin_referencias(self):
        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "ELIMINADO"
        )
        eliminar_insumo_inventario(self.db, self.item.id_inventario)

        self.assertIsNone(self.db.get(inventario, self.item.id_inventario))

    def test_no_permite_eliminar_definitivamente_un_insumo_activo(self):
        with self.assertRaisesRegex(ValueError, "inhabilita el insumo"):
            eliminar_insumo_inventario(self.db, self.item.id_inventario)

    def test_inhabilita_y_habilita_un_insumo(self):
        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "INACTIVO"
        )
        self.assertEqual(self.item.estado, "INACTIVO")

        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "ACTIVO"
        )
        self.assertEqual(self.item.estado, "ACTIVO")

    def test_eliminar_insumo_lo_marca_sin_borrarlo(self):
        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "ELIMINADO"
        )

        self.assertIsNotNone(self.db.get(inventario, self.item.id_inventario))
        self.assertEqual(self.item.estado, "ELIMINADO")

    def test_bloquea_eliminacion_si_un_producto_de_menu_lo_usa(self):
        producto = productos(
            nombre="Gaseosa personal",
            precio=4000,
            stock=0,
            id_categoria=self.categoria_menu.id_categoria,
            id_inventario=self.item.id_inventario,
        )
        self.db.add(producto)
        self.db.commit()
        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "INACTIVO"
        )

        with self.assertRaisesRegex(ValueError, "productos del menú"):
            eliminar_insumo_inventario(self.db, self.item.id_inventario)

        self.assertIsNotNone(self.db.get(inventario, self.item.id_inventario))

    def test_bloquea_eliminacion_si_hay_compras_historicas(self):
        self.db.add(
            detalles_compras(
                cantidad=2,
                precio=1000,
                subtotal=2000,
                id_inventario=self.item.id_inventario,
            )
        )
        self.db.commit()
        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "INACTIVO"
        )

        with self.assertRaisesRegex(ValueError, "historial"):
            eliminar_insumo_inventario(self.db, self.item.id_inventario)

        self.assertIsNotNone(self.db.get(inventario, self.item.id_inventario))

    def test_categoria_solo_se_elimina_cuando_no_tiene_insumos(self):
        cambiar_estado_categoria_inventario(
            self.db, self.categoria.id_categoria_inventario, "INACTIVO"
        )
        with self.assertRaisesRegex(ValueError, "todos los insumos"):
            eliminar_categoria_inventario(
                self.db, self.categoria.id_categoria_inventario
            )

        cambiar_estado_insumo_inventario(
            self.db, self.item.id_inventario, "ELIMINADO"
        )
        eliminar_insumo_inventario(self.db, self.item.id_inventario)
        eliminar_categoria_inventario(
            self.db, self.categoria.id_categoria_inventario
        )

        self.assertIsNone(
            self.db.get(categorias_inventario, self.categoria.id_categoria_inventario)
        )

    def test_no_permite_eliminar_definitivamente_una_categoria_activa(self):
        with self.assertRaisesRegex(ValueError, "inhabilita la categoría"):
            eliminar_categoria_inventario(
                self.db, self.categoria.id_categoria_inventario
            )

    def test_inhabilita_y_habilita_una_categoria(self):
        cambiar_estado_categoria_inventario(
            self.db, self.categoria.id_categoria_inventario, "INACTIVO"
        )
        self.assertEqual(self.categoria.estado, "INACTIVO")

        cambiar_estado_categoria_inventario(
            self.db, self.categoria.id_categoria_inventario, "ACTIVO"
        )
        self.assertEqual(self.categoria.estado, "ACTIVO")

    def test_eliminar_categoria_mantiene_registro_para_restaurarlo(self):
        cambiar_estado_categoria_inventario(
            self.db, self.categoria.id_categoria_inventario, "ELIMINADO"
        )

        self.assertIsNotNone(
            self.db.get(categorias_inventario, self.categoria.id_categoria_inventario)
        )
        self.assertEqual(self.categoria.estado, "ELIMINADO")

    def test_sincroniza_categorias_ya_existentes_en_inventario(self):
        self.db.delete(self.categoria)
        self.db.flush()
        self.db.expire_all()

        sincronizar_categorias_inventario(self.db)
        self.db.flush()

        self.assertEqual(
            self.db.query(categorias_inventario.nombre).all(),
            [("Bebidas",)],
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import catalogo_proveedores, categorias, inventario, productos, proveedores
from services.inventario_service import (
    buscar_inventario_para_producto,
    sincronizar_inventario_catalogo_proveedores,
    vincular_producto_menu,
)
from services.proveedores_service import sembrar_catalogo_proveedores


class InventarioServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.categoria_menu = categorias(nombre="Bebidas Frías", estado="ACTIVO")
        self.db.add(self.categoria_menu)
        self.db.flush()
        self.producto = productos(
            nombre="Gaseosa Cola",
            precio=4000,
            stock=0,
            id_categoria=self.categoria_menu.id_categoria,
        )
        self.db.add(self.producto)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def crear_item_inventario(self, nombre="Gaseosa Cola", categoria="Bebidas Frías"):
        item = inventario(
            nombre=nombre,
            categoria=categoria,
            unidad_medida="unidad",
            cantidad=10,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        self.db.add(item)
        self.db.flush()
        return item

    def test_categoria_y_nombre_coincidentes_vinculan_producto_automaticamente(self):
        item = self.crear_item_inventario(
            nombre="  gaseosa cola ",
            categoria="bebidas frias",
        )

        self.assertTrue(vincular_producto_menu(self.db, item))
        self.assertEqual(self.producto.id_inventario, item.id_inventario)
        self.assertIs(
            buscar_inventario_para_producto(
                self.db,
                "Gaseosa Cola",
                "Bebidas Frías",
            ),
            item,
        )

    def test_mismo_nombre_vincula_aunque_la_categoria_sea_distinta(self):
        item = self.crear_item_inventario(categoria="Bebidas")

        self.assertTrue(vincular_producto_menu(self.db, item))
        self.assertEqual(self.producto.id_inventario, item.id_inventario)

    def test_marca_en_parentesis_se_vincula_por_nombre_individual(self):
        self.producto.nombre = "Cerveza Nacional (Poker, Águila, Andina)"
        item = self.crear_item_inventario(
            nombre="Poker",
            categoria="Cervezas",
        )

        self.assertTrue(vincular_producto_menu(self.db, item))
        self.assertEqual(self.producto.id_inventario, item.id_inventario)

    def test_compara_nombres_ignorando_espacios_mayusculas_y_tildes(self):
        self.producto.nombre = "Gaseosa Águila"
        item = self.crear_item_inventario(
            nombre="gaseosaaguila",
            categoria="BEBIDASFRIAS",
        )

        self.assertTrue(vincular_producto_menu(self.db, item))
        self.assertEqual(self.producto.id_inventario, item.id_inventario)

    def test_no_vincula_si_hay_varios_articulos_con_el_mismo_nombre_y_categoria(self):
        self.crear_item_inventario()
        segundo_item = self.crear_item_inventario()

        self.assertIsNone(
            buscar_inventario_para_producto(
                self.db,
                "Gaseosa Cola",
                "Bebidas Frías",
            )
        )
        self.assertFalse(vincular_producto_menu(self.db, segundo_item))
        self.assertIsNone(self.producto.id_inventario)

    def test_no_reemplaza_un_vinculo_existente_a_otro_articulo(self):
        item_vinculado = self.crear_item_inventario(nombre="Cola personal")
        item_coincidente = self.crear_item_inventario()
        self.producto.id_inventario = item_vinculado.id_inventario
        self.db.flush()

        self.assertFalse(vincular_producto_menu(self.db, item_coincidente))
        self.assertEqual(self.producto.id_inventario, item_vinculado.id_inventario)

    def test_sincroniza_articulos_iguales_separados_por_proveedor_idempotentemente(self):
        proveedores_prueba = [
            proveedores(nombre="Proveedor A", que_provee="Bebidas", estado="ACTIVO"),
            proveedores(nombre="Proveedor B", que_provee="Bebidas", estado="ACTIVO"),
        ]
        self.db.add_all(proveedores_prueba)
        self.db.flush()
        self.db.add_all(
            [
                catalogo_proveedores(
                    id_proveedor=proveedor.id_proveedor,
                    grupo="Aguas",
                    nombre="Águila Original - Vidrio",
                    detalles="Botella de vidrio.",
                    precio_unitario=None,
                )
                for proveedor in proveedores_prueba
            ]
        )
        self.db.commit()

        self.assertEqual(sincronizar_inventario_catalogo_proveedores(self.db), 2)
        self.db.commit()
        self.assertEqual(sincronizar_inventario_catalogo_proveedores(self.db), 0)
        items = (
            self.db.query(inventario)
            .filter(inventario.nombre == "Águila Original - Vidrio")
            .order_by(inventario.id_proveedor)
            .all()
        )

        self.assertEqual(len(items), 2)
        self.assertNotEqual(items[0].id_proveedor, items[1].id_proveedor)
        self.assertTrue(all(item.cantidad == 0 for item in items))
        self.assertTrue(all(item.costo_unitario == 0 for item in items))
        self.assertTrue(all(not vincular_producto_menu(self.db, item) for item in items))

    def test_sincroniza_snacks_y_separa_las_variantes_del_catalogo(self):
        sembrar_catalogo_proveedores(self.db)

        creados = sincronizar_inventario_catalogo_proveedores(self.db)
        self.db.commit()

        todo_rico = (
            self.db.query(inventario)
            .filter(inventario.nombre == "Todo Rico BBQ")
            .one()
        )
        self.assertEqual(todo_rico.categoria, "Snacks")
        self.assertEqual(todo_rico.cantidad, 0)
        self.assertEqual(todo_rico.costo_unitario, 0)
        self.assertIsNotNone(todo_rico.id_proveedor)
        self.assertEqual(
            self.db.query(inventario)
            .filter(inventario.nombre == "Todo Rico")
            .count(),
            0,
        )
        self.assertGreater(creados, 0)
        self.assertEqual(sincronizar_inventario_catalogo_proveedores(self.db), 0)


if __name__ == "__main__":
    unittest.main()

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    categorias,
    detalle_ventas,
    estados_productos,
    inventario,
    productos,
)
from services.inventario_service import sincronizar_inventario_catalogo_proveedores
from services.menu_catalog_service import BEBIDAS_CERVEZA, sembrar_menu
from services.proveedores_service import sembrar_catalogo_proveedores


class MenuCatalogServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.activo = estados_productos(nombre="ACTIVO")
        self.inactivo = estados_productos(nombre="INACTIVO")
        self.db.add_all([self.activo, self.inactivo])
        self.db.flush()
        self.burgers = categorias(nombre="Burgers", estado="ACTIVO")
        self.fast_food = categorias(nombre="Fast Food", estado="ACTIVO")
        self.db.add_all([self.burgers, self.fast_food])
        self.db.flush()
        self.especial = productos(
            nombre="Especial",
            precio=18000,
            stock=17,
            descripcion="Descripción anterior",
            id_categoria=self.burgers.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        self.super_especial = productos(
            nombre="Súper Especial",
            precio=24000,
            stock=12,
            descripcion="Versión anterior",
            id_categoria=self.burgers.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        self.super_especial_duplicado = productos(
            nombre="Super Especial",
            precio=24000,
            stock=4,
            descripcion="Fila duplicada antigua",
            id_categoria=self.burgers.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        self.cazuela = productos(
            nombre="Cazuela de Papas",
            precio=15000,
            stock=8,
            descripcion="Producto anterior",
            id_categoria=self.fast_food.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        self.filadelfia_legacy = productos(
            nombre="Mixta Añadida",
            precio=22000,
            stock=6,
            descripcion="Descripción anterior",
            id_categoria=self.burgers.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        self.db.add_all([
            self.especial,
            self.super_especial,
            self.super_especial_duplicado,
            self.cazuela,
            self.filadelfia_legacy,
        ])
        self.db.commit()
        self.detalle_historico = detalle_ventas(
            cantidad=1,
            precio_unitario=22000,
            subtotal=22000,
            id_venta=1,
            id_producto=self.filadelfia_legacy.id_producto,
        )
        self.db.add(self.detalle_historico)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_seed_actualiza_catalogo_sin_alterar_stock_y_es_repetible(self):
        cantidad = sembrar_menu(self.db)
        self.db.refresh(self.especial)

        self.assertEqual(self.especial.precio, 26000)
        self.assertEqual(self.especial.stock, 17)
        self.assertIn("doble queso mozzarella", self.especial.descripcion)
        self.assertEqual(cantidad, sembrar_menu(self.db))
        self.db.refresh(self.super_especial)
        self.db.refresh(self.super_especial_duplicado)
        self.assertEqual(self.super_especial.precio, 28000)
        self.assertEqual(self.super_especial.id_estado, self.activo.id_estado_producto)
        self.assertEqual(
            self.super_especial_duplicado.id_estado,
            self.inactivo.id_estado_producto,
        )
        self.assertEqual(
            self.db.query(productos)
            .filter(productos.nombre == "Especial", productos.id_categoria == self.burgers.id_categoria)
            .count(),
            1,
        )
        self.db.refresh(self.cazuela)
        self.assertEqual(self.cazuela.id_estado, self.inactivo.id_estado_producto)
        self.db.refresh(self.filadelfia_legacy)
        self.db.refresh(self.detalle_historico)
        self.assertEqual(self.filadelfia_legacy.nombre, "Sándwich Filadelfia")
        self.assertEqual(self.detalle_historico.nombre_producto, "Mixta Añadida")
        bebidas_frias = self.db.query(categorias).filter_by(nombre="Bebidas Frías").first()
        for nombre, precio, descripcion in BEBIDAS_CERVEZA:
            bebida = (
                self.db.query(productos)
                .filter_by(nombre=nombre, id_categoria=bebidas_frias.id_categoria)
                .one()
            )
            if precio is None:
                self.assertEqual(bebida.precio, 0)
                self.assertEqual(bebida.id_estado, self.inactivo.id_estado_producto)
                self.assertIn("Pendiente definir precio", bebida.descripcion)
            else:
                self.assertEqual(bebida.precio, precio)
                self.assertEqual(bebida.id_estado, self.activo.id_estado_producto)
        self.assertIsNotNone(
            self.db.query(categorias).filter(categorias.nombre == "Mazorcadas").first()
        )

    def test_seed_agrega_catalogo_de_proveedores_y_desactiva_nombres_genericos(self):
        bebidas_frias = categorias(
            nombre="Bebidas Frías",
            estado="ACTIVO",
        )
        self.db.add(bebidas_frias)
        self.db.flush()
        bebida_generica = productos(
            nombre="Bebidas 250 ml",
            precio=3000,
            stock=0,
            id_categoria=bebidas_frias.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        bebida_vendida = productos(
            nombre="Bebidas 350 ml",
            precio=4000,
            stock=0,
            id_categoria=bebidas_frias.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        club_colombia_antiguo = productos(
            nombre="Club Colombia Negra",
            precio=4000,
            stock=0,
            id_categoria=bebidas_frias.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        club_colombia_actual = productos(
            nombre="Club Colombia Negra",
            precio=6200,
            stock=0,
            id_categoria=bebidas_frias.id_categoria,
            id_estado=self.activo.id_estado_producto,
        )
        self.db.add_all(
            [
                bebida_generica,
                bebida_vendida,
                club_colombia_antiguo,
                club_colombia_actual,
            ]
        )
        self.db.flush()
        detalle_generico = detalle_ventas(
            cantidad=1,
            precio_unitario=4000,
            subtotal=4000,
            id_venta=1,
            id_producto=bebida_vendida.id_producto,
            nombre_producto="Bebidas 350 ml",
        )
        self.db.add(detalle_generico)
        self.db.commit()

        sembrar_catalogo_proveedores(self.db)
        sincronizar_inventario_catalogo_proveedores(self.db)
        sembrar_menu(self.db)

        snacks = self.db.query(categorias).filter_by(nombre="Snacks").one()
        todo_rico = (
            self.db.query(productos)
            .filter(
                productos.nombre == "Todo Rico BBQ",
                productos.id_categoria == snacks.id_categoria,
            )
            .one()
        )
        self.assertEqual(todo_rico.precio, 0)
        self.assertEqual(todo_rico.id_estado, self.inactivo.id_estado_producto)
        self.assertIsNotNone(todo_rico.id_inventario)
        self.assertIsNotNone(self.db.get(inventario, todo_rico.id_inventario))

        bebida_generica = self.db.get(productos, bebida_generica.id_producto)
        bebida_vendida = self.db.get(productos, bebida_vendida.id_producto)
        detalle_generico = self.db.get(detalle_ventas, detalle_generico.id_detalle)
        self.assertEqual(
            bebida_generica.id_estado,
            self.inactivo.id_estado_producto,
        )
        self.assertEqual(
            bebida_vendida.id_estado,
            self.inactivo.id_estado_producto,
        )
        self.assertEqual(detalle_generico.nombre_producto, "Bebidas 350 ml")

        productos_club_colombia = (
            self.db.query(productos)
            .filter(
                productos.nombre == "Club Colombia Negra",
                productos.id_categoria == bebidas_frias.id_categoria,
            )
            .all()
        )
        activos = [
            producto
            for producto in productos_club_colombia
            if producto.id_estado == self.activo.id_estado_producto
        ]
        self.assertEqual(len(activos), 1)
        self.assertEqual(activos[0].precio, 6200)

        self.assertEqual(sembrar_menu(self.db), sembrar_menu(self.db))


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import detalle_ventas, inventario, productos
from services.venta_service import registrar_venta


class VentaInventarioVinculadoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.bebidas = inventario(
            nombre="Gaseosa lata",
            categoria="Bebidas",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        self.session.add(self.bebidas)
        self.session.flush()

        self.productos_menu = [
            productos(
                nombre="Gaseosa menú 1",
                precio=4000,
                stock=0,
                id_inventario=self.bebidas.id_inventario,
            ),
            productos(
                nombre="Gaseosa menú 2",
                precio=5000,
                stock=0,
                id_inventario=self.bebidas.id_inventario,
            ),
        ]
        self.session.add_all(self.productos_menu)
        self.session.commit()
        self.caja = SimpleNamespace(id_caja=1)

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_venta_descuenta_existencia_compartida_entre_productos_menu(self):
        venta = registrar_venta(
            self.session,
            [
                {
                    "id_producto": self.productos_menu[0].id_producto,
                    "nombre": self.productos_menu[0].nombre,
                    "precio": self.productos_menu[0].precio,
                    "cantidad": 2,
                },
                {
                    "id_producto": self.productos_menu[1].id_producto,
                    "nombre": self.productos_menu[1].nombre,
                    "precio": self.productos_menu[1].precio,
                    "cantidad": 1,
                },
            ],
            metodo_id=1,
            caja_actual=self.caja,
        )

        self.assertIsNotNone(venta.id_venta)
        self.assertEqual(
            self.session.get(inventario, self.bebidas.id_inventario).cantidad,
            2,
        )
        self.assertEqual(
            self.session.query(detalle_ventas)
            .filter(detalle_ventas.id_venta == venta.id_venta)
            .count(),
            2,
        )

    def test_venta_rechaza_exceso_combinado_del_mismo_insumo(self):
        with self.assertRaisesRegex(ValueError, "No hay suficiente inventario"):
            registrar_venta(
                self.session,
                [
                    {
                        "id_producto": self.productos_menu[0].id_producto,
                        "nombre": self.productos_menu[0].nombre,
                        "precio": self.productos_menu[0].precio,
                        "cantidad": 3,
                    },
                    {
                        "id_producto": self.productos_menu[1].id_producto,
                        "nombre": self.productos_menu[1].nombre,
                        "precio": self.productos_menu[1].precio,
                        "cantidad": 3,
                    },
                ],
                metodo_id=1,
                caja_actual=self.caja,
            )

        self.assertEqual(
            self.session.get(inventario, self.bebidas.id_inventario).cantidad,
            5,
        )

    def test_venta_rechaza_insumo_inhabilitado(self):
        self.bebidas.estado = "ELIMINADO"
        self.session.commit()

        with self.assertRaisesRegex(ValueError, "está inhabilitado"):
            registrar_venta(
                self.session,
                [{
                    "id_producto": self.productos_menu[0].id_producto,
                    "nombre": self.productos_menu[0].nombre,
                    "precio": self.productos_menu[0].precio,
                    "cantidad": 1,
                }],
                metodo_id=1,
                caja_actual=self.caja,
            )

        self.assertEqual(
            self.session.get(inventario, self.bebidas.id_inventario).cantidad,
            5,
        )

    def test_venta_descuenta_articulo_coincidente_por_nombre_sin_vinculo_previo(self):
        item = inventario(
            nombre="Gaseosa sin azúcar",
            categoria="Refrigerados",
            unidad_medida="unidad",
            cantidad=4,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        producto = productos(
            nombre="Gaseosa sin azúcar",
            precio=4000,
            stock=0,
        )
        self.session.add_all([item, producto])
        self.session.commit()

        registrar_venta(
            self.session,
            [{
                "id_producto": producto.id_producto,
                "nombre": producto.nombre,
                "precio": producto.precio,
                "cantidad": 2,
            }],
            metodo_id=1,
            caja_actual=self.caja,
        )

        self.assertEqual(self.session.get(inventario, item.id_inventario).cantidad, 2)
        self.assertEqual(producto.id_inventario, item.id_inventario)

    def test_venta_descuenta_marca_individual_en_nombre_compuesto_de_cerveza(self):
        item = inventario(
            nombre="Poker",
            categoria="Cervezas",
            unidad_medida="unidad",
            cantidad=6,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        producto = productos(
            nombre="Cerveza Nacional (Poker, Águila, Andina)",
            precio=4000,
            stock=0,
        )
        self.session.add_all([item, producto])
        self.session.commit()

        registrar_venta(
            self.session,
            [{
                "id_producto": producto.id_producto,
                "nombre": producto.nombre,
                "precio": producto.precio,
                "cantidad": 2,
            }],
            metodo_id=1,
            caja_actual=self.caja,
        )

        self.assertEqual(self.session.get(inventario, item.id_inventario).cantidad, 4)
        self.assertEqual(producto.id_inventario, item.id_inventario)

    def test_producto_generico_descuenta_cada_variante_seleccionada(self):
        aguila = inventario(
            nombre="Águila",
            categoria="Cervezas",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        andina = inventario(
            nombre="Andina",
            categoria="Cervezas",
            unidad_medida="unidad",
            cantidad=4,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        producto = productos(
            nombre="Cerveza Nacional (Poker, Águila, Andina)",
            precio=4000,
            stock=0,
        )
        self.session.add_all([aguila, andina, producto])
        self.session.commit()

        registrar_venta(
            self.session,
            [
                {
                    "id_producto": producto.id_producto,
                    "id_inventario": aguila.id_inventario,
                    "nombre": "Cerveza Nacional — Águila",
                    "precio": producto.precio,
                    "cantidad": 2,
                },
                {
                    "id_producto": producto.id_producto,
                    "id_inventario": andina.id_inventario,
                    "nombre": "Cerveza Nacional — Andina",
                    "precio": producto.precio,
                    "cantidad": 1,
                },
            ],
            metodo_id=1,
            caja_actual=self.caja,
        )

        self.assertEqual(self.session.get(inventario, aguila.id_inventario).cantidad, 3)
        self.assertEqual(self.session.get(inventario, andina.id_inventario).cantidad, 3)

    def test_venta_descuenta_ignorando_espacios_mayusculas_y_tildes(self):
        item = inventario(
            nombre="GASEOSAAGUILA",
            categoria="Bebidas",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=1,
            costo_unitario=2000,
            estado="ACTIVO",
        )
        producto = productos(
            nombre="Gaseosa Águila",
            precio=4000,
            stock=0,
        )
        self.session.add_all([item, producto])
        self.session.commit()

        registrar_venta(
            self.session,
            [{
                "id_producto": producto.id_producto,
                "nombre": producto.nombre,
                "precio": producto.precio,
                "cantidad": 1,
            }],
            metodo_id=1,
            caja_actual=self.caja,
        )

        self.assertEqual(self.session.get(inventario, item.id_inventario).cantidad, 4)
        self.assertEqual(producto.id_inventario, item.id_inventario)


if __name__ == "__main__":
    unittest.main()

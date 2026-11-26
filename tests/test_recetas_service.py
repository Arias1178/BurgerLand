import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    categorias,
    categorias_inventario,
    catalogo_proveedores,
    estados_productos,
    inventario,
    receta_producto,
    proveedores,
    productos,
)
from services.menu_catalog_service import sembrar_menu
from services.recetas_service import (
    PROVEEDORES_INGREDIENTES,
    extraer_ingredientes_descripcion,
    sembrar_inventario_y_recetas_menu,
)


class RecetasServiceTests(unittest.TestCase):
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

    def test_parser_respects_double_portions_and_menu_weights(self):
        componentes = {
            ingrediente.nombre: cantidad
            for ingrediente, cantidad in extraer_ingredientes_descripcion(
                "Pan, doble carne, doble queso mozzarella, "
                "300 g de alitas, 150 g de papas a la francesa y "
                "3 huevos de codorniz"
            )
        }

        self.assertEqual(componentes["Pan de hamburguesa"], 1)
        self.assertEqual(componentes["Carne de la casa"], 280)
        self.assertEqual(componentes["Queso mozzarella"], 2)
        self.assertEqual(componentes["Alitas de pollo"], 300)
        self.assertEqual(componentes["Papas a la francesa"], 150)
        self.assertEqual(componentes["Huevo de codorniz"], 3)

    def test_menu_seed_creates_supplier_backed_ingredients_and_recipes_idempotently(self):
        self.db.add_all(
            [
                estados_productos(nombre="ACTIVO"),
                estados_productos(nombre="INACTIVO"),
            ]
        )
        self.db.commit()
        sembrar_menu(self.db)

        creadas = sembrar_inventario_y_recetas_menu(self.db)

        self.assertGreater(creadas, 0)
        self.assertGreater(self.db.query(proveedores).count(), 0)
        self.assertGreater(self.db.query(categorias_inventario).count(), 0)
        inventario_proveedores = (
            self.db.query(inventario)
            .join(proveedores, proveedores.id_proveedor == inventario.id_proveedor)
            .filter(
                proveedores.nombre.in_({
                    nombre for nombre, _ in PROVEEDORES_INGREDIENTES
                })
            )
            .all()
        )
        catalogo_proveedor = (
            self.db.query(catalogo_proveedores)
            .filter(
                catalogo_proveedores.id_proveedor.in_(
                    {item.id_proveedor for item in inventario_proveedores}
                )
            )
            .all()
        )
        self.assertEqual(
            {
                (articulo.id_proveedor, articulo.nombre)
                for articulo in catalogo_proveedor
            },
            {
                (item.id_proveedor, item.nombre)
                for item in inventario_proveedores
            },
        )
        pan_catalogo = next(
            articulo
            for articulo in catalogo_proveedor
            if articulo.nombre == "Pan de hamburguesa"
        )
        self.assertIn("unidad", pan_catalogo.detalles)
        self.assertTrue(
            all(
                item.cantidad == 0 and item.id_proveedor is not None
                for item in self.db.query(inventario).all()
                if item.id_proveedor is not None
            )
        )
        burger = (
            self.db.query(productos)
            .filter(productos.nombre == "Especial")
            .one()
        )
        receta = (
            self.db.query(receta_producto, inventario)
            .join(
                inventario,
                inventario.id_inventario == receta_producto.id_inventario,
            )
            .filter(receta_producto.id_producto == burger.id_producto)
            .all()
        )
        ingredientes = {
            (item.nombre, receta.cantidad, receta.grupo_opcion, receta.opcion)
            for receta, item in receta
        }
        self.assertIn(("Pan de hamburguesa", 1, None, None), ingredientes)
        self.assertIn(("Queso mozzarella", 2, None, None), ingredientes)
        self.assertIn(
            ("Carne Koller", 280, "proteina_burger", "Koller"),
            ingredientes,
        )
        pechuga_napolitana = (
            self.db.query(productos)
            .filter(productos.nombre == "Pechuga Napolitana")
            .one()
        )
        receta_pechuga = (
            self.db.query(receta_producto, inventario)
            .join(
                inventario,
                inventario.id_inventario == receta_producto.id_inventario,
            )
            .filter(
                receta_producto.id_producto == pechuga_napolitana.id_producto,
                inventario.nombre == "Pechuga de pollo",
            )
            .one()
        )
        self.assertEqual(receta_pechuga[0].cantidad, 300)
        productos_sin_receta = (
            self.db.query(productos.nombre)
            .join(categorias, productos.id_categoria == categorias.id_categoria)
            .filter(categorias.nombre.in_({
                "Burgers",
                "Sándwiches",
                "Hot Dogs",
                "Fast Food",
                "Mazorcadas",
                "Combos",
                "Para Compartir",
                "Menú Infantil",
                "Adiciones",
                "A la Plancha",
            }))
            .filter(
                ~self.db.query(receta_producto.id_receta)
                .filter(receta_producto.id_producto == productos.id_producto)
                .exists()
            )
            .all()
        )
        self.assertEqual(productos_sin_receta, [])

        catalogo_count = self.db.query(catalogo_proveedores).count()
        pan_catalogo.precio_unitario = 1234
        self.db.commit()
        self.assertEqual(sembrar_inventario_y_recetas_menu(self.db), 0)
        self.assertEqual(
            self.db.query(catalogo_proveedores).count(),
            catalogo_count,
        )
        self.db.refresh(pan_catalogo)
        self.assertEqual(pan_catalogo.precio_unitario, 1234)


if __name__ == "__main__":
    unittest.main()

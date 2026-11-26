import unittest
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import categorias, estados_productos, productos, rol
from views.menu import menu_view


class MenuViewTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        with self.session_factory() as db:
            admin_role = rol(nombre="ADMIN")
            estado_activo = estados_productos(nombre="ACTIVO")
            categoria = categorias(nombre="Pruebas", estado="ACTIVO")
            db.add_all([admin_role, estado_activo, categoria])
            db.flush()
            self.producto = productos(
                nombre="Producto propio",
                precio=5000,
                stock=0,
                descripcion=None,
                id_categoria=categoria.id_categoria,
                id_estado=estado_activo.id_estado_producto,
            )
            db.add(self.producto)
            db.commit()
            self.producto_id = self.producto.id_producto
            self.admin_role_id = admin_role.id_rol

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _buscar_controles(self, control, tipo):
        if isinstance(control, tipo):
            yield control
        for hijo in getattr(control, "controls", []) or []:
            yield from self._buscar_controles(hijo, tipo)
        contenido = getattr(control, "content", None)
        if contenido is not None:
            yield from self._buscar_controles(contenido, tipo)

    def test_editar_nombre_de_producto_sin_descripcion(self):
        page = MagicMock(spec=ft.Page)
        with patch("views.menu.SessionLocal", self.session_factory):
            view = menu_view(
                page,
                ft.Container(),
                usuario_actual=MagicMock(id_rol=self.admin_role_id),
            )

            botones_editar = [
                boton
                for boton in self._buscar_controles(view, ft.TextButton)
                if boton.content == "Editar"
            ]
            botones_editar[-1].on_click(None)

            dialogo = page.show_dialog.call_args.args[0]
            campos = list(self._buscar_controles(dialogo.content, ft.TextField))
            campos[0].value = "Nombre actualizado"
            dialogo.actions[1].on_click(None)

            with self.session_factory() as db:
                producto = db.get(productos, self.producto_id)
                self.assertEqual(producto.nombre, "Nombre actualizado")
                self.assertIsNone(producto.descripcion)


if __name__ == "__main__":
    unittest.main()

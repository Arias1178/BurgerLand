import unittest
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import Usuario, rol
from views.navbar import construir_navbar
from views.usuarios import usuarios_view


class UsuariosViewTests(unittest.TestCase):
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
            worker_role = rol(nombre="VENDEDOR")
            db.add_all([admin_role, worker_role])
            db.flush()
            self.admin = Usuario(
                nombre="Admin",
                correo="admin@burgerland.test",
                contraseña="hash",
                id_rol=admin_role.id_rol,
            )
            db.add(self.admin)
            db.commit()
            self.admin_id = self.admin.id_usuario

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _buscar_controles(self, control, tipo):
        if isinstance(control, tipo):
            yield control
        for hijo in getattr(control, "controls", []):
            yield from self._buscar_controles(hijo, tipo)
        contenido = getattr(control, "content", None)
        if contenido is not None:
            yield from self._buscar_controles(contenido, tipo)

    def test_admin_can_open_user_roles_screen_and_navbar(self):
        page = MagicMock(spec=ft.Page)
        with patch("views.usuarios.SessionLocal", self.session_factory):
            view = usuarios_view(
                page,
                ft.Container(),
                Usuario(
                    id_usuario=self.admin_id,
                    id_rol=1,
                    nombre="Admin",
                    correo="admin@burgerland.test",
                    contraseña="hash",
                ),
            )

        self.assertIsInstance(view, ft.Column)
        listas = list(self._buscar_controles(view, ft.ListView))
        self.assertEqual(len(listas), 1)
        self.assertEqual(len(listas[0].controls), 1)
        navbar = construir_navbar(
            page,
            "usuarios",
            mostrar_inicio=lambda: None,
            mostrar_venta=lambda: None,
            mostrar_historial=lambda: None,
            mostrar_menu=lambda: None,
            mostrar_inventario=lambda: None,
            mostrar_proveedores=lambda: None,
            mostrar_compras=lambda: None,
            mostrar_informes=lambda: None,
            mostrar_usuarios=lambda: None,
        )
        self.assertIsInstance(navbar, ft.Container)

    def test_user_search_filters_the_list_and_shows_empty_state(self):
        page = MagicMock(spec=ft.Page)
        with patch("views.usuarios.SessionLocal", self.session_factory):
            view = usuarios_view(
                page,
                ft.Container(),
                Usuario(
                    id_usuario=self.admin_id,
                    id_rol=1,
                    nombre="Admin",
                    correo="admin@burgerland.test",
                    contraseña="hash",
                ),
            )

        campos_busqueda = list(self._buscar_controles(view, ft.TextField))
        self.assertEqual(len(campos_busqueda), 1)
        campos_busqueda[0].value = "no-existe"
        campos_busqueda[0].on_change(None)

        textos = [
            control.value
            for control in self._buscar_controles(view, ft.Text)
            if control.value
        ]
        self.assertIn("0 de 1 usuarios", textos)
        self.assertIn("No encontramos usuarios", textos)


if __name__ == "__main__":
    unittest.main()

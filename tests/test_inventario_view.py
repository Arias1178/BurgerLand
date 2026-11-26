import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import categorias_inventario, rol
from views.inventario import inventario_view


class InventarioViewTests(unittest.TestCase):
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
            db.add(admin_role)
            db.commit()
            self.admin_role_id = admin_role.id_rol

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _find_button(self, controls, label):
        for control in controls:
            if isinstance(control, (ft.Button, ft.TextButton)):
                content = getattr(control, "content", None)
                text = getattr(content, "value", content)
                if text == label:
                    return control
            children = list(getattr(control, "controls", []) or [])
            content = getattr(control, "content", None)
            if content is not None:
                children.append(content)
            found = self._find_button(children, label)
            if found is not None:
                return found
        return None

    def test_admin_can_create_inventory_category_from_category_dialog(self):
        page = MagicMock(spec=ft.Page)
        admin = SimpleNamespace(id_rol=self.admin_role_id)

        with patch("views.inventario.SessionLocal", self.session_factory):
            view = inventario_view(page, ft.Container(), usuario_actual=admin)
            categories_button = self._find_button([view], "Categorías")
            self.assertIsNotNone(categories_button)
            categories_button.on_click(None)

            categories_dialog = page.show_dialog.call_args.args[0]
            create_button = self._find_button(
                categories_dialog.actions,
                "Crear categoría",
            )
            self.assertIsNotNone(create_button)
            create_button.on_click(None)

            create_dialog = page.show_dialog.call_args.args[0]
            field = next(
                control
                for control in create_dialog.content.controls
                if isinstance(control, ft.TextField)
            )
            field.value = "Empaques"
            submit_button = self._find_button(create_dialog.actions, "Crear")
            self.assertIsNotNone(submit_button)
            submit_button.on_click(None)

            with self.session_factory() as db:
                category = (
                    db.query(categorias_inventario)
                    .filter_by(nombre="Empaques")
                    .one()
                )
                self.assertEqual(category.estado, "ACTIVO")

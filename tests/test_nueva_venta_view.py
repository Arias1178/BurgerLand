import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import mesas, productos
from services.cuenta_service import guardar_cuenta_abierta
from views.nueva_venta_view import nueva_venta_view


class NuevaVentaViewTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        with self.session_factory() as db:
            mesa = mesas(numero=1, estado="LIBRE")
            db.add(mesa)
            db.commit()
            self.mesa_id = mesa.id_mesa

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _find_control(self, control, control_type, label):
        if isinstance(control, control_type) and getattr(control, "label", None) == label:
            return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_control(child, control_type, label)
            if found is not None:
                return found
        return None

    def _find_button(self, control, label):
        if isinstance(control, ft.Button):
            texto = getattr(control.content, "value", None)
            if texto == label:
                return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_button(child, label)
            if found is not None:
                return found
        return None

    def _find_text(self, control, value):
        if isinstance(control, ft.Text) and control.value == value:
            return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_text(child, value)
            if found is not None:
                return found
        return None

    def _find_icon_button(self, control, tooltip):
        if isinstance(control, ft.IconButton) and control.tooltip == tooltip:
            return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_icon_button(child, tooltip)
            if found is not None:
                return found
        return None

    def test_table_selector_back_arrow_returns_to_sales_view(self):
        page = MagicMock(spec=ft.Page)
        on_back = MagicMock()
        with patch("views.nueva_venta_view.SessionLocal", self.session_factory):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=on_back,
                caja_actual=SimpleNamespace(id_caja=1),
            )

        boton_volver = self._find_icon_button(view, "Volver a ventas")
        self.assertIsNotNone(boton_volver)
        boton_volver.on_click(None)
        on_back.assert_called_once_with()

    def test_product_view_back_arrow_returns_to_table_selector(self):
        page = MagicMock(spec=ft.Page)
        on_back = MagicMock()
        with patch("views.nueva_venta_view.SessionLocal", self.session_factory):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
                on_volver_a_mesas=on_back,
            )

        boton_volver = self._find_icon_button(view, "Volver a seleccionar mesa")
        self.assertIsNotNone(boton_volver)
        boton_volver.on_click(None)
        on_back.assert_called_once_with()

    def test_leaving_sale_with_cart_requires_confirmation(self):
        with self.session_factory() as db:
            producto = productos(
                nombre="Hamburguesa",
                precio=12_000,
                stock=0,
            )
            db.add(producto)
            db.commit()
            cuenta = guardar_cuenta_abierta(
                db,
                [
                    {
                        "id_producto": producto.id_producto,
                        "nombre": producto.nombre,
                        "precio": producto.precio,
                        "cantidad": 1,
                    }
                ],
                self.mesa_id,
            )
            cuenta_id = cuenta.id_cuenta

        page = MagicMock(spec=ft.Page)
        on_back = MagicMock()
        with patch("views.nueva_venta_view.SessionLocal", self.session_factory):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_elegida=True,
                cuenta_id=cuenta_id,
                on_volver_a_mesas=on_back,
            )

        boton_volver = self._find_icon_button(view, "Volver a seleccionar mesa")
        boton_volver.on_click(None)
        on_back.assert_not_called()
        dialogo = page.show_dialog.call_args.args[0]
        self.assertEqual(dialogo.title.value, "¿Salir de la venta?")
        dialogo.actions[1].on_click(None)
        on_back.assert_called_once_with()

    def test_selecting_a_table_opens_the_sale_view(self):
        page = MagicMock(spec=ft.Page)

        with patch(
            "views.nueva_venta_view.SessionLocal",
            self.session_factory,
        ):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
            )

        self.assertIsInstance(view, ft.Column)
        phone_field = self._find_control(view, ft.TextField, "Celular del cliente")
        self.assertIsNotNone(phone_field)
        self.assertIsNone(phone_field.expand)
        self.assertEqual(phone_field.height, 56)
        self.assertEqual(phone_field.width, 220)

    def test_divide_button_remains_available_for_one_item_open_account(self):
        with self.session_factory() as db:
            producto = productos(
                nombre="Hamburguesa",
                precio=12_000,
                stock=0,
            )
            db.add(producto)
            db.commit()
            cuenta = guardar_cuenta_abierta(
                db,
                [
                    {
                        "id_producto": producto.id_producto,
                        "nombre": producto.nombre,
                        "precio": producto.precio,
                        "cantidad": 1,
                    }
                ],
                self.mesa_id,
            )
            cuenta_id = cuenta.id_cuenta

        page = MagicMock(spec=ft.Page)
        with patch(
            "views.nueva_venta_view.SessionLocal",
            self.session_factory,
        ):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
                cuenta_id=cuenta_id,
            )

        boton_dividir = self._find_button(view, "Dividir cuenta")
        self.assertIsNotNone(boton_dividir)
        self.assertTrue(boton_dividir.visible)

    def test_split_dialog_explains_options_and_shows_total(self):
        with self.session_factory() as db:
            producto = productos(
                nombre="Hamburguesa",
                precio=12_000,
                stock=0,
            )
            db.add(producto)
            db.commit()
            cuenta = guardar_cuenta_abierta(
                db,
                [
                    {
                        "id_producto": producto.id_producto,
                        "nombre": producto.nombre,
                        "precio": producto.precio,
                        "cantidad": 1,
                    }
                ],
                self.mesa_id,
            )
            cuenta_id = cuenta.id_cuenta

        page = MagicMock(spec=ft.Page)
        with patch(
            "views.nueva_venta_view.SessionLocal",
            self.session_factory,
        ):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
                cuenta_id=cuenta_id,
            )

        boton_dividir = self._find_button(view, "Dividir cuenta")
        boton_dividir.on_click(None)
        dialogo = page.show_dialog.call_args.args[0]
        self.assertEqual(dialogo.title.value, "Dividir cuenta")
        self.assertIsNotNone(
            self._find_text(
                dialogo.content,
                "Cada persona elige los productos o unidades que paga.",
            )
        )
        self.assertIsNotNone(
            self._find_text(
                dialogo.content,
                "Divide el total entre las personas automáticamente.",
            )
        )
        self.assertIsNotNone(
            self._find_text(
                dialogo.content,
                "Escribe cuánto paga cada persona; la suma debe dar el total.",
            )
        )
        self.assertIsNotNone(
            self._find_text(dialogo.content, "Total: $12.000")
        )


if __name__ == "__main__":
    unittest.main()

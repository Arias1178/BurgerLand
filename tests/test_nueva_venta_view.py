import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import flet as ft
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import categorias, mesas, productos, subcuentas
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
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False)
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

    def _find_button_containing_text(self, control, value):
        if isinstance(control, ft.Button) and self._find_text(control, value):
            return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_button_containing_text(child, value)
            if found is not None:
                return found
        return None

    def _find_clickable_container_containing_text(self, control, value):
        if (
            isinstance(control, ft.Container)
            and control.on_click
            and self._find_text(control, value)
        ):
            return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_clickable_container_containing_text(child, value)
            if found is not None:
                return found
        return None

    def _walk(self, control):
        yield control
        for child in getattr(control, "controls", []) or []:
            yield from self._walk(child)
        content = getattr(control, "content", None)
        if content is not None:
            yield from self._walk(content)

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

    def _find_scrollable_row(self, control, text):
        if (
            isinstance(control, ft.Row)
            and control.scroll == ft.ScrollMode.AUTO
            and any(self._find_text(child, text) for child in control.controls)
        ):
            return control
        children = list(getattr(control, "controls", []) or [])
        content = getattr(control, "content", None)
        if content is not None:
            children.append(content)
        for child in children:
            found = self._find_scrollable_row(child, text)
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

    def test_category_selector_scrolls_horizontally_and_changes_category(self):
        with self.session_factory() as db:
            db.add_all(
                [
                    categorias(nombre="Sección A", estado="ACTIVO"),
                    categorias(nombre="Sección B", estado="ACTIVO"),
                ]
            )
            db.commit()

        page = MagicMock(spec=ft.Page)
        with patch("views.nueva_venta_view.SessionLocal", self.session_factory):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
            )

        selector = self._find_scrollable_row(view, "Sección B")
        self.assertIsNotNone(selector)
        self.assertEqual(selector.height, 48)
        self.assertIsNone(selector.expand)
        categoria_b = next(
            control
            for control in selector.controls
            if self._find_text(control, "Sección B")
        )
        categoria_b.on_click(None)

        selector = self._find_scrollable_row(view, "Sección B")
        categoria_b = next(
            control
            for control in selector.controls
            if self._find_text(control, "Sección B")
        )
        self.assertEqual(categoria_b.bgcolor, "#454B60")

    def test_product_without_description_uses_compact_card(self):
        with self.session_factory() as db:
            category = categorias(nombre="Burgers", estado="ACTIVO")
            db.add(category)
            db.flush()
            db.add(
                productos(
                    nombre="Hamburguesa sencilla",
                    precio=8000,
                    stock=0,
                    descripcion=None,
                    id_categoria=category.id_categoria,
                    id_estado=None,
                )
            )
            db.add(
                productos(
                    nombre="Hamburguesa con descripción",
                    precio=10000,
                    stock=0,
                    descripcion="Con queso y cebolla",
                    id_categoria=category.id_categoria,
                    id_estado=None,
                )
            )
            db.commit()

        page = MagicMock(spec=ft.Page)
        with patch("views.nueva_venta_view.SessionLocal", self.session_factory):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
            )

        card = self._find_button_containing_text(view, "Hamburguesa sencilla")
        self.assertIsNotNone(card)
        self.assertEqual(card.height, 90)
        self.assertIsNone(self._find_text(card, ""))
        card_with_description = self._find_button_containing_text(
            view,
            "Hamburguesa con descripción",
        )
        self.assertIsNotNone(card_with_description)
        self.assertEqual(card_with_description.height, 125)

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

    def test_selecting_a_table_opens_sale_view_without_supplier_controls(self):
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
        self.assertIsNone(
            self._find_control(view, ft.TextField, "Celular del cliente")
        )
        self.assertIsNone(self._find_text(view, "COMPROBANTE POR WHATSAPP"))
        self.assertIsNone(self._find_button(view, "Enviar precuenta por WhatsApp"))
        self.assertIsNone(self._find_text(view, "Proveedores"))
        self.assertIsNone(self._find_text(view, "Cobro de proveedores: $0"))

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

    def test_equal_split_completes_for_existing_account(self):
        with self.session_factory() as db:
            producto = productos(nombre="Prueba", precio=10_000, stock=0)
            db.add(producto)
            db.commit()
            cuenta = guardar_cuenta_abierta(
                db,
                [
                    {
                        "id_producto": producto.id_producto,
                        "nombre": producto.nombre,
                        "precio": producto.precio,
                        "cantidad": 20,
                    }
                ],
                self.mesa_id,
            )
            cuenta_id = cuenta.id_cuenta

        page = MagicMock(spec=ft.Page)
        with patch("views.nueva_venta_view.SessionLocal", self.session_factory):
            view = nueva_venta_view(
                page=page,
                navbar=ft.Container(),
                usuario_actual=None,
                on_venta_completada=lambda: None,
                caja_actual=SimpleNamespace(id_caja=1),
                mesa_id=self.mesa_id,
                mesa_elegida=True,
                cuenta_id=cuenta_id,
                on_recargar_cuenta=MagicMock(),
            )
            self._find_button(view, "Dividir cuenta").on_click(None)
            opciones = page.show_dialog.call_args.args[0]
            opcion_iguales = self._find_clickable_container_containing_text(
                opciones,
                "Partes iguales",
            )
            self.assertIsNotNone(opcion_iguales)
            opcion_iguales.on_click(None)

            dialogo = page.show_dialog.call_args.args[0]
            field = next(
                control
                for control in self._walk(dialogo)
                if isinstance(control, ft.TextField)
            )
            field.value = "3"
            submit = next(
                control
                for control in dialogo.actions
                if getattr(
                    getattr(control, "content", None),
                    "value",
                    getattr(control, "content", None),
                )
                == "Dividir cuenta"
                and callable(getattr(control, "on_click", None))
            )
            submit.on_click(None)

        with self.session_factory() as db:
            partes = (
                db.query(subcuentas)
                .filter_by(id_cuenta=cuenta_id)
                .order_by(subcuentas.etiqueta)
                .all()
            )
        self.assertEqual([parte.total for parte in partes], [66_666, 66_666, 66_668])


if __name__ == "__main__":
    unittest.main()

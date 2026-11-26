import unittest
from unittest.mock import MagicMock

import flet as ft

from views.inicio import inicio_view


class InicioViewTests(unittest.TestCase):
    def _find_control(self, control, control_type, predicate):
        if isinstance(control, control_type) and predicate(control):
            return control
        content = getattr(control, "content", None)
        if content is not None:
            found = self._find_control(content, control_type, predicate)
            if found is not None:
                return found
        for child in getattr(control, "controls", []) or []:
            found = self._find_control(child, control_type, predicate)
            if found is not None:
                return found
        return None

    def test_successful_cash_open_refreshes_to_open_cash_view(self):
        page = MagicMock(spec=ft.Page)
        on_abrir_caja = MagicMock(
            return_value={"ok": True, "mensaje": "Caja abierta correctamente."}
        )
        on_refrescar = MagicMock()
        view = inicio_view(
            page,
            ft.Container(),
            on_abrir_caja=on_abrir_caja,
            on_refrescar=on_refrescar,
        )
        boton_abrir = self._find_control(
            view,
            ft.ElevatedButton,
            lambda control: control.content == "Iniciar caja",
        )

        self.assertIsNotNone(boton_abrir)
        boton_abrir.on_click(None)

        on_abrir_caja.assert_called_once_with("2.000.000")
        on_refrescar.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

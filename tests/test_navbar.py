import unittest

from views.navbar import construir_navbar


class NavbarTests(unittest.TestCase):
    def construir_navbar_prueba(self, contabilidad_visible):
        return construir_navbar(
            page=None,
            activo="inicio",
            mostrar_inicio=lambda: None,
            mostrar_venta=lambda: None,
            mostrar_historial=lambda: None,
            mostrar_menu=lambda: None,
            mostrar_inventario=lambda: None,
            mostrar_proveedores=lambda: None,
            mostrar_compras=lambda: None,
            mostrar_informes=lambda: None,
            mostrar_contabilidad=lambda: None,
            contabilidad_visible=contabilidad_visible,
        )

    def test_oculta_contabilidad_cuando_no_es_visible(self):
        navbar = self.construir_navbar_prueba(contabilidad_visible=False)
        etiquetas = [control.content.value for control in navbar.content.controls]

        self.assertNotIn("Contabilidad", etiquetas)

    def test_muestra_contabilidad_cuando_es_visible(self):
        navbar = self.construir_navbar_prueba(contabilidad_visible=True)
        etiquetas = [control.content.value for control in navbar.content.controls]

        self.assertIn("Contabilidad", etiquetas)


if __name__ == "__main__":
    unittest.main()

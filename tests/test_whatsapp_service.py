import json
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

from services.whatsapp_service import (
    ESTADO_ENVIADO,
    ESTADO_PENDIENTE,
    WhatsAppError,
    crear_url_wa_me,
    enviar_comprobante,
    generar_comprobante_pdf,
    generar_mensaje_comprobante,
    validar_numero_colombiano,
)


class WhatsAppServiceTests(unittest.TestCase):
    def test_valida_celular_colombiano_y_agrega_prefijo(self):
        self.assertEqual(validar_numero_colombiano("3001234567"), "+573001234567")
        self.assertEqual(
            validar_numero_colombiano("+57 300 123 4567"),
            "+573001234567",
        )
        self.assertEqual(
            validar_numero_colombiano("(300) 123-4567"),
            "+573001234567",
        )

    def test_rechaza_numero_que_no_es_celular_colombiano(self):
        for numero in ("2001234567", "300123456", "+57300123456", "5730012345678"):
            with self.subTest(numero=numero):
                with self.assertRaises(ValueError):
                    validar_numero_colombiano(numero)

    def test_mensaje_incluye_consecutivo_mesa_productos_pago_y_total(self):
        mensaje = generar_mensaje_comprobante(
            negocio="BurgerLand",
            consecutivo="123",
            fecha_hora=datetime(2026, 11, 4, 12, 0),
            mesa="Mesa 5",
            items=[
                {
                    "nombre": "Hamburguesa",
                    "cantidad": 2,
                    "precio": 10000,
                    "personalizacion": "sin cebolla",
                }
            ],
            subtotal=20000,
            total=20000,
            metodo_pago="NEQUI",
        )
        self.assertIn("Comprobante de venta", mensaje)
        self.assertIn("Consecutivo: 123", mensaje)
        self.assertIn("Mesa: Mesa 5", mensaje)
        self.assertIn("Hamburguesa x2: $20.000", mensaje)
        self.assertIn("Nota: sin cebolla", mensaje)
        self.assertIn("Subtotal: $20.000", mensaje)
        self.assertIn("Método de pago: NEQUI", mensaje)
        self.assertIn("¡Gracias por tu compra!", mensaje)
        self.assertNotIn("DIAN", mensaje)

    def test_mensaje_de_cuenta_abierta_indica_que_es_precuenta(self):
        mensaje = generar_mensaje_comprobante(
            negocio="BurgerLand",
            consecutivo="Cuenta abierta #7",
            fecha_hora=datetime(2026, 11, 4, 12, 0),
            mesa="Mesa 2",
            items=[{"nombre": "Hamburguesa", "cantidad": 1, "precio": 10000}],
            subtotal=10000,
            total=10000,
            metodo_pago="Pendiente",
            pendiente_pago=True,
        )
        self.assertIn("Estado: Pendiente de pago (precuenta)", mensaje)

    def test_pdf_del_comprobante_se_genera_con_cabecera_pdf(self):
        archivo = generar_comprobante_pdf(
            negocio="BurgerLand",
            consecutivo="123",
            fecha_hora=datetime(2026, 11, 4, 12, 0),
            mesa="Mesa 5",
            items=[
                {
                    "nombre": "Hamburguesa",
                    "cantidad": 1,
                    "precio": 12000,
                }
            ],
            subtotal=12000,
            total=12000,
            metodo_pago="EFECTIVO",
        )
        self.assertTrue(archivo.startswith(b"%PDF-"))

    def test_url_wa_me_codifica_el_mensaje_y_normaliza_el_numero(self):
        url = crear_url_wa_me("3001234567", "Hola BurgerLand\nTotal: $20.000")
        self.assertTrue(url.startswith("https://wa.me/573001234567?text="))
        self.assertIn("%0A", url)
        self.assertIn("%2420.000", url)

    def test_modo_simple_informa_que_no_puede_confirmar_entrega(self):
        with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "wa_me"}, clear=False):
            resultado = enviar_comprobante("3001234567", "Comprobante de venta")
        self.assertEqual(resultado.estado, ESTADO_PENDIENTE)
        self.assertIn("https://wa.me/573001234567?", resultado.url)

    def test_cloud_api_sin_credenciales_falla_explicito(self):
        with patch.dict(
            os.environ,
            {"WHATSAPP_PROVIDER": "cloud_api"},
            clear=True,
        ):
            with self.assertRaisesRegex(WhatsAppError, "WHATSAPP_ACCESS_TOKEN"):
                enviar_comprobante("3001234567", "Comprobante de venta")

    def test_cloud_api_subir_pdf_y_enviar_documento(self):
        respuestas = []
        for contenido in (
            b'{"id":"media-1"}',
            b'{"messages":[{"id":"wamid-1"}]}',
        ):
            respuesta = MagicMock()
            respuesta.__enter__.return_value.read.return_value = contenido
            respuestas.append(respuesta)

        with (
            patch.dict(
                os.environ,
                {
                    "WHATSAPP_PROVIDER": "cloud_api",
                    "WHATSAPP_ACCESS_TOKEN": "token-prueba",
                    "WHATSAPP_PHONE_NUMBER_ID": "phone-id-prueba",
                    "WHATSAPP_GRAPH_API_VERSION": "v99.0",
                },
                clear=True,
            ),
            patch("services.whatsapp_service.urlopen", side_effect=respuestas) as abrir,
        ):
            resultado = enviar_comprobante(
                "3001234567",
                "Comprobante de venta",
                b"%PDF-prueba",
                "comprobante-123.pdf",
            )

        self.assertEqual(resultado.estado, ESTADO_ENVIADO)
        self.assertEqual(resultado.message_id, "wamid-1")
        self.assertEqual(abrir.call_count, 2)
        request_media = abrir.call_args_list[0].args[0]
        request_message = abrir.call_args_list[1].args[0]
        self.assertIn(b"%PDF-prueba", request_media.data)
        self.assertEqual(
            request_media.get_header("Authorization"),
            "Bearer token-prueba",
        )
        self.assertEqual(
            request_message.get_header("Authorization"),
            "Bearer token-prueba",
        )
        self.assertEqual(
            json.loads(request_message.data)["document"]["id"],
            "media-1",
        )
        self.assertEqual(
            json.loads(request_message.data)["to"],
            "573001234567",
        )

    def test_rechaza_proveedor_no_configurado(self):
        with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "otro"}, clear=False):
            with self.assertRaisesRegex(WhatsAppError, "WHATSAPP_PROVIDER"):
                enviar_comprobante("3001234567", "Comprobante de venta")


if __name__ == "__main__":
    unittest.main()

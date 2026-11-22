import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.database import Base
from database.models import (
    cuentas_abiertas,
    detalle_ventas,
    inventario,
    items_cuenta,
    mesas,
    metodos_pago,
    movimiento_caja,
    productos,
    subcuentas,
    ventas,
)
from services.cuenta_service import (
    CuentaModificadaError,
    anular_cuenta_abierta,
    cobrar_cuenta_abierta,
    cobrar_subcuenta,
    dividir_cuenta_en_partes_iguales,
    dividir_cuenta_por_items,
    dividir_cuenta_por_valores,
    guardar_cuenta_abierta,
    listar_cuentas_abiertas,
    listar_subcuentas,
)
from services.whatsapp_service import actualizar_estado_envio_venta


class CuentaServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.mesa = mesas(numero=1, estado="LIBRE")
        self.metodo = metodos_pago(nombre="EFECTIVO")
        self.producto = productos(
            nombre="Hamburguesa",
            precio=10000,
            stock=0,
            descripcion="Prueba",
        )
        self.db.add_all([self.mesa, self.metodo, self.producto])
        self.db.commit()
        self.carrito = [
            {
                "id_producto": self.producto.id_producto,
                "nombre": "Hamburguesa",
                "precio": 10000,
                "cantidad": 2,
                "personalizacion": "sin cebolla",
                "agregado_en": datetime.datetime(2026, 11, 4, 10, 0),
            }
        ]

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def crear_cuenta(self):
        return guardar_cuenta_abierta(
            self.db,
            self.carrito,
            self.mesa.id_mesa,
            usuario_id=1,
        )

    def test_guardar_reabrir_cuenta_persiste_items_y_ocupa_mesa(self):
        cuenta = self.crear_cuenta()

        self.assertEqual(cuenta.estado, "ABIERTA")
        self.assertEqual(cuenta.total, 20000)
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "OCUPADA")
        item = (
            self.db.query(items_cuenta)
            .filter(items_cuenta.id_cuenta == cuenta.id_cuenta)
            .one()
        )
        self.assertEqual(item.nombre, "Hamburguesa")
        self.assertEqual(item.cantidad, 2)
        self.assertEqual(item.agregado_en, datetime.datetime(2026, 11, 4, 10, 0))
        self.assertEqual(listar_cuentas_abiertas(self.db)[0]["cantidad_items"], 2)

    def test_dos_cajeros_no_sobrescriben_la_version_anterior(self):
        cuenta = self.crear_cuenta()
        otra_sesion = self.Session()
        try:
            cuenta_stale = otra_sesion.get(cuentas_abiertas, cuenta.id_cuenta)
            carrito_actualizado = [dict(self.carrito[0], cantidad=3)]
            guardar_cuenta_abierta(
                self.db,
                carrito_actualizado,
                self.mesa.id_mesa,
                cuenta_id=cuenta.id_cuenta,
                version=cuenta.version,
            )
            with self.assertRaises(CuentaModificadaError):
                guardar_cuenta_abierta(
                    otra_sesion,
                    self.carrito,
                    self.mesa.id_mesa,
                    cuenta_id=cuenta.id_cuenta,
                    version=cuenta_stale.version,
                )
        finally:
            otra_sesion.close()

    def test_cobrar_cuenta_cierra_cuenta_y_libera_mesa(self):
        cuenta = self.crear_cuenta()

        venta = cobrar_cuenta_abierta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            self.metodo.id_metodos_pago,
            usuario_actual=None,
            caja_actual=type("CajaPrueba", (), {"id_caja": 1})(),
        )

        self.assertEqual(self.db.get(cuentas_abiertas, cuenta.id_cuenta).estado, "PAGADA")
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "LIBRE")
        self.assertEqual(venta.total, 20000)
        self.assertEqual(self.db.query(ventas).count(), 1)
        self.assertEqual(self.db.query(detalle_ventas).filter_by(id_venta=venta.id_venta).count(), 1)
        self.assertEqual(self.db.query(movimiento_caja).count(), 1)

    def test_numero_y_opcion_autoenvio_se_conservan_en_venta_cobrada(self):
        cuenta = guardar_cuenta_abierta(
            self.db,
            self.carrito,
            self.mesa.id_mesa,
            usuario_id=1,
            whatsapp_cliente="3001234567",
            whatsapp_en_confirmar=True,
        )

        venta = cobrar_cuenta_abierta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            self.metodo.id_metodos_pago,
            usuario_actual=None,
            caja_actual=type("CajaPrueba", (), {"id_caja": 1})(),
        )

        self.assertEqual(venta.whatsapp_cliente, "+573001234567")
        self.assertEqual(venta.whatsapp_estado_envio, "PENDIENTE")
        cuenta_actual = self.db.get(cuentas_abiertas, cuenta.id_cuenta)
        self.assertTrue(cuenta_actual.whatsapp_en_confirmar)

    def test_estado_y_error_de_whatsapp_se_guardan_en_la_venta(self):
        cuenta = self.crear_cuenta()
        venta = cobrar_cuenta_abierta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            self.metodo.id_metodos_pago,
            usuario_actual=None,
            caja_actual=type("CajaPrueba", (), {"id_caja": 1})(),
        )

        actualizar_estado_envio_venta(
            self.db,
            venta.id_venta,
            "ERROR",
            "Token no configurado",
        )

        venta_actualizada = self.db.get(ventas, venta.id_venta)
        self.assertEqual(venta_actualizada.whatsapp_estado_envio, "ERROR")
        self.assertEqual(venta_actualizada.whatsapp_error, "Token no configurado")

    def test_dividir_en_partes_iguales_asigna_residuo_a_la_ultima(self):
        self.carrito[0]["precio"] = 10001
        cuenta = self.crear_cuenta()

        subcuentas_creadas = dividir_cuenta_en_partes_iguales(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            3,
        )

        self.assertEqual(
            [subcuenta.total for subcuenta in subcuentas_creadas],
            [6667, 6667, 6668],
        )
        self.assertEqual(
            sum(subcuenta.total for subcuenta in subcuentas_creadas),
            cuenta.total,
        )
        self.assertEqual(self.db.get(cuentas_abiertas, cuenta.id_cuenta).modo_division, "IGUALES")

    def test_division_por_valor_personalizado_suma_el_total_y_redondea_cop(self):
        cuenta = self.crear_cuenta()

        subcuentas_creadas = dividir_cuenta_por_valores(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            ["10000.4", "9999.6"],
        )

        self.assertEqual([item.total for item in subcuentas_creadas], [10000, 10000])
        self.assertEqual(
            sum(item.total for item in subcuentas_creadas),
            cuenta.total,
        )
        self.assertEqual(
            self.db.get(cuentas_abiertas, cuenta.id_cuenta).modo_division,
            "VALORES",
        )

    def test_division_por_valor_rechaza_diferencia_y_valores_negativos(self):
        cuenta = self.crear_cuenta()

        with self.assertRaisesRegex(ValueError, "coincidir con el total"):
            dividir_cuenta_por_valores(
                self.db,
                cuenta.id_cuenta,
                cuenta.version,
                [10000, 9000],
            )
        with self.assertRaisesRegex(ValueError, "mayor que cero"):
            dividir_cuenta_por_valores(
                self.db,
                cuenta.id_cuenta,
                cuenta.version,
                [20001, -1],
            )

    def test_cobros_parciales_prorratean_costo_de_proveedores_sin_duplicarlo(self):
        proveedores = [
            {"id": 8, "nombre": "Proveedor A", "costo": 1000},
            {"id": 9, "nombre": "Proveedor B", "costo": 500},
        ]
        cuenta = guardar_cuenta_abierta(
            self.db,
            self.carrito,
            self.mesa.id_mesa,
            proveedores_seleccionados=proveedores,
            usuario_id=1,
        )
        subcuentas_creadas = dividir_cuenta_en_partes_iguales(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            3,
        )
        caja_prueba = type("CajaPrueba", (), {"id_caja": 1})()
        version_cuenta = cuenta.version

        for subcuenta in subcuentas_creadas:
            cobrar_subcuenta(
                self.db,
                cuenta.id_cuenta,
                version_cuenta,
                subcuenta.id_subcuenta,
                subcuenta.version,
                self.metodo.id_metodos_pago,
                None,
                caja_prueba,
            )
            version_cuenta += 1

        costo_total_ventas = sum(
            venta.costo_proveedor for venta in self.db.query(ventas).all()
        )
        self.assertEqual(costo_total_ventas, 1500)

    def test_pagar_subcuentas_iguales_descuenta_inventario_una_vez_y_libera_al_final(self):
        insumo = inventario(
            nombre="Carne",
            categoria="Carnes",
            unidad_medida="unidad",
            cantidad=5,
            stock_minimo=0,
            costo_unitario=1000,
            estado="ACTIVO",
        )
        self.db.add(insumo)
        self.db.flush()
        self.producto.id_inventario = insumo.id_inventario
        self.db.commit()
        cuenta = self.crear_cuenta()
        subcuentas_creadas = dividir_cuenta_en_partes_iguales(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            2,
        )
        caja_prueba = type("CajaPrueba", (), {"id_caja": 1})()

        venta_primera, cerrada_primera = cobrar_subcuenta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            subcuentas_creadas[0].id_subcuenta,
            subcuentas_creadas[0].version,
            self.metodo.id_metodos_pago,
            None,
            caja_prueba,
        )

        self.assertFalse(cerrada_primera)
        self.assertEqual(venta_primera.total, 10000)
        self.assertEqual(self.db.get(inventario, insumo.id_inventario).cantidad, 3)
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "OCUPADA")

        cuenta_refrescada = self.db.get(cuentas_abiertas, cuenta.id_cuenta)
        segunda = self.db.get(subcuentas, subcuentas_creadas[1].id_subcuenta)
        _, cerrada_final = cobrar_subcuenta(
            self.db,
            cuenta.id_cuenta,
            cuenta_refrescada.version,
            segunda.id_subcuenta,
            segunda.version,
            self.metodo.id_metodos_pago,
            None,
            caja_prueba,
        )

        self.assertTrue(cerrada_final)
        self.assertEqual(self.db.get(inventario, insumo.id_inventario).cantidad, 3)
        self.assertEqual(self.db.get(cuentas_abiertas, cuenta.id_cuenta).estado, "PAGADA")
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "LIBRE")
        self.assertEqual(self.db.query(ventas).count(), 2)
        self.assertEqual(self.db.query(movimiento_caja).count(), 2)

    def test_dividir_por_items_y_pagar_unidad_por_subcuenta(self):
        cuenta = self.crear_cuenta()
        subcuentas_creadas = dividir_cuenta_por_items(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            [[1, 1]],
        )
        asignaciones = listar_subcuentas(self.db, cuenta.id_cuenta)

        self.assertEqual([subcuenta.total for subcuenta in subcuentas_creadas], [10000, 10000])
        self.assertEqual(
            [registro["items"][0]["asignacion"].cantidad for registro in asignaciones],
            [1, 1],
        )

        primera_venta, cuenta_cerrada = cobrar_subcuenta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            subcuentas_creadas[0].id_subcuenta,
            subcuentas_creadas[0].version,
            self.metodo.id_metodos_pago,
            None,
            type("CajaPrueba", (), {"id_caja": 1})(),
            whatsapp_cliente="3001234567",
        )

        self.assertEqual(primera_venta.total, 10000)
        self.assertEqual(primera_venta.whatsapp_cliente, "+573001234567")
        self.assertFalse(cuenta_cerrada)
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "OCUPADA")

    def test_dividir_por_items_rechaza_unidades_sin_asignar(self):
        cuenta = self.crear_cuenta()

        with self.assertRaisesRegex(ValueError, "Distribuye las 2 unidades"):
            dividir_cuenta_por_items(
                self.db,
                cuenta.id_cuenta,
                cuenta.version,
                [[1, 0]],
            )

        cuenta_actual = self.db.get(cuentas_abiertas, cuenta.id_cuenta)
        self.assertIsNone(cuenta_actual.modo_division)

    def test_version_anterior_no_permite_cobrar_dos_veces_en_paralelo(self):
        cuenta = self.crear_cuenta()
        subcuentas_creadas = dividir_cuenta_en_partes_iguales(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            2,
        )
        version_cuenta = cuenta.version
        otra_sesion = self.Session()
        caja_prueba = type("CajaPrueba", (), {"id_caja": 1})()
        try:
            cobrar_subcuenta(
                otra_sesion,
                cuenta.id_cuenta,
                version_cuenta,
                subcuentas_creadas[0].id_subcuenta,
                subcuentas_creadas[0].version,
                self.metodo.id_metodos_pago,
                None,
                caja_prueba,
            )
            with self.assertRaises(CuentaModificadaError):
                cobrar_subcuenta(
                    self.db,
                    cuenta.id_cuenta,
                    version_cuenta,
                    subcuentas_creadas[1].id_subcuenta,
                    subcuentas_creadas[1].version,
                    self.metodo.id_metodos_pago,
                    None,
                    caja_prueba,
                )
        finally:
            otra_sesion.close()

    def test_no_anular_cuenta_si_ya_se_pago_una_subcuenta(self):
        cuenta = self.crear_cuenta()
        subcuentas_creadas = dividir_cuenta_en_partes_iguales(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            2,
        )
        cobrar_subcuenta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            subcuentas_creadas[0].id_subcuenta,
            subcuentas_creadas[0].version,
            self.metodo.id_metodos_pago,
            None,
            type("CajaPrueba", (), {"id_caja": 1})(),
        )

        cuenta_actual = self.db.get(cuentas_abiertas, cuenta.id_cuenta)
        with self.assertRaisesRegex(ValueError, "subcuentas pagadas"):
            anular_cuenta_abierta(
                self.db,
                cuenta.id_cuenta,
                cuenta_actual.version,
            )
        self.assertEqual(
            self.db.get(cuentas_abiertas, cuenta.id_cuenta).estado,
            "ABIERTA",
        )

    def test_cobrar_guarda_cambios_del_carrito_antes_de_cerrar(self):
        cuenta = self.crear_cuenta()
        carrito_actualizado = [dict(self.carrito[0], cantidad=3, precio=12000)]
        proveedores = [{"id": 9, "nombre": "Proveedor", "costo": 500}]

        venta = cobrar_cuenta_abierta(
            self.db,
            cuenta.id_cuenta,
            cuenta.version,
            self.metodo.id_metodos_pago,
            usuario_actual=None,
            caja_actual=type("CajaPrueba", (), {"id_caja": 1})(),
            carrito=carrito_actualizado,
            proveedores_seleccionados=proveedores,
        )

        cuenta_pagada = self.db.get(cuentas_abiertas, cuenta.id_cuenta)
        self.assertEqual(venta.total, 36000)
        self.assertEqual(cuenta_pagada.total, 36000)
        self.assertEqual(cuenta_pagada.proveedores_json, '[{"id": 9, "nombre": "Proveedor", "costo": 500}]')
        self.assertEqual(self.db.query(items_cuenta).filter_by(id_cuenta=cuenta.id_cuenta).one().cantidad, 3)

    def test_guardar_cuenta_mueve_mesa_y_actualiza_estados(self):
        cuenta = self.crear_cuenta()
        otra_mesa = mesas(numero=2, estado="LIBRE")
        self.db.add(otra_mesa)
        self.db.commit()

        cuenta_actualizada = guardar_cuenta_abierta(
            self.db,
            self.carrito,
            otra_mesa.id_mesa,
            cuenta_id=cuenta.id_cuenta,
            version=cuenta.version,
        )

        self.assertEqual(cuenta_actualizada.id_mesa, otra_mesa.id_mesa)
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "LIBRE")
        self.assertEqual(self.db.get(mesas, otra_mesa.id_mesa).estado, "OCUPADA")

    def test_anular_cuenta_libera_mesa_sin_crear_venta(self):
        cuenta = self.crear_cuenta()

        anular_cuenta_abierta(self.db, cuenta.id_cuenta, cuenta.version)

        self.assertEqual(self.db.get(cuentas_abiertas, cuenta.id_cuenta).estado, "ANULADA")
        self.assertEqual(self.db.get(mesas, self.mesa.id_mesa).estado, "LIBRE")
        self.assertEqual(self.db.query(ventas).count(), 0)

    def test_una_mesa_no_acepta_dos_cuentas_abiertas(self):
        self.crear_cuenta()
        with self.assertRaisesRegex(ValueError, "no está disponible"):
            guardar_cuenta_abierta(self.db, self.carrito, self.mesa.id_mesa)


if __name__ == "__main__":
    unittest.main()

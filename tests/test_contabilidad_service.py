import datetime as dt
import unittest

from create_db import init_db
from database.database import SessionLocal
from database.models import (
    caja,
    categorias_gasto,
    costo_producto,
    detalle_ventas,
    empleados,
    estados_caja,
    gastos,
    parametros_legales,
    productos,
    ventas,
)
from services.contabilidad_service import calcular_nomina_mensual, generar_cierre_contable


class ContabilidadServiceTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.db.query(caja).delete()
        self.db.query(ventas).delete()
        self.db.query(detalle_ventas).delete()
        self.db.query(costo_producto).delete()
        self.db.query(gastos).delete()
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_calcular_nomina_mensual_saldo_minimo_2026(self):
        parametros = self.db.query(parametros_legales).filter(parametros_legales.anio == 2026).first()
        empleado = empleados(
            nombre="Ana",
            cargo="Cajera",
            tipo_contrato="INDEFINIDO",
            salario_base=1750905,
            fecha_ingreso=dt.date(2026, 1, 1),
            activo=1,
        )
        self.db.add(empleado)
        self.db.commit()
        self.db.refresh(empleado)

        calculo = calcular_nomina_mensual(empleado.id_empleado, "2026-09", parametros)
        salario_base = 1750905.0
        auxilio = 249095.0
        salud = salario_base * 0.085
        pension = salario_base * 0.12
        arl = salario_base * 0.00522
        caja_comp = salario_base * 0.04
        cesantias = (salario_base + auxilio) * (1 / 12)
        intereses = cesantias * 0.12
        prima = (salario_base + auxilio) * (1 / 12)
        vacaciones = salario_base * (1 / 24)
        esperado = salario_base + auxilio + salud + pension + arl + caja_comp + cesantias + intereses + prima + vacaciones
        self.assertAlmostEqual(calculo.costo_total_empleador, esperado)

    def test_generar_cierre_contable_usa_ventas_y_costos(self):
        estado_abierta = self.db.query(estados_caja).filter(estados_caja.nombre == "ABIERTA").first()
        if estado_abierta is None:
            estado_abierta = estados_caja(nombre="ABIERTA")
            self.db.add(estado_abierta)
            self.db.commit()
            self.db.refresh(estado_abierta)

        estado_cerrada = self.db.query(estados_caja).filter(estados_caja.nombre == "CERRADA").first()
        if estado_cerrada is None:
            estado_cerrada = estados_caja(nombre="CERRADA")
            self.db.add(estado_cerrada)
            self.db.commit()
            self.db.refresh(estado_cerrada)

        caja_obj = caja(
            fecha_apertura=dt.datetime(2026, 9, 1, 8, 0, 0),
            fecha_cierre=dt.datetime(2026, 9, 1, 20, 0, 0),
            saldo_inicial=500000,
            saldo_final=500000,
            id_estado_caja=estado_cerrada.id_estado_caja,
            id_usuario=1,
        )
        self.db.add(caja_obj)
        self.db.commit()
        self.db.refresh(caja_obj)

        producto = self.db.query(productos).first()
        self.assertIsNotNone(producto)

        venta = ventas(
            fecha_hora=dt.datetime(2026, 9, 1, 12, 0, 0),
            total=135000,
            id_estado_ventas=1,
            id_caja=caja_obj.id_caja,
            id_usuario=1,
            id_metodos_pagos=1,
            costo_proveedor=20000,
        )
        self.db.add(venta)
        self.db.commit()
        self.db.refresh(venta)

        detalle = detalle_ventas(
            cantidad=2,
            precio_unitario=67500,
            subtotal=135000,
            id_venta=venta.id_venta,
            id_producto=producto.id_producto,
        )
        self.db.add(detalle)
        self.db.add(costo_producto(
            id_producto=producto.id_producto,
            costo_unitario=30000,
            fecha_actualizacion=dt.date(2026, 9, 1),
        ))
        self.db.commit()

        categoria = self.db.query(categorias_gasto).first()
        if categoria is None:
            categoria = categorias_gasto(nombre="Otros", tipo="VARIABLE")
            self.db.add(categoria)
            self.db.commit()
            self.db.refresh(categoria)

        self.db.add(gastos(fecha=dt.date(2026, 9, 1), id_categoria_gasto=categoria.id_categoria_gasto, descripcion="Servicio", valor=25000, id_usuario=1))
        self.db.commit()

        cierre = generar_cierre_contable(caja_obj.id_caja)
        self.assertEqual(cierre.ingresos_totales, 135000)
        self.assertEqual(cierre.costo_ventas, 60000)
        self.assertEqual(cierre.utilidad_bruta, 75000)
        self.assertEqual(cierre.gastos_del_dia, 25000)
        self.assertEqual(cierre.utilidad_operacional, 50000)


if __name__ == "__main__":
    unittest.main()
